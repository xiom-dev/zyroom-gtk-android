#!/usr/bin/env python3
"""Fabrique la page des MP du hall de guilde, `site-domaine/mp/`.

    python3 outils/page-mp.py

Trois sorties, toutes à déposer sur xiom.be avec `index.html` et `.htaccess` :

- `noms.json` : chaque MP de KipeeCraft (`Supreme_PrimeRoots_Zun_Amber`) et
  les fiches du jeu qui la portent (`m0155dxapf01.sitem`), avec son nom
  français. C'est le pont entre les recettes et le stock du hall.
- `mp.depart.json` : les recettes de `KipeeCraft/Recipes`, lues une fois.
  Le site s'en sert tant qu'aucune modification n'a été enregistrée ; ensuite
  il ne lit plus que son propre `mp.json`, que cet outil ne touche jamais.
- `mp.php` : le modèle `mp.modele.php` avec les empreintes des mots de passe
  et le sel, tirés de `~/.config/zyroom/`. Ignoré par git.

Deux sortes de mots de passe, dans `~/.config/zyroom/` :

- `mp.lecture` : celui de la guilde, sans nom. Il ouvre la lecture seule.
- `mp.motsdepasse` : un par personne qui modifie, une ligne `Nom: phrase`.
  Ajouter quelqu'un : une ligne de plus, relancer, redéposer `mp.php`.

**Pourquoi la table des noms se calcule et ne s'écrit pas à la main.** Un
identifiant du jeu se lit morceau par morceau : `m0155` la matière, `dxa` une
MP forée (les bêtes ont un code à elles, `chh` le Mektoub…), `p` l'écosystème,
`f` le grade. KipeeCraft écrit les mêmes renseignements en anglais ; il suffit
de retrouver, parmi les noms français du jeu, la fiche qui porte les quatre.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "site-domaine", "mp")
MODELE = os.path.join(DOSSIER, "mp.modele.php")
SECRETS = os.path.expanduser("~/.config/zyroom")
MOTS_DE_PASSE = os.path.join(SECRETS, "mp.motsdepasse")
LECTURE = os.path.join(SECRETS, "mp.lecture")
SEL = os.path.join(SECRETS, "mp.sel")

KIPEECRAFT = os.path.expanduser("~/jeu/ryzom/KipeeCraft")
BASE_KC = os.path.join(KIPEECRAFT, "kipeecraft-py", "src", "kipeecraft",
                       "resources", "defaults", "DB", "Ryzom.json")
RECETTES = os.path.join(KIPEECRAFT, "Recipes")

#: Les noms francais du jeu, tels que ZyRoom les a tires du `string_client.pack`.
NOMS_DU_JEU = (
    "~/.var/app/net.ryzom.zyroomgtk.dev/cache/zyroom-gtk/names.json",
    "~/.var/app/net.ryzom.zyroomgtk/cache/zyroom-gtk/names.json",
    "~/.cache/zyroom-gtk/names.json",
)

ECOSYSTEMES = {"Desert": "d", "Forest": "f", "Jungle": "j", "Lake": "l",
               "PrimeRoots": "p", "none": "c"}
#: **L'echelle des grades est decalee d'une lettre entre forage et chasse.**
#: Une MP foree va de b (base) a f (supreme) ; une MP de bete, de a a e.
GRADES_FORAGE = {"Basic": "b", "Fine": "c", "Choice": "d", "Excellent": "e",
                 "Supreme": "f"}
GRADES_CHASSE = {"Basic": "a", "Fine": "b", "Choice": "c", "Excellent": "d",
                 "Supreme": "e"}
#: Les types qui se forent : leur nom francais ne dit pas toujours le type
#: ("Boucles excellentes de bois / Scrath"), on ne le verifie donc pas.
TYPES_FORES = {"Amber", "Bark", "Fiber", "Resin", "Sap", "Seed", "Wood", "Oil",
               "WoodNode", "Shell"}
#: Les matieres dont le nom francais n'est pas l'anglais.
TRADUCTIONS = {"Moon": "Lune", "Glue": "Colle", "Big": "grosse",
               "Cuty": "Mignonne", "Redhot": "Ardente", "Smart": "Intelligente",
               "Horny": "Cornee"}
#: Le mot francais qui doit figurer dans le nom d'une MP de bete.
TYPES_FR = {
    "Beak": "bec", "Bone": "os", "Bud": "bourgeon", "Carapace": "carapace",
    "Claw": "griffe", "Crest": "crete", "Eye": "oeil", "Fang": "croc",
    "Flesh": "chair", "Fur": "fourrure", "Head": "tete", "Hoof": "sabot",
    "Horn": "corne", "Jaw": "machoire", "Larva": "larve", "Leaf": "feuille",
    "Leather": "cuir", "Ligament": "ligament", "Mandible": "mandibule",
    "Moss": "mousse", "Mushroom": "champignon", "Nail": "ongle",
    "Pelvis": "bassin", "Rostrum": "rostre", "Secretion": "secretion",
    "Shell": "carapace", "Skin": "peau", "Spine": "epine", "Sting": "dard",
    "Tail": "queue", "Tooth": "dent", "Trunk": "trompe", "Whiskers": "moustache",
    "Wing": "aile", "Wood": "bois",
}


def plat(texte: str) -> str:
    """En minuscules et sans accents, pour comparer des noms."""
    texte = texte.replace("Œ", "Oe").replace("œ", "oe")
    texte = unicodedata.normalize("NFD", texte)
    return texte.encode("ascii", "ignore").decode().lower()


def lire_noms_du_jeu() -> dict[str, str]:
    for chemin in NOMS_DU_JEU:
        chemin = os.path.expanduser(chemin)
        if os.path.isfile(chemin):
            with open(chemin, encoding="utf-8") as fh:
                return json.load(fh)["names"]
    raise SystemExit("Noms du jeu introuvables : lancer ZyRoom une fois.")


def fiches_de(cle: str, mps: dict[str, str]) -> list[str]:
    """Les fiches du jeu d'une MP de KipeeCraft, ou une liste vide.

    Plusieurs fiches pour une seule MP, c'est le Mektoub : le jeu en a deux
    sortes (`chh`, `chj`) qui donnent la même MP. Le stock les additionne.
    """
    morceaux = cle.split("_")
    if len(morceaux) != 4:
        return []
    grade, eco, matiere, type_ = morceaux
    if eco not in ECOSYSTEMES or grade not in GRADES_FORAGE:
        return []
    mot = re.compile(r"\b" + re.escape(plat(TRADUCTIONS.get(matiere, matiere)))
                     + r"\b")
    type_fr = TYPES_FR.get(type_)
    fore = type_ in TYPES_FORES
    trouvees = []
    for fiche, nom in mps.items():
        chasse = fiche[5:8] != "dxa"
        grades = GRADES_CHASSE if chasse else GRADES_FORAGE
        if fiche[8] != ECOSYSTEMES[eco] or fiche[9] != grades[grade]:
            continue
        nom_plat = plat(nom)
        if not mot.search(nom_plat):
            continue
        # Une MP de bete doit dire ce qu'elle est : sinon l'oeil du Bodoc
        # et son poil se confondent.
        if chasse or not fore:
            if not type_fr or not re.search(r"\b" + type_fr, nom_plat):
                continue
        trouvees.append(fiche)
    # Une MP foree et une piece de bete du meme nom : la Shell du Clopper est
    # sa carapace, pas la "carapace corrompue de Clopper" foree. On garde
    # la chasse.
    if len(trouvees) > 1:
        trouvees = [f for f in trouvees if f[5:8] != "dxa"] or trouvees
    if len(trouvees) > 1:
        # Plusieurs fiches pour une seule MP ne se tolerent que si elles ne
        # different que par le code de la bete (le Mektoub).
        if len({f[:5] + f[8:] for f in trouvees}) != 1:
            return []
    return sorted(trouvees)


def table_des_noms() -> tuple[dict, list[str]]:
    noms = lire_noms_du_jeu()
    mps = {k: v for k, v in noms.items()
           if re.match(r"m\d{4}[a-z]{3}[a-z]{2}01\.sitem$", k)}
    with open(BASE_KC, encoding="utf-8") as fh:
        base = json.load(fh)
    cles = sorted({"_".join((m["grade"], m["eco"], m["name"], m["type"]))
                   for partie in base["parts"].values()
                   for m in partie["materials"]})
    table, manquent = {}, []
    for cle in cles:
        fiches = fiches_de(cle, mps)
        if fiches:
            table[cle] = {"fiches": fiches, "nom": mps[fiches[0]]}
        else:
            manquent.append(cle)
    return table, manquent


def intitules_des_plans() -> dict[str, str]:
    """`PatternID` -> intitulé français du plan, « Bijoux (Qualité haute) »."""
    sys.path.insert(0, os.path.join(KIPEECRAFT, "kipeecraft-py", "src"))
    from kipeecraft.core.patterns import PlanBook
    return {str(plan.id): plan.full_label for plan in PlanBook.load()}


def identifiant(nom: str) -> str:
    """Le nom d'une recette réduit à ce qu'une adresse ou un JSON tolère.

    Même règle que la page (`identifiant` dans index.html) : une recette
    importée par le site et la même recette lue ici doivent tomber sur le
    même identifiant, sinon elle existerait en double.
    """
    plat_ = re.sub(r"[^a-z0-9]+", "-", plat(nom)).strip("-")
    return plat_[:60] or "recette"


#: Une ligne de piece d'un `.kc` : "slot3=3x Choice_PrimeRoots_Dzao_Fiber 2".
#: Le dernier nombre est la colonne de la base de KipeeCraft ; il ne sert pas
#: au compte des MP.
LIGNE_SLOT = re.compile(r"^slot(\d+)=(\d+)x\s+(\S+)", re.M)


def lire_recette(chemin: str) -> dict | None:
    """Une recette `.kc`, ou None si le fichier n'en porte pas."""
    with open(chemin, encoding="latin-1") as fh:
        texte = fh.read().replace("\r\n", "\n")
    plan = re.search(r"^PatternID=(\d+)", texte, re.M)
    pieces = [{"n": int(q), "mp": mp}
              for _, q, mp in LIGNE_SLOT.findall(texte)]
    if not plan or not pieces:
        return None
    nom = os.path.splitext(os.path.basename(chemin))[0]
    return {"id": identifiant(nom), "nom": nom, "plan": int(plan.group(1)),
            "pieces": pieces, "minimums": {}}


