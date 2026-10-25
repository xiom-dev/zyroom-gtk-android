#!/usr/bin/env python3
"""Fabrique la liste des rois et des nommés, `site-domaine/mp/mobs.json`.

    python3 outils/page-mobs.py

L'onglet Mobs de la page des MP du hall la lit, et la croise avec les MP
des recettes : quels boss chasser, lesquels laisser tranquilles.

**La liste vient du jeu lui-même**, du client Ryzom installé :

- `string_client.pack` nomme chaque fiche de créature (`chwfe7.creature` =
  « Aranakin ») ;
- `place_words_fr.txt` (dans `gamedev.bnp`) donne les noms de lieux en
  français.

Ballistic Mystix (`?p=mob;boss`) ne sert plus qu'à dire où vivent les
nommés et quels lieux accueillent des boss : sa liste de rois date d'avant
la refonte de 2021 et en oubliait les trois quarts.

**Une fiche de créature se lit lettre par lettre** : `c`, la classe, l'espèce,
l'écosystème (d f j l p), la tranche de niveau (a à f), puis un chiffre :
1 à 4 une bête ordinaire, 5 un nommé, 7 un roi. Les tranches e et f sont
celles des régions 200 et 250 : rois 220 et 270 (MP suprêmes), nommés 210
et 260 (MP excellentes). Vérifié sur les 119 boss de Ballistic Mystix :
tous s'y retrouvent, à la qualité annoncée.

**Quels rois existent vraiment.** Depuis la refonte des rois (mai 2021, voir
fr.wiki.ryzom.com/wiki/Nouveautés_2021), chaque région a ses rois, au niveau
de la région, qui se relaient sur ses sites. Le jeu a une fiche de roi pour
toutes les combinaisons espèce × écosystème × tranche, bien plus qu'il n'en
fait apparaître : la liste vient donc du relevé fait en jeu (`RELEVE`, la
page « Chasse aux Rois » de la guilde), six rois par région. Les fiches du
jeu ne servent qu'à retrouver l'espèce de chaque roi.

Les tribus primitives (Cute, Frahar, Gibbaï) ne lâchent aucune MP de
recette : écartées.

Puis déposer `mobs.json` sur xiom.be, à côté de `index.html`.
"""
from __future__ import annotations

import html
import json
import os
import re
import struct
import sys
import unicodedata
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "site-domaine", "mp")
SORTIE = os.path.join(DOSSIER, "mobs.json")
NOMS = os.path.join(DOSSIER, "noms.json")

# Le lecteur du pack de ZyRoom-GTK, le meme que pour les noms des MP.
sys.path.insert(0, os.path.join(RACINE, "zyroom-gtk"))
from zyroom.namedb import _parse_pack  # noqa: E402

BOSS = "https://ballisticmystix.net/?p=mob;boss"
CLIENT = ("~/.local/share/Ryzom/ryzom_live", "~/.local/share/Ryzom/ryzom_dev")

