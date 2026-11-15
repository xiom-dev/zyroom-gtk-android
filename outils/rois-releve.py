#!/usr/bin/env python3
"""Releve des rois : ce que PadUI a note en jeu, et les temps de repop.

    python3 ~/jeu/ryzom/zyroom/xiom-dev/outils/rois-releve.py [perso ...]

Lance seul par l'enveloppe du jeu (ryzom_client) a chaque demarrage : les
notes de la partie d'avant rejoignent l'historique, le rapport est refait
dans ~/jeu/ryzom/rois/repops.txt. Sans perso : tous ceux du profil
(RYZOM_PROFIL, 0 par defaut).

PadUI (releve_rois de l'installateur, 11/11/2026) note dans une memoire
circulaire de 48 places, que le jeu garde dans save/interface_<perso>.icfg
en quittant :
  1  un roi qui apparait dans Environs (fenetre ouverte) ;
  2  « Vous avez tue le <roi> » ;
  3  « Vous ciblez Ossements » (un roi mort la, le nom ne se lit que sur
     place : Ludo pose alors un drapeau a son nom).
Chaque note : l'heure, le nom, la position (celle de la creature ciblee ou
vue, sinon du joueur).

Ce script relit l'icfg (jeu ferme : il n'est ecrit qu'en quittant), ajoute
les notes nouvelles a l'historique ~/jeu/ryzom/rois/releve.json (les 48
places tournent : le lancer apres chaque partie pour ne rien perdre), nomme
chaque endroit par le drapeau de pop le plus proche (les tiens, ceux de
Nizyros, Eleanide et Thysela dans ~/jeu/ryzom/landmarks) et affiche, roi par
roi, ce qui a ete vu et les repops mesures (tue -> revu).
"""
import json
import os
import re
import struct
import sys
import time

PROFIL = os.path.expanduser("~/.local/share/Ryzom/" + os.environ.get("RYZOM_PROFIL", "0"))
HISTORIQUE = os.path.expanduser("~/jeu/ryzom/rois/releve.json")
RAPPORT = os.path.expanduser("~/jeu/ryzom/rois/repops.txt")
DRAPEAUX_AUTRES = os.path.expanduser("~/jeu/ryzom/landmarks")
CATALOGUE = os.path.expanduser("~/jeu/ryzom/padui/installeur/paquet/donnees/catalogue.json")
PLACES = 48
SORTES = {1: "vu", 2: "tué", 3: "ossements"}
PROCHE = 200.0           # m : un drapeau de pop plus loin ne nomme pas l'endroit


def lire_icfg(chemin):
    """Les notes de la memoire : [{t, k, nom, x, y}]."""
    d = open(chemin, "rb").read()

    def val(nom):
        cle = nom.encode()
        i = d.find(struct.pack("<I", len(cle)) + cle)
        return None if i < 0 else struct.unpack_from("<q", d, i + 4 + len(cle))[0]
    notes = []
    for i in range(PLACES):
        base = f"UI:SAVE:PADUI:ROIS:{i}:"
        t, k = val(base + "T"), val(base + "K")
        if not t or k not in SORTES:
            continue
        n = val(base + "LEN") or 0
        octets = b""
        for b in range(8):
            v = (val(base + f"NAME:{b}") or 0) & 0xFFFFFFFF
            octets += struct.pack("<I", v)
        nom = octets[:n].decode("utf-8", "replace")
        notes.append({"t": t, "k": k, "nom": nom, "x": val(base + "X") or 0, "y": val(base + "Y") or 0})
    return notes


