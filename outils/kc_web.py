"""Le pont entre la page des MP et KipeeCraft, dans le navigateur.

Ce module tourne dans Pyodide, a l'interieur du Web Worker de `kc/travail.js`.
Il ne fait que traduire : la page envoie du JSON, on appelle le coeur de
kipeecraft-py tel quel, on rend du JSON. Aucun calcul n'est refait ici --
c'est tout l'interet de Pyodide : un seul code, celui qui reproduit
KipeeCraft 1.2a au centieme pres.

Range dans `kipeecraft.zip` par `outils/page-kc.py`.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path

from kipeecraft.core import audit as _audit
from kipeecraft.core.craft import Ingredient, Recipe, craft as _craft
from kipeecraft.core.enums import Color, Ecosystem, Grade, Origin, Part, Stat, Tier
from kipeecraft.core.evolver import Evolver, EvolverError, Settings, build_pools
from kipeecraft.core.jeweler import (Jeweler, JewelerError, JewelerSettings,
                                     shopping_list)
from kipeecraft.core.materials import MaterialDatabase, type_label
from kipeecraft.core.patterns import PlanBook
from kipeecraft.core.postcraft import (PostcraftError, PostcraftLibrary,
                                       filename_for, load_file)
from kipeecraft.formats import project as proj
from kipeecraft.formats import recipe as kc
from kipeecraft.formats.project import JEWEL_STATS

#: Ou le zip est deballe, dans le systeme de fichiers de Pyodide.
DONNEES = Path("/kc/kipeecraft/resources/defaults")
#: Les formules retouchees par le joueur, ecrites a part des d'origine.
RETOUCHES = Path("/kc/retouches")

database: MaterialDatabase | None = None
plans: PlanBook | None = None
postcraft: PostcraftLibrary | None = None
#: Demande d'arret de la recherche en cours, posee par un autre message.
arret = False


def _cle(part: Part, materiau) -> str:
    return part.value + "|" + materiau.legacy_key


def _materiau(part: Part, cle: str):
    m = database.by_legacy_key(part, cle)
    if m is None:
        raise ValueError(f"matériau inconnu : {cle}")
    return m


def demarrer(retouches_json: str) -> str:
    """Charge les donnees et rend tout ce que la page doit connaitre."""
    global database, plans, postcraft
    database = MaterialDatabase.load(DONNEES / "DB" / "Ryzom.json")
    plans = PlanBook.load()
    postcraft = PostcraftLibrary.load(DONNEES / "postcraft")
    for nom, texte in json.loads(retouches_json or "{}").items():
        try:
            _appliquer(nom, texte)
        except (PostcraftError, OSError):
            pass                 # une retouche illisible n'empeche pas le reste

    return json.dumps({
        "stats": {s.value: [s.label, s.short_label] for s in Stat},
        "pieces": {p.value: {"nom": p.label, "stats": [s.value for s in p.stats]}
                   for p in Part},
        "paliers": [[t.name, t.label] for t in Tier],
        "grades": {g.value: [g.label, g.short_label, g.legacy_name] for g in Grade},
        "ecos": {e.value: [e.label, e.legacy_name] for e in Ecosystem},
        "couleurs": {c.value: [c.label, c.name.lower()] for c in Color},
        "bijou": [s.value for s in JEWEL_STATS],
        "plans": [{
            "id": p.id, "nom": p.name, "palier": p.tier.name,
            "intitule": p.label, "complet": p.full_label,
            "categorie": p.category.label,
            "options": list(postcraft.options_of(p.id)) or [0],
            "pieces": [[pp.part.value, pp.quantity] for pp in p.parts],
            "stats": [s.value for s in p.stats],
        } for p in plans],
        "materiaux": {part.value: [{
            "k": m.legacy_key, "n": m.name, "t": m.type, "tl": type_label(m.type),
            "g": m.grade.value, "e": m.ecosystem.value, "c": m.color.value,
            "o": m.origin.value, "q0": m.min_quality, "q1": m.max_quality,
            "v": list(m.values), "i": m.ignored,
        } for m in database[part]] for part in Part},
        "resume": (f"{len(database)} matériaux · {len(plans)} plans · "
                   f"{len(postcraft)} jeux de formules"),
    }, ensure_ascii=False)


# ------------------------------------------------------------------ recettes

def _recette(d: dict) -> Recipe:
    """Une recette depuis la page : le plan, et par piece [[cle, nombre], ...]."""
    plan = plans[int(d["plan"])]
    recette = Recipe(plan=plan, option=int(d.get("option", 0)),
                     comment=d.get("commentaire", ""))
    for rang, pieces in enumerate(d["cases"]):
        part = plan.parts[rang].part
        recette.slots[rang] = [Ingredient(_materiau(part, cle), int(n))
                               for cle, n in pieces]
    return recette


def _vers_page(recette: Recipe) -> dict:
    return {"plan": recette.plan.id, "option": recette.option,
            "commentaire": recette.comment,
            "cases": [[[i.material.legacy_key, i.quantity] for i in case]
                      for case in recette.slots]}


def _nombres(valeurs: dict) -> dict:
    # JSON ne connait ni l'infini ni NaN : une formule qui divise par zero
    # ne doit pas casser tout l'envoi.
    return {s.value: (v if math.isfinite(v) else None) for s, v in valeurs.items()}


def calculer(demande: str) -> str:
    d = json.loads(demande)
    recette = _recette(d)
    formules = postcraft.get(recette.plan.id, recette.option)
    try:
        r = _craft(recette, formules, quality=int(d.get("qualite", 250)),
                   rite=bool(d.get("rite")), formula_quality=int(d.get("qformule", 0)))
    except PostcraftError as exc:
        r = _craft(recette, None, quality=int(d.get("qualite", 250)))
        d["erreur"] = str(exc)
    return json.dumps({
        "moyennes": _nombres(r.averages), "precraft": _nombres(r.precraft),
        "postcraft": _nombres(r.postcraft), "moyenne": r.average,
        "qualite": r.quality, "grade": r.grade.value if r.grade else None,
        "couleur": r.color.value if r.color else None, "cout": r.cost,
        "boost": r.boost, "perdu": r.wasted,
        "complete": recette.is_complete, "vide": recette.is_empty,
        "formules": formules is not None, "erreur": d.get("erreur"),
    })


def lire_kc(texte: str) -> str:
    try:
        return json.dumps({"recette": _vers_page(kc.loads(texte, database, plans))},
                          ensure_ascii=False)
    except kc.RecipeError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)


def ecrire_kc(demande: str) -> str:
    return kc.dumps(_recette(json.loads(demande)))


# ------------------------------------------------------------------ formules

def _appliquer(nom: str, texte: str) -> None:
    RETOUCHES.mkdir(parents=True, exist_ok=True)
    chemin = RETOUCHES / nom
    chemin.write_text(texte, encoding="cp1252", errors="replace")
    f = load_file(chemin)
    postcraft.entries[(f.pattern_id, f.option)] = f


def formules(plan_id: int, option: int) -> str:
    plan = plans[plan_id]
    f = postcraft.get(plan_id, option)
    origine = load_file(DONNEES / "postcraft" / f.path.name) if f and f.path else None
    return json.dumps({
        "fichier": f.path.name if f and f.path else
                   filename_for(plan_id, option, plan.name),
        "texte": f.to_text() if f else "",
        "origine": origine.to_text() if origine else "",
        "problemes": list(f.problems) if f else [],
    }, ensure_ascii=False)


def retoucher(nom: str, texte: str) -> str:
    """Applique une retouche ; rend les anomalies de lecture."""
    try:
        _appliquer(nom, texte)
    except PostcraftError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)
    f = load_file(RETOUCHES / nom)
    return json.dumps({"problemes": list(f.problems)}, ensure_ascii=False)


def retablir(nom: str) -> str:
    f = load_file(DONNEES / "postcraft" / nom)
    postcraft.entries[(f.pattern_id, f.option)] = f
    return "{}"


# ------------------------------------------------------------------ audit

def auditer() -> str:
    rapport = _audit.audit(database, plans, postcraft)
    return json.dumps({
        "resume": rapport.summary(),
        "examine": rapport.checked,
        "constats": [[f.severity.value, f.severity.label, f.category, f.subject,
                      f.message] for f in rapport],
    }, ensure_ascii=False)


# ------------------------------------------------------------------ bijouterie

def _projet(d: dict) -> proj.JewelerProject:
    return proj.build_jeweler(int(d["plan"]), _conditions(d), _filtres(d), _maitre(d),
                              min_quality=int(d.get("qmin", 0)) or -1,
                              use_ignored=bool(d.get("ecartes")),
                              jewel_races=tuple(d.get("races", ())))


def projet_vers_page(texte: str) -> str:
    """Un `.kcj` relu, dans la forme du formulaire de la page."""
    try:
        p = proj.loads(texte)
    except proj.ProjectError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)
    if not isinstance(p, proj.JewelerProject):
        return json.dumps({"erreur": "projet Armurerie, pas Bijouterie"},
                          ensure_ascii=False)
    return json.dumps({"projet": {
        "plan": p.pattern_id,
        "conditions": _conditions_vers_page(p.conditions),
        "filtres": _filtres_vers_page(p.filters),
        "maitre": _maitre_vers_page(p.master_filter),
        "qmin": max(0, p.min_quality), "ecartes": p.use_ignored,
        "races": list(p.jewel_races),
    }}, ensure_ascii=False)


def projet_kcj(demande: str) -> str:
    return proj.dumps(_projet(json.loads(demande)))


def arreter() -> None:
    global arret
    arret = True


async def _derouler(moteur, reglages, avancer) -> None:
    """La boucle de `run`, commune a l'Evolver et a la Bijouterie.

    `run` est d'un seul tenant : dans un worker, elle empecherait le message
    « arreter » d'arriver. On deroule donc ses tours ici, avec un `await`
    toutes les 150 ms -- la boucle est la meme, seule la respiration change.
    """
    global arret
    arret = False
    debut = time.monotonic()
    souffle = debut
    oisif = 0
    population = moteur._new_population()
    moteur._record(population[0])
    while not arret:
        if reglages.stop_when_satisfied and moteur.best and moteur.best.score.is_perfect:
            break
        ecoule = time.monotonic() - debut
        if reglages.time_limit and ecoule >= reglages.time_limit:
            break
        moteur._generation += 1
        population = moteur._next_population(population)
        if moteur._record(population[0]):
            oisif = 0
        else:
            oisif += 1
            if reglages.patience and oisif >= reglages.patience:
                oisif = 0
                moteur._restarts += 1
                population = moteur._new_population()
        if time.monotonic() - souffle >= 0.15:
            souffle = time.monotonic()
            meilleur = moteur.best
            avancer(json.dumps({"generation": moteur.generation, "ecoule": ecoule,
                                "etat": meilleur.score.describe() if meilleur else "…"},
                               ensure_ascii=False))
            await asyncio.sleep(0)


def _filtrer(pools, plan, ecartes_, permis, employer_ecartes):
    """Ce que la page ajoute aux filtres : les materiaux ecartes par le
    joueur, et le stock du hall quand on ne veut que lui."""
    ecartes = {tuple(x.split("|", 1)) for x in ecartes_}
    pieces = [pp.part for pp in plan.parts]
    pools = tuple(tuple(m for m in pool
                        if (employer_ecartes or (part.value, m.legacy_key) not in ecartes)
                        and (permis is None or m.legacy_key in permis))
                  for pool, part in zip(pools, pieces))
    vides = [p.label for p, pool in zip(pieces, pools) if not pool]
    if vides:
        raise EvolverError("aucun matériau ne passe les filtres pour " + ", ".join(vides))
    return pools


def _conditions(d: dict):
    return tuple(proj.Condition(
        stat=Stat(c["stat"]) if c.get("stat") else None,
        weight=int(c.get("priorite", 1)) if c.get("stat") else 0,
        operator=proj.Operator(int(c.get("op", 0))),
        value=float(c.get("valeur", 0))) for c in d.get("conditions", ()))


def _filtres(d: dict):
    return tuple(proj.MaterialFilter(**{k: int(f.get(k, 0)) for k in
                 ("grade", "ecosystem", "name", "type", "color", "origin")})
                 for f in d.get("filtres", ()))


def _maitre(d: dict):
    maitre = d.get("maitre", {})
    return proj.MasterFilter(
        harvested_grades=frozenset(maitre.get("fores", ())),
        looted_grades=frozenset(maitre.get("lootes", ())),
        ecosystems=frozenset(maitre.get("ecos", ())))


def _maitre_vers_page(m) -> dict:
    return {"fores": sorted(m.harvested_grades), "lootes": sorted(m.looted_grades),
            "ecos": sorted(m.ecosystems)}


def _filtres_vers_page(filtres) -> list:
    return [{k: getattr(f, k) for k in
             ("grade", "ecosystem", "name", "type", "color", "origin")} for f in filtres]


def _conditions_vers_page(conditions) -> list:
    return [{"stat": c.stat.value if c.stat else 0, "priorite": c.weight,
             "op": int(c.operator), "valeur": c.value} for c in conditions]


# ------------------------------------------------------------------ evolver

def _projet_evolver(d: dict) -> proj.EvolverProject:
    p = proj.build_evolver(int(d["plan"]), _conditions(d), _filtres(d), _maitre(d),
                           min_quality=int(d.get("qmin", 0)) or -1,
                           max_quality=int(d.get("qmax", 0)) or -1,
                           forced_color=int(d.get("couleur", 0)),
                           use_ignored=bool(d.get("ecartes")))
    # build_evolver ne l'ecrit pas ; la cle est celle de l'original.
    p.raw["CB_force_boost"] = str(int(bool(d.get("boost"))))
    return p


def projet_kce(demande: str) -> str:
    return proj.dumps(_projet_evolver(json.loads(demande)))


def kce_vers_page(texte: str) -> str:
    try:
        p = proj.loads(texte)
    except proj.ProjectError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)
    if not isinstance(p, proj.EvolverProject):
        return json.dumps({"erreur": "projet Bijouterie, pas Évolveur"}, ensure_ascii=False)
    return json.dumps({"projet": {
        "plan": p.pattern_id, "conditions": _conditions_vers_page(p.conditions),
        "filtres": _filtres_vers_page(p.filters), "maitre": _maitre_vers_page(p.master_filter),
        "qmin": max(0, p.min_quality), "qmax": max(0, p.max_quality),
        "couleur": p.forced_color, "ecartes": p.use_ignored, "boost": p.prefer_boost,
    }}, ensure_ascii=False)


async def evoluer(demande: str, avancer) -> str:
    """Cherche une recette qui tient les conditions (pourcentages de precraft)."""
    d = json.loads(demande)
    plan = plans[int(d["plan"])]
    projet = _projet_evolver(d)
    reglages = Settings.from_project(
        projet, plan, max_distinct=int(d.get("variete", 0)),
        time_limit=float(d.get("duree", 20)), stop_when_satisfied=bool(d.get("tot")))
    if not reglages.active_conditions:
        return json.dumps({"erreur": "aucune condition : ajoute au moins une caractéristique"})
    manquent = reglages.unreachable()
    if manquent:
        return json.dumps({"erreur": f"{plan.full_label} ne porte pas "
                           + ", ".join(c.stat.label for c in manquent)}, ensure_ascii=False)
    try:
        pools = build_pools(plan, database, filters=projet.filters,
                            master=projet.master_filter, use_ignored=projet.use_ignored,
                            min_quality=projet.min_quality, max_quality=projet.max_quality)
        pools = _filtrer(pools, plan, d.get("liste_ecartes", ()),
                         set(d["permis"]) if d.get("permis") is not None else None,
                         projet.use_ignored)
        moteur = Evolver(reglages, pools)
    except EvolverError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)

    await _derouler(moteur, reglages, avancer)
    solution = moteur.best
    if solution is None:
        return json.dumps({"erreur": "aucune recette trouvée"})
    recette = solution.recipe
    recette.comment = "Créée par l'Évolveur"
    try:
        r = _craft(recette, postcraft.get(plan.id, recette.option))
    except PostcraftError:
        r = _craft(recette, None)
    return json.dumps({
        "verdict": solution.score.describe(),
        "manque": [[c.stat.label, ecart] for c, ecart in solution.unmet(projet.conditions)],
        "generations": solution.generation,
        "recette": _vers_page(recette),
        "resultat": {"precraft": _nombres(r.precraft), "postcraft": _nombres(r.postcraft)},
        "kc": kc.dumps(recette),
    }, ensure_ascii=False)


async def bijouter(demande: str, avancer) -> str:
    """Cherche une parure dont les totaux tiennent les conditions."""
    d = json.loads(demande)
    plan = plans[int(d["plan"])]
    formules_ = postcraft.get(plan.id, 0)
    if formules_ is None:
        return json.dumps({"erreur": f"aucune formule de postcraft pour {plan.full_label}"})
    projet = _projet(d)
    reglages = JewelerSettings.from_project(
        projet, plan, formules_, count=int(d.get("nombre", 10)),
        max_distinct=int(d.get("variete", 0)),
        time_limit=float(d.get("duree", 30)),
        stop_when_satisfied=bool(d.get("tot")))
    if not reglages.active_conditions:
        return json.dumps({"erreur": "aucune condition : ajoute au moins une caractéristique"})
    manquent = reglages.unreachable()
    if manquent:
        return json.dumps({"erreur": f"{plan.full_label} ne produit pas "
                           + ", ".join(c.stat.label for c in manquent)})

    try:
        pools = build_pools(plan, database, filters=projet.filters,
                            master=projet.master_filter,
                            use_ignored=projet.use_ignored,
                            min_quality=projet.min_quality)
        pools = _filtrer(pools, plan, d.get("liste_ecartes", ()),
                         set(d["permis"]) if d.get("permis") is not None else None,
                         projet.use_ignored)
        moteur = Jeweler(reglages, pools)
    except (JewelerError, EvolverError) as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)

    await _derouler(moteur, reglages, avancer)
    parure = moteur.best
    if parure is None:
        return json.dumps({"erreur": "aucune parure trouvée"})
    conditions = projet.conditions
    return json.dumps({
        "verdict": parure.score.describe(),
        "manque": [[c.stat.label, ecart] for c, ecart in parure.unmet(conditions)],
        "distincts": parure.distinct_jewels(),
        "generations": parure.generation,
        "totaux": _nombres(parure.totals),
        "bijoux": [_vers_page(r) for r in parure.jewels],
        "valeurs": [_nombres(v) for v in parure.per_jewel],
        "races": list(parure.races),
        "courses": shopping_list(parure),
        "kc": [kc.dumps(r) for r in parure.jewels],
    }, ensure_ascii=False)
