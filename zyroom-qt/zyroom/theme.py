"""Le thème sombre de ZyRoom, traduit de GTK vers Qt.

**Les couleurs ne changent pas.** Ce sont les cinq teintes du portage Android,
reprises telles quelles par la version GTK, et reprises telles quelles ici :
c'est ce qui fait qu'on reconnaît l'application d'un système à l'autre.

**En revanche la façon de peindre change du tout au tout.** GTK n'a qu'un
outil, la feuille de style, et la version GTK repeint donc tout à la main —
sélecteur par sélecteur, jusqu'aux cases à cocher, parce qu'Adwaita reprenait
la main sur les couleurs nommées depuis GTK 4.16.

Qt en a deux, et il faut les deux :

- la **palette** (`palette()`) dit au style natif de quelles couleurs il
  dispose. Fusion s'en sert pour tout ce qu'il dessine lui-même : les flèches
  des listes déroulantes, les coches, les curseurs, les cadres.
- la **feuille de style** (`feuille()`) ne sert qu'aux accents : les bandes,
  la grille d'objets, la jauge sarcelle, les infobulles.

**Pourquoi ce partage, et pas tout en QSS.** Styliser un widget en QSS le fait
basculer hors du rendu natif : Qt cesse alors de dessiner ce qu'il complétait
tout seul, et attend une image à la place. Vérifié à l'écran — une règle sur
`QComboBox` effaçait la flèche du déroulant, et les listes ressemblaient à des
champs de texte : plus rien ne disait qu'on pouvait cliquer. La palette n'a pas
cet effet de bord ; elle informe le style au lieu de le remplacer.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetrics,
                           QIcon, QPainter,
                           QPalette, QPixmap)
from PySide6.QtWidgets import QLineEdit

#: Les cinq couleurs d'Android, telles quelles.
COULEURS = {
    "fond":            "#10171a",   # background
    "surface":         "#172226",   # surface
    "variante":        "#1e2c31",   # surfaceVariant
    "texte":           "#e2e8e6",   # onSurface
    "texte_faible":    "#bcc8c6",   # onSurfaceVariant
    "sarcelle":        "#3f7a68",   # primary
    "sarcelle_sombre": "#2b5648",
    "sarcelle_clair":  "#7fb3a2",   # le sarcelle lisible en texte sur du noir
    "or":              "#e8c15a",   # secondary
    "erreur":          "#e2696a",   # error
    # Les bandes du haut et du bas, un cran sous le fond : elles tiennent la
    # grille entre elles au lieu de s'y fondre.
    "bande":           "#0b1113",
    "accent_texte":    "#06120e",   # ce qui s'ecrit par-dessus le sarcelle
    # Le zebrage des tableaux : une pointe de sarcelle plutot qu'un gris.
    # C'est ce qui fait la difference entre un tableau terne et un tableau
    # habille. GTK l'ecrit mix(surface, sarcelle, 0.14) ; QSS ne sait pas
    # melanger, on pose donc le resultat.
    "zebre":           "#1d2e2f",
    # Le vert de ce qui est monte au maximum : mix(sarcelle, blanc, 0.35).
    # Le vert de ce qui est monte au maximum. La valeur exacte que GTK
    # calcule pour `mix(@zy_sarcelle, white, 0.35)` : 0,65 de sarcelle et 0,35
    # de blanc, composante par composante. Elle etait a #82a89d, un point de
    # vert en dessous.
    "fini":            "#82a99d",
    "vert":            "#4caf50",
}


def _c(nom: str) -> QColor:
    return QColor(COULEURS[nom])


def palette() -> QPalette:
    """La palette sombre, pour tout ce que le style natif dessine lui-même."""
    p = QPalette()
    r = QPalette.ColorRole
    g = QPalette.ColorGroup

    p.setColor(r.Window, _c("fond"))
    p.setColor(r.WindowText, _c("texte"))
    # Base : le fond des champs de saisie et des listes. AlternateBase sert
    # aux lignes paires des tableaux.
    p.setColor(r.Base, _c("surface"))
    p.setColor(r.AlternateBase, _c("variante"))
    p.setColor(r.Text, _c("texte"))
    p.setColor(r.PlaceholderText, _c("texte_faible"))
    p.setColor(r.Button, _c("variante"))
    p.setColor(r.ButtonText, _c("texte"))
    p.setColor(r.ToolTipBase, _c("variante"))
    p.setColor(r.ToolTipText, _c("texte"))
    p.setColor(r.Highlight, _c("sarcelle_sombre"))
    p.setColor(r.HighlightedText, _c("texte"))
    p.setColor(r.Link, _c("sarcelle_clair"))
    # Les cadres graves autour des zones de defilement.
    p.setColor(r.Light, _c("variante"))
    p.setColor(r.Mid, _c("bande"))
    p.setColor(r.Dark, _c("bande"))
    p.setColor(r.Shadow, _c("bande"))

    # Ce qui est desactive s'eteint sans disparaitre : le gris pale du
    # theme clair serait illisible sur ce fond.
    for role in (r.WindowText, r.Text, r.ButtonText):
        p.setColor(g.Disabled, role, _c("texte_faible"))
    return p


def echelle_du_bureau() -> float:
    """Le facteur d'agrandissement du texte que GNOME applique, ou 1.

    **GTK l'applique tout seul, Qt l'ignore.** Un bureau réglé sur 1,25 — ce
    qui est courant — affiche donc un « 10 » à 12,5 points dans la version GTK
    et à 10 dans celle-ci : le même réglage, un texte un quart plus petit d'un
    côté. C'est ce que Ludo voyait en comparant les deux à taille égale.

    Lu par `gsettings`, sans lequel on ne peut pas le connaître : Qt n'expose
    pas ce réglage, et il ne vit ni dans les variables d'environnement ni dans
    les métriques de l'écran. Hors de GNOME — sous Windows, ou si la commande
    manque — on rend 1, et rien ne change.
    """
    import subprocess

    try:
        fait = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface",
             "text-scaling-factor"],
            capture_output=True, text=True, timeout=3)
        facteur = float(fait.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1.0
    # Un facteur aberrant ferait une fenêtre illisible : on s'en tient à ce que
    # GNOME lui-même propose, de la moitié au double.
    return facteur if 0.5 <= facteur <= 2.0 else 1.0


def _corps_du_bureau() -> float:
    """Le corps de la police par défaut, en points.

    `QApplication` peut ne pas exister encore — la palette se construit avant
    lui dans certains chemins — et une police sans corps en points en rend
    -1. Onze dans les deux cas, la valeur par défaut de GNOME, celle sur
    laquelle la version GTK retombe elle aussi.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    corps = app.font().pointSizeF() if app is not None else -1.0
    corps = corps if corps > 0 else 11.0
    # La police que Qt rend est celle du bureau, mais sans son agrandissement :
    # GNOME le tient a part, dans `text-scaling-factor`.
    return corps * echelle_du_bureau()


