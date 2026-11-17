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
Le journal du jeu (log_<perso>.txt) donne en plus, depuis le 17/11/2026,
  4  l'examen des ossements : « ces restes sont ceux d'un Timketh mort voici
     environ 12 heure(s) » (le roi et l'heure de sa mort, a une heure pres).
     Le jeu ne l'ecrit pas lui-meme : PadUI (padui_mobmap.lua) le recopie
     dans le journal quand /chatLog est actif.
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
SORTES = {1: "vu", 2: "tué", 3: "ossements", 4: "mort (examen des ossements, à 1 h près)"}
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


# Ajout (17/11) : le journal de discussion du jeu (save/log_<perso>.txt), qui
# garde tout depuis le premier lancement. On y retrouve les morts de rois
# meme quand un autre joueur a donne le dernier coup (PadUI ne voit alors pas
# de « Vous avez tue ») : apres les derniers coups ou sorts du joueur sur le
# roi, sa ligne d'XP, « sur un cadavre » ou le butin supreme d'un membre.
# Les reperages : « Vous ciblez un <roi> » et les annonces « roi <nom> » des
# canaux guilde, equipe, univers et alentours (recus seulement en ligne).
# Lecture par morceaux : ~/jeu/ryzom/rois/journal_<perso>.json garde l'octet
# atteint et les evenements trouves ; chaque lancement ne lit que la suite.
COMBAT = {"DG", "DGM", "SPLM", "MISM", "DMG", "DGS", "MIS"}
ANNONCES = {"GUILD", "TEAM", "UNIVERSE", "AROUND"}
GROUPE = 300             # s : deux lignes de combat plus espacees = deux combats
APRES_MORT = 180         # s : signe de mort au plus tard apres le dernier coup
LIGNE = re.compile(r"^(\d{4}/\d\d/\d\d \d\d:\d\d:\d\d) \(([^)]*)\) \* (.*)$")
REGION = re.compile(r"^Vous êtes (?:dans|sur|à|au|aux|en) (.+?)\.")
VERSION_CACHE = 3        # 2 : ossements et regions ; 3 : examen des ossements (17/11) ; autre = tout relire
OS_APRES_MORT = 900      # s : des ossements si vite apres une mort sont les siens
# L'examen des ossements (ligne recopiee par PadUI) : le roi et depuis quand
# il est mort. Deux examens a moins de 2 h pour le meme roi = la meme mort.
EXAMEN = re.compile(r"ces restes sont ceux d['\u2019]une? (.+?) morte? voici environ (\d+) (minute|heure|jour)")
UNITES = {"minute": 60, "heure": 3600, "jour": 86400}
MEME_MORT = 7200
# Les depots de la guilde (xiom.be/padui/deposer.php), lus avec le code du
# site garde par l'installateur PadUI ; derniere copie gardee hors ligne.
DONNEES = "https://xiom.be/padui/donnees.php"
REGLAGES_INSTALLATEUR = os.path.expanduser("~/.config/La Lune Eternelle/PadUI-Installateur.conf")
COPIE_GUILDE = os.path.expanduser("~/jeu/ryzom/rois/guilde.json")


def rois_du_catalogue():
    if not os.path.isfile(CATALOGUE):
        return []
    return [n for n, roi in json.load(open(CATALOGUE, encoding="utf-8")).items() if roi]


def lire_journal(perso, rois):
    """Les evenements du journal du perso : [{t, k, nom, lieu}] (k : 1 vu, 2 tue, 3 ossements, 4 mort datee)."""
    chemin = os.path.join(PROFIL, "save", f"log_{perso}.txt")
    cache_f = os.path.join(os.path.dirname(HISTORIQUE), f"journal_{perso}.json")
    cache = json.load(open(cache_f, encoding="utf-8")) if os.path.isfile(cache_f) else {}
    if not os.path.isfile(chemin) or not rois:
        return cache.get("evenements", [])
    taille = os.path.getsize(chemin)
    debut = cache.get("octet", 0)
    if cache.get("version") != VERSION_CACHE:
        debut, cache = 0, {}
    if debut > taille:
        # Journal remplace ou vide : tout relire.
        debut, cache = 0, {}
    evenements = cache.get("evenements", [])
    simples = {n.lower(): n for n in rois if " " not in n}
    composes = [(n.lower(), n) for n in rois if " " in n]
    combats, signes = {}, []
    region = cache.get("region", "")
    with open(chemin, "rb") as f:
        f.seek(debut)
        brut = f.read()
    # Seulement les lignes completes : la derniere peut etre en cours d'ecriture.
    fin = brut.rfind(b"\n") + 1
    for octets in brut[:fin].split(b"\n"):
        ligne = octets.decode("utf-8", "replace")
        m = LIGNE.match(ligne)
        if not m:
            continue
        canal, txt = m.group(2), m.group(3)
        if canal == "SYSTEM/ZON":
            r = REGION.match(txt)
            if r:
                region = r.group(1)
            continue
        sous = canal.split("/")[1] if "/" in canal else ""
        e = EXAMEN.search(txt) if canal.startswith("SYSTEM") else None
        if e:
            bas = e.group(1).lower()
            nom = next((n for c, n in composes if c == bas), None) or simples.get(bas)
            if nom:
                t = time.mktime(time.strptime(m.group(1), "%Y/%m/%d %H:%M:%S"))
                mort = t - int(e.group(2)) * UNITES[e.group(3)]
                if not any(x["k"] == 4 and x["nom"] == nom and abs(x["t"] - mort) < MEME_MORT for x in evenements):
                    evenements.append({"t": mort, "k": 4, "nom": nom, "lieu": region, "examen": t})
            continue
        signe = canal == "SYSTEM/XP" or "sur un cadavre" in txt or (canal == "SYSTEM/ITMO" and "suprême" in txt)
        utile = signe or canal == "SYSTEM" or sous in COMBAT or canal in ANNONCES
        if not utile:
            continue
        t = time.mktime(time.strptime(m.group(1), "%Y/%m/%d %H:%M:%S"))
        if signe:
            signes.append(t)
            continue
        if canal == "SYSTEM" and txt.startswith("Vous ciblez Ossements"):
            evenements.append({"t": t, "k": 3, "nom": "Ossements", "lieu": region})
            continue
        bas = txt.lower()
        nom = next((n for c, n in composes if c in bas), None)
        if not nom:
            nom = next((simples[w] for w in re.findall(r"\w+", bas) if w in simples), None)
        if not nom:
            continue
        if canal == "SYSTEM" and txt.startswith("Vous ciblez"):
            evenements.append({"t": t, "k": 1, "nom": nom, "lieu": region})
        elif sous in COMBAT or (canal == "SYSTEM" and "vous attaque" in txt):
            combats.setdefault(nom, []).append(t)
        elif canal in ANNONCES and re.search(r"\broi\b", bas):
            # « roi Shooketh, niv ?, Desert Ardent, Couloir Brule, pres de ... »
            lieu = txt.split(",", 2)[2].strip(" ⚔️\u2694\ufe0f") if txt.count(",") >= 2 else ""
            evenements.append({"t": t, "k": 1, "nom": nom, "lieu": re.sub(r"@\{[0-9A-F]+\}", "", lieu)})
    signes.sort()
    for nom, ts in combats.items():
        ts.sort()
        groupes = []
        for t in ts:
            if groupes and t - groupes[-1][-1] < GROUPE:
                groupes[-1].append(t)
            else:
                groupes.append([t])
        for g in groupes:
            mort = next((s for s in signes if 0 <= s - g[-1] <= APRES_MORT), None)
            if mort:
                evenements.append({"t": mort, "k": 2, "nom": nom, "lieu": ""})
    evenements.sort(key=lambda e: e["t"])
    # Les Ossements cibles pour l'examen : l'examen dit deja tout (le roi).
    examens = [e["examen"] for e in evenements if e["k"] == 4 and "examen" in e]
    evenements = [e for e in evenements if e["k"] != 3 or not any(0 <= x - e["t"] <= 120 for x in examens)]
    os.makedirs(os.path.dirname(cache_f), exist_ok=True)
    with open(cache_f, "w", encoding="utf-8") as f:
        json.dump({"version": VERSION_CACHE, "octet": debut + fin, "region": region, "evenements": evenements},
                  f, ensure_ascii=False, indent=0)
    return evenements


def rois_de_la_guilde():
    """Les evenements deposes par la guilde : (liste, etat). Hors ligne, la
    derniere copie ; jamais bloquant (6 s au plus)."""
    import urllib.request
    mdp = ""
    if os.path.isfile(REGLAGES_INSTALLATEUR):
        for ligne in open(REGLAGES_INSTALLATEUR, encoding="utf-8", errors="replace"):
            if ligne.startswith("mdp="):
                mdp = ligne[4:].strip()
    copie = json.load(open(COPIE_GUILDE, encoding="utf-8")) if os.path.isfile(COPIE_GUILDE) else []
    if not mdp:
        return copie, "pas de code du site dans l'installateur PadUI"
    try:
        demande = urllib.request.Request(DONNEES, data=json.dumps({"mdp": mdp, "rois": True}).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(demande, timeout=6) as r:
            lus = json.load(r).get("rois", [])
    except Exception as e:  # reseau, site, reponse : la copie fait l'affaire
        return copie, f"xiom.be injoignable ({type(e).__name__}), copie précédente"
    with open(COPIE_GUILDE, "w", encoding="utf-8") as f:
        json.dump(lus, f, ensure_ascii=False, indent=0)
    return lus, "à jour"


def lieux_padui():
    """Les regions et lieux de PadUI (PadUILieux de padui_mobs.lua) :
    {nom sans article, minuscules: [(x, y), ...]}."""
    chemin = os.path.join(PROFIL, "user", "padui_mobs.lua")
    if not os.path.isfile(chemin):
        return {}
    texte = open(chemin, encoding="utf-8", errors="replace").read()
    out = {}
    for m in re.finditer(r'\{n="([^"]+)",z=\{([-\d,]+)\}\}', texte):
        v = [int(x) for x in m.group(2).split(",")]
        out.setdefault(sans_article(m.group(1)), []).append(list(zip(v[0::2], v[1::2])))
    return out


def sans_article(nom):
    return re.sub(r"^(le|la|les|l'|l’)\s*", "", nom.strip().lower())


def dedans(x, y, poly):
    """Le point est-il dans le polygone (regle du rayon)."""
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            c = not c
        j = i
    return c


def candidats(region, pops, lieux, rois):
    """Les rois dont un drapeau de pop est dans cette region."""
    trouves = set()
    for poly in lieux.get(sans_article(region), []):
        for x, y, titre in pops:
            if dedans(x, y, poly):
                for w in re.findall(r"\w+", titre.lower()):
                    if w in rois:
                        trouves.add(rois[w])
    return sorted(trouves)


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
    rois = rois_du_catalogue()
    journal = []
    for perso in persos:
        journal += [dict(e, perso=perso, journal=True) for e in lire_journal(perso, rois)]
    # Les depots de la guilde : un evenement deja connu ici (meme roi, meme
    # sorte, moins de 10 min d'ecart) n'est pas recompte.
    guilde, etat = rois_de_la_guilde()
    connus = historique + journal
    ajoutes = []
    for e in guilde:
        if any(c["nom"] == e.get("nom") and c["k"] == e.get("k") and abs(c["t"] - e.get("t", 0)) < 600
               for c in connus + ajoutes):
            continue
        ajoutes.append(dict(e, journal=True))
    def compte(liste, k):
        return sum(1 for e in liste if e["k"] == k)
    lignes = [f"Relevé des rois, refait le {time.strftime('%d/%m/%Y %H:%M')} : {len(nouvelles)} notes nouvelles, "
              f"{len(historique)} en tout ; journal du jeu : {compte(journal, 2)} morts, "
              f"{compte(journal, 1)} repérages, {compte(journal, 3)} ossements, {compte(journal, 4)} examens ; dépôts de la guilde ({etat}) : "
              f"{len(ajoutes)} événements en plus."]
    tout = sorted(historique + journal + ajoutes, key=lambda n: n["t"])
    if not tout:
        lignes.append("Rien encore : joue avec Environs ouvert ; les notes arrivent au lancement suivant du jeu.")
    else:
        lignes += rapport(tout, drapeaux_de_pop(persos), {r.lower(): r for r in rois})
    texte = "\n".join(lignes) + "\n"
    with open(RAPPORT, "w", encoding="utf-8") as f:
        f.write(texte)
    print(texte, end="")


def rapport(historique, pops, rois=None):
    lignes = []
    lieux = lieux_padui()
    for n in historique:
        # Les evenements du journal n'ont pas de position, parfois un lieu.
        n["endroit"] = n.get("lieu") or "journal" if n.get("journal") else endroit(n, pops)
    # Les ossements de sa propre victime (moins de 15 min apres une mort
    # notee par la meme source) ne disent rien de plus.
    morts = {}
    gardes = []
    for n in historique:
        source = n.get("de", "ici")
        if n["k"] in (2, 4):
            morts[source] = n["t"]
        if n["k"] == 3 and n["t"] - morts.get(source, -1e12) < OS_APRES_MORT:
            continue
        gardes.append(n)
    historique = gardes
    # Roi par roi ; les ossements, par endroit. Des ossements dans une region
    # ou un seul roi a un drapeau de pop comptent aussi comme sa mort.
    groupes = {}
    for n in historique:
        cle = n["nom"] if n["k"] != 3 else "Ossements — " + n["endroit"]
        groupes.setdefault(cle, []).append(n)
        if n["k"] == 3 and n.get("journal") and rois:
            n["candidats"] = candidats(n["endroit"], pops, lieux, rois)
            if len(n["candidats"]) == 1:
                groupes.setdefault(n["candidats"][0], []).append(n)
    for liste in groupes.values():
        liste.sort(key=lambda n: n["t"])
    bornes = []
    for cle in sorted(groupes):
        # Un meme combat ou passage donne des dizaines de lignes : un roi vu
        # moins de 30 min apres l'evenement precedent n'est pas recompte.
        liste = []
        for n in groupes[cle]:
            if n["k"] == 1 and liste and n["t"] - liste[-1]["t"] < 1800:
                continue
            # Une mort datee par l'examen et une mort vue (ou un autre examen)
            # a moins de 2 h : la meme mort ; la mort vue est plus precise.
            if n["k"] in (2, 4) and liste and liste[-1]["k"] in (2, 4) and n["t"] - liste[-1]["t"] < MEME_MORT:
                if n["k"] == 2 and liste[-1]["k"] == 4:
                    liste[-1] = n
                continue
            liste.append(n)
        groupes[cle] = liste
    for cle in sorted(groupes):
        lignes.append(f"\n{cle}")
        liste = groupes[cle]
        for n in liste:
            heure = time.strftime("%d/%m %H:%M", time.localtime(n["t"]))
            ou = f"  ({n['endroit']})" if n["k"] != 3 or not cle.startswith("Ossements") else ""
            if n["k"] == 3 and cle.startswith("Ossements") and n.get("candidats") is not None:
                ou = "  (rois possibles : " + (", ".join(n["candidats"]) or "aucun drapeau de pop ici") + ")"
            de = f"  [{n['de']}]" if n.get("de") else ""
            lignes.append(f"  {heure}  {SORTES[n['k']]}{ou}{de}")
        # Repops mesures : une mort (ou ses ossements), puis la premiere fois
        # qu'on le revoit.
        for i, n in enumerate(liste):
            if n["k"] not in (2, 3, 4) or cle.startswith("Ossements"):
                continue
            revu = next((m for m in liste[i + 1:] if m["k"] == 1 and m["t"] - n["t"] > 600), None)
            if revu:
                bornes.append((revu["t"] - n["t"], cle))
                lignes.append(f"  -> repop observé : {duree(revu['t'] - n['t'])} au plus "
                              f"({'mort vers' if n['k'] == 4 else 'tué'} {time.strftime('%d/%m %H:%M', time.localtime(n['t']))}, "
                              f"revu {time.strftime('%d/%m %H:%M', time.localtime(revu['t']))})")
    if bornes:
        # En tete : les rois revus le plus vite apres une mort (un maximum :
        # le roi a pu revenir bien avant que quelqu'un repasse).
        tete = ["", "Revus le plus vite après une mort (le repop est au plus de) :"]
        for s, cle in sorted(bornes)[:10]:
            tete.append(f"  {duree(s):>10}  {cle}")
        lignes = tete + lignes
    return lignes


if __name__ == "__main__":
    main()