ECOS = {"d": "Desert", "f": "Forest", "j": "Jungle", "l": "Lake", "p": "PrimeRoots"}
#: (chiffre de la fiche, tranche) -> qualite du butin
QUALITES = {("7", "e"): 220, ("7", "f"): 270, ("5", "e"): 210, ("5", "f"): 260}
#: Les rois de chaque region, releves en jeu le 20/10/2026 (page « Chasse aux
#: Rois » de la guilde) : lignes orange = regions 200 (rois 220), rouges =
#: regions 250 (rois 270). Les regions blanches et jaunes ont des rois trop
#: bas pour les recettes. A refaire a la main si le jeu change ses rois.
RELEVE = {
    "Gouffre d'Ichor": (220, "Timkoo Plodekoo Kincherkoo Kipeskoo Goakoo Ocykoo"),
    "Forêt Insaisissable": (220, "Javkoo Clopperkoo Kirokoo Jugukoo Messakoo Stinkoo"),
    "La Fosse aux Epreuves": (220, "Kibakoo Kizokoo Ragukoo Aranakoo Raspakoo Zerkoo"),
    "Profondeurs Interdites": (270, "Gubakoo Kinkoo Cuttlekoo Slavekoo Jukoo Madakoo"),
    "Terre de la Continuité": (270, "Caprykoo Craykoo Kidikoo Igakoo Shalakoo Yelkoo"),
    "Cité Engloutie": (270, "Varykoo Najakoo Izakoo Wombakoo Gnookoo Hornkoo"),
    "Sources Interdites": (270, "Kipukoo Vorkoo Ginkoo Rendokoo Armkoo Lumpkoo"),
    "Bosquet de l'Ombre": (220, "Bodokya Kipukya Madakya Najakya Psykokya Wombakya"),
    "Noeud de la Démence": (220, "Madakya Psykokya Kidikya Kinkya Najakya Wombakya"),
    "Vide": (270, "Cratchakya Najakya Gubakya Kirokya Yetikya Plodekya"),
    "Plages d'Abondance": (220, "Armkan Kipeskan Kipukan Shalakan Yelkan Zerkan"),
    "Ile Enchantée": (220, "Kizokan Shalakan Kipukan Kipeskan Mekan Yelkan"),
    "Lagons de Loria": (270, "Kincherkan Kipukan Kipeskan Hornkan Wombakan Kirokan"),
    "Masure de l'Hérétique": (220, "Cuttlekin Kipeskin Kirokin Bolkin Kipukin Slavekin"),
    "Source Cachée": (220, "Kibakin Bolkin Gnookin Kipeskin Kizokin Slavekin"),
    "Marais Supérieur": (220, "Kirokin Bolkin Cratchakin Gnookin Slavekin Yelkin"),
    "Bosquet de la Confusion": (270, "Slavekin Kipeekin Kirokin Cuttlekin Jugukin Madakin"),
    "Dunes de l'Exil": (220, "Ocyketh Kipeeketh Lumpketh Varyketh Aranaketh Plodeketh"),
    "Canyon Interdit": (220, "Kipesketh Varyketh Lumpketh Aranaketh Kincherketh Kipuketh"),
    "Dunes Sauvages": (220, "Aranaketh Ocyketh Varyketh Plodeketh Kipeeketh Timketh"),
    "Couloir Brûlé": (270, "Shalaketh Cuttleketh Zerketh Kipesketh Kipuketh Tyraketh"),
}
#: Le suffixe d'un roi dit son ecosysteme.
SUFFIXES = {"keth": "Desert", "kin": "Forest", "kan": "Lake", "kya": "Jungle",
            "koo": "PrimeRoots"}
def client() -> str:
    for c in CLIENT:
        if os.path.exists(os.path.expanduser(c)):
            return os.path.expanduser(c)
    sys.exit("Client Ryzom introuvable : " + ", ".join(CLIENT))


def lire_bnp(chemin: str, nom: str) -> bytes:
    """Un fichier d'une archive .bnp de NeL : la table est en fin de fichier."""
    with open(chemin, "rb") as f:
        f.seek(-4, 2)
        f.seek(struct.unpack("<I", f.read(4))[0])
        for _ in range(struct.unpack("<I", f.read(4))[0]):
            n = f.read(f.read(1)[0]).decode("latin-1")
            taille, debut = struct.unpack("<II", f.read(8))
            if n == nom:
                f.seek(debut)
                return f.read(taille)
    raise KeyError(nom)


def lieux_fr(dossier: str) -> dict[str, str]:
    """Nom anglais d'un lieu -> son nom francais, d'apres le client."""
    bnp = os.path.join(dossier, "data", "gamedev.bnp")

    def table(langue: str) -> dict[str, str]:
        texte = lire_bnp(bnp, f"place_words_{langue}.txt").decode("utf-8-sig")
        # identifiant du lieu -> nom
        return {c[1]: c[2] for c in (l.split("\t") for l in texte.splitlines())
                if len(c) > 2}

    en, fr = table("en"), table("fr")
    return {nom: fr[ident] for ident, nom in en.items() if ident in fr}


