"""Le pont entre la page xiom.be/zyroom et le code de ZyRoom-GTK.

Tourne dans Pyodide, dans le Web Worker de `zyroom/travail.js`. La page
recoit les flux de l'API (personnage directement, guilde par zyroom.php) et
les passe ici : la lecture, les noms, les categories, les volumes, les tris
sont ceux de l'application, sans copie. Seul ce que window.py fait au milieu
de son interface GTK -- l'infobulle, le filtre, la ligne d'etat -- est
reecrit, au plus pres, dans `entite()` et dans la page.

Range dans `zyroom.zip` par `outils/page-zyroom.py`.
"""
from __future__ import annotations

import io
import json
import os
import time
import unicodedata

from zyroom import (alerts, carte, enchantements, meteo, movements, outposts, partage,
                    roster, ryzom_api, skills as skills_mod, sorting, watch)
from zyroom.categorydb import CategoryDb
from zyroom.models import (CLASS_NAMES, COLOR_NAMES, ECOSYSTEM_NAMES, EQUIP_NAMES,
                           MAT_CATEGORY, MAT_SPEC, ItemInfo, ItemType, categorie_item,
                           item_sig)
from zyroom.movements import sans_parenthese
from zyroom.namedb import NameDb, nom_anglais
from zyroom.sheetdb import SheetDb

#: Ou le zip est deballe dans Pyodide.
RACINE = "/zr/zyroom"

noms = NameDb("/zr/names.json")
fiches = SheetDb()
categories = CategoryDb()

#: Les gouttes, comme specialites.SPECIALITES (module GTK, non importable ici).
SPECIALITES = (
    ("hp_buff", "Vie", "#e2696a"),
    ("sap_buff", "Sève", "#4caf50"),
    ("sta_buff", "Endurance", "#a97fd0"),
    ("focus_buff", "Concentration", "#4a90d9"),
)

#: Les cles de tri, comme window._SORT_KEYS (l'index est celui du menu).
TRIS = {
    1: lambda it, nom: sorting.sort_key(it, _norm(nom), categories.categories),
    2: lambda it, nom: int(it.ecosystem),
    3: lambda it, nom: int(it.item_class),
    4: lambda it, nom: it.quality,
    5: lambda it, nom: it.volume,
    6: lambda it, nom: it.stack,
    7: lambda it, nom: it.price,
    8: lambda it, nom: _norm(nom),
}


def _norm(texte: str) -> str:
    """Comme ui_commun._norm : minuscule sans accents."""
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def demarrer() -> str:
    noms.load_cache()
    fiches.load(f"{RACINE}/data/sheetid.csv")
    categories.load(f"{RACINE}/data/category.csv")
    return json.dumps({
        "noms": len(noms._map), "classes": CLASS_NAMES, "ecosystemes": ECOSYSTEM_NAMES,
        "equipements": EQUIP_NAMES, "specialites": [[l, c] for _a, l, c in SPECIALITES],
    }, ensure_ascii=False)


def _infobulle(it, nom: str) -> list[str]:
    """Comme window._item_tooltip, sans la surveillance (pas encore en ligne)."""
    lignes = [nom]
    if it.quality:
        lignes.append(f"Qualité : {it.quality}")
    if it.stack:
        lignes.append(f"Quantité : {it.stack}")
    if it.item_type == ItemType.EQUIPMENT and it.hp:
        lignes.append(f"Durabilité : {it.hp} / {it.hp_max}" if it.hp_max
                      else f"Durabilité : {it.hp}")
    if it.volume:
        lignes.append(f"Volume : {it.volume:.2f}")
    if it.price:
        lignes.append(f"Prix : {it.price:,.0f} dappers".replace(",", " "))
    if it.continent:
        lignes.append(f"Continent : {it.continent}")
    if it.locked:
        lignes.append("🔒 Protégé")
    return lignes