#: Ce qui a ete decide pour une recette precise et que le `.kc` ne dit pas.
#: Le site, lui, garde ces reglages dans son `mp.json` ; ceci n'est que le
#: point de depart.
MINIMUMS_DE_DEPART = {
    # La Sha doit etre en 250 pour donner le bonus (Ludo, 9 octobre 2026).
    "parrure-210-xlsup-pvp-matis": {"Supreme_PrimeRoots_Sha_Amber": 250},
}


#: Decides avec Ludo le 9 octobre 2026 : dix crafts par recette, craft en
#: qualite 210, "stop forage" au-dela de trois fois le besoin, "bientot en
#: rupture" sous trois crafts. La guilde est La Lune Eternelle.
REGLAGES_DE_DEPART = {"objectif": 10, "qualite": 210, "stop": 3, "rupture": 3,
                      "guilde": 105906237}


def recettes_de_depart() -> list[dict]:
    recettes, vus = [], set()
    for nom in sorted(os.listdir(RECETTES), key=str.lower):
        if not nom.lower().endswith(".kc"):
            continue
        recette = lire_recette(os.path.join(RECETTES, nom))
        if recette is None:
            print("  pas de recette dans", nom)
            continue
        if recette["id"] in vus:
            raise SystemExit(f"Deux recettes donnent l'identifiant {recette['id']}")
        vus.add(recette["id"])
        recette["minimums"] = MINIMUMS_DE_DEPART.get(recette["id"], {})
        recettes.append(recette)
    return recettes