def lire_boss() -> list[dict]:
    """Les boss de Ballistic Mystix : nom, qualite et lieu."""
    requete = urllib.request.Request(BOSS, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(requete, timeout=30) as r:
        page = r.read().decode("utf-8")
    boss = []
    for corps in re.findall(r"<h3>.*?</h3>(.*?)</table>", page, re.S):
        for ligne in re.findall(r"<tr[^>]*>(.*?)</tr>", corps, re.S):
            cases = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", ligne, re.S)]
            # numero, nom, espece, etoiles (image), qualite, grade, lieu
            if len(cases) < 7 or not cases[0].isdigit() or not cases[4].isdigit():
                continue
            boss.append({"nom": cases[1], "q": int(cases[4]), "lieu": cases[6]})
    return boss


def cle_nom(nom: str) -> str:
    """Le nom pour comparer : le "ï" s'ecrit d'une ou de deux facons."""
    return unicodedata.normalize("NFC", nom).lower()


def main() -> int:
    dossier = client()
    with open(os.path.join(dossier, "save", "string_client.pack"), "rb") as f:
        noms_jeu = _parse_pack(f.read())
    # "chwfe7" -> "Aranakin" : seulement les fiches de faune (6 caracteres)
    fiches = {k[:-9]: v for k, v in noms_jeu.items()
              if k.endswith(".creature") and len(k) == 15}
    with open(NOMS, encoding="utf-8") as f:
        mps = json.load(f)["mp"]
    # Code d'espece (3 lettres) -> espece de KipeeCraft, d'apres les fiches
    # des MP : m0590ckhca01 est une MP de Kipee, "ckh".
    especes = {}
    for cle, mp in mps.items():
        for fiche in mp.get("fiches", []):
            if fiche[5:8] != "dxa":
                especes[fiche[5:8]] = cle.split("_")[2]
    # Le type de chaque matiere ("m0518" -> "Skin"), d'apres KipeeCraft.
    types = {}
    for cle, mp in mps.items():
        for fiche in mp.get("fiches", []):
            types[fiche[:5]] = cle.split("_")[3]
    # **Les MP de chaque boss viennent du jeu, pas de KipeeCraft.** Sa table
    # ignore les MP que personne n'a encore saisies (Capryni supreme des
    # Primes...) ; le pack nomme toutes celles qui existent :
    # m<matiere><espece><eco><grade>01.sitem, grade d excellent, e supreme.
    def butin(code: str, eco: str, roi: bool) -> list[list[str]]:
        motif = re.compile(rf"m\d{{4}}{code}{eco}{'e' if roi else 'd'}01\.sitem")
        # Seules les matieres dont KipeeCraft connait le type (sur une autre
        # espece ou un autre grade) : la viande, le sang, le poil ou le crane,
        # vieux objets "de premier ordre" ou "exceptionnels", n'en sont pas.
        return sorted([k, types[k[:5]]] for k in noms_jeu
                      if motif.fullmatch(k) and k[:5] in types)
    lettre = {e: l for l, e in ECOS.items()}
    # Nom d'un roi -> code de son espece, d'apres ses fiches (chiffre 7).
    code_roi = {}
    for s, nom in fiches.items():
        if s[5] == "7":
            code_roi.setdefault(nom, set()).add(s[:3])

    traduction = lieux_fr(dossier)
    connus = {}                       # (nom, qualite) -> lieu precis
    for b in lire_boss():
        if b["q"] not in (210, 220, 260, 270):
            continue
        morceaux = b["lieu"].split(", ") if b["lieu"] else []
        connus.setdefault((cle_nom(b["nom"]), b["q"]), []).append(
            ", ".join(traduction.get(p, p) for p in morceaux) or "Kitinière")

    mobs, souci = [], False
    # Les rois du releve : un par nom et qualite, avec toutes ses regions.
    rois = {}
    for region, (q, noms_rois) in RELEVE.items():
        for nom in noms_rois.split():
            rois.setdefault((nom, q), []).append(region)
    for (nom, q), regions in rois.items():
        codes = code_roi.get(nom, set())
        eco = next((e for s, e in SUFFIXES.items() if nom.endswith(s)), None)
        if len(codes) != 1 or next(iter(codes)) not in especes or not eco:
            print(f"Roi introuvable dans le jeu : {nom}", file=sys.stderr)
            souci = True
            continue
        code = next(iter(codes))
        mobs.append({"nom": nom, "espece": especes[code], "q": q,
                     "roi": True, "eco": eco, "lieu": ", ".join(regions),
                     "mps": butin(code, lettre[eco], True)})
    # Les nommes : leurs fiches (chiffre 5), lieu d'apres Ballistic Mystix.
    for s, nom in fiches.items():
        cle = (s[5], s[4])
        if s[5] != "5" or cle not in QUALITES or s[3] not in ECOS or s[:3] not in especes:
            continue
        # "Kincher nomme" : une fiche sans vrai nom, jamais en jeu.
        if "nommé" in nom:
            continue
        q, eco = QUALITES[cle], ECOS[s[3]]
        lieux = connus.get((cle_nom(nom), q))
        mobs.append({"nom": nom, "espece": especes[s[:3]], "q": q, "roi": False,
                     "eco": eco, "lieu": " · ".join(lieux) if lieux else "",
                     "mps": butin(s[:3], s[3], False)})
    if souci:
        return 1

    # Un meme nom deux fois (une fiche par variante) : une seule ligne.
    uniques = {}
    for m in mobs:
        uniques.setdefault((m["nom"], m["q"], m["eco"]), m)
    mobs = sorted(uniques.values(), key=lambda m: (not m["roi"], -m["q"], m["nom"]))
    # Un boss par ligne : le fichier se relit et se compare facilement.
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps(m, ensure_ascii=False) for m in mobs) + "\n]\n")
    rois = sum(m["roi"] for m in mobs)
    print(f"{SORTIE} : {rois} rois, {len(mobs) - rois} nommés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