def _objet(it) -> dict:
    nom = noms.name(it.sheet)
    bonus = [[libelle, getattr(it, attribut), couleur]
             for attribut, libelle, couleur in SPECIALITES if getattr(it, attribut, 0)]
    sort = enchantements.resume(it, noms.name)
    enchant = ""
    if sort:
        enchant = f"Enchantement : {sort}"
        if it.sap_charges:
            enchant += f"\nCharges de sève : {it.sap_charges}"
        if it.enchant_cost:
            enchant += f" (coût {abs(it.enchant_cost)})"
    brique = enchantements.brique_icone(it)
    return {
        "fiche": it.sheet, "nom": nom, "id": it.item_id, "sig": item_sig(it), "hp": it.hp, "icone": ryzom_api.item_icon_url(it),
        "cle": _norm(f"{nom} {it.sheet} {nom_anglais(it.sheet)}"),
        "categorie": categorie_item(it, nom),
        "q": it.quality, "n": it.stack, "vol": it.volume, "prix": it.price,
        "eco": int(it.ecosystem), "classe": int(it.item_class),
        "equip": int(it.equip) if it.item_type == ItemType.EQUIPMENT else -1,
        "cadenas": it.locked, "vente": it.expires > 0,
        "bonus": bonus, "bulle": _infobulle(it, nom), "enchant": enchant,
        "sort": ryzom_api.brique_icon_url(brique) if brique else "",
    }


def _ordres(items: list) -> dict:
    """Pour chaque tri, l'ordre des objets, croissant et decroissant.

    Les deux sont calcules ici plutot que l'un renverse dans la page : un tri
    decroissant de Python garde l'ordre d'origine des egaux, ce que renverser
    l'ordre croissant ne ferait pas.
    """
    nommes = [(i, it, noms.name(it.sheet)) for i, it in enumerate(items)]
    ordres = {}
    for rang, cle in TRIS.items():
        for sens, inverse in (("asc", False), ("desc", True)):
            ordres[f"{rang}{sens}"] = [i for i, _it, _n in
                                       sorted(nommes, key=lambda x: cle(x[1], x[2]),
                                              reverse=inverse)]
    return ordres


#: Les entites lues, pour la fiche detaillee et les alertes.
lues: dict[tuple, object] = {}


def entite(xml: str, sorte: str) -> str:
    """Un flux de l'API, lu par ryzom_api, pret a afficher."""
    lire = ryzom_api.parse_character if sorte == "character" else ryzom_api.parse_guild
    try:
        ent = lire(xml.encode("utf-8"), fiches.name)
    except ryzom_api.ApiError as exc:
        return json.dumps({"erreur": str(exc)}, ensure_ascii=False)
    lues[(ent.kind, ent.entity_id)] = ent
    return json.dumps({
        "sorte": ent.kind, "id": ent.entity_id, "nom": ent.name, "guilde": ent.guild,
        "argent": ent.money, "motd": ent.motd, "portrait": ent.portrait_url,
        "connexion": ent.lastlogin, "deconnexion": ent.lastlogout,
        "calcul": ent.created,
        "betes": [{
            "nom": b.nom, "etiquette": b.etiquette, "zig": b.zig, "dehors": b.dehors,
            "statut": b.statut, "satiete": b.satiete,
            "pixel": carte.pixel(b.x, b.y) if b.dehors else None,
        } for b in ent.betes],
        "pixel": carte.pixel(ent.x, ent.y) if (ent.x or ent.y) else None,
        "competences": _competences(ent.skills),
        "points": {k: list(v) for k, v in ent.skill_points.items()},
        "effectif": _effectif(ent.members),
        "nb_membres": len(ent.members),
        "contenants": [{
            "cle": inv.key, "nom": sans_parenthese(inv.label), "capacite": inv.capacity,
            "volume": inv.total_volume, "objets": [_objet(it) for it in inv.items],
            "ordres": _ordres(inv.items),
        } for inv in ent.inventories],
    }, ensure_ascii=False)


def _competences(liste) -> list:
    """L'arbre, comme page_skills : ordre, profondeur, niveau atteint, fini."""
    if not liste:
        return []
    arbre = skills_mod.build_tree(liste)
    finies = skills_mod.finished(arbre)
    return [{
        "code": n.skill.code, "nom": noms.name(n.skill.code), "parent": n.parent,
        "racine": n.root, "profondeur": n.depth, "enfants": n.has_children,
        "avance": n.skill.progress, "fini": n.skill.code in finies,
        "niveau": (skills_mod.niveau_atteint(arbre, n.skill.code)
                   if n.has_children else n.skill.level),
    } for n in arbre]


