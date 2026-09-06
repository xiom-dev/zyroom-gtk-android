#!/usr/bin/env python3
"""Compare les deux fenêtres **par l'image**, et non point par point.

    outils/parite-image.py                 capture, puis compare
    outils/parite-image.py DOSSIER         compare deux captures déjà prises
    outils/parite-image.py --tolerance 0   n'accorde plus rien

**Pourquoi cet outil existe.** Le relevé point par point (`outils/parite.py`)
ne voit que ce qu'on pense à lui demander. Onze écarts d'aspect ont été
trouvés à l'œil par Ludo avant lui — dont un bandeau du bas vingt-deux pixels
trop mince, qu'aucun des quarante-sept points ne regardait. Une image, elle,
porte tout ce qui est à l'écran : il ne reste qu'à savoir quoi y lire.

**Ce qui se compare d'un toolkit à l'autre, et ce qui ne se compare pas.** Une
différence pixel à pixel ne dirait rien : les deux fenêtres n'affichent pas le
même texte d'état, et deux moteurs de rendu ne posent jamais un glyphe
exactement pareil. Ce qui se compare, c'est la **structure** :

  - les **bandes** de la fenêtre — la barre du haut, celle des sélecteurs, la
    ligne de volume, la grille, le pied — repérées par la couleur de fond qui
    domine chaque ligne de pixels. Leur ordre, leur début et leur hauteur.
  - la **palette** de chaque bande : les couleurs qui y occupent une part
    notable. Une couleur présente d'un côté et absente de l'autre, c'est un
    style qui ne s'applique pas — ainsi de la signature restée blanche quand
    la règle visait un `QLabel` alors que le widget est un `QPushButton`.

**La tolérance.** Deux pixels par défaut, et non zéro : Pango et le moteur de
Qt ne rendent pas un glyphe de la même hauteur au pixel près, et un outil qui
crie à chaque lancement ne sert plus à rien. Zéro reste disponible pour
regarder de très près — `--tolerance 0`.

**Le cadre de la fenêtre GTK.** GTK4 peint sous X11 quelques lignes de cadre
sous sa fenêtre, que Qt n'a pas. Elles se reconnaissent à leur gris neutre :
aucun fond du thème n'est neutre, tous tirent sur le bleu-vert. On les écarte
avant de comparer, sans quoi les deux images seraient décalées d'un bout.
"""
from __future__ import annotations

import ast
import collections
import os
import subprocess
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:                                     # pragma: no cover
    print("Pillow est nécessaire : pip install --user Pillow", file=sys.stderr)
    raise SystemExit(2)

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

#: Les fonds du thème. Une ligne de pixels dont la couleur dominante est l'un
#: d'eux appartient à cette bande ; les autres lignes — celles où le contenu
#: l'emporte, une rangée d'icônes par exemple — prolongent la bande en cours.
def fonds() -> dict:
    """Les fonds du theme, lus dans `theme.py` **sans l'importer**.

    L'importer ferait venir PySide6, que le Python du systeme n'a pas : cet
    outil doit tourner avec le Pillow du systeme, pas dans l'environnement
    virtuel de Qt. On lit donc l'arbre syntaxique du fichier et on y prend le
    dictionnaire `COULEURS`, qui n'est fait que de litteraux.
    """
    source = os.path.join(RACINE, "zyroom", "theme.py")
    with open(source, encoding="utf-8") as fichier:
        arbre = ast.parse(fichier.read())
    couleurs = None
    for noeud in arbre.body:
        if (isinstance(noeud, ast.Assign)
                and any(getattr(c, "id", "") == "COULEURS"
                        for c in noeud.targets)):
            couleurs = ast.literal_eval(noeud.value)
    if couleurs is None:
        raise SystemExit("COULEURS introuvable dans zyroom/theme.py")
    noms = ("fond", "surface", "variante", "bande", "zebre")
    return {_rvb(couleurs[nom]): nom for nom in noms}


#: La largeur reservee aux boutons de fenetre, a droite de la barre du haut.
#: Mesuree sur la capture GTK : reduire, agrandir et fermer tiennent dans cent
#: quarante pixels.
BOUTONS_DE_FENETRE = 140