#: La coche des cases a cocher. Chemin absolu construit a cote de ce module :
#: il tombe juste dans les sources comme dans le bundle PyInstaller, qui range
#: `symboles/` sous `zyroom/`. Les separateurs sont des barres obliques -- une
#: feuille de style Qt ne lit pas les antislashs de Windows.
def _symbole(nom: str) -> str:
    """Le chemin d'une image d'aspect, en separateurs avant.

    **Dans `aspect/` et non dans `symboles/`.** Ce dernier est recopie tel quel
    depuis la version GTK par `outils/sync-noyau.sh`, qui le refait a neuf a
    chaque passage : la coche et le chevron y auraient disparu a la premiere
    synchronisation. Ils n'ont d'ailleurs rien a y faire -- GTK n'en a pas
    besoin, Adwaita les dessine.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "aspect", nom).replace(os.sep, "/")


COCHE = _symbole("coche.png")
#: Le chevron d'une liste deroulante. Qt n'en dessine plus des que la feuille
#: touche au `drop-down` ; celui-la est le « v » d'Adwaita.
CHEVRON = _symbole("chevron.png")


def feuille(taille: int = 0) -> str:
    """Les accents, par-dessus la palette. Prête pour `setStyleSheet`.

    `taille` est le corps du texte en points, zéro pour celui du bureau.

    **Il doit passer par ici, et non par `QApplication.setFont`.** Appliquer
    une feuille de style fait repolir tous les widgets, et Qt leur redonne
    alors la police du style — écrasant celle qu'on avait posée sur
    l'application. Mesuré : les libellés restaient à onze points pendant que
    `app.font()` en annonçait seize. Écrite dans la feuille, la règle survit
    au polish parce qu'elle en fait partie.
    """
    # L'echelle du bureau s'applique a tout ce qui suit : c'est ce que GTK
    # fait de son cote, et sans quoi le meme reglage donne deux tailles.
    echelle = echelle_du_bureau()
    taille = taille * echelle if taille > 0 else 0

    corps = ""
    if taille > 0:
        # `*` atteint tout, y compris les deux libelles du nom grave, dont le
        # corps est calcule a part -- il les rapetissait a la taille courante.
        # On le leur rend ici, dans les memes proportions que fenetre.py.
        corps = (f"* {{ font-size: {taille}pt; }}\n"
                 f"#nom-grave {{ font-size: {taille * 2.4:.2f}pt; }}\n"
                 f"#nom-mouture {{ font-size: {taille * 2.2:.2f}pt; }}\n")
    # La somme en dappers, un point au-dessus du reste -- comme la version
    # GTK, qui calcule la meme chose a partir du meme corps. Quand rien n'est
    # regle, le corps est celui du bureau : on le demande a Qt plutot que de
    # le supposer, sinon les deux barres divergeraient sur un bureau qui
    # n'ecrit pas en onze points.
    base = taille if taille > 0 else _corps_du_bureau()
    # **Deux decimales et non un entier.** Sur un bureau qui grossit le texte
    # -- celui de Ludo est a 1,25 --, un reglage de dix points fait douze
    # points et demi. `f"{12.5:.0f}"` rend « 12 » : Python arrondit au pair, et
    # ce demi-point perdu se voyait a l'oeil, tout le texte de Qt etant un
    # pixel plus court que celui de GTK. Une feuille Qt accepte les decimales ;
    # GTK, lui, ne tronque rien.
    corps += f"QLabel#dappers {{ font-size: {base + 1:.2f}pt; }}\n"
    # La signature a 90 % du corps : la classe `caption` de GTK, que Qt ne sait
    # pas exprimer en pourcentage.
    corps += (f"QLabel#signature, QPushButton#signature "
              f"{{ font-size: {base * 0.9:.2f}pt; }}\n")
    return corps + """