def _effectif(membres) -> list:
    """Les noms par grade, chef d'abord (page_roster._remplir_effectif_roster)."""
    tries = sorted(membres, key=lambda m: (roster.rang_grade(m[1]), m[0].lower()))
    groupes: dict[str, list] = {}
    for nom, grade, *_reste in tries:
        groupes.setdefault(grade, []).append(nom)
    return [[roster.nom_grade(g), noms_] for g, noms_ in groupes.items()]


def registre(gid: str, texte: str) -> str:
    """Les arrivees, departs et changements de grade publies par le releve."""
    os.makedirs("/tmp/registre", exist_ok=True)
    with open(f"/tmp/registre/roster-{gid}.jsonl", "w", encoding="utf-8") as fh:
        fh.write(texte)
    out = []
    for c in roster.RosterStore("/tmp/registre", gid).history():
        sens = ("grade-" + ("haut" if c.promotion else "bas")) if c.kind == "grade" else c.kind
        out.append({"at": c.at, "sens": sens, "texte": roster.decrire(c)})
    return json.dumps({"lignes": out, "jours": roster.RETENTION_JOURS}, ensure_ascii=False)


def saison(xml: str) -> str:
    return json.dumps(ryzom_api.parse_time(xml.encode("utf-8")), ensure_ascii=False)


# ------------------------------------------------------------ le journal
#
# Le journal d'un personnage se tient dans le navigateur : a chaque relevé,
# on compare l'instantane au precedent, comme window._relever_en_silence.
# Celui du hall est celui que le releve publie (guild-<id>.jsonl) : il voit
# passer la guilde tous les quarts d'heure, la page ne le ferait pas mieux.

# **L'heure du navigateur, pas celle de Pyodide.** Movement.when passe par
# time.localtime, qui vaut UTC dans Pyodide : le journal aurait ete decale de
# deux heures l'ete. La date de JavaScript connait le fuseau du joueur, ete
# et hiver compris.
try:
    from js import Date

    def _quand(mv) -> str:
        d = Date.new(mv.ts * 1000)
        return (f"{int(d.getFullYear())}-{int(d.getMonth()) + 1:02d}-{int(d.getDate()):02d} "
                f"{int(d.getHours()):02d}:{int(d.getMinutes()):02d}")

    movements.Movement.when = property(_quand)
except ImportError:
    pass            # hors du navigateur (essais) : l'heure locale suffit

#: Comme window._LOG_JOURS, _LOG_MINIMUM et _LOG_MAX.
JOURS, MINIMUM, MAXIMUM = 30, 400, 8000

#: Les journaux lus, par entite : la recherche refiltre sans tout relire.
journaux: dict[str, list] = {}


def releve(xml: str, sorte: str, avant: str) -> str:
    """Les mouvements depuis le releve precedent, et le nouvel instantane."""
    lire = ryzom_api.parse_character if sorte == "character" else ryzom_api.parse_guild
    ent = lire(xml.encode("utf-8"), fiches.name)
    apres = alerts.build_snapshot(ent)
    precedent = json.loads(avant) if avant else {}
    nouveaux = movements.diff(precedent, apres, ent) if precedent else []
    return json.dumps({"instantane": apres,
                       "lignes": [json.dumps(m.as_dict(), ensure_ascii=False) for m in nouveaux]},
                      ensure_ascii=False)


def charger_journal(cle: str, texte: str, depuis: float) -> int:
    """Lit un journal (.jsonl), du plus recent au plus ancien.

    `depuis` : ce que « Vider » a efface dans ce navigateur -- on ne garde
    que ce qui est plus recent.
    """
    out = []
    for ligne in texte.splitlines():
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            mv = movements.lire_etranger(json.loads(ligne))
        except Exception:
            continue
        if mv.ts > depuis:
            out.append(mv)
    out.sort(key=lambda m: -m.ts)
    journaux[cle] = out
    return len(out)


