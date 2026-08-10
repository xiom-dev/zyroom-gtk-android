"""Mise à jour de l'application depuis l'application elle-même.

Une application Flatpak est en bac à sable : elle ne peut pas lancer
`flatpak update`. Le système fournit pour cela un portail,
`org.freedesktop.portal.Flatpak`, qui expose un « moniteur de mise à jour » :
il prévient quand une version plus récente existe dans le dépôt d'origine, et
sait l'installer après confirmation de l'utilisateur par une fenêtre du système.

Deux limites à connaître :

  - **C'est le portail qui décide quand vérifier.** Il n'existe aucune méthode
    « vérifie maintenant » ; il sonde à sa propre cadence, et le signal peut
    donc arriver longtemps après le lancement. D'où le `Veilleur` ci-dessous,
    qui regarde lui-même le dépôt publié : le portail reste seul à savoir
    installer, mais il n'est plus seul à savoir qu'il y a quelque chose à
    installer.
  - **Rien ne se passe hors Flatpak.** Lancée depuis les sources ou installée
    par le paquet Debian, l'application ne trouve pas le portail : le module se
    met alors en sommeil et le bouton n'apparaît jamais, ce qui est correct —
    c'est apt qui met à jour dans ce cas.
"""
from __future__ import annotations

import re
import urllib.request

from gi.repository import Gio, GLib

_PORTAL_NAME = "org.freedesktop.portal.Flatpak"
_PORTAL_PATH = "/org/freedesktop/portal/Flatpak"
_MONITOR_IFACE = "org.freedesktop.portal.Flatpak.UpdateMonitor"

#: Le dépôt d'où viennent les mises à jour, celui qu'annonce le bundle installé.
DEPOT = "https://xiom-dev.github.io/zyroom-gtk-android/repo/"

#: Ce que le bac à sable dit de l'application en cours d'exécution.
_INFO_FLATPAK = "/.flatpak-info"


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


class Veilleur:
    """Regarde le dépôt publié, sans passer par le portail.

    Le portail sonde à sa guise — souvent une fois par heure — et le bouton
    « Mettre à jour » n'apparaissait donc qu'avec beaucoup de retard, parfois
    jamais dans une séance de jeu. Ici on lit simplement, en HTTPS, l'empreinte
    que le dépôt annonce pour cette application, et on la compare à celle qu'on
    exécute. C'est un fichier de soixante-cinq octets ; on peut le demander à
    chaque lancement et tous les quarts d'heure sans peser sur rien.

    Le portail garde son rôle : lui seul peut installer. Il refait de son côté
    la comparaison au moment de le faire, et n'installe donc jamais sur la foi
    de cette lecture-ci.

    Hors bac à sable, `possible` est faux : il n'y a ni empreinte installée à
    lire, ni mise à jour à proposer.
    """

    def __init__(self) -> None:
        self.application, self.commit_installe = _identite_flatpak()

    @property
    def possible(self) -> bool:
        return bool(self.application and self.commit_installe)

    @property
    def url(self) -> str:
        """L'adresse de la référence publiée pour cette application."""
        return (f"{DEPOT}refs/heads/app/{self.application}/x86_64/master")

    def commit_publie(self, timeout: int = 15) -> str:
        """L'empreinte annoncée par le dépôt, ou une chaîne vide s'il se tait.

        Une panne de réseau ne doit rien casser : sans réponse, on s'en tient à
        ce qu'on a, et on redemandera au prochain quart d'heure.
        """
        try:
            with urllib.request.urlopen(self.url, timeout=timeout) as reponse:
                texte = reponse.read(200).decode("ascii", "ignore").strip()
        except Exception:                               # noqa: BLE001
            return ""
        return texte if re.fullmatch(r"[0-9a-f]{64}", texte) else ""

    def mise_a_jour_disponible(self) -> str:
        """L'empreinte qui attend, ou une chaîne vide s'il n'y a rien de neuf."""
        if not self.possible:
            return ""
        publie = self.commit_publie()
        return publie if publie and publie != self.commit_installe else ""


def _identite_flatpak() -> tuple[str, str]:
    """(identifiant d'application, empreinte installée), vides hors Flatpak.

    `/.flatpak-info` est écrit par Flatpak dans chaque bac à sable ; sa clé
    `app-commit` est exactement ce que le dépôt publie sous `refs/heads`.
    """
    try:
        with open(_INFO_FLATPAK, encoding="utf-8") as fichier_info:
            contenu = fichier_info.read()
    except OSError:
        return "", ""
    fichier = GLib.KeyFile()
    try:
        fichier.load_from_data(contenu, len(contenu), GLib.KeyFileFlags.NONE)
        return (fichier.get_string("Application", "name"),
                fichier.get_string("Instance", "app-commit"))
    except Exception:                                   # noqa: BLE001
        return "", ""


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
