#!/usr/bin/env python3
"""Fabrique la table de forage des Primes, en recoupant les deux relevés de la guilde.

**Deux sources, gardées dans `donnees/`**, et c'est leur croisement qui fait la
table — aucune des deux ne suffit seule.

* `pop-des-primes-par-saison.csv` — le **classeur des saisons**, rangé en
  saison × zone × condition × famille. Complet : quarante-sept matières par
  zone, quarante-six pour la Terre de la Continuité. Le Worst n'y est écrit
  qu'une fois, dans l'onglet « Printemps Reboot », et vaut pour les quatre
  saisons — c'est la Note 2 de l'autre classeur qui le dit.
* `tuto-forage-prime.xlsx` — le **Tuto Forage Prime**, dont un onglet par zone
  porte une cartographie `x` / `-` en six bandes d'humidité. Chantier en cours,
  très inégalement rempli, mais c'est le relevé le plus récent et il teste
  chaque saison séparément.

**La règle de fusion.** Le classeur des saisons pose le suprême ; la
cartographie corrige — un `x` ajoute, un `-` retire —, puis fournit seule
l'excellente et le choix, que le classeur des saisons ne relève pas.
Confrontées sur le suprême, les deux tombent d'accord sur 192 cases, la
cartographie en ajoute 29 — surtout en Best, ce que la Note 2 annonçait : « pop
deux saisons par an, reste à trouver lesquelles » — et en retire 16.

**Les six bandes se replient sur quatre.** Bad1 vaut toujours Bad2, et Good1
toujours Good2 : huit cent trente-six paires, sans une exception. On garde donc
les quatre conditions que l'API du jeu rend elle-même, et rien n'est perdu.

**Ce qu'on ne lit plus.** L'onglet « Feuille 14 » — les pages 16 à 18 du PDF qui
circule — ressemble à une table générale mais n'en est pas une : confrontée aux
onglets de zone, elle colle à Sources Interdites (101 accords sur 103) et
diverge des trois autres. L'appliquer partout revenait à afficher Sources
Interdites dans les quatre colonnes.

**Les excellentes des continents** viennent de l'onglet « Pop des Mps XL
continents ». Elles ne parlent **pas** des Primes : le tutoriel écrit lui-même
que ce pop est identique sur tous les continents, et les gisements
correspondants sont au Gouffre d'Ichor ou à la Porte des Vents. Gardées à part.

    python3 outils/table_forage.py

À relancer quand la guilde avance sur sa cartographie.
"""
import collections
import csv
import os
import re
import sys
import unicodedata
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_ANDROID = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPOT = os.path.dirname(_ANDROID)

sys.path.insert(0, os.path.join(_DEPOT, "zyroom-gtk"))
from zyroom import armory                                        # noqa: E402
from zyroom.gisements import LIBELLES                            # noqa: E402

CLASSEUR = os.path.join(_DEPOT, "donnees", "tuto-forage-prime.xlsx")
SAISONNIER = os.path.join(_DEPOT, "donnees", "pop-des-primes-par-saison.csv")
CIBLE_PY = os.path.join(_DEPOT, "zyroom-gtk", "zyroom", "forage.py")

SAISONS = ("PRINTEMPS", "ETE", "AUTOMNE", "HIVER")
CONDITIONS = ("WORST", "BAD", "GOOD", "BEST")

#: Les dix familles, dans l'ordre des colonnes du classeur des saisons.
FAMILLES = ("Ambres", "Graines", "Fibres", "Résine", "Huile", "Sève",
            "Carapace", "Écorce", "Bois", "Boucles")

#: Les quatre zones des Primes, dans l'ordre ou les deux classeurs les rangent.
ZONES = ("Sources Interdites", "Terre de la Continuité",
         "Cité Engloutie", "Profondeurs Interdites")

#: Onglet de cartographie de chaque zone, dans le Tuto Forage Prime.
ONGLETS = {
    "Sources Interdites": "Sources interdites 250",
    "Terre de la Continuité": "Terres de la continuité 250",
    "Cité Engloutie": "Cités engloutie 250",
    "Profondeurs Interdites": "Profondeurs interdites 250",
}

