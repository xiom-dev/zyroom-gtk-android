"""La barre d'attente, peinte à la main. Le pendant exact de celle de Qt.

**Pourquoi ne pas se contenter d'une `Gtk.ProgressBar` pulsée.** Son curseur
**rebondit** au bord : arrivé à droite, il repart vers la gauche, et l'on veut
un défilement à sens unique. Le renvoyer au départ demandait un `set_fraction`
qui sort du mode pulsé, suivi d'un `pulse` qui y revient — et ce va-et-vient
interrompt l'animation interne de GTK, qui finissait par se coincer. Le
curseur s'arrêtait, il fallait fermer la fenêtre pour qu'il reparte.

Trente lignes de peinture donnent ce que le réglage ne sait pas faire : un
curseur qui va toujours dans le même sens, sans animation à interrompre.
Elles donnent aussi la parité par construction — `zyroom-qt/zyroom/attente.py`
tient les mêmes nombres et la même mécanique, et les deux se comparent
ligne à ligne.

Les couleurs sont celles qu'Adwaita donne à une barre de progression, que le
CSS du programme ne remplace pas : seul le remplissage devient sarcelle.
"""
from __future__ import annotations

from gi.repository import GLib, Gtk

#: La fraction de la barre qu'occupe le curseur, et dont il avance à chaque
#: battement. C'était le `set_pulse_step` de la barre d'avant.
PAS = 0.15

#: Le battement, en millisecondes.
CADENCE = 100

#: Le fond, le liseré et le remplissage, en composantes de 0 à 1 — c'est ce
#: que Cairo attend. Respectivement #282828, #15539e et #3f7a68.
FOND = (0x28 / 255, 0x28 / 255, 0x28 / 255)
LISERE = (0x15 / 255, 0x53 / 255, 0x9e / 255)
CURSEUR = (0x3f / 255, 0x7a / 255, 0x68 / 255)
RAYON = 4.0

#: Les mesures de la barre, en pixels.
LARGEUR = 60
HAUTEUR = 10


def positions() -> int:
    """Combien de positions le curseur occupe avant de revenir au départ.

    Sept positions à 0,15 : six pas pleins, puis un dernier raccourci pour que
    le curseur **touche le bord droit**. Le compte précédent — cinq positions —
    l'arrêtait aux trois quarts de la barre, et il repartait de là : on voyait
    un curseur qui n'allait jamais au bout.
    """
    import math

    return math.ceil((1.0 - PAS) / PAS) + 1


def decalage(position: int) -> float:
    """Où commence le curseur, en fraction de la barre.

    Le dernier pas est **borné** : sans cela le curseur dépasserait le bord et
    Cairo le dessinerait à cheval sur le vide.
    """
    return min(PAS * position, 1.0 - PAS)


class BarreAttente(Gtk.DrawingArea):
    """Un curseur qui court de gauche à droite tant qu'on attend."""

    def __init__(self) -> None:
        super().__init__()
        self._position = 0
        self._minuteur = None
        self.set_size_request(LARGEUR, HAUTEUR)
        self.set_valign(Gtk.Align.CENTER)
        self.set_draw_func(self._peindre)
        self.set_visible(False)

    def set_visible(self, visible: bool) -> None:
        """Le minuteur ne tourne que quand la barre se voit.

        Peindre pour personne coûterait un réveil dix fois par seconde, et la
        barre passe l'essentiel de son temps cachée.
        """
        super().set_visible(visible)
        if visible and self._minuteur is None:
            self._position = 0
            self._minuteur = GLib.timeout_add(CADENCE, self._battre)
        elif not visible and self._minuteur is not None:
            GLib.source_remove(self._minuteur)
            self._minuteur = None

    def _battre(self) -> bool:
        # Le minuteur s'arrête avec la barre, et jamais autrement : c'est la
        # seule façon de ne pas le perdre en route. L'ancienne version le
        # laissait s'éteindre depuis son propre battement, et il arrivait que
        # la barre reste visible sans que rien ne la fasse avancer.
        if not self.get_visible():
            self._minuteur = None
            return False
        self._position = (self._position + 1) % positions()
        self.queue_draw()
        return True

    def _peindre(self, _zone, cr, largeur, hauteur) -> None:
        def rectangle(x, y, l, h, r):
            import math
            cr.new_sub_path()
            cr.arc(x + l - r, y + r, r, -math.pi / 2, 0)
            cr.arc(x + l - r, y + h - r, r, 0, math.pi / 2)
            cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
            cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
            cr.close_path()

        cr.set_source_rgb(*FOND)
        rectangle(0, 0, largeur, hauteur, RAYON)
        cr.fill()

        large = largeur * PAS
        depart = largeur * decalage(self._position)
        # Le liseré est peint à l'intérieur : sans ce retrait d'un demi-pixel,
        # Cairo le centre sur le bord et la moitié tombe hors du curseur.
        rectangle(depart + 0.5, 0.5, large - 1, hauteur - 1, RAYON)
        cr.set_source_rgb(*CURSEUR)
        cr.fill_preserve()
        cr.set_source_rgb(*LISERE)
        cr.set_line_width(1)
        cr.stroke()