def _filtre(cle: str, cherche: str, mode: int) -> list:
    """Comme window._filtered_log."""
    qualite = movements.qualite_cherchee(cherche)
    aiguille = "" if qualite is not None else _norm(cherche.strip())
    out = []
    for mv in journaux.get(cle, []):
        if mode == 1 and mv.delta <= 0:
            continue
        if mode == 2 and mv.delta >= 0:
            continue
        if qualite is not None and mv.quality != qualite:
            continue
        if aiguille and aiguille not in _norm(f"{noms.name(mv.sheet)} {mv.sheet} {mv.inv_label}"):
            continue
        out.append(mv)
    return out


def vue_journal(cle: str, cherche: str, mode: int) -> str:
    """Les lignes a montrer et la ligne d'etat, comme window._refresh_log."""
    tous = journaux.get(cle, [])
    retenus = _filtre(cle, cherche, mode)
    montrees = movements.lignes_recentes(retenus, JOURS, MINIMUM, MAXIMUM)
    lignes, jour_precedent = [], None
    for mv in retenus[:montrees]:
        argent = mv.inv_key == movements.MONEY_KEY
        jour = mv.when[:10]
        lignes.append({
            "quand": mv.when, "contenant": sans_parenthese(mv.inv_label),
            "delta": mv.delta,
            "quantite": f"{mv.delta:+,}".replace(",", " ") if argent else f"{mv.delta:+d}",
            "nom": "Dappers" if argent else noms.name(mv.sheet),
            "q": mv.quality, "argent": argent,
            "icone": "" if argent else ryzom_api.item_icon_url(
                ItemInfo(sheet=mv.sheet, quality=mv.quality)),
            "jour": jour_precedent is not None and jour != jour_precedent,
            "texte": movements.describe(mv, noms.name),
        })
        jour_precedent = jour
    if not tous:
        etat = ("Aucun mouvement enregistré. Le journal se remplit à chaque "
                "synchronisation où quelque chose a bougé.")
    elif len(retenus) > montrees:
        etat = (f"{montrees} lignes affichées sur {len(retenus)} retenues "
                f"({len(tous)} au journal) — affinez la recherche.")
    else:
        etat = f"{len(retenus)} lignes sur {len(tous)} au journal"
    return json.dumps({"lignes": lignes, "etat": etat}, ensure_ascii=False)


def copier_journal(cle: str, cherche: str, mode: int) -> str:
    """Le texte du bouton « Copier » : toutes les lignes retenues."""
    return "\n".join(movements.describe(mv, noms.name) for mv in _filtre(cle, cherche, mode))


# ------------------------------------------------------------ avant-postes
#
# L'annuaire public des guildes (guilds.php) dit qui tient quoi. Le journal
# des prises, lui, se deduit de deux releves : celui de ce navigateur, tenu
# dans ses fichiers (outposts-etat.json, outposts.jsonl, outposts-vu.json),
# que la page garde et nous rend a chaque appel.

PEUPLES = (("fyros", "Fyros"), ("matis", "Matis"), ("tryker", "Tryker"), ("zorai", "Zoraï"))
DOSSIER_OP = "/tmp/avant-postes"
annuaire = {"carte": [], "emblemes": {}, "premier": False}


def _poser(fichiers: str) -> outposts.OutpostStore:
    os.makedirs(DOSSIER_OP, exist_ok=True)
    for nom in os.listdir(DOSSIER_OP):
        os.remove(os.path.join(DOSSIER_OP, nom))
    for nom, texte in json.loads(fichiers or "{}").items():
        with open(os.path.join(DOSSIER_OP, os.path.basename(nom)), "w", encoding="utf-8") as fh:
            fh.write(texte)
    return outposts.OutpostStore(DOSSIER_OP)


def _relever_fichiers() -> dict:
    out = {}
    for nom in os.listdir(DOSSIER_OP):
        with open(os.path.join(DOSSIER_OP, nom), encoding="utf-8") as fh:
            out[nom] = fh.read()
    return out


def charger_annuaire(xml: str, fichiers: str) -> str:
    """Lit l'annuaire et journalise les changements de main."""
    store = _poser(fichiers)
    carte_, emblemes = outposts.parse_annuaire(xml.encode("utf-8"))
    annuaire["premier"] = store.jamais_releve()
    store.record(carte_)
    annuaire["carte"], annuaire["emblemes"] = carte_, emblemes
    return json.dumps({"fichiers": _relever_fichiers()}, ensure_ascii=False)