#: Onglet des excellentes des continents.
ONGLET_CONTINENTS = "Pop des Mps XL continents"

#: Les six bandes de la cartographie, et leur repli sur les quatre du jeu.
BANDES = ("WORST", "BAD2", "BAD1", "GOOD1", "GOOD2", "BEST")
VERS_QUATRE = {"WORST": "WORST", "BAD2": "BAD", "BAD1": "BAD",
               "GOOD1": "GOOD", "GOOD2": "GOOD", "BEST": "BEST"}

#: Les titres de saison du classeur des saisons, tels qu'ils y sont ecrits.
TITRES_SAISON = {"printemps": "PRINTEMPS", "été": "ETE", "ete": "ETE",
                 "autmone": "AUTOMNE", "automne": "AUTOMNE",
                 "hivers": "HIVER", "hiver": "HIVER"}

#: Les trois matieres que l'onglet des continents nomme en francais, la ou le
#: reste du classeur — et Armory — les nomme en anglais.
ALIAS_CONTINENTS = {"colle": "glue", "lune": "moon", "montega": "motega"}

#: Premiere colonne de donnees de l'onglet des continents. Le nom de la
#: matiere est en B, et les huit colonnes — quatre saisons de deux conditions —
#: commencent en D, apres une colonne vide.
CONTINENTS_DEPART = 3

#: Ce que l'onglet des continents ecrit dans ses cellules, coquille comprise.
CONTINENTS_VALEURS = {"best": "BEST", "good": "GOOD", "bad": "BAD",
                      "worst": "WORST", "wrost": "WORST"}


def normalise(texte: str) -> str:
    """Un nom de matiere, reduit a ce qui permet de le reconnaitre."""
    texte = str(texte).split("/")[0].replace("²", "")
    texte = texte.replace("?", "").replace("Agro", "").strip().lower()
    texte = unicodedata.normalize("NFD", texte)
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


#: {nom normalise: (famille, matiere)} — les quarante-sept noms canoniques.
#:
#: C'est `armory.py` qui nomme les matieres dans toute l'application : les deux
#: classeurs doivent s'aligner sur lui. La cartographie emploie deja ces
#: noms-la, a une coquille pres.
CANON = {normalise(m): (f, m)
         for zones in armory.SUPREMES.values()
         for familles in zones.values()
         for f, matieres in familles.items()
         for m in matieres}

#: Coquille du Tuto Forage Prime, qui ecrit « Scratch » la ou Armory ecrit
#: « Scrath » — la faute d'origine est chez Ryzom, et les deux la portent.
CANON["scratch"] = CANON["scrath"]

#: {couple anglais: couple canonique} — pour le classeur des saisons.
#:
#: Celui-ci ecrit les noms francais, et jusqu'a trois par matiere
#: (« Mignonne », « Migno Omg AGGRO »). `gisements.LIBELLES` les ramene tous a
#: l'anglais ; cette table-ci fait le dernier pas vers le nom canonique.
PAR_ANGLAIS = {}
for _couple in CANON.values():
    PAR_ANGLAIS.setdefault(LIBELLES[_couple], _couple)


# ----------------------------------------------------------- lecture du xlsx
#
# Un classeur xlsx est un zip de XML : les quelques lignes qui suivent
# remplacent openpyxl, qu'il faudrait installer dans un environnement virtuel
# pour un outil qui tourne deux fois par an.

_CELL = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
_VAL = re.compile(r"<(?:v|t)[^>]*>(.*?)</(?:v|t)>", re.S)


def _texte(brut: str) -> str:
    """Le contenu d'une balise XML, entites comprises."""
    for avant, apres in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                         ("&#39;", "'"), ("&apos;", "'"), ("&amp;", "&")):
        brut = brut.replace(avant, apres)
    return brut


def _colonne(lettres: str) -> int:
    n = 0
    for c in lettres:
        n = n * 26 + ord(c) - 64
    return n - 1


