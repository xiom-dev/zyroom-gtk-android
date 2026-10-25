#!/usr/bin/env python3
"""Drapeaux de forage pour PadUI : seuls ceux des sources qui sortent.

Croise trois fichiers :
- les drapeaux du joueur, `save/landmarks_<perso>.xml` du client Ryzom : on
  garde ceux des Primes dont le titre nomme une matière (« oath XL »,
  « spot resine dung 250 », « colle XL »…) ;
- `donnees/forage-releve-guilde.json` : le relevé de xiom.be/forage, qui dit
  quelle matière sort, zone par zone, saison par saison, temps par temps
  (seules les cases vues en jeu, « x ») ;
- `zyroom-gtk/zyroom/gisements.py` : les positions des gisements des Primes,
  qui disent dans quelle zone tombe chaque drapeau.

Écrit `padui_sources_data.lua`, que `padui_sources.lua` lit en jeu : il
masque les drapeaux du joueur et ne réaffiche que ceux des matières qui
sortent avec la saison et le temps du moment, comme l'écran Météo de ZyRoom.

    python3 outils/padui-sources.py [perso] [dossier_profil_ryzom]
"""

import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "zyroom-gtk"))
from zyroom.gisements import GISEMENTS, LIBELLES  # noqa: E402

RELEVE = os.path.join(RACINE, "donnees", "forage-releve-guilde.json")
PERSO = sys.argv[1] if len(sys.argv) > 1 else "xiom"
PROFIL = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/.local/share/Ryzom/0")
DRAPEAUX = os.path.join(PROFIL, "save", f"landmarks_{PERSO}.xml")
SORTIE = os.path.join(PROFIL, "user", "padui_sources_data.lua")
CONTINENTS = ("terre", "sources")  # les Primes
# Noms français des matières dans les titres des drapeaux -> nom du relevé.
ALIAS = {"colle": "Glue", "corne": "Horny", "cornee": "Horny", "grosse": "Big",
         "ardente": "Redhot", "mignone": "Cuty", "mignonne": "Cuty",
         "patee": "Patee", "scratch": "Scrath", "splint": "Splinter", "shal": "Sha"}
# Au-delà, le drapeau n'est pas sur un gisement connu de cette matière.
LOIN = 600


def lua(texte: str) -> str:
    return "'" + texte.replace("\\", "\\\\").replace("'", "\\'") + "'"


def sans_accent(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte.lower())
                   if unicodedata.category(c) != "Mn")


def main() -> int:
    with open(RELEVE, encoding="utf-8") as f:
        releve = json.load(f)
    # (zone, matiere) -> {"Supp": {"Saison|Temps"}, "XL": {...}}
    moments = {}
    for cle, valeur in releve["cases"].items():
        if valeur == "x":
            zone, saison, matiere, qualite, temps = cle.split("|")
            moments.setdefault((zone, matiere), {}).setdefault(qualite, set()).add(
                saison + "|" + temps)
    matieres = {sans_accent(m): m for (_z, m) in moments}
    matieres.update(ALIAS)

    def gisements_de(matiere):
        # Comme meteo.positions_des_primes : positions rangées sous « supreme ».
        couples = [c for (_f, m), c in LIBELLES.items() if m == matiere]
        return [p for c in couples for p in GISEMENTS.get(("supreme",) + c, ((), ()))[1]]

    drapeaux, ignores = [], []
    for groupe in ET.parse(DRAPEAUX).getroot():
        if groupe.get("continent") not in CONTINENTS:
            continue
        for d in groupe:
            titre = d.get("title", "")
            mots = re.findall(r"\w+", sans_accent(titre))
            matiere = next((matieres[m] for m in mots if m in matieres), None)
            if not matiere:
                ignores.append(titre)
                continue
            x, y = float(d.get("x")), float(d.get("y"))
            proches = sorted(gisements_de(matiere), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
            if not proches or (proches[0][0] - x) ** 2 + (proches[0][1] - y) ** 2 > LOIN ** 2:
                ignores.append(titre)
                continue
            drapeaux.append((matiere, proches[0][2], x, y, titre.strip()))

    # Tous les drapeaux du joueur, pour que PadUI puisse les reafficher lui-meme
    # quand le filtre de la carte masque les originaux. mob = nom d'un nomme
    # ou d'un roi du catalogue PadUI present dans le titre.
    catalogue = {}
    texte_cat = open(os.path.join(PROFIL, "user", "padui_mob_catalog.lua"), encoding="utf-8").read()
    for m in re.finditer(r"\[(?:'((?:[^'\\]|\\.)*)')\]=\{[^}]*kind='(\w+)'", texte_cat):
        catalogue[sans_accent(m.group(1).replace("\\'", "'"))] = (m.group(1).replace("\\'", "'"), m.group(2) == "boss")
    tous = []
    for groupe in ET.parse(DRAPEAUX).getroot():
        for d in groupe:
            titre = d.get("title", "").strip()
            mob = next((catalogue[w] for w in re.findall(r"[\w'-]+", sans_accent(titre)) if w in catalogue), None)
            tous.append((groupe.get("continent"), float(d.get("x")), float(d.get("y")), titre, mob))

    def table(ensemble):
        return ",".join("[%s]=true" % lua(m) for m in sorted(ensemble))

    lignes_m = [" [%s]={supp={%s},xl={%s}}," % (lua(z + "|" + m), table(q.get("Supp", ())),
                                                 table(q.get("XL", ())))
                for (z, m), q in sorted(moments.items())]
    lignes_d = [" {mp=%s,zone=%s,x=%.2f,y=%.2f,title=%s}," % (lua(m), lua(z), x, y, lua(t))
                for m, z, x, y, t in drapeaux]
    texte = ("-- Fichier produit par outils/padui-sources.py (depot xiom-dev) :\n"
             "-- ne pas modifier a la main. Drapeaux de %s, releve de xiom.be/forage\n"
             "-- du %s, positions des gisements de ZyRoom.\n"
             "PadUISourcesData = {\n releve=%s,\n"
             " moments={\n%s\n },\n flags={\n%s\n },\n landmarks={\n%s\n }\n}\n"
             % (PERSO, releve.get("_releve_le", "?"), lua(releve.get("_releve_le", "?")),
                "\n".join(lignes_m), "\n".join(lignes_d),
                "\n".join(" {c=%s,x=%.2f,y=%.2f,title=%s%s}," % (
                    lua(c), x, y, lua(t), (",mob=%s,king=%s" % (lua(mob[0]), "true" if mob[1] else "false")) if mob else "")
                    for c, x, y, t, mob in tous)))
    with open(SORTIE, "w", encoding="utf-8") as f:
        f.write(texte)
    print(f"{len(drapeaux)} drapeaux de forage écrits dans {SORTIE}")
    print(f"{len(tous)} drapeaux en tout, dont {sum(1 for t in tous if t[4])} de rois/nommés")
    print(f"{len(ignores)} drapeaux des Primes sans matière reconnue : {ignores}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