def _embleme(icone: str) -> str:
    return ryzom_api.guild_icon_url(icone, "s") if icone else ""


def _bulle(c) -> str:
    """Comme page_outposts._infobulle_changement (l'heure est mise par la page)."""
    if c.taken:
        return f"Pris par {c.to}"
    if c.lost:
        return f"Perdu par {c.frm}"
    return f"{c.frm} ▸ {c.to}"


def vue_avant_postes(fichiers: str, ma_guilde: str, journal: bool) -> str:
    """La carte par peuple, ou le journal des prises (page_outposts)."""
    store = _poser(fichiers)
    carte_ = annuaire["carte"]
    out = {"journal": journal, "charge": bool(carte_)}
    if journal:
        histoire = store.history()
        out["premier"] = annuaire["premier"]
        out["prises"] = [{
            "at": c.at, "nom": noms.name(f"{c.outpost}.outpost"),
            "de": c.frm, "vers": c.to,
            "embleme_de": _embleme(annuaire["emblemes"].get(c.frm, "")),
            "embleme_vers": _embleme(annuaire["emblemes"].get(c.to, "")),
        } for c in histoire]
        store.marquer_lu()
    else:
        recents = store.recents()
        miens = sum(1 for o in carte_ if o.guild == ma_guilde)
        entete = f"{len(carte_)} avant-postes tenus sur Atys"
        if ma_guilde:
            entete += f", dont {miens} à {ma_guilde}"
        out["entete"] = entete + "."
        out["pastilles"] = bool(recents)
        out["peuples"] = []
        for code, nom in PEUPLES:
            siens = sorted((o for o in carte_ if o.people == code),
                           key=lambda o: (-o.level, noms.name(o.name_key)))
            if siens:
                out["peuples"].append([nom, [{
                    "nom": noms.name(o.name_key), "niveau": o.level, "guilde": o.guild,
                    "embleme": _embleme(o.icon), "mien": o.guild == ma_guilde,
                    "change": ({"at": recents[o.code].at, "texte": _bulle(recents[o.code])}
                               if o.code in recents else None),
                } for o in siens]])
        connus = {c for c, _n in PEUPLES}
        out["orphelins"] = ", ".join(f"{o.code} ({o.guild})" for o in carte_
                                      if o.people not in connus)
    out["non_lus"] = store.non_lus(ma_guilde)
    out["fichiers"] = _relever_fichiers()
    return json.dumps(out, ensure_ascii=False)


# ------------------------------------------------------------ meteo et forage
#
# Comme ZyRoom-Qt, l'application des joueurs : la courbe, ce qui sort et les
# gisements, d'apres le releve du forage que la guilde publie (forage.json)
# -- jamais le bouton du releve, jamais xiom.be/forage, ni les MP a verifier.

releve_meteo = [None]
#: La qualite des gisements telle que la page la passe (page_gisements._QUALITE).
QUALITE_GISEMENT = {"supreme": meteo.SUPREME, "excellent": meteo.EXCELLENTE}


class _Reponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _tables_publiees(texte: str):
    """partage.tables_du_forage, sur le texte que la page a deja telecharge."""
    ancien = partage.urllib.request.urlopen
    partage.urllib.request.urlopen = lambda *_a, **_k: _Reponse(texte.encode("utf-8"))
    try:
        return partage.tables_du_forage()
    finally:
        partage.urllib.request.urlopen = ancien


def meteo_continents() -> str:
    """Les continents a demander a weather.php, comme page_meteo._load_meteo."""
    return ",".join(sorted(set(meteo.CONTINENT_DE_ZONE.values())))


def meteo_charger(meteo_json: str, temps_xml: str, forage_json: str) -> str:
    """Le releve de l'API, recale comme page_meteo._load_meteo."""
    releve = meteo.parse_weather(meteo_json)
    try:
        t = ryzom_api.parse_time(temps_xml.encode("utf-8"))
        saison, dans = t["season_index"], t["minutes_to_next"]
    except Exception:
        saison, dans = -1, -1.0
    releve_meteo[0] = meteo.MeteoAtys(releve.cycle_courant, releve.heure_atys, saison,
                                      releve.continents, releve.pris_a, saison_dans=dans)
    if forage_json:
        tables = _tables_publiees(forage_json)
        if tables is not None:
            meteo.poser_tables(tables)
    return "{}"