def _rvb(code: str) -> tuple:
    code = code.lstrip("#")
    return tuple(int(code[i:i + 2], 16) for i in (0, 2, 4))


def neutre(couleur: tuple) -> bool:
    """Un gris sans teinte : le cadre que GTK peint autour de sa fenêtre.

    Aucun fond du thème n'est neutre — ils tirent tous sur le bleu-vert. Le
    test est donc sans risque de confusion.
    """
    r, v, b = couleur
    return abs(r - v) <= 2 and abs(v - b) <= 2 and abs(r - b) <= 2


def dominantes(image: Image.Image) -> list:
    """La couleur qui domine chaque ligne de pixels."""
    largeur, hauteur = image.size
    pixels = image.load()
    resultat = []
    for y in range(hauteur):
        compte = collections.Counter(pixels[x, y] for x in range(largeur))
        resultat.append(compte.most_common(1)[0][0])
    return resultat


def utile(lignes: list) -> tuple:
    """Les bornes de la fenêtre, cadre de GTK écarté."""
    haut, bas = 0, len(lignes) - 1
    while haut < bas and neutre(lignes[haut]):
        haut += 1
    while bas > haut and neutre(lignes[bas]):
        bas -= 1
    return haut, bas


def colonnes_utiles(image: Image.Image) -> tuple:
    """Les bornes en largeur, cadre de GTK écarté.

    Le cadre est sur les quatre côtés, pas seulement en haut et en bas : ses
    colonnes grises entraient dans la palette de **chaque** bande, et l'outil
    annonçait un #282828 « présent chez GTK, absent chez Qt » du haut en bas
    de la fenêtre.
    """
    largeur, hauteur = image.size
    pixels = image.load()
    milieu = hauteur // 2

    def colonne_neutre(x: int) -> bool:
        compte = collections.Counter(
            pixels[x, y] for y in range(max(0, milieu - 50), milieu + 50))
        return neutre(compte.most_common(1)[0][0])

    gauche, droite = 0, largeur - 1
    while gauche < droite and colonne_neutre(gauche):
        gauche += 1
    while droite > gauche and colonne_neutre(droite):
        droite -= 1
    return gauche, droite


def bandes(image: Image.Image) -> list:
    """Les bandes de la fenêtre : (nom du fond, début, hauteur).

    Le début est compté depuis le haut **utile**, pour que les deux images se
    comparent malgré le cadre que GTK ajoute.
    """
    lignes = dominantes(image)
    haut, bas = utile(lignes)
    table = fonds()
    etiquettes = []
    courante = None
    for y in range(haut, bas + 1):
        nom = table.get(lignes[y])
        if nom is not None:
            courante = nom
        etiquettes.append(courante if courante is not None else "?")

    resultat = []
    debut = 0
    for i in range(1, len(etiquettes) + 1):
        if i == len(etiquettes) or etiquettes[i] != etiquettes[debut]:
            resultat.append((etiquettes[debut], debut, i - debut))
            debut = i
    # Les bandes d'une ou deux lignes sont du bruit de rendu, pas une bande.
    return [b for b in resultat if b[2] >= 3]


#: Une couleur compte comme presente dans une bande au-dela de cette part, et
#: comme *absente* en dessous de PRESENCE_NULLE. Entre les deux, elle est la
#: mais discrete : ce n'est pas un style qui manque, c'est du texte un peu plus
#: epais d'un cote que de l'autre, et l'annoncer serait crier pour rien.
PRESENCE = 0.005
PRESENCE_NULLE = 0.0005

#: Deux couleurs qui ne different que de cela sur chaque composante sont la
#: meme a l'oeil : le lissage d'un bord en produit des dizaines autour de
#: chaque aplat. Sans ce voisinage, l'outil reclamait un #081018 qui n'etait
#: que le bord adouci du #10171a d'a cote.
VOISINAGE = 8


