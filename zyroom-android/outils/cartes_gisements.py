#!/usr/bin/env python3
"""Récupère les mini-cartes de gisements du tracker d'atys.us.

Ce que ça rapporte : pour chaque matière suprême ou excellente, l'image de
l'endroit où elle sort — une vue de 512 × 480 de la carte du jeu, marqueur et
nom incrustés. C'est ce qui manque à l'écran météo, qui dit *quoi* sort et pas
*où*.

**Le jeton reste dehors.** L'adresse du tracker contient une empreinte qui
identifie ton personnage ; elle ne doit jamais entrer dans le dépôt. Le script
la lit dans un fichier de configuration, hors de l'arbre Git, et vérifie avant
d'écrire quoi que ce soit qu'elle ne s'est glissée dans aucune sortie.

    mkdir -p ~/.config/zyroom
    printf '%s\\n' 'https://www.atys.us/tracker.php?checksum=…&user=…' \\
        > ~/.config/zyroom/atys.url
    chmod 600 ~/.config/zyroom/atys.url

    python3 outils/cartes_gisements.py            # tout récupérer
    python3 outils/cartes_gisements.py --limite 5 # un essai, cinq fiches

Le script est reprenable : une image déjà là n'est pas retéléchargée. On peut
donc l'interrompre et le relancer.

**Ce qu'on a découvert en le faisant.** La fiche `nodeinfo.php` prend un
paramètre `location`, mais il ne change rien au résultat : suprême beng ambre
rend les deux mêmes cartes qu'on la demande depuis le désert, la jungle ou les
Primes. Les cartes ne dépendent donc que du couple (qualité, matière), et le
parcours fait 94 fiches au lieu des 376 qu'on croyait. Si le site changeait sur
ce point, il faudrait remettre `location` dans la clé.

Attribution : tracker de Tgwaste sur atys.us, données de gisements de
ballisticmystix.net. Elle doit figurer dans l'À propos des deux applications,
comme pour les symboles de matières et les noms d'avant-postes.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

RACINE = "https://www.atys.us"
CONFIG = os.path.expanduser("~/.config/zyroom/atys.url")

#: Les six lieux du tracker. Ils ne servent qu'à dresser le catalogue : la
#: fiche d'un gisement, elle, ignore le lieu qu'on lui donne (voir l'en-tête).
LIEUX = ("fyros", "matis", "tryker", "zorai", "sources", "wastelands")

#: Les suprêmes ne sortent que dans les Primes, mais la fiche les rend quel que
#: soit le lieu demandé : on interroge donc les deux qualités pour tout le monde
#: et c'est l'absence de carte qui dit qu'un couple n'existe pas.
QUALITES = ("supreme", "excellent")

AGENT = "Mozilla/5.0 (compatible; ZyRoom/1.0; +https://github.com/xiom-dev)"

_CARTE = re.compile(r"maps/([0-9a-f]{40})\.png")
_FICHE = re.compile(r"nodeinfo\.php\?([^\"']+)")
_TITRE = re.compile(r"font-size: 18px;'>(.*?)</td>", re.S)
_NOMBRE = re.compile(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)")


def empreinte(source: str = "") -> str:
    """L'empreinte du tracker : argument, variable d'environnement, ou fichier.

    On accepte aussi bien l'adresse entière — celle qu'on copie depuis le
    navigateur, jeton compris — que les quarante caractères tout seuls. Dans les
    deux cas, seule l'empreinte `checksum` est retenue : le bloc `user`, qui
    porte le nom du personnage, sa guilde et son grade, n'est jamais lu.
    """
    for brut in (source, os.environ.get("ATYS_URL", ""), _fichier(CONFIG)):
        if not brut:
            continue
        trouve = re.search(r"checksum=([0-9a-f]{40})", brut) or \
            re.fullmatch(r"\s*([0-9a-f]{40})\s*", brut)
        if trouve:
            return trouve.group(1)
    raise SystemExit(
        f"Pas d'empreinte. Copie l'adresse du tracker dans {CONFIG} :\n"
        f"    mkdir -p {os.path.dirname(CONFIG)}\n"
        f"    printf '%s\\n' 'https://www.atys.us/tracker.php?checksum=…' "
        f"> {CONFIG}\n"
        f"    chmod 600 {CONFIG}")


def _fichier(chemin: str) -> str:
    try:
        with open(chemin, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def lit(url: str, pause: float, essais: int = 3) -> bytes:
    """Une requête polie : un agent qui se nomme, une pause, et trois essais."""
    for essai in range(essais):
        try:
            requete = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(requete, timeout=60) as reponse:
                contenu = reponse.read()
            time.sleep(pause)
            return contenu
        except (urllib.error.URLError, TimeoutError) as souci:
            if essai == essais - 1:
                raise SystemExit(f"échec sur {_propre(url)} : {souci}")
            time.sleep(pause * (essai + 2) * 2)
    raise AssertionError                                    # pragma: no cover


def _propre(url: str) -> str:
    """L'adresse sans son empreinte : ce qu'on peut afficher ou écrire."""
    return re.sub(r"checksum=[0-9a-f]{40}", "checksum=…", url)


def catalogue(cle: str, pause: float) -> list:
    """Les couples (famille, matière) que le tracker connaît.

    On les relève sur le site plutôt que de les figer ici : le jour où Ryzom
    ajoute une matière, le script la trouvera tout seul. Deux vues par lieu — ce
    qui sort maintenant, et le récapitulatif par saison — et l'union des deux
    donne les quarante-sept couples.
    """
    trouves = set()
    for lieu in LIEUX:
        for vue in ("", "&display=Seasons"):
            url = f"{RACINE}/tracker.php?checksum={cle}&location={lieu}{vue}"
            page = lit(url, pause).decode("utf-8", "replace")
            for parametres in _FICHE.findall(page):
                champs = dict(p.split("=", 1) for p in parametres.split("&")
                              if "=" in p)
                famille, matiere = champs.get("nodename"), champs.get("nodekind")
                if famille and matiere:
                    trouves.add((famille, matiere))
        print(f"  {lieu:11s} → {len(trouves)} couples connus", flush=True)
    return sorted(trouves)


def fiche(cle: str, famille: str, matiere: str, qualite: str, pause: float):
    """Une fiche de gisement : ses fourchettes d'humidité et ses cartes.

    Une matière qui n'existe pas dans cette qualité rend une fiche sans carte —
    c'est ainsi qu'on sépare les suprêmes des seules excellentes, le site ne
    disant nulle part lesquelles sont lesquelles.
    """
    url = (f"{RACINE}/nodeinfo.php?userinfo=&checksum={cle}&location=wastelands"
           f"&nodename={famille}&nodekind={matiere}&quality={qualite}")
    page = lit(url, pause).decode("utf-8", "replace")
    titre = _TITRE.search(page)
    humidites = [[float(bas), float(haut)]
                 for bas, haut in _NOMBRE.findall(titre.group(1) if titre else "")]
    # `dict.fromkeys` plutôt qu'un ensemble : l'ordre de la page est le seul
    # ordre stable dont on dispose, et c'est lui qui numérote les fichiers.
    return humidites, list(dict.fromkeys(_CARTE.findall(page)))


def sans_jeton(texte: str, cle: str) -> str:
    """Refuse de rendre un texte où l'empreinte figure encore.

    Le garde-fou du fichier : le manifeste cite des adresses, et une seule
    oubliée publierait le jeton de Ludo dans le dépôt.
    """
    if cle and cle in texte:
        raise SystemExit("l'empreinte s'est glissée dans la sortie — rien écrit")
    return texte


def main() -> int:
    ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    defaut = os.path.join(os.path.dirname(ici), "cartes-gisements")

    options = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    options.add_argument("--url", default="",
                         help="adresse du tracker (sinon ATYS_URL, sinon "
                              f"{CONFIG})")
    options.add_argument("--sortie", default=defaut,
                         help=f"où déposer les images (défaut : {defaut})")
    options.add_argument("--pause", type=float, default=1.0,
                         help="secondes entre deux requêtes (défaut : 1)")
    options.add_argument("--limite", type=int, default=0,
                         help="s'arrêter après N fiches, pour un essai")
    options.add_argument("--refaire", action="store_true",
                         help="retélécharger les images déjà présentes")
    reglages = options.parse_args()

    cle = empreinte(reglages.url)
    os.makedirs(reglages.sortie, exist_ok=True)
    print(f"empreinte lue, {len(cle)} caractères — elle ne sera pas écrite")
    print(f"sortie : {reglages.sortie}\n")

    print("catalogue des matières :")
    couples = catalogue(cle, reglages.pause)
    print(f"→ {len(couples)} couples famille/matière\n")

    gisements, connues, images, sautees = [], {}, 0, 0
    fiches = [(q, f, m) for f, m in couples for q in QUALITES]
    if reglages.limite:
        fiches = fiches[:reglages.limite]

    for rang, (qualite, famille, matiere) in enumerate(fiches, 1):
        humidites, cartes = fiche(cle, famille, matiere, qualite, reglages.pause)
        if not cartes:
            continue
        fichiers = []
        for numero, nom in enumerate(cartes, 1):
            cible = f"{qualite}_{famille}_{matiere}_{numero}.png"
            chemin = os.path.join(reglages.sortie, cible)
            if nom in connues:
                # La même vue sert deux gisements : on la garde une seule fois
                # et le manifeste dit laquelle.
                cible = connues[nom]
                chemin = os.path.join(reglages.sortie, cible)
            elif os.path.exists(chemin) and not reglages.refaire:
                sautees += 1
                connues[nom] = cible
            else:
                contenu = lit(f"{RACINE}/maps/{nom}.png", reglages.pause)
                with open(chemin, "wb") as fh:
                    fh.write(contenu)
                images += 1
                connues[nom] = cible
            fichiers.append({
                "fichier": cible,
                "cle": nom,
                "octets": os.path.getsize(chemin),
                "sha256": hashlib.sha256(open(chemin, "rb").read()).hexdigest(),
            })
        gisements.append({
            "qualite": qualite, "famille": famille, "matiere": matiere,
            "humidites": humidites, "cartes": fichiers,
        })
        print(f"  [{rang:3d}/{len(fiches)}] {qualite:9s} {famille}/{matiere} "
              f"→ {len(fichiers)} carte(s)", flush=True)

    manifeste = {
        "source": f"{RACINE}/ — tracker de Tgwaste",
        "donnees": "https://ballisticmystix.net",
        "recupere_le": time.strftime("%Y-%m-%d"),
        "note": ("Les cartes ne dépendent que du couple (qualité, matière) : le "
                 "paramètre `location` de la fiche n'a aucun effet."),
        "gisements": gisements,
    }
    texte = sans_jeton(json.dumps(manifeste, ensure_ascii=False, indent=2), cle)
    with open(os.path.join(reglages.sortie, "manifeste.json"), "w",
              encoding="utf-8") as fh:
        fh.write(texte + "\n")

    poids = sum(c["octets"] for g in gisements for c in g["cartes"])
    print(f"\n{len(gisements)} gisements, {len(connues)} vues distinctes "
          f"({images} téléchargées, {sautees} déjà là), {poids // 1024} ko")
    print("manifeste.json écrit — sans l'empreinte, vérifié")
    return 0


if __name__ == "__main__":
    sys.exit(main())