def _symbole(famille: str) -> str:
    """Comme meteo.symbole, mais l'image est servie par la page (symboles/)."""
    from zyroom import armory
    icone = armory.SYMBOLES.get(famille)
    return f"symboles/{icone}.png" if icone else ""


def meteo_vue() -> str:
    """L'entete, la courbe et ce qui sort maintenant (page_meteo._refresh_meteo)."""
    base = releve_meteo[0]
    if base is None:
        return json.dumps({"vide": True})
    r = base.a_present()
    out = {"heure_atys": r.heure_atys, "cycles": [[c.cycle, c.value] for c in r.cycles_des_primes()],
           "seuils": list(meteo.SEUILS), "transition": meteo.TRANSITION_HEURES,
           "heures_par_cycle": meteo.HEURES_PAR_CYCLE,
           "minutes_par_heure": meteo.MINUTES_PAR_HEURE_ATYS}
    # Recharger quand la prevision ne remplit plus la courbe (_meteo_tick).
    out["recharger"] = meteo.heures_restantes(r) < 40.0 * 0.85 + meteo.HEURES_PAR_CYCLE
    m = r.maintenant()
    if m is not None:
        suite = [c for c in r.cycles_des_primes() if c.cycle > r.cycle_courant]
        prochain = next((c for c in suite if c.condition != m.condition), None)
        taux = r.humidite()
        if taux is None:
            taux = m.value
        out["entete"] = {
            "taux": f"{meteo.condition_de(taux)} {int(taux * 100)} %",
            "pendant": meteo.duree(r.minutes_avant(prochain.cycle)) if prochain else "",
            "decor": f"{meteo.texte_meteo(m.text).lower()}, {meteo.nom_saison(r.saison).lower()}, "
                     f"{r.heure_du_jour} h sur Atys, {'nuit' if r.nuit else 'jour'}",
        }
        zones = []
        for zone in meteo.ZONES:
            blocs = []
            for qualite, groupes in meteo.sorties_de(r.saison, zone, m.condition):
                nom = meteo.QUALITE_GISEMENT.get(qualite, "")
                blocs.append({
                    "mot": f"{meteo.mot_qualite(qualite)} ({sum(len(x) for x in groupes.values())})",
                    "a_confirmer": qualite == meteo.A_CONFIRMER,
                    "familles": [[famille, _symbole(famille), [
                        [mat, f"{nom}|{famille}|{mat}"
                         if meteo.positions_des_primes(qualite, famille, mat) else ""]
                        for mat in mats]] for famille, mats in sorted(groupes.items())],
                })
            zones.append([zone, blocs])
        out["zones"] = zones
    return json.dumps(out, ensure_ascii=False)


