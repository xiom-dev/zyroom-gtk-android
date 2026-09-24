"""Ce que le forage a rendu, relevé dans le journal du jeu.

Ryzom écrit le contenu de sa fenêtre de chat dans un fichier dès qu'on tape
`/chatLog` — le canal système compris, donc chaque prise, horodatée à la
seconde :

    (SYSTEM/ITM) * Vous obtenez 3 Ambres excellents / Sha des Primes Racines
                   de qualité 183.

L'heure donne le cycle météo, le cycle donne la condition et la saison, et le
canal `ZON` donne la zone. Une prise devient ainsi une case du relevé de la
guilde — **sans que personne la coche**.

**Rien n'est deviné.** Si la météo de ce cycle n'a pas été notée, ou si la
zone n'est pas connue, la prise est écartée plutôt qu'approximée.

Trois fichiers, dans le dossier de données de l'application :

* `forage/journal.log` — les seules lignes de forage, recopiées du jeu. Ni la
  guilde ni les tells n'y entrent : elles ne sortent pas du fichier du jeu ;
* `forage/meteo.jsonl` — les cycles à venir, notés à chaque fois que l'écran
  météo interroge l'API. Sans ce carnet, la condition d'un cycle passé est
  perdue : l'API ne rend que le présent et six heures d'avance ;
* `forage/posees.json` — ce qu'on a déjà coché, pour ne pas redemander au
  site ce qu'on sait déjà.

**Le journal du jeu n'est jamais modifié.** Le paquet Flatpak lit la maison
en lecture seule, et c'est très bien ainsi : on retient où l'on s'est arrêté
et on reprend là. Le fichier du jeu appartient au jeu.
"""
from __future__ import annotations

import datetime
import glob
import json
import os
import re
import urllib.error
import urllib.request

from . import forage, meteo
from .config import data_dir

#: L'adresse du relevé commun de la guilde.
SITE = "https://xiom.be/forage/releve.php"

#: Les secrets, hors de l'application : la clef d'écriture et le mot de passe
#: de lecture, ceux-là mêmes que la page emploie.
#:
#: **Dans `~/.config/zyroom`, et non dans le dossier de l'application.** Ils
#: sont partagés avec l'outil qui fabrique la page du relevé, et ils ne
#: doivent entrer ni dans le dépôt ni dans le bac à sable du paquet.
_SECRETS = os.path.expanduser("~/.config/zyroom")
CLE_FICHIER = os.path.join(_SECRETS, "forage.cle")
MDP_FICHIER = os.path.join(_SECRETS, "forage.motdepasse")

#: Là où le jeu écrit son journal de chat, un fichier par personnage.
JOURNAUX_DU_JEU = "~/.local/share/Ryzom/*/save/log_*.txt"

#: Les canaux du jeu qui parlent de forage, et eux seuls.
#:
#: ITM     ce qu'on trouve et ce qu'on obtient
#: ITMF    les échecs, dont « ne se trouvent pas… étant données les conditions
#:         climatiques » — le jeu y énonce la règle du relevé
#: SPL     la source explose, le nuage toxique
#: ZON     où l'on se tient, la seule façon de savoir dans quelle zone forer
#: CHK     spécialisation, terrain, distance
#: XP      « points gagnés pour la prospection », qui marque une prise
CANAUX = frozenset(("SYSTEM/ITM", "SYSTEM/ITMF", "SYSTEM/SPL", "SYSTEM/ZON",
                    "SYSTEM/CHK", "SYSTEM/CHKCB", "SYSTEM/XP"))

#: Sur le canal SYSTEM nu tout est mêlé — sauvegardes, combats, cibles, et la
#: liste des joueurs en ligne. On n'en prend que l'état d'une source et le nom
#: d'une région. Les noms des autres joueurs n'ont rien à faire ici.
_UTILE = re.compile(r"La source |région [\"«]")

_LIGNE = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \((SYSTEM[^)]*)\) "
                    r"\* (.*)$")
_COULEUR = re.compile(r"@\{[0-9A-Fa-f]{4}\}")
_PRISE = re.compile(r"Vous obtenez \d+ (.+?) de qualité \d+")
_LIEU = re.compile(r"Vous (?:êtes dans|quittez) (?:le |la |les |l')?(.+?)\.")