/* Les bandes qui encadrent la grille : la barre du haut, celle des deux
   selecteurs, et le pied. Un cran sous le fond, pour tenir la grille entre
   elles au lieu de s'y fondre. */
#entete, #bande {
    background-color: %(bande)s;
}
/* Le trait qui separe la barre du haut de la ligne des selecteurs. Adwaita le
   pose sous sa `headerbar` ; sans lui, les deux bandes de Qt n'en faisaient
   qu'une. Un pixel de #070707, mesure sur toute la largeur de la fenetre GTK
   -- c'est la comparaison par l'image qui l'a trouve, personne ne l'avait vu. */
#entete {
    border-bottom: 1px solid #070707;
}

/* **Tous les boutons**, et non les seuls boutons nommes. Adwaita donne a un
   bouton un fond gris, des coins de six pixels et un texte presque blanc ;
   Fusion, lui, dessinait un degrade clair borde de gris bleute, que la
   comparaison par l'image a repere bande par bande (#404850 et #485058
   « presents chez Qt, absents chez GTK »). Les boutons nommes -- le principal,
   la navigation, la signature, le compteur -- gardent leur regle : un
   selecteur d'identifiant l'emporte sur un selecteur de type.

   Les seuls boutons sans cadre s'appellent « plat », comme la classe `flat`
   que la version GTK pose sur les deux boutons de zoom. */
QPushButton, QToolButton {
    /* Le degrade d'Adwaita, releve en coupe sur un bouton de la fenetre GTK :
       #3a3a3a en haut, #373737 en bas, et une bordure #1b1b1b tout autour. Un
       aplat sans bordure s'en approchait de loin -- la comparaison par l'image
       reclamait ces deux couleurs bande apres bande. */
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #3a3a3a, stop: 0.5 #393939,
                                      stop: 1 #373737);
    border: 1px solid #1b1b1b;
    border-radius: 6px;
    color: #eeeeec;
    padding: 4px 10px;
    min-height: 21px;
}
QPushButton:hover, QToolButton:hover     { background-color: #454545; }
QPushButton:pressed, QToolButton:pressed { background-color: #2a2a2a; }
QPushButton:disabled, QToolButton:disabled {
    background-color: #2d2d2d;
    color: #6a6a6a;
}
QPushButton#plat, QToolButton#plat {
    background: transparent;
    border: none;
}
QPushButton#plat:hover, QToolButton#plat:hover {
    background-color: #303030;
}

/* Les boutons d'action de la barre du haut : l'ajout, la corbeille, la
   cloche, le dossier, la resynchronisation et le menu. Adwaita leur donne un
   fond gris et des coins de six pixels ; Qt, lui, les laissait plats --
   `setAutoRaise`. La comparaison par l'image l'a vu la premiere : le #383838
   d'Adwaita etait « present chez GTK, absent chez Qt » dans toute la bande du
   haut. Trente-quatre pixels sur trente et un, mesures sur la fenetre GTK.

   Les deux boutons de zoom, eux, restent plats : la version GTK leur pose la
   classe `flat`, et ils n'ont donc pas ce nom. */
QToolButton#barre, QPushButton#barre {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #3a3a3a, stop: 0.5 #393939,
                                      stop: 1 #373737);
    border: 1px solid #1b1b1b;
    border-radius: 6px;
    color: #eeeeec;
    min-width: 22px;
    min-height: 21px;
    padding: 4px 5px;
}
QToolButton#barre:hover, QPushButton#barre:hover {
    background-color: #454545;
}
QToolButton#barre:pressed, QPushButton#barre:pressed {
    background-color: #2a2a2a;
}
QToolButton#barre:disabled, QPushButton#barre:disabled {
    background-color: #2d2d2d;
    color: #6a6a6a;
}
/* Le menu deroulant du bouton « ☰ » n'affiche pas de fleche : GTK n'en met
   pas non plus a cote de son icone. */
QToolButton#barre::menu-indicator { image: none; width: 0; }

/* La navigation : trois boutons qui se touchent, comme la classe « linked »
   de GTK. Les coins ne s'arrondissent qu'aux extremites du bloc. */
