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

from PySide6.QtGui import QColor, QFontMetrics, QPalette

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
    "fini":            "#82a89d",
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
    corps = ""
    if taille > 0:
        # `*` atteint tout, y compris les deux libelles du nom grave, dont le
        # corps est calcule a part -- il les rapetissait a la taille courante.
        # On le leur rend ici, dans les memes proportions que fenetre.py.
        corps = (f"* {{ font-size: {taille}pt; }}\n"
                 f"#nom-grave {{ font-size: {taille * 2.9:.0f}pt; }}\n"
                 f"#nom-mouture {{ font-size: {taille * 2.7:.0f}pt; }}\n")
    return corps + """
/* Les bandes qui encadrent la grille : la barre du haut, celle des deux
   selecteurs, et le pied. Un cran sous le fond, pour tenir la grille entre
   elles au lieu de s'y fondre. */
#entete, #bande {
    background-color: %(bande)s;
}

/* La navigation : trois boutons qui se touchent, comme la classe « linked »
   de GTK. Les coins ne s'arrondissent qu'aux extremites du bloc. */
QPushButton#nav, QToolButton#nav {
    background-color: %(variante)s;
    color: %(texte)s;
    border: 1px solid %(bande)s;
    border-radius: 0;
    padding: 4px 14px;
}
QPushButton#nav:hover, QToolButton#nav:hover {
    background-color: %(sarcelle_sombre)s;
}
/* Le fond suffit a dire lequel est choisi. Le gras, lui, changeait la
   largeur du texte : le bouton s'elargissait d'un coup au clic, poussant ses
   voisins, et la police epaissie a la volee -- sans graisse dessinee dans la
   fonte -- paraissait floue. */
QPushButton#nav:checked, QToolButton#nav[actif="true"] {
    background-color: %(sarcelle_sombre)s;
    color: %(texte)s;
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

/* La signature, discrete : c'est une mention, pas un bouton d'action. */
QPushButton#signature {
    background: transparent;
    border: none;
    color: %(texte_faible)s;
    padding: 0 0 2px 0;
}
QPushButton#signature:disabled { color: %(texte_faible)s; }

/* Le bouton d'action principale : le seul aplat franc de la fenetre. */
QPushButton#principal {
    background-color: %(sarcelle)s;
    color: %(accent_texte)s;
    font-weight: bold;
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
QLabel#valeur    { color: %(or)s; font-weight: bold; }
QLabel#erreur    { color: %(erreur)s; }
QLabel#signature { color: %(texte_faible)s; }
""" % COULEURS


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
