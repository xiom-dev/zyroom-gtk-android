"""Les bulles d'alerte près de l'horloge.

**Ce que Qt fait autrement que GTK.** La version GTK envoie une
`Gio.Notification` à son `Gtk.Application` : GLib parle alors au service de
notification du bureau, par D-Bus. Rien de cela n'existe sous Windows.

Qt passe par une icône de zone de notification, qui sait afficher un message
sur les deux systèmes : le protocole du bureau sous Linux, les bulles de la
zone de notification sous Windows. C'est le seul chemin commun.

**L'icône reste invisible.** On ne veut pas d'un ZyRoom installé à côté de
l'horloge — seulement le droit d'y faire paraître un message. Qt exige
pourtant qu'elle existe et soit montrée pour que `showMessage` fonctionne :
elle porte donc l'icône de l'application, et disparaît avec elle.

Rien n'est garanti : un bureau sans service de notification, une session sans
zone de notification, et le message ne paraît pas. C'est sans conséquence — les
alertes restent listées dans la cloche, qui est l'endroit où on vient les lire.
"""
from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon

_zone: QSystemTrayIcon | None = None


def _icone_zone(parent) -> QSystemTrayIcon | None:
    global _zone
    if _zone is not None:
        return _zone
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None
    icone = QIcon.fromTheme("net.ryzom.zyroomqt")
    if icone.isNull():
        icone = parent.windowIcon()
    _zone = QSystemTrayIcon(icone, parent)
    _zone.setToolTip("ZyRoom-Qt")
    _zone.show()
    return _zone


def envoyer(parent, titre: str, corps: str) -> bool:
    """Affiche une bulle. Rend vrai si elle a pu partir."""
    zone = _icone_zone(parent)
    if zone is None or not QSystemTrayIcon.supportsMessages():
        return False
    zone.showMessage(titre, corps, QSystemTrayIcon.MessageIcon.Information,
                     10_000)
    return True


def retirer() -> None:
    """Retire la bulle en attente, s'il y en a une.

    Couper le robinet ne vide pas le seau : celle qui attend déjà près de
    l'horloge y resterait, et c'est elle qu'on voulait voir partir.
    """
    if _zone is not None:
        _zone.hide()
        _zone.show()


def arreter() -> None:
    """Retire l'icône de la zone, à la fermeture."""
    global _zone
    if _zone is not None:
        _zone.hide()
        _zone = None