def gisement(adresse: str) -> str:
    """La carte d'une matiere (page_gisements._montre_gisement et _textes_carte)."""
    qualite, famille, matiere = adresse.split("|", 2)
    attendue = QUALITE_GISEMENT.get(qualite)
    points = meteo.positions_des_primes(attendue, famille, matiere)
    lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
    base = releve_meteo[0]
    r = base.a_present() if base is not None else None
    m = r.maintenant() if r is not None else None
    actifs = None
    maintenant = apres = ""
    if m is not None and any(lieu in meteo.ZONES for lieu in lieux):
        actifs = {lieu for lieu in lieux if lieu not in meteo.ZONES
                  or meteo.sort_en(attendue, lieu, famille, matiere, r.saison, m.condition)}
        dehors = [lieu for lieu in lieux if lieu not in actifs]
        sortent = len(lieux) - len(dehors)
        valeurs = {"condition": meteo.texte_condition(m.condition),
                   "taux": round(m.value * 100), "sortent": sortent, "total": len(lieux)}
        maintenant = (("En ce moment — %(condition)s, %(taux)d %% : aucun des %(total)d gisements ne sort."
                       if not sortent else
                       "En ce moment — %(condition)s, %(taux)d %% : un gisement sur %(total)d."
                       if sortent == 1 else
                       "En ce moment — %(condition)s, %(taux)d %% : %(sortent)d gisements sur %(total)d.")
                      % valeurs + ("  Les autres sont en gris." if dehors and sortent else ""))
        if not sortent:
            minutes = None
            zones = [lieu for lieu in lieux if lieu in meteo.ZONES]
            for c in r.cycles_des_primes():
                if c.cycle > r.cycle_courant and any(
                        meteo.sort_en(attendue, lieu, famille, matiere, r.saison, c.condition)
                        for lieu in zones):
                    minutes = r.minutes_avant(c.cycle)
                    break
            apres = (f"Prochaine fois dans {meteo.duree(minutes)} — {meteo.moment_du_changement(minutes)}."
                     if minutes is not None else
                     "Pas avant six heures — au-delà, le jeu ne dit plus le temps qu'il fera.")
    return json.dumps({
        "titre": f"{matiere} — {famille}", "mot": meteo.mot_qualite(attendue),
        "maintenant": maintenant, "apres": apres,
        "lieux": [[lieu, actifs is None or lieu in actifs] for lieu in lieux],
        "points": [[p[0], p[1], lieu, actifs is None or lieu in actifs]
                   for x, y, lieu in points if (p := carte.pixel(x, y)) is not None],
        "nombre": len(points),
    }, ensure_ascii=False)


# ------------------------------------------------------------ fiche detaillee

def _temps_restant(expire: int) -> str:
    """Comme detail._time_left."""
    reste = expire - time.time()
    if reste <= 0:
        return "expiré"
    return f"{int(reste // 3600)} h {int((reste % 3600) // 60)} min"


def fiche(sorte: str, ident: str, ci: int, oi: int) -> str:
    """Les sections de detail.build_detail, en donnees plutot qu'en widgets."""
    it = lues[(sorte, ident)].inventories[ci].items[oi]
    if it.item_type in (ItemType.NATURAL_MAT, ItemType.ANIMAL_MAT):
        categories.fill(it)
    sections = []

    def section(titre, lignes, toujours=False):
        lignes = [[k, str(v)] for k, v in lignes if v is not None and v != ""]
        if lignes or toujours:
            sections.append([titre, lignes])

    nom = noms.name(it.sheet)
    section("Général", [
        ("Nom", nom if nom != it.sheet else ""), ("Fiche", it.sheet), ("Identifiant", it.item_id),
        ("Qualité", it.quality or ""), ("Quantité", it.stack or ""),
        ("Classe", CLASS_NAMES[int(it.item_class)] if it.item_class != it.item_class.UNKNOWN else ""),
        ("Écosystème", ECOSYSTEM_NAMES[int(it.ecosystem)] if it.ecosystem != it.ecosystem.UNKNOWN else ""),
        ("Volume", f"{it.volume:.2f}" if it.volume else ""), ("Poids", f"{it.weight:.2f}" if it.weight else ""),
        ("Durabilité", it.hp if it.item_type == ItemType.EQUIPMENT and it.hp else ""),
        ("Protégé", "oui" if it.locked else ""),
    ], toujours=True)
    section("Combat", [("Dégâts", it.c_dmg or ""), ("Vitesse", it.c_speed or ""),
                       ("Portée", it.c_range or ""), ("Mod. esquive", it.c_dodge or ""),
                       ("Mod. parade", it.c_parry or ""), ("Mod. esquive adverse", it.c_adv_dodge or ""),
                       ("Mod. parade adverse", it.c_adv_parry or "")])
    section("Protection", [("Facteur de protection", f"{it.c_factor_prot:.2f}" if it.c_factor_prot else ""),
                           ("Prot. tranchant max.", it.c_slash or ""),
                           ("Prot. contondant max.", it.c_blunt or ""),
                           ("Prot. perforant max.", it.c_pierce or "")])
    section("Bijou", [(f"Protection {n}", v) for n, v in it.protections]
            + [(f"Résistance {n}", f"{v:.2f}") for n, v in it.resistances])
    section("Amplificateur", [("Vit. sort élémentaire", it.a_elem_speed or ""),
                              ("Puiss. élémentaire", it.a_elem_power or ""),
                              ("Vit. affliction off.", it.a_off_speed or ""),
                              ("Puiss. affliction off.", it.a_off_power or ""),
                              ("Vit. soin", it.a_heal_speed or ""), ("Puiss. soin", it.a_heal_power or ""),
                              ("Vit. affliction déf.", it.a_def_speed or ""),
                              ("Puiss. affliction déf.", it.a_def_power or "")])
    section("Bonus", [("Vie", it.hp_buff or ""), ("Sève", it.sap_buff or ""),
                      ("Endurance", it.sta_buff or ""), ("Concentration", it.focus_buff or "")])
    if it.mat_category1 or it.mat_specs1:
        lignes = []
        if 0 <= it.mat_category1 < len(MAT_CATEGORY):
            lignes.append(("Catégorie 1", MAT_CATEGORY[it.mat_category1]))
        lignes += [(MAT_SPEC[i], "★" * n) for i, n in it.mat_specs1 if 0 < i < len(MAT_SPEC)]
        if 0 < it.mat_category2 < len(MAT_CATEGORY):
            lignes.append(("Catégorie 2", MAT_CATEGORY[it.mat_category2]))
        lignes += [(MAT_SPEC[i], "★" * n) for i, n in it.mat_specs2 if 0 < i < len(MAT_SPEC)]
        if it.mat_colors:
            lignes.append(("Couleurs", ", ".join(COLOR_NAMES[c] for c in it.mat_colors
                                                 if 0 <= c < len(COLOR_NAMES))))
        section("Matière", lignes)
    if it.price or it.expires:
        section("Vente", [("Prix", f"{it.price:,.0f} dappers".replace(",", " ") if it.price else ""),
                          ("Continent", it.continent),
                          ("Expire dans", _temps_restant(it.expires) if it.expires else "")])
    return json.dumps({"titre": nom, "sections": sections}, ensure_ascii=False)