def palette(image: Image.Image, y0: int, y1: int, decalage: int,
            x0: int = 0, x1: int | None = None) -> dict:
    """Les couleurs d'une bande et leur part, arrondies pour absorber le lissage.

    Le pas de huit efface la différence entre un glyphe rendu par Pango et le
    même rendu par Qt, sans effacer un écart de style : deux couleurs voulues
    différentes le sont toujours de bien plus que huit unités.
    """
    if x1 is None:
        x1 = image.size[0] - 1
    pixels = image.load()
    compte = collections.Counter()
    for y in range(y0 + decalage, min(y1 + decalage, image.size[1])):
        for x in range(x0, x1 + 1, 2):        # une colonne sur deux : assez
            r, v, b = pixels[x, y]
            compte[(r // 8 * 8, v // 8 * 8, b // 8 * 8)] += 1
    total = sum(compte.values()) or 1
    return {c: n / total for c, n in compte.items()}


def retrouvee(couleur: tuple, chez_lautre: dict) -> bool:
    """La couleur existe-t-elle chez l'autre, à un cheveu près ?

    Une égalité stricte réclamerait du rendu une exactitude qu'il n'a pas : le
    bord adouci d'un aplat produit des voisins à une ou deux unités. On accepte
    donc un écart de `VOISINAGE` sur chaque composante — bien en deçà de ce qui
    sépare deux couleurs voulues différentes.
    """
    for autre, part in chez_lautre.items():
        if part < PRESENCE_NULLE:
            continue
        if all(abs(a - b) <= VOISINAGE for a, b in zip(couleur, autre)):
            return True
    return False


def code(couleur: tuple) -> str:
    return "#%02x%02x%02x" % couleur


def comparer(chemin_gtk: str, chemin_qt: str, tolerance: int) -> list:
    """Les écarts entre les deux images. Liste vide si elles s'accordent."""
    gtk = Image.open(chemin_gtk).convert("RGB")
    qt = Image.open(chemin_qt).convert("RGB")
    ecarts = []

    if gtk.size != qt.size:
        ecarts.append(f"taille des fenêtres : GTK {gtk.size}, Qt {qt.size}")

    bg, bq = bandes(gtk), bandes(qt)
    if len(bg) != len(bq):
        ecarts.append(
            f"nombre de bandes : GTK {len(bg)}, Qt {len(bq)}\n"
            f"      GTK : {[(n, d, h) for n, d, h in bg]}\n"
            f"      Qt  : {[(n, d, h) for n, d, h in bq]}")
        return ecarts

    lignes_gtk, lignes_qt = dominantes(gtk), dominantes(qt)
    haut_gtk, bas_gtk = utile(lignes_gtk)
    haut_qt, bas_qt = utile(lignes_qt)
    gauche_gtk, droite_gtk = colonnes_utiles(gtk)
    gauche_qt, droite_qt = colonnes_utiles(qt)

    # **Le cadre de la fenêtre GTK laisse moins de place au contenu.** GTK4
    # peint quelques lignes de cadre en haut et en bas ; Qt n'en a pas, et sa
    # fenêtre a d'autant plus de hauteur utile. C'est la bande extensible — la
    # grille — qui encaisse la différence, et tout ce qui la suit s'en trouve
    # décalé. Sans cette correction, l'outil accusait l'application d'un écart
    # qui vient de l'environnement de capture.
    jeu = abs((bas_gtk - haut_gtk) - (bas_qt - haut_qt))
    extensible = max(range(len(bg)), key=lambda i: bg[i][2])

    for rang, ((ng, dg, hg), (nq, dq, hq)) in enumerate(zip(bg, bq), 1):
        if ng != nq:
            ecarts.append(f"bande {rang} : fond « {ng} » chez GTK, "
                          f"« {nq} » chez Qt")
            continue
        # Les bandes d'avant la grille sont ancrées en haut, celles d'après
        # sont ancrées en bas : on les compare depuis le bord qui les tient.
        if rang - 1 <= extensible:
            pg, pq, bord = dg, dq, "commence à"
        else:
            pg = (bas_gtk - haut_gtk) - (dg + hg)
            pq = (bas_qt - haut_qt) - (dq + hq)
            bord = "finit à (compté du bas)"
        if abs(pg - pq) > tolerance:
            ecarts.append(f"bande {rang} ({ng}) {bord} {pg} chez GTK, "
                          f"{pq} chez Qt — {abs(pg - pq)} px d'écart")
        marge = tolerance + (jeu if rang - 1 == extensible else 0)
        if abs(hg - hq) > marge:
            ecarts.append(f"bande {rang} ({ng}) fait {hg} px chez GTK, "
                          f"{hq} px chez Qt — {abs(hg - hq)} px d'écart")
        # **La barre du haut s'arrête avant les boutons de fenêtre.** GTK4
        # dessine lui-même le réduire, l'agrandir et le fermer dans sa barre ;
        # Qt les laisse au bureau, qui n'existe pas sur le serveur X virtuel.
        # Ce n'est pas un écart de l'application, c'est ce que chacun délègue
        # ou non à l'environnement — et sans cette réserve, le blanc de ces
        # trois boutons se lisait comme une couleur manquante chez Qt.
        reserve = BOUTONS_DE_FENETRE if rang == 1 else 0
        pg = palette(gtk, dg, dg + hg, haut_gtk,
                     gauche_gtk, droite_gtk - reserve)
        pq = palette(qt, dq, dq + hq, haut_qt,
                     gauche_qt, droite_qt - reserve)
        for couleur, part in sorted(pg.items()):
            if part >= PRESENCE and not retrouvee(couleur, pq):
                ecarts.append(f"bande {rang} ({ng}) : {code(couleur)} occupe "
                              f"{part * 100:.1f} % chez GTK, rien chez Qt")
        for couleur, part in sorted(pq.items()):
            if part >= PRESENCE and not retrouvee(couleur, pg):
                ecarts.append(f"bande {rang} ({ng}) : {code(couleur)} occupe "
                              f"{part * 100:.1f} % chez Qt, rien chez GTK")
    return ecarts


def planche(chemin_gtk: str, chemin_qt: str, sortie: str) -> str:
    """Les deux fenêtres côte à côte, leurs bandes tracées. Pour l'œil."""
    gtk = Image.open(chemin_gtk).convert("RGB")
    qt = Image.open(chemin_qt).convert("RGB")
    l = gtk.size[0] + qt.size[0] + 12
    h = max(gtk.size[1], qt.size[1])
    vue = Image.new("RGB", (l, h), (0, 0, 0))
    vue.paste(gtk, (0, 0))
    vue.paste(qt, (gtk.size[0] + 12, 0))
    crayon = ImageDraw.Draw(vue)
    for image, dx in ((gtk, 0), (qt, gtk.size[0] + 12)):
        haut = utile(dominantes(image))[0]
        for _nom, debut, _hauteur in bandes(image):
            y = haut + debut
            crayon.line([(dx, y), (dx + image.size[0], y)],
                        fill=(232, 193, 90))
    vue.save(sortie)
    return sortie


def main() -> int:
    arguments = sys.argv[1:]
    tolerance = 2
    if "--tolerance" in arguments:
        i = arguments.index("--tolerance")
        tolerance = int(arguments[i + 1])
        del arguments[i:i + 2]
    dossier = arguments[0] if arguments else None

    if dossier is None:
        dossier = "/tmp/parite-images"
        capturer = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "parite", "capturer.sh")
        print("== Capture des deux fenêtres ==")
        subprocess.run([capturer, dossier], check=True)

    chemin_gtk = os.path.join(dossier, "gtk.png")
    chemin_qt = os.path.join(dossier, "qt.png")
    for chemin in (chemin_gtk, chemin_qt):
        if not os.path.isfile(chemin):
            print(f"Capture manquante : {chemin}", file=sys.stderr)
            return 2

    ecarts = comparer(chemin_gtk, chemin_qt, tolerance)
    vue = planche(chemin_gtk, chemin_qt, os.path.join(dossier, "planche.png"))

    print()
    if not ecarts:
        print(f"Les deux images s'accordent (tolérance {tolerance} px).")
        print(f"  {vue}")
        return 0
    print(f"{len(ecarts)} écart(s) à l'image — GTK fait foi :\n")
    for ecart in ecarts:
        print(f"  {ecart}")
    print(f"\n  Les deux fenêtres côte à côte : {vue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