def drapeaux_de_pop(persos):
    """Les drapeaux dont le titre nomme un roi du catalogue : [(x, y, titre)]."""
    rois = set()
    if os.path.isfile(CATALOGUE):
        rois = {n.lower() for n, roi in json.load(open(CATALOGUE, encoding="utf-8")).items() if roi}
    fichiers = [os.path.join(PROFIL, "save", f"landmarks_{p}.xml") for p in persos]
    if os.path.isdir(DRAPEAUX_AUTRES):
        fichiers += [os.path.join(DRAPEAUX_AUTRES, f) for f in sorted(os.listdir(DRAPEAUX_AUTRES))]
    out = []
    for f in fichiers:
        if not os.path.isfile(f):
            continue
        texte = open(f, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'<landmark type="\d+" x="([-\d.]+)" y="([-\d.]+)" title="([^"]*)"', texte):
            titre = m.group(3).replace("&#xE8;", "è").replace("&#xE9;", "é").strip()
            if any(w in rois for w in re.findall(r"\w+", titre.lower())):
                out.append((float(m.group(1)), float(m.group(2)), titre))
    return out


def endroit(note, pops):
    meilleur, titre = PROCHE ** 2, None
    for x, y, t in pops:
        d = (x - note["x"]) ** 2 + (y - note["y"]) ** 2
        if d <= meilleur:
            meilleur, titre = d, t
    return titre or "hors des drapeaux de pop"


def duree(s):
    h, m = divmod(int(s) // 60, 60)
    return f"{h} h {m:02d}" if h else f"{m} min"


def main():
    save = os.path.join(PROFIL, "save")
    persos = sys.argv[1:] or sorted(re.findall(r"^interface_(.+)\.icfg$", f)[0]
                                    for f in os.listdir(save) if re.match(r"^interface_.+\.icfg$", f))
    historique = json.load(open(HISTORIQUE, encoding="utf-8")) if os.path.isfile(HISTORIQUE) else []
    connues = {(n["t"], n["k"], n["nom"]) for n in historique}
    nouvelles = []
    for perso in persos:
        icfg = os.path.join(save, f"interface_{perso}.icfg")
        if not os.path.isfile(icfg):
            print(f"introuvable : {icfg}")
            continue
        for n in lire_icfg(icfg):
            if (n["t"], n["k"], n["nom"]) not in connues:
                connues.add((n["t"], n["k"], n["nom"]))
                nouvelles.append(dict(n, perso=perso))
    historique = sorted(historique + nouvelles, key=lambda n: n["t"])
    os.makedirs(os.path.dirname(HISTORIQUE), exist_ok=True)
    with open(HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=0)
    lignes = [f"Relevé des rois, refait le {time.strftime('%d/%m/%Y %H:%M')} : {len(nouvelles)} notes nouvelles, "
              f"{len(historique)} en tout."]
    if not historique:
        lignes.append("Rien encore : joue avec Environs ouvert ; les notes arrivent au lancement suivant du jeu.")
    else:
        lignes += rapport(historique, drapeaux_de_pop(persos))
    texte = "\n".join(lignes) + "\n"
    with open(RAPPORT, "w", encoding="utf-8") as f:
        f.write(texte)
    print(texte, end="")


def rapport(historique, pops):
    lignes = []
    for n in historique:
        n["endroit"] = endroit(n, pops)
    # Roi par roi ; les ossements, par endroit.
    groupes = {}
    for n in historique:
        cle = n["nom"] if n["k"] != 3 else "Ossements — " + n["endroit"]
        groupes.setdefault(cle, []).append(n)
    for cle in sorted(groupes):
        lignes.append(f"\n{cle}")
        liste = groupes[cle]
        for n in liste:
            heure = time.strftime("%d/%m %H:%M", time.localtime(n["t"]))
            ou = "" if n["k"] == 3 else f"  ({n['endroit']})"
            lignes.append(f"  {heure}  {SORTES[n['k']]}{ou}")
        # Repops mesures : un tue, puis la premiere fois qu'on le revoit.
        for i, n in enumerate(liste):
            if n["k"] != 2:
                continue
            revu = next((m for m in liste[i + 1:] if m["k"] == 1), None)
            if revu:
                lignes.append(f"  -> repop observé : {duree(revu['t'] - n['t'])} au plus "
                              f"(tué {time.strftime('%d/%m %H:%M', time.localtime(n['t']))}, "
                              f"revu {time.strftime('%d/%m %H:%M', time.localtime(revu['t']))})")
    return lignes


if __name__ == "__main__":
    main()