# ------------------------------------------------------------ la cloche

DOSSIER_ALERTES = "/tmp/alertes"


def alertes(sorte: str, ident: str, garde: str, reglages: str, argent: str,
            temps_xml: str, postes: str) -> str:
    """La liste de la cloche, comme page_alertes._check_alerts.

    `garde` : les objets surveilles (le guard.json de l'application) ;
    `argent` : les mouvements du tresor du dernier releve, s'il vient d'avoir
    lieu ; `temps_xml` et `postes` ne sont passes qu'au retour d'une synchro.
    """
    ent = lues.get((sorte, ident))
    if ent is None:
        return json.dumps({"alertes": [], "garde": json.loads(garde or "{}")})
    r = json.loads(reglages)
    os.makedirs(DOSSIER_ALERTES, exist_ok=True)
    chemin = f"{DOSSIER_ALERTES}/garde.json"
    with open(chemin, "w", encoding="utf-8") as fh:
        fh.write(garde or "{}")
    store = watch.WatchStore(chemin)
    out = alerts.volume_alerts(ent, int(r.get("volume", 90)))
    out += alerts.watch_alerts(ent, store, noms.name)
    out += alerts.sales_alerts(ent, int(r.get("ventes", 12)), noms.name)
    mouvements_argent = [movements.lire_etranger(json.loads(l)) for l in json.loads(argent or "[]")]
    out += alerts.money_alerts(mouvements_argent, store.money_watched())
    etat_postes = None
    if postes is not None and temps_xml is not None:
        chemin_postes = f"{DOSSIER_ALERTES}/postes.json"
        with open(chemin_postes, "w", encoding="utf-8") as fh:
            fh.write(postes or "{}")
        out += alerts.outpost_alerts(ent, chemin_postes, noms.name)
        with open(chemin_postes, encoding="utf-8") as fh:
            etat_postes = fh.read()
        if temps_xml:
            try:
                saison_ = alerts.season_alert(ryzom_api.parse_time(temps_xml.encode("utf-8")),
                                              int(r.get("saison", 12)))
                if saison_:
                    out.append(saison_)
            except Exception:
                pass
    return json.dumps({"alertes": [[a.kind, a.title, a.detail] for a in out],
                       "garde": store.items(), "postes": etat_postes}, ensure_ascii=False)