QPushButton#nav, QToolButton#nav {
    /* #383838, le gris qu'Adwaita donne a un bouton -- et non la variante du
       theme. Mesure sur la fenetre GTK : l'onglet « Journal » au repos y est
       gris, il etait bleu-vert chez nous. La comparaison par l'image l'a vu,
       le releve point par point ne regardait que le bouton choisi. */
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #3a3a3a, stop: 0.5 #393939,
                                      stop: 1 #373737);
    /* #eeeeec et non la couleur de texte du theme : c'est celle qu'Adwaita
       donne au texte d'un bouton, et la version GTK ne la redefinit pas. Douze
       points d'ecart sur chaque composante, invisibles a l'oeil -- mais GTK
       fait foi, et le controle de parite les voit. */
    color: #eeeeec;
    border: 1px solid %(bande)s;
    border-radius: 0;
    padding: 4px 14px;
    /* Trente-deux pixels de haut, mesures sur la fenetre GTK. Le contenu seul
       en donnait vingt-neuf : trois de moins, visibles des qu'on pose les deux
       captures l'une sous l'autre. Vingt-sept depuis que les boutons portent
       une image de trente : c'est elle qui commande la hauteur, et la barre
       de GTK en faisait trois de plus que la notre. */
    min-height: 27px;
}
/* Le chevron du menu « Bonus ». Qt pose sa fleche par defaut dans le coin en
   bas a droite, minuscule et sombre ; GTK dessine un chevron clair a hauteur
   du texte, a sa droite -- `set_always_show_arrow`. On reprend donc le chevron
   des listes deroulantes, centre verticalement, et on reserve sa place dans le
   remplissage du bouton pour que le texte ne se decale pas. */
QToolButton#nav {
    padding-right: 16px;
}
QToolButton#nav::menu-indicator {
    image: url("%(chevron)s");
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 14px;
    height: 14px;
    right: 2px;
}
/* La bordure gauche de tous sauf le premier : sans cela deux bordures d'un
   pixel se touchent et la separation en fait deux, la ou GTK n'en montre
   qu'une seule -- mesure sur les deux captures. */
QPushButton#nav[rang="suite"], QToolButton#nav[rang="suite"] {
    border-left: none;
}
QPushButton#nav:hover, QToolButton#nav:hover {
    background-color: %(sarcelle_sombre)s;
}
/* Le fond suffit a dire lequel est choisi. Le gras, lui, changeait la
   largeur du texte : le bouton s'elargissait d'un coup au clic, poussant ses
   voisins, et la police epaissie a la volee -- sans graisse dessinee dans la
   fonte -- paraissait floue. */
QPushButton#nav:checked {
    background-color: %(sarcelle_sombre)s;
    color: %(texte)s;
}
/* Le bouton « Bonus » enfonce ne se peint pas comme les deux autres : GTK lui
   pose la classe `suggested-action`, qui est plus claire et porte un texte
   presque noir, la ou un onglet choisi prend la sarcelle sombre. Deux verts
   differents, donc, et c'est voulu : le menu se distingue des onglets. Qt les
   confondait, faute d'avoir deux regles. */
QToolButton#nav[actif="true"] {
    background-color: %(sarcelle)s;
    color: #06120e;
}

/* Le message du jour d'une guilde, encadre comme sur Android. */
#motd {
    background-color: %(variante)s;
    border-radius: 8px;
    margin: 2px 8px;
}

/* Le nom de l'application, en bas au centre : l'or du titre et du logo. */
#nom-appli, #nom-grave, #nom-mouture { color: %(or)s; }

/* La ligne d'etat : l'or aussi, celui des intitules de section. Elle dit qui
   l'on regarde, dans quel contenant, et de quand datent les donnees. */
#peuple { color: %(or)s; }

/* Le zebrage. Une propriete dynamique et non une classe : QSS n'a pas de
   classes, il interroge les proprietes des objets -- `setProperty("zebre",
   True)` du cote Python. Il sert aux lignes des tableaux comme aux blocs de
   l'effectif, qui sont des boites et non des lignes de liste. */
QWidget[zebre="true"] { background-color: %(zebre)s; }

/* Ce qui est monte au maximum, dans l'arbre des competences comme sur un
   avant-poste qui nous appartient : le vert de l'application. */
/* Sans gras : la police epaissie a la volee, sans graisse dessinee dans la
   fonte, rend le vert flou. La couleur suffit a dire que c'est monte au
   maximum. */
#fini { color: %(fini)s; }

/* Les triangles du registre : la couleur porte le sens, la direction le
   confirme -- pour qui distingue mal les deux teintes. */
#tri-arrivee { color: %(vert)s; font-weight: bold; }
#tri-depart  { color: %(erreur)s; font-weight: bold; }
#tri-grade   { color: %(texte)s; font-weight: bold; }

/* Un cran sous le corps courant : trois colonnes doivent tenir dans une
   moitie de fenetre, et un nom d'avant-poste va jusqu'a quarante signes. */
#compact { font-size: 92%%; }

/* Les tetes de branche de l'arbre des competences. */
#titre { font-weight: bold; }

/* La signature, discrete : c'est une mention, pas un bouton d'action.

   **#888b8a et non la couleur de texte attenuee.** GTK lui pose la classe
   `dim-label` d'Adwaita, qui n'est pas une couleur mais une opacite de 0,55 ;
   sur le fond de la bande, cela donne exactement ce gris. Le #bcc8c6 d'avant
   etait nettement plus clair.

   C'est bien ici qu'il faut le poser : le widget est un QPushButton, pas un
   QLabel -- une premiere correction avait vise le mauvais selecteur, et
   n'avait donc rien change a l'ecran. */
