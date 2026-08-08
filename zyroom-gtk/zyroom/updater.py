"""Mise à jour de l'application depuis l'application elle-même.

Une application Flatpak est en bac à sable : elle ne peut pas lancer
`flatpak update`. Le système fournit pour cela un portail,
`org.freedesktop.portal.Flatpak`, qui expose un « moniteur de mise à jour » :
il prévient quand une version plus récente existe dans le dépôt d'origine, et
sait l'installer après confirmation de l'utilisateur par une fenêtre du système.

Deux limites à connaître :

  - **C'est le portail qui décide quand vérifier.** Il n'existe aucune méthode
    « vérifie maintenant » ; il sonde à sa propre cadence, et le signal peut
    donc arriver plusieurs minutes après le lancement.
  - **Rien ne se passe hors Flatpak.** Lancée depuis les sources ou installée
    par le paquet Debian, l'application ne trouve pas le portail : le module se
    met alors en sommeil et le bouton n'apparaît jamais, ce qui est correct —
    c'est apt qui met à jour dans ce cas.
"""
from __future__ import annotations

from gi.repository import Gio, GLib

_PORTAL_NAME = "org.freedesktop.portal.Flatpak"
_PORTAL_PATH = "/org/freedesktop/portal/Flatpak"
_MONITOR_IFACE = "org.freedesktop.portal.Flatpak.UpdateMonitor"


class Updater:
    """Surveille les mises à jour et sait les appliquer.

    `on_available(version)` est appelé quand une version plus récente existe,
    `on_progress(texte, terminé, erreur)` pendant l'installation. Les deux
    arrivent sur le fil principal, ils peuvent toucher à l'interface.
    """

    def __init__(self, on_available, on_progress) -> None:
        self._on_available = on_available
        self._on_progress = on_progress
        self._monitor: Gio.DBusProxy | None = None
        self._start()

    @property
    def available(self) -> bool:
        """Vrai si le moniteur a pu être créé — donc si on tourne en Flatpak."""
        return self._monitor is not None

    def _start(self) -> None:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            portal = Gio.DBusProxy.new_sync(
                bus, Gio.DBusProxyFlags.NONE, None,
                _PORTAL_NAME, _PORTAL_PATH, _PORTAL_NAME, None)
            handle = portal.call_sync(
                "CreateUpdateMonitor", GLib.Variant("(a{sv})", ({},)),
                Gio.DBusCallFlags.NONE, -1, None).unpack()[0]
            self._monitor = Gio.DBusProxy.new_sync(
                bus, Gio.DBusProxyFlags.NONE, None,
                _PORTAL_NAME, handle, _MONITOR_IFACE, None)
            self._monitor.connect("g-signal", self._on_signal)
        except Exception:
            # Hors bac à sable, ou portail absent : pas de mise à jour intégrée.
            self._monitor = None

    def _on_signal(self, _proxy, _sender, signal, params) -> None:
        if signal == "UpdateAvailable":
            info = params.unpack()[0]
            # `remote-commit` est le seul champ qui identifie la version qui
            # attend ; il n'y a pas de numéro de version dans ce signal.
            self._on_available(info.get("remote-commit", "")[:12])
        elif signal == "Progress":
            info = params.unpack()[0]
            self._on_progress(*_lire_progression(info))

    def update(self) -> None:
        """Lance la mise à jour. Le système demande confirmation de son côté.

        L'appel est **asynchrone** : le portail ne rend la main qu'une fois sa
        fenêtre de confirmation refermée, et un appel bloquant figeait l'interface
        pendant tout ce temps — le gestionnaire de fenêtres finissait par
        signaler une application qui ne répond plus.
        """
        if self._monitor is None:
            return
        self._monitor.call(
            "Update", GLib.Variant("(sa{sv})", ("", {})),
            Gio.DBusCallFlags.NONE, -1, None, self._update_done, None)

    def _update_done(self, proxy, result, _data) -> None:
        try:
            proxy.call_finish(result)
        except GLib.Error as echec:
            # Le refus le plus courant : le portail n'ouvre sa fenêtre que pour
            # l'application au premier plan. Le message brut ne dirait rien à un
            # joueur.
            if "focused" in echec.message:
                self._on_progress(
                    "Gardez la fenêtre au premier plan pendant la mise à jour.",
                    True, True)
            else:
                self._on_progress(f"Mise à jour refusée : {echec.message}",
                                  True, True)

    def close(self) -> None:
        if self._monitor is None:
            return
        try:
            self._monitor.call_sync("Close", None, Gio.DBusCallFlags.NONE,
                                    -1, None)
        except Exception:                               # noqa: BLE001
            pass
        self._monitor = None


#: Codes d'état du portail (`status` du signal Progress).
_EN_COURS, _VIDE, _TERMINE, _ECHEC = 0, 1, 2, 3


def _lire_progression(info: dict) -> tuple[str, bool, bool]:
    """(texte affichable, terminé, en erreur) à partir d'un signal Progress."""
    if info.get("error"):
        message = info.get("error_message") or info["error"]
        return f"Échec de la mise à jour : {message}", True, True

    etat = info.get("status", _EN_COURS)
    if etat == _TERMINE:
        return "Mise à jour installée — relancez l'application.", True, False
    if etat == _ECHEC:
        return "La mise à jour a échoué.", True, True
    if etat == _VIDE:
        return "Aucune mise à jour à installer.", True, False

    part = info.get("progress")
    return (f"Mise à jour en cours… {part} %" if part is not None
            else "Mise à jour en cours…"), False, False