def lire_secret(chemin: str, aide: str) -> str:
    if not os.path.isfile(chemin):
        raise SystemExit(f"Absent : {chemin}\n{aide}")
    with open(chemin, encoding="utf-8") as fh:
        return fh.read().strip()


def fabriquer_php() -> None:
    import bcrypt
    lignes = lire_secret(MOTS_DE_PASSE, "Une ligne par personne : « Nom: phrase »")
    sel = lire_secret(SEL, "En tirer un : python3 -c \"import secrets; "
                           "print(secrets.token_hex(24))\" > " + SEL)
    empreintes = {}
    for ligne in lignes.splitlines():
        if not ligne.strip() or ligne.lstrip().startswith("#"):
            continue
        nom, _, phrase = ligne.partition(":")
        nom, phrase = nom.strip(), phrase.strip()
        if not re.fullmatch(r"[\w \-']{1,24}", nom) or not phrase:
            raise SystemExit(f"Ligne illisible dans {MOTS_DE_PASSE} : {nom!r}")
        # PHP attend le prefixe "$2y$" ; c'est le meme algorithme que "$2b$".
        empreintes[nom] = "$2y$" + bcrypt.hashpw(
            phrase.encode(), bcrypt.gensalt(12)).decode()[4:]
    with open(MODELE, encoding="utf-8") as fh:
        modele = fh.read()
    lecture = lire_secret(LECTURE, "Le mot de passe de lecture de la guilde, seul sur sa ligne")
    for trou in ("__UTILISATEURS__", "__LECTURE__", "__SEL__"):
        if modele.count(trou) != 1:
            raise SystemExit(f"{MODELE} : {trou} attendu une fois")
    # Ni apostrophe ni antislash dans ce JSON (noms filtres, empreintes
    # bcrypt) : il tient tel quel entre les apostrophes du PHP.
    utilisateurs = json.dumps(empreintes, ensure_ascii=False)
    empreinte_lecture = "$2y$" + bcrypt.hashpw(
        lecture.encode(), bcrypt.gensalt(12)).decode()[4:]
    php = (modele.replace("__UTILISATEURS__", utilisateurs)
           .replace("__LECTURE__", empreinte_lecture).replace("__SEL__", sel))
    with open(os.path.join(DOSSIER, "mp.php"), "w", encoding="utf-8") as fh:
        fh.write(php)
    print("→ mp.php : lecture + écriture pour", ", ".join(empreintes))


def ecrire(nom: str, donnees) -> None:
    with open(os.path.join(DOSSIER, nom), "w", encoding="utf-8") as fh:
        json.dump(donnees, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")


def main() -> int:
    table, manquent = table_des_noms()
    ecrire("noms.json", {"mp": table, "plans": intitules_des_plans()})
    print(f"→ noms.json : {len(table)} MP ({len(manquent)} sans fiche dans le jeu)")

    recettes = recettes_de_depart()
    inconnues = sorted({p["mp"] for r in recettes for p in r["pieces"]
                        if p["mp"] not in table})
    ecrire("mp.depart.json", {"version": 1, "reglages": REGLAGES_DE_DEPART,
                              "recettes": recettes})
    print(f"→ mp.depart.json : {len(recettes)} recettes")
    for mp in inconnues:
        print("   MP sans fiche :", mp)

    fabriquer_php()
    print("à déposer dans mp/ sur xiom.be : index.html, mp.php, noms.json,"
          " mp.depart.json, .htaccess")
    return 0


if __name__ == "__main__":
    sys.exit(main())