QPushButton#signature {
    background: transparent;
    color: #888b8a;
    /* La boite d'un bouton Adwaita sans cadre, au pixel : 24 de contenu, 4 de
       remplissage haut et bas, 1 de bordure de chaque cote -- 34 en tout, et
       2 de marge basse. Mesure sur la fenetre GTK : le bouton y fait 34 de
       haut, le nôtre n'en faisait que 18, et le bandeau du bas etait de ce
       fait 22 pixels plus mince que celui de la reference. La bordure est
       transparente et non absente : elle porte deux de ces pixels. */
    border: 1px solid transparent;
    min-height: 24px;
    padding: 4px 10px;
    margin-bottom: 2px;
}
QPushButton#signature:disabled { color: #888b8a; }

/* Le bouton d'action principale : le seul aplat franc de la fenetre. */
QPushButton#principal {
    background-color: %(sarcelle)s;
    color: %(accent_texte)s;
    /* Pas de gras : la version GTK pose `suggested-action` sur ce bouton, et
       ni le theme d'Adwaita ni la feuille du programme ne le graissent. Ludo
       l'a vu a l'oeil ; le controle de parite le voit maintenant aussi. */
    border: 1px solid %(sarcelle_sombre)s;
    border-radius: 4px;
    padding: 4px 12px;
}
QPushButton#principal:hover   { background-color: %(sarcelle_clair)s; }
QPushButton#principal:pressed { background-color: %(sarcelle_sombre)s; }
QPushButton#principal:disabled {
    background-color: %(variante)s;
    color: %(texte_faible)s;
}

/* Tout ce qui etait bleu passe au sarcelle : la jauge de volume comme
   l'avancement d'une competence. Une seule regle pour les deux, comme la
   version GTK -- j'avais mis du vert sur l'avancement, et les deux
   applications ne se ressemblaient plus. */
QProgressBar {
    background-color: %(variante)s;
    border: none;
    border-radius: 5px;
    height: 10px;
}
QProgressBar::chunk {
    background-color: %(sarcelle)s;
    border-radius: 5px;
}

/* La jauge de volume, calquee au pixel sur le Gtk.LevelBar de la version
   GTK -- c'est elle la reference. Le theme y donne au bloc neuf pixels et
   une bordure d'un pixel, un fond #282828 pour le vide, et un lisere qui
   change de couleur au passage des paliers. Les trois couleurs viennent du
   Default-dark.css de GTK, pas de notre palette : les reprendre autrement
   aurait fait deux jauges cousines au lieu de deux jumelles. */
/* La barre d'attente, calquee sur celle de GTK. Adwaita lui donne un fond
   #282828 et un lisere #15539e, que notre CSS ne remplace pas -- il ne change
   que la couleur de remplissage. Le rayon est de 4, contre 5 pour les jauges.

   **`width` est ce qui n'en fait qu'un.** Sans largeur declaree, Qt repete le
   motif du chunk sur toute la barre : on voyait plusieurs curseurs balayer de
   front, la ou GTK n'en promene qu'un. Neuf pixels, soit le `pulse_step` de
   0,15 applique aux soixante de la barre -- la meme mesure des deux cotes. */
QProgressBar#attente {
    background-color: #282828;
    border: none;
    border-radius: 4px;
}
QProgressBar#attente::chunk {
    background-color: %(sarcelle)s;
    border: 1px solid #15539e;
    border-radius: 4px;
    width: 9px;
    margin: 0px;
}

QProgressBar#jauge, QProgressBar#jauge-volume {
    background-color: #282828;
    border: none;             /* le lisere appartient au bloc rempli, pas au fond */
    border-radius: 5px;
}
QProgressBar#jauge::chunk, QProgressBar#jauge-volume::chunk {
    background-color: %(sarcelle)s;
    border: 1px solid #15539e;      /* high, le palier par defaut */
    border-radius: 5px;
}
/* Seule la jauge de volume a des paliers : GTK lui pose trois
   `add_offset_value`, la jauge des competences aucun -- son bloc ne porte
   que « filled », et son lisere reste bleu de bout en bout.

   **« low » n'est pas orange.** La classe existe bien -- GTK la pose sous les
   soixante pour cent --, mais Adwaita ne lui donne aucune couleur propre :
   un `Gtk.LevelBar` aux memes trois offsets, mesure a cinquante-neuf pour
   cent, peint exactement le meme bleu qu'a soixante-dix, et ne vire au vert
   qu'au dernier palier. L'orange
   #f57900 qu'on lui avait donne dessinait un lisere rouge-orange autour de la
   ligne de volume, que la fenetre GTK ne montre a aucun moment. */
QProgressBar#jauge-volume[niveau="low"]::chunk  { border-color: #15539e; }
QProgressBar#jauge-volume[niveau="high"]::chunk { border-color: #15539e; }
QProgressBar#jauge-volume[niveau="full"]::chunk { border-color: #26ab62; }

/* La grille d'objets. Pas de bordure sur les cases : l'icone se suffit,
   et une grille de quatre cents objets deviendrait un quadrillage. */