def feuilles(chemin: str) -> dict:
    """{nom d'onglet: [[cellule, …], …]} — tout le classeur, en texte."""
    z = zipfile.ZipFile(chemin)
    chaines = [_texte("".join(_VAL.findall(bloc)))
               for bloc in re.findall(
                   r"<si>(.*?)</si>",
                   z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    noms = re.findall(r'<sheet[^>]*name="([^"]*)"',
                      z.read("xl/workbook.xml").decode("utf-8"))
    tout = {}
    for rang, nom in enumerate(noms, 1):
        lignes: dict = collections.defaultdict(dict)
        brut = z.read(f"xl/worksheets/sheet{rang}.xml").decode("utf-8")
        for m in _CELL.finditer(brut):
            valeurs = _VAL.findall(m[4] or "")
            if not valeurs:
                continue
            v = _texte(valeurs[0])
            if 't="s"' in (m[3] or "") and v.isdigit():
                v = chaines[int(v)]
            if v.strip():
                lignes[int(m[2])][_colonne(m[1])] = v.strip()
        if not lignes:
            tout[nom] = []
            continue
        large = max(max(d) for d in lignes.values()) + 1
        tout[nom] = [[lignes.get(r, {}).get(c, "") for c in range(large)]
                     for r in range(1, max(lignes) + 1)]
    return tout


# --------------------------------------------------- le classeur des saisons

def par_saison() -> dict:
    """{(saison, zone, condition): {(famille, matière)}} — la base du suprême.

    Le fichier est une grille dessinée à la main : un titre de saison, puis
    quatre blocs de zone, chacun ouvert par sa rangée de familles. La zone
    n'est écrite que sur sa première ligne, et parfois pas du tout — on suit
    donc l'ordre des blocs, qui, lui, ne varie pas.
    """
    trouve = collections.defaultdict(set)
    saison = condition = None
    rang = -1
    colonnes: dict = {}
    with open(SAISONNIER, encoding="utf-8") as fh:
        for ligne in csv.reader(fh):
            ligne = (ligne + [""] * 30)[:30]
            titre, cond = ligne[1].strip(), ligne[2].strip()
            mot = titre.split()[0].lower() if titre else ""
            if TITRES_SAISON.get(mot) and len(titre.split()) > 1:
                saison, condition, rang = TITRES_SAISON[mot], None, -1
                continue
            if ligne[3].strip() in FAMILLES:
                colonnes = {i: ligne[i].strip() for i in range(3, 15)
                            if ligne[i].strip() in FAMILLES}
                rang, condition = rang + 1, None
                continue
            if cond.lower() in ("worst", "bad", "good", "best"):
                condition = cond.upper()
            if not (saison and condition and 0 <= rang < len(ZONES)):
                continue
            for i, famille in colonnes.items():
                nom = ligne[i].strip()
                if not nom:
                    continue
                anglais = LIBELLES.get((famille, nom))
                couple = PAR_ANGLAIS.get(anglais)
                if couple is None:
                    raise SystemExit(f"nom inconnu : {famille} / {nom}")
                # Le Worst n'est ecrit qu'au printemps : Note 2, mode n°1, il
                # vaut pour les quatre saisons.
                saisons = SAISONS if condition == "WORST" else (saison,)
                for s in saisons:
                    trouve[(s, ZONES[rang], condition)].add(couple)
    return trouve


# ---------------------------------------------------------- la cartographie

def cartographie(tout: dict) -> dict:
    """{(ligne, zone): {(famille, matière): {(saison, condition): 'x'|'-'}}}.

    Trois lignes par matière — Choix, XL, Supp — et vingt-quatre colonnes
    chacune. On replie les six bandes sur quatre. Un `x?` est une déduction que
    la guilde reste à vérifier : sa légende demande de la lire comme un pop.
    """
    trouve = collections.defaultdict(lambda: collections.defaultdict(dict))
    for zone, onglet in ONGLETS.items():
        matiere = None
        for ligne in tout[onglet]:
            ligne = (ligne + [""] * 30)[:30]
            etiquette = ligne[1].strip()
            if ligne[0].strip() and etiquette in ("Choix", "XL", "Supp"):
                matiere = CANON.get(normalise(ligne[0]))
            if etiquette not in ("Choix", "XL", "Supp") or matiere is None:
                continue
            for k in range(24):
                v = ligne[2 + k].strip()
                if v:
                    trouve[(etiquette, zone)][matiere][
                        (SAISONS[k // 6], VERS_QUATRE[BANDES[k % 6]])] = (
                            "x" if v.startswith("x") else "-")
    return trouve


def continents(tout: dict) -> dict:
    """{(famille, matière): {(saison, condition)}} — les excellentes hors Primes.

    Deux saisons, deux conditions par matière, les mêmes sur tous les
    continents — le tutoriel l'écrit en toutes lettres. Cette table s'accorde
    exactement avec les fourchettes d'humidité relevées sur atys.us :
    quarante-cinq matières sur quarante-cinq.
    """
    trouve = collections.defaultdict(set)
    for ligne in tout[ONGLET_CONTINENTS]:
        ligne = (ligne + [""] * 20)[:20]
        if not ligne[1].strip():
            continue
        nom = normalise(ligne[1])
        couple = CANON.get(ALIAS_CONTINENTS.get(nom, nom))
        if couple is None:
            continue                    # un en-tete de famille, pas une matiere
        for k in range(8):
            v = CONTINENTS_VALEURS.get(
                ligne[CONTINENTS_DEPART + k].strip().lower())
            if v:
                trouve[couple].add((SAISONS[k // 2], v))
    return trouve


# ---------------------------------------------------------------- la fusion

def fusionne(base: dict, carto: dict) -> dict:
    """{qualité: {zone: {(famille, matière): {(saison, condition)}}}}."""
    tables = {q: collections.defaultdict(lambda: collections.defaultdict(set))
              for q in ("SUPREME", "EXCELLENTE", "CHOIX")}
    for (saison, zone, condition), couples in base.items():
        for couple in couples:
            tables["SUPREME"][zone][couple].add((saison, condition))
    for (etiquette, zone), matieres in carto.items():
        qualite = {"Supp": "SUPREME", "XL": "EXCELLENTE",
                   "Choix": "CHOIX"}[etiquette]
        for couple, cases in matieres.items():
            for cle, marque in cases.items():
                if marque == "x":
                    tables[qualite][zone][couple].add(cle)
                else:
                    tables[qualite][zone][couple].discard(cle)
    # Une matiere dont la cartographie a tout retire ne doit pas rester en
    # clef vide : elle se lirait comme « relevee, mais nulle part ».
    return {q: {z: {c: k for c, k in m.items() if k}
                for z, m in t.items()} for q, t in tables.items()}


def verifie(tables: dict, conts: dict) -> None:
    """Les contrôles qui empêchent une table muette de passer pour vraie."""
    if set(tables["SUPREME"]) != set(ZONES):
        raise SystemExit(f"zones lues : {sorted(tables['SUPREME'])}")
    for zone, matieres in tables["SUPREME"].items():
        if not 45 <= len(matieres) <= 47:
            raise SystemExit(f"{zone} : {len(matieres)} matières suprêmes")
    for qualite, table in tables.items():
        for zone, matieres in table.items():
            inconnues = set(matieres) - set(LIBELLES)
            if inconnues:
                raise SystemExit(f"{qualite}/{zone} : {sorted(inconnues)} "
                                 f"absentes de gisements.LIBELLES")
            for couple, creneaux in matieres.items():
                for saison, condition in creneaux:
                    if saison not in SAISONS or condition not in CONDITIONS:
                        raise SystemExit(f"{couple} : ({saison}, {condition})")
    if len(conts) != 47:
        raise SystemExit(f"continents : {len(conts)} matières, 47 attendues")
    for couple, creneaux in conts.items():
        if len(creneaux) != 4 or len({s for s, _c in creneaux}) != 2:
            raise SystemExit(f"continents : {couple} rend {sorted(creneaux)}")


# --------------------------------------------------------------- l'écriture

def _matieres(table: dict, marge: str) -> list:
    lignes = []
    for couple, creneaux in sorted(table.items()):
        lignes.append(f'{marge}("{couple[0]}", "{couple[1]}"): ' + "{")
        for saison, condition in sorted(creneaux):
            lignes.append(f'{marge}    ("{saison}", "{condition}"),')
        lignes.append(marge + "},")
    return lignes


def _bloc(entete: list, table: dict) -> list:
    lignes = list(entete)
    for zone in ZONES:
        lignes.append(f'    "{zone}": ' + "{")
        lignes += _matieres(table.get(zone, {}), " " * 8)
        lignes.append("    },")
    return lignes + ["}", ""]


def python(tables: dict, conts: dict) -> str:
    lignes = [
        '"""Ce que rend un gisement des Primes, selon la zone, la saison et le temps.',
        "",
        "Fichier produit par ../zyroom-android/outils/table_forage.py — ne pas",
        "modifier à la main. Il croise les deux relevés de la guilde gardés",
        "dans `donnees/` : le classeur des saisons, complet, et la cartographie",
        "du Tuto Forage Prime, plus récente mais inachevée.",
        "",
        "**Les quatre zones ne se ressemblent pas.** C'était l'erreur d'avant :",
        "une seule table pour les quatre, alors que la Terre de la Continuité",
        "ne sort pas ce que sortent les Sources Interdites au même moment.",
        "",
        "Le suprême est complet. L'excellente et le choix ne sont relevés que",
        "par endroits : la guilde y travaille encore, et un silence ne veut pas",
        "dire « rien ne sort ».",
        '"""',
        "",
    ]
    lignes += _bloc([
        "#: {zone: {(famille, matière): {(saison, condition)}}} — le suprême.",
        "#:",
        "#: Une vingtaine de matières par zone sortent dès que le temps est",
        "#: exécrable, aux quatre saisons ; les autres à un créneau précis.",
        "SUPREMES = {"], tables["SUPREME"])
    lignes += _bloc([
        "#: {zone: {(famille, matière): {(saison, condition)}}} — l'excellente",
        "#: des Primes, telle que la cartographie la donne. Clairsemée.",
        "EXCELLENTES = {"], tables["EXCELLENTE"])
    lignes += _bloc([
        "#: {zone: {(famille, matière): {(saison, condition)}}} — le choix,",
        "#: là où la guilde l'a noté. Clairsemé lui aussi.",
        "CHOIX = {"], tables["CHOIX"])
    lignes += [
        "#: {(famille, matière): {(saison, condition)}} — les excellentes des",
        "#: **continents**, qui ne parlent pas des Primes.",
        "#:",
        "#: Le tutoriel écrit que ce pop est identique sur tous les continents,",
        "#: et les gisements correspondants sont au Gouffre d'Ichor ou à la",
        "#: Porte des Vents. Deux saisons, deux conditions par matière.",
        "EXCELLENTES_CONTINENTS = {",
    ]
    lignes += _matieres(conts, " " * 4)
    return "\n".join(lignes + ["}", ""])


def main() -> int:
    tout = feuilles(CLASSEUR)
    base = par_saison()
    carto = cartographie(tout)
    tables = fusionne(base, carto)
    conts = continents(tout)
    verifie(tables, conts)

    accord = ajout = retrait = 0
    for zone in ZONES:
        for couple, cases in carto.get(("Supp", zone), {}).items():
            for cle, marque in cases.items():
                dedans = couple in base.get((cle[0], zone, cle[1]), ())
                accord += marque == "x" and dedans
                ajout += marque == "x" and not dedans
                retrait += marque == "-" and dedans
    print(f"recoupement du suprême : {accord} accords, {ajout} ajouts de la "
          f"cartographie, {retrait} retraits")
    for qualite in ("SUPREME", "EXCELLENTE", "CHOIX"):
        print(f"{qualite:11s} " + "  ".join(
            f"{z[:12]} {len(tables[qualite].get(z, {})):2d}" for z in ZONES))
    print(f"continents  {len(conts)} matières")
    with open(CIBLE_PY, "w", encoding="utf-8") as fh:
        fh.write(python(tables, conts))
    print("→", CIBLE_PY)
    return 0


if __name__ == "__main__":
    sys.exit(main())