#: Les saisons telles que la page du relevé les nomme, dans l'ordre de l'API.
SAISONS_PAGE = ("Printemps", "Été", "Automne", "Hiver")

#: Les conditions, idem.
CONDITIONS_PAGE = {"worst": "Worst", "bad": "Bad",
                   "good": "Good", "best": "Best"}

#: Ce que le jeu écrit dans le nom d'une matière, vers la colonne de la page.
QUALITES_PAGE = (("supr", "Supp"), ("excellent", "XL"), ("choix", "Choix"))


def dossier() -> str:
    chemin = os.path.join(data_dir(), "forage")
    os.makedirs(chemin, exist_ok=True)
    return chemin


def _f(nom: str) -> str:
    return os.path.join(dossier(), nom)


def _lire(nom: str, defaut):
    try:
        with open(_f(nom), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return defaut


def _ecrire(nom: str, valeur) -> None:
    with open(_f(nom), "w", encoding="utf-8") as fh:
        json.dump(valeur, fh, ensure_ascii=False)


# ------------------------------------------------------------- le carnet météo
def noter_meteo(releve) -> None:
    """Note les cycles d'un relevé, pour pouvoir les retrouver plus tard.

    Appelé à chaque fois que l'écran météo interroge l'API — donc sans une
    requête de plus. C'est ce carnet qui permet de dater une prise : passé six
    heures, l'API ne sait plus dire le temps qu'il a fait.
    """
    cycles = releve.cycles_des_primes() if releve is not None else []
    if not cycles or not 0 <= releve.saison < 4:
        return
    ligne = {
        "releve_a": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "heure_atys": releve.heure_atys,
        "cycle_courant": releve.cycle_courant,
        "saison": releve.saison,
        "cycles": {c.cycle: c.condition for c in cycles},
    }
    with open(_f("meteo.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def _carnet() -> tuple:
    """(condition par cycle, saison par cycle de référence, ancre du temps)."""
    conditions, reperes, ancre = {}, [], None
    try:
        lignes = open(_f("meteo.jsonl"), encoding="utf-8").read().splitlines()
    except OSError:
        return {}, [], None
    for brut in lignes:
        try:
            d = json.loads(brut)
        except ValueError:
            continue
        for c, cond in d["cycles"].items():
            conditions[int(c)] = cond
        if 0 <= d.get("saison", -1) < 4:
            reperes.append((int(d["cycle_courant"]), int(d["saison"])))
        ancre = (datetime.datetime.fromisoformat(d["releve_a"]),
                 float(d["heure_atys"]))
    return conditions, reperes, ancre


# --------------------------------------------------------- le journal du jeu
def moissonner() -> int:
    """Recopie les lignes de forage nouvelles. Rend leur nombre.

    On garde où l'on s'est arrêté dans chaque fichier : le journal du jeu
    n'est ni vidé ni touché — l'application le lit en lecture seule, et c'est
    au jeu qu'il appartient.
    """
    reperes = _lire("lu.json", {})
    gardees = 0
    for chemin in sorted(glob.glob(os.path.expanduser(JOURNAUX_DU_JEU))):
        try:
            taille = os.path.getsize(chemin)
        except OSError:
            continue
        depuis = reperes.get(chemin, 0)
        if taille < depuis:
            depuis = 0          # le fichier a été vidé : on repart du début
        if taille == depuis:
            continue
        try:
            with open(chemin, encoding="utf-8", errors="replace") as fh:
                fh.seek(depuis)
                neuf = fh.read()
        except OSError:
            continue
        reperes[chemin] = taille
        perso = os.path.basename(chemin)[4:-4]
        lignes = []
        for brut in neuf.splitlines():
            trouve = _LIGNE.match(_COULEUR.sub("", brut))
            if not trouve:
                continue
            canal, texte = trouve.group(2), trouve.group(3)
            if canal in CANAUX or _UTILE.search(texte):
                lignes.append(f"{perso}\t{_COULEUR.sub('', brut).rstrip()}\n")
        if lignes:
            with open(_f("journal.log"), "a", encoding="utf-8") as fh:
                fh.writelines(lignes)
            gardees += len(lignes)
    _ecrire("lu.json", reperes)
    return gardees


def _matieres() -> dict:
    """{nom en minuscules: Nom} — les quarante-sept noms du relevé."""
    noms = {m for t in (forage.SUPREMES, forage.EXCELLENTES)
            for z in t.values() for _f_, m in z}
    return {n.lower(): n for n in noms}


def prises() -> list:
    """Les prises du journal, chacune ramenée à une case du relevé."""
    conditions, reperes, ancre = _carnet()
    if ancre is None:
        return []
    depart, heure0 = ancre
    mats = _matieres()

    def saison_pres_de(cycle: int) -> int:
        # Une saison dure quatre jours et demi réels, soit mille quatre cents
        # cycles : n'importe quel relevé de la même soirée la donne juste.
        return min(reperes, key=lambda r: abs(r[0] - cycle))[1] if reperes else -1

    zone, sortie = None, []
    try:
        lignes = open(_f("journal.log"), encoding="utf-8").read().splitlines()
    except OSError:
        return []
    for brut in lignes:
        if "\t" not in brut:
            continue
        ligne = brut.split("\t", 1)[1]
        lieu = _LIEU.search(ligne)
        if lieu and lieu.group(1) in meteo.ZONES:
            zone = lieu.group(1)
        prise = _PRISE.search(ligne)
        if not prise or zone is None:
            continue
        texte = prise.group(1).lower()
        # Le jeu nomme les matières de deux façons — « Ambres excellents /
        # Sha » mais « Fibres de choix de Dzao » — d'où la recherche du nom
        # n'importe où dans la phrase plutôt qu'à une place convenue.
        matiere = next((n for bas, n in mats.items() if bas in texte), None)
        qualite = next((q for mot, q in QUALITES_PAGE if mot in texte), None)
        if matiere is None or qualite is None:
            continue
        quand = datetime.datetime.strptime(
            ligne[:19], "%Y/%m/%d %H:%M:%S").astimezone()
        cycle = int((heure0 + (quand - depart).total_seconds() / 180) // 3)
        condition, saison = conditions.get(cycle), saison_pres_de(cycle)
        if condition is None or not 0 <= saison < 4:
            continue            # hors du carnet : on n'approxime pas
        sortie.append("|".join((zone, SAISONS_PAGE[saison], matiere, qualite,
                                CONDITIONS_PAGE[condition])))
    return list(dict.fromkeys(sortie))


# ------------------------------------------------------------------- le site
def _secret(chemin: str) -> str:
    with open(chemin, encoding="utf-8") as fh:
        return fh.read().strip()


def _poste(corps: dict) -> dict:
    requete = urllib.request.Request(
        SITE, data=json.dumps(corps).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return json.load(reponse)
    except urllib.error.HTTPError as souci:
        return {"erreur": f"HTTP {souci.code}"}


def envoyer() -> dict:
    """Coche sur le relevé commun ce que le journal confirme.

    Rend un bilan : combien de prises lues, combien de croix posées, et ce
    qui a manqué. **Une case déjà vue en jeu n'est jamais écrasée** — une
    observation humaine passe avant la nôtre.
    """
    lues = moissonner()
    cases = prises()
    connues = set(_lire("posees.json", []))
    neuves = [c for c in cases if c not in connues]
    bilan = {"lignes": lues, "prises": len(cases), "posees": 0,
             "deja": len(cases) - len(neuves), "erreur": ""}
    if not neuves:
        return bilan
    try:
        jeton = _poste({"action": "entrer",
                        "mdp": _secret(MDP_FICHIER)}).get("jeton", "")
        if not jeton:
            bilan["erreur"] = "mot de passe refusé"
            return bilan
        requete = urllib.request.Request(SITE, headers={"X-Forage": jeton})
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            tableau = json.load(reponse).get("cases", {})
        cle = _secret(CLE_FICHIER)
    except (OSError, ValueError) as souci:
        bilan["erreur"] = str(souci)
        return bilan

    vues = set(connues)
    for case in neuves:
        actuel = tableau.get(case)
        actuel = actuel.get("v") if isinstance(actuel, dict) else actuel
        if actuel == "x":
            vues.add(case)
            continue
        if _poste({"cle": cle, "case": case, "valeur": "x",
                   "foreuse": "relevé auto"}).get("ok"):
            bilan["posees"] += 1
            vues.add(case)
    _ecrire("posees.json", sorted(vues))
    return bilan