QListWidget {
    background-color: %(surface)s;
    border: none;
}
QListWidget::item {
    border-radius: 6px;
    margin: 2px;
}
QListWidget::item:hover    { background-color: %(variante)s; }
QListWidget::item:selected { background-color: %(sarcelle_sombre)s; }

/* Les ascenseurs, discrets : la grille est deja chargee. */
QScrollBar:vertical {
    background: %(surface)s; width: 10px; margin: 0;
}
QScrollBar::handle:vertical {
    background: %(variante)s; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: %(sarcelle_sombre)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* Les infobulles : c'est la fiche d'un objet, elle se lit. */
QToolTip {
    background-color: %(variante)s;
    color: %(texte)s;
    border: 1px solid %(sarcelle_sombre)s;
    padding: 6px;
}

/* Les libelles discrets et les valeurs mises en avant. */
QLabel#discret   { color: %(texte_faible)s; }
/* La saison d'Atys. Or, et **pas** gras : la version GTK pose la
   couleur seule, et la graisse rendait la ligne floue. */
QLabel#valeur    { color: %(or)s; }
QLabel#erreur    { color: %(erreur)s; }
/* La signature du pied. **#888b8a et non la couleur de texte attenuee** : GTK
   lui pose la classe `dim-label` d'Adwaita, qui n'est pas une couleur mais une
   opacite de 0,55 ; sur le fond de la bande, cela donne exactement ce gris. Et
   `caption`, qui la met a 90 %% du corps -- ce que Qt ne faisait pas, d'ou une
   signature plus grande et plus claire que celle de la reference.

   Le corps est pose plus haut, avec les autres tailles calculees : les
   pourcentages n'existent pas dans une feuille Qt. */
QLabel#signature { color: #888b8a; }

/* Les cases a cocher : quatorze pixels de cote, un fond gris et une bordure
   quand elles sont vides, le sarcelle de l'application et une coche sombre
   quand elles sont cochees. Toutes ces valeurs sont relevees au pixel sur la
   fenetre GTK -- Fusion, lui, ne dessinait qu'un chevron nu sans case, et les
   cases vides n'avaient pas la meme bordure. */
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #424242;
    border-radius: 4px;
    background-color: #353535;
}
QCheckBox::indicator:checked {
    background-color: %(sarcelle)s;
    border-color: %(sarcelle)s;
    image: url("%(coche)s");
}
QCheckBox::indicator:disabled { background-color: %(fond)s; }

/* Les champs de saisie et les listes deroulantes a la mesure d'Adwaita :
   vingt-quatre pixels de contenu, quatre de remplissage en haut et en bas, un
   de bordure de chaque cote -- trente-quatre en tout. Sans cette regle, Fusion
   les dessinait dix pixels plus courts, et les rangees de la fenetre d'Options
   se suivaient tous les trente-trois pixels la ou GTK les espace de
   quarante-quatre. Mesure sur les deux fenetres. */
QLineEdit {
    background-color: %(variante)s;
    border: 1px solid #1b1b1b;
    border-radius: 6px;
    color: %(texte)s;
    padding: 4px 8px;
    min-height: 25px;
}
QLineEdit:focus { border-color: %(sarcelle)s; }

/* Une liste deroulante n'est pas un champ : GTK en fait un **bouton**, et
   Adwaita lui donne le meme gris qu'a l'ajout ou a la corbeille de la barre du
   haut -- #383838, mesure. La peindre du bleu-vert des champs etait une erreur
   de ma part, que la comparaison par l'image a relevee. */
QComboBox {
    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                      stop: 0 #3a3a3a, stop: 0.5 #393939,
                                      stop: 1 #373737);
    border: 1px solid #1b1b1b;
    border-radius: 6px;
    color: %(texte)s;
    /* Huit de chaque cote, et pas un de plus a droite : Qt reserve la zone du
       `drop-down` **en plus** du remplissage, si bien qu'un padding-right de
       trente volait vingt-deux pixels au texte -- « La Lune Eternelle (atys) »
       s'affichait « La Lun ». L'air avant le chevron se gagne en demandant une
       largeur plus grande, dans `deroulante.py`, jamais en rognant le texte. */
    /* Six pixels en haut et en bas, et non quatre : depuis que les
       contenants portent leur image, la ligne des selecteurs faisait quatre
       pixels de moins que celle de GTK -- vu par la comparaison par l'image,
       qui lit les bandes de la fenetre. Le remplissage horizontal, lui, ne
       bouge pas : `deroulante.py` mesure avec. */
    padding: 4px 8px;
    min-height: 25px;
}
QComboBox:hover { background-color: #454545; }
QComboBox:focus { border-color: %(sarcelle)s; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    image: url("%(chevron)s");
    /* Seize pixels comme le chevron de GTK, et non quatorze : a l'oeil, la
       fleche de Qt paraissait plus timide que celle d'a cote. */
    width: 16px;
    height: 16px;
}

/* Le compteur des Options : un champ, un moins, un plus, sur une seule ligne.
   Toutes ces valeurs sont relevees au pixel sur la fenetre GTK : le fond d'un
   champ, une bordure sombre, des separateurs d'un pixel entre les trois
   parties, et le gris des glyphes. Voir `compteur.py` pour la raison d'un
   compteur ecrit a la main. */
#compteur {
    background-color: %(variante)s;
    border: 1px solid #1b1b1b;
    border-radius: 6px;
}
QSpinBox#compteur-champ {
    background: transparent;
    border: none;
    color: %(texte)s;
    padding: 4px 8px;
    min-height: 26px;
}
QPushButton#compteur-bouton {
    background: transparent;
    border: none;
    /* Le trait d'un pixel qui separe les trois parties, comme dans GTK. */
    border-left: 1px solid #1d272a;
    color: #dbdbd9;
    padding: 4px 0;
    min-height: 26px;
}
QPushButton#compteur-bouton:hover   { background-color: %(surface)s; }
QPushButton#compteur-bouton:pressed { background-color: %(fond)s; }
/* Eteint a la borne : le compteur dit ce qu'il peut encore faire. */
QPushButton#compteur-bouton:disabled { color: #5c6462; }
""" % dict(COULEURS, coche=COCHE, chevron=CHEVRON)


#: La couleur qu'Adwaita donne au texte -- et donc a l'icone -- d'un bouton.
ENCRE_BOUTON = "#eeeeec"


def icone_symbolique(nom: str, couleur: str = ENCRE_BOUTON) -> QIcon:
    """Une icône du thème du bureau, **recolorée** comme GTK le ferait.

    Les icônes dites « symboliques » sont des silhouettes destinées à prendre
    la couleur du texte qui les entoure : GTK les repeint, Qt les sert telles
    quelles. Sur un fond sombre, la loupe du champ de recherche et la corbeille
    de la barre du haut restaient donc gris foncé là où GTK les montre
    presque blanches. C'est la comparaison par l'image qui l'a vu.

    Le procédé est celui de tout le monde : on dessine l'icône, puis on remplit
    par-dessus en ne gardant que ce qui est déjà opaque (`SourceIn`).

    Rend une icône vide si le bureau n'a pas cette icône — sous Windows, par
    exemple, où l'appelant retombe sur son repli textuel.
    """
    # La cascade de GTK, dans cet ordre : le nom demande dans le theme du
    # bureau ; a defaut, dans ce meme theme, la version **coloree** -- rendue
    # telle quelle, un plus bleu reste bleu ; et seulement ensuite le repli
    # d'Adwaita, silhouette blanche qu'on repeint. C'est ce qui fait qu'une
    # machine reglee sur « gnome » montre le plus bleu et le dossier beige,
    # mais garde le menu blanc d'Adwaita, que « gnome » ne porte pas.
    if nom.endswith("-symbolic") and _fichier_du_bureau(nom) is None:
        colore = _fichier_du_bureau(nom[: -len("-symbolic")])
        if colore is not None:
            return QIcon(colore)
    source = QIcon.fromTheme(nom)
    if source.isNull():
        return QIcon()
    # Assez grand pour que la réduction reste nette sur un écran fin.
    pixmap = source.pixmap(64, 64)
    if pixmap.isNull():
        return QIcon()
    teinte = QPixmap(pixmap.size())
    teinte.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(teinte)
    peintre.drawPixmap(0, 0, pixmap)
    peintre.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_SourceIn)
    peintre.fillRect(teinte.rect(), QColor(couleur))
    peintre.end()
    return QIcon(teinte)


def _fichier_du_bureau(nom: str):
    """Le fichier de cette icone dans le theme du bureau, ou None.

    On regarde le disque plutot que d'interroger `QIcon.fromTheme` : celui-ci
    a deja un repli sur Adwaita, et rendrait la silhouette blanche au moment
    meme ou l'on cherche a savoir si le theme du bureau, lui, a quelque chose.
    Les tailles sont parcourues de la plus grande a la plus petite -- une
    icone reduite reste nette, agrandie non.
    """
    import glob
    theme = _theme_du_bureau()
    if not theme:
        return None
    for racine in ("/usr/share/icons", os.path.expanduser("~/.local/share/icons")):
        trouves = []
        for suffixe in ("svg", "png"):
            trouves += glob.glob(f"{racine}/{theme}/**/{nom}.{suffixe}",
                                 recursive=True)
        if trouves:
            def taille(chemin: str) -> int:
                for morceau in chemin.split(os.sep):
                    if "x" in morceau and morceau.split("x")[0].isdigit():
                        return int(morceau.split("x")[0])
                return 1024          # « scalable » passe devant les tailles fixes
            return max(trouves, key=taille)
    return None


def _theme_du_bureau() -> str:
    """Le theme d'icones choisi dans GNOME, ou rien.

    Lu par `gsettings`, faute de mieux : Qt ne recoit pas ce reglage sous
    Wayland, et le portail ne le sert qu'a grand renfort de D-Bus. Absent ou
    illisible -- un autre bureau, Windows --, l'appelant retombe sur Adwaita.
    """
    import subprocess
    try:
        sortie = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "icon-theme"],
            capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return ""
    return sortie.stdout.strip().strip("'\"") if sortie.returncode == 0 else ""


def caler_icones() -> None:
    """Les memes icones que GTK : celles d'Adwaita, et pas celles du bureau.

    GTK4 ne va pas chercher ses icones symboliques dans le theme du bureau :
    il les porte dans ses propres ressources, et ce sont donc toujours celles
    d'Adwaita qui s'affichent -- la loupe, la corbeille, le dossier, la
    resynchronisation. Qt, lui, prend celles du theme courant, quand il en
    trouve un : d'ou une loupe au trait plus fin et pas tout a fait posee au
    meme endroit.

    On lui designe donc Adwaita, la ou il est installe, et on ajoute les
    dossiers d'icones du systeme a sa recherche -- il ne connait d'origine que
    ses propres ressources. Sans Adwaita -- sous Windows -- rien ne change et
    l'appelant garde ses replis textuels.
    """
    chemins = list(QIcon.themeSearchPaths())
    for dossier in ("/usr/share/icons",
                    os.path.expanduser("~/.local/share/icons")):
        if os.path.isdir(dossier) and dossier not in chemins:
            chemins.append(dossier)
    QIcon.setThemeSearchPaths(chemins)
    # **Le theme du bureau, et non un theme impose.** GTK suit le reglage de
    # GNOME : sur une machine reglee sur « gnome », il montre le plus bleu de
    # `list-add` et le dossier beige de `document-open`, faute de version
    # symbolique dans ce theme -- pas les silhouettes blanches d'Adwaita. Qt
    # ne lit pas ce reglage sous Wayland ; on le lui donne, sans quoi les deux
    # fenetres ne montrent pas les memes pictogrammes sur la meme machine.
    bureau = _theme_du_bureau()
    if bureau and any(os.path.isdir(os.path.join(d, bureau)) for d in chemins):
        QIcon.setThemeName(bureau)
    elif any(os.path.isdir(os.path.join(d, "Adwaita")) for d in chemins):
        QIcon.setThemeName("Adwaita")
    QIcon.setFallbackThemeName("Adwaita")


def _famille_emoji() -> str:
    """La fonte emoji en couleur, nommee explicitement.

    Laisser Qt choisir son repli ne donne pas le meme dessin que GTK : la
    loupe sortait bleue et penchee a droite, la ou GTK -- qui passe par Noto
    Color Emoji -- la montre orange et penchee a gauche, et le signe plus
    sortait gris au lieu du bleu de Noto. On nomme donc la fonte, avec les
    equivalents des autres systemes derriere.
    """
    connues = set(QFontDatabase.families())
    for famille in ("Noto Color Emoji", "Segoe UI Emoji", "Apple Color Emoji",
                    "Noto Emoji"):
        if famille in connues:
            return famille
    return ""


def icone_emoji(caractere: str, cote: int = 32) -> QIcon:
    """Un emoji en couleur, servi comme icone.

    Une action de `QLineEdit` reclame une `QIcon` : le glyphe est donc peint
    dans une image, avec la police emoji du systeme, plutot que pose comme du
    texte. `QFont` choisit seul la fonte de repli qui porte le caractere --
    Noto Color Emoji ici --, et la peinture garde ses couleurs.
    """
    pixmap = QPixmap(cote, cote)
    pixmap.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(pixmap)
    police = QFont(_famille_emoji())
    police.setPixelSize(int(cote * 0.82))
    peintre.setFont(police)
    peintre.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, caractere)
    peintre.end()
    return QIcon(pixmap)


def poser_loupe(champ) -> None:
    """La loupe a gauche d'un champ de recherche, comme GTK la pose partout.

    La version GTK n'emploie que des `Gtk.SearchEntry`, et une `SearchEntry`
    porte sa loupe d'origine — les cinq champs de recherche de l'application
    en ont donc une. Un `QLineEdit`, lui, n'a rien de tel : il faut la poser
    soi-meme, et il suffisait d'oublier un champ pour que celui-la seul s'en
    passe. C'est ce qui etait arrive au journal, au chatlog, aux competences
    et au roster : seul l'inventaire avait la sienne.

    **L'emoji, et non l'icone symbolique.** La fenetre GTK du paquet montre la
    loupe en couleur — cercle orange, verre vert — et non le trait blanc de
    `system-search-symbolic` : releve au pixel sur la capture, et c'est elle
    qui fait foi.
    """
    loupe = icone_symbolique("system-search-symbolic")
    if loupe.isNull():
        loupe = icone_symbolique("edit-find-symbolic")
    if not loupe.isNull():
        champ.addAction(loupe, QLineEdit.ActionPosition.LeadingPosition)


def largeur(widget, facteur: float) -> int:
    """Une largeur exprimée en hauteurs de ligne, et non en pixels.

    Les largeurs fixes écrites en pixels ne suivent pas la police : grossie
    d'un point, la flèche d'une branche ou le symbole d'un bouton se fait
    couper par un cadre resté à sa taille. Rapportée à la hauteur d'une ligne,
    la même mesure grandit avec le texte qu'elle encadre.

    Les facteurs sont calés sur la police par défaut : 1,8 rendait les 34 px
    des boutons carrés, 4,7 les 90 px des colonnes de niveau.
    """
    return max(1, round(QFontMetrics(widget.font()).height() * facteur))
