"""Chemins de l'application, réglages et persistance des entités.

Conventions XDG (standard Linux/Debian) :
  - config  : ~/.config/zyroom-gtk/  (characters.ini, guilds.ini, settings.ini)
  - cache   : ~/.cache/zyroom-gtk/   (icônes, flux XML, noms)

Les fichiers .ini reprennent l'esprit des character.ini / guild.ini d'origine
(une section [id] par entité) mais stockent la clé API **en clair** : chaque
joueur y met sa propre clé, il n'y a donc rien de sensible à chiffrer.
"""
from __future__ import annotations

import configparser
import glob
import hashlib
import os

APP_ID = "zyroom-gtk"

# Répertoire des données embarquées (sheetid.csv)
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SHEETID_CSV = os.path.join(_DATA_DIR, "sheetid.csv")
CATEGORY_CSV = os.path.join(_DATA_DIR, "category.csv")

# Entités pré-configurées, si le paquet en livre. Le mécanisme reste en place
# mais **rien n'est livré** : y mettre la guilde revenait à donner sa clé d'API,
# en clair, à quiconque installe le paquet — et donc à qui saurait l'en extraire.
# La clé se transmet désormais de la main à la main, sur le Discord de la guilde.
_DEFAULTS_DIR = os.path.join(_DATA_DIR, "default")


def _xdg(env: str, default_subdir: str) -> str:
    base = os.environ.get(env) or os.path.join(os.path.expanduser("~"), default_subdir)
    path = os.path.join(base, APP_ID)
    os.makedirs(path, exist_ok=True)
    return path


def config_dir() -> str:
    return _xdg("XDG_CONFIG_HOME", ".config")


def cache_dir() -> str:
    return _xdg("XDG_CACHE_HOME", ".cache")


def data_dir() -> str:
    return _xdg("XDG_DATA_HOME", ".local/share")


def backup_dir() -> str:
    path = os.path.join(data_dir(), "backup")
    os.makedirs(path, exist_ok=True)
    return path


def detect_save_folder() -> str:
    """Cherche le dossier « save » de Ryzom à des emplacements plausibles."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "share", "Ryzom", "save"),
        os.path.join(home, ".ryzom", "save"),
        os.path.join(home, "Ryzom", "save"),
        os.path.join(home, "jeu", "ryzom", "save"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return ""


def icon_cache_dir() -> str:
    path = os.path.join(cache_dir(), "icons")
    os.makedirs(path, exist_ok=True)
    return path


def names_cache_path() -> str:
    return os.path.join(cache_dir(), "names.json")


def portrait_path(kind: str, entity_id: str, url: str = "") -> str:
    """Emplacement du cache du portrait d'une entité (rendu 3D / icône).

    Le nom porte une empreinte de l'adresse demandée. Sans elle, changer la
    façon de composer le rendu — le cadrage, l'équipement — ne changeait rien à
    l'écran : le fichier existait déjà, et il était servi tel quel. Il aurait
    fallu que chaque joueur vide son cache, ce que personne ne fait ni ne
    devine.

    Une entité change de portrait quand elle change d'équipement : les anciens
    fichiers sont donc écartés au passage, sinon le cache grossirait d'une image
    à chaque tenue.
    """
    path = os.path.join(cache_dir(), "portrait")
    os.makedirs(path, exist_ok=True)
    if not url:
        return os.path.join(path, f"{kind}-{entity_id}.png")
    empreinte = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    courant = os.path.join(path, f"{kind}-{entity_id}-{empreinte}.png")
    prefixe = f"{kind}-{entity_id}"
    for nom in os.listdir(path):
        if nom.startswith(prefixe) and os.path.join(path, nom) != courant:
            try:
                os.remove(os.path.join(path, nom))
            except OSError:
                pass
    return courant


def entity_xml_path(kind: str, entity_id: str) -> str:
    """Emplacement du cache d'un flux API (consultation hors-ligne)."""
    path = os.path.join(cache_dir(), kind)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{entity_id}.xml")


def last_sync(kind: str, entity_id: str):
    """Date de la dernière synchronisation d'une entité, ou None.

    Le cache est réécrit à chaque appel réussi à l'API : sa date de
    modification date donc exactement les données affichées.
    """
    import datetime

    path = entity_xml_path(kind, entity_id)
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return None


def format_last_sync(when) -> str:
    """Formule lisible : « aujourd'hui à 14h05 », « le 02/08 à 19h37 »."""
    if when is None:
        return "jamais synchronisé"

    import datetime

    today = datetime.date.today()
    if when.date() == today:
        return f"aujourd'hui à {when:%Hh%M}"
    if (today - when.date()).days == 1:
        return f"hier à {when:%Hh%M}"
    return f"le {when:%d/%m} à {when:%Hh%M}"


def snapshot_path(kind: str, entity_id: str) -> str:
    """Emplacement de l'instantané d'inventaire (détection de mouvements)."""
    path = os.path.join(cache_dir(), "watch")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{kind}-{entity_id}.json")


def movements_path(kind: str, entity_id: str) -> str:
    """Emplacement du journal des mouvements d'une entité.

    En données (et non en cache) : c'est un historique que l'API ne saura pas
    reconstruire, vider le cache ne doit pas l'effacer.
    """
    path = os.path.join(data_dir(), "movements")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{kind}-{entity_id}.jsonl")


def guard_path(kind: str, entity_id: str) -> str:
    """Emplacement de la liste des objets surveillés (durabilité/quantité).
    Équivalent du guard.dat d'origine, stocké en config (choix utilisateur)."""
    path = os.path.join(config_dir(), "guard")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{kind}-{entity_id}.json")


def detect_pack() -> str:
    """Cherche un string_client.pack à des emplacements plausibles.

    Le client Linux l'écrit dans le dossier `save/` du profil courant —
    `~/.local/share/Ryzom/<profil>/save/` — et il y a souvent plusieurs
    profils : à défaut de copie déposée à la main, on prend le plus récent.
    """
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "jeu", "ryzom", "string_client.pack"),
        os.path.join(home, "Downloads", "string_client.pack"),
        os.path.join(home, "Téléchargements", "string_client.pack"),
        os.path.join(home, ".local", "share", "Ryzom", "string_client.pack"),
        "/usr/share/ryzom/string_client.pack",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    saves = glob.glob(os.path.join(home, ".local", "share", "Ryzom", "*", "save",
                                   "string_client.pack"))
    if saves:
        return max(saves, key=os.path.getmtime)
    return ""


class Settings:
    """Réglages généraux (settings.ini)."""

    def __init__(self) -> None:
        self._path = os.path.join(config_dir(), "settings.ini")
        self._ini = configparser.ConfigParser()
        self._ini.read(self._path, encoding="utf-8")
        if not self._ini.has_section("GENERAL"):
            self._ini.add_section("GENERAL")

    @property
    def pack_file(self) -> str:
        return self._ini.get("GENERAL", "PackFile", fallback="")

    @pack_file.setter
    def pack_file(self, value: str) -> None:
        self._ini.set("GENERAL", "PackFile", value)
        self._flush()

    @property
    def language(self) -> str:
        """Langue de l'interface : '', 'fr', 'en' ou 'de' ('' = système)."""
        return self._ini.get("GENERAL", "UILanguage", fallback="")

    @language.setter
    def language(self, value: str) -> None:
        self._ini.set("GENERAL", "UILanguage", value)
        self._flush()

    @property
    def volume_threshold(self) -> int:
        """Seuil d'alerte de volume, en %. Défaut 90 (comme l'original)."""
        return self._ini.getint("GENERAL", "VolumeThreshold", fallback=90)

    @volume_threshold.setter
    def volume_threshold(self, value: int) -> None:
        self._ini.set("GENERAL", "VolumeThreshold", str(int(value)))
        self._flush()

    @property
    def sales_count(self) -> int:
        """Alerte si une vente expire dans moins de N heures (défaut 12)."""
        return self._ini.getint("GENERAL", "SalesCount", fallback=12)

    @sales_count.setter
    def sales_count(self, value: int) -> None:
        self._ini.set("GENERAL", "SalesCount", str(int(value)))
        self._flush()

    @property
    def sync_interval(self) -> int:
        """Resynchronisation automatique toutes les N minutes (0 = jamais).

        L'API de Ryzom ne rafraîchit ses données que périodiquement : inutile de
        l'interroger plus souvent qu'un quart d'heure.
        """
        return self._ini.getint("GENERAL", "SyncInterval", fallback=15)

    @sync_interval.setter
    def sync_interval(self, value: int) -> None:
        self._ini.set("GENERAL", "SyncInterval", str(max(0, int(value))))
        self._flush()

    @property
    def sync_on_start(self) -> bool:
        """Synchroniser une entité la première fois qu'on l'ouvre dans la session."""
        return self._ini.getboolean("GENERAL", "SyncOnStart", fallback=True)

    @sync_on_start.setter
    def sync_on_start(self, value: bool) -> None:
        self._ini.set("GENERAL", "SyncOnStart", "1" if value else "0")
        self._flush()

    @property
    def season_count(self) -> int:
        """Alerte si la saison change dans moins de N heures (défaut 12)."""
        return self._ini.getint("GENERAL", "SeasonCount", fallback=12)

    @season_count.setter
    def season_count(self, value: int) -> None:
        self._ini.set("GENERAL", "SeasonCount", str(int(value)))
        self._flush()

    @property
    def notifications(self) -> bool:
        """Envoyer les alertes au bureau, en plus de la cloche (défaut : oui).

        Ce sont les bulles qui s'affichent près de l'horloge à chaque
        synchronisation : avec une resynchronisation au quart d'heure et un
        coffre plein, elles reviennent quatre fois par heure et rien dans le
        bureau ne permet de les faire taire. Coupée, l'application n'envoie
        plus rien ; la cloche et sa fenêtre continuent de tout montrer.
        """
        return self._ini.getboolean("GENERAL", "Notifications", fallback=True)

    @notifications.setter
    def notifications(self, value: bool) -> None:
        self._ini.set("GENERAL", "Notifications", "1" if value else "0")
        self._flush()

    @property
    def save_folder(self) -> str:
        """Dossier « save » de Ryzom (pour la sauvegarde automatique)."""
        return self._ini.get("GENERAL", "SaveFolder", fallback="")

    @save_folder.setter
    def save_folder(self, value: str) -> None:
        self._ini.set("GENERAL", "SaveFolder", value)
        self._flush()

    @property
    def backup_auto(self) -> bool:
        return self._ini.getboolean("BACKUP", "Auto", fallback=False)

    @backup_auto.setter
    def backup_auto(self, value: bool) -> None:
        if not self._ini.has_section("BACKUP"):
            self._ini.add_section("BACKUP")
        self._ini.set("BACKUP", "Auto", "1" if value else "0")
        self._flush()

    # --- Proxy HTTP (section [PROXY]) ---
    def _proxy_get(self, key: str, fallback: str = "") -> str:
        return self._ini.get("PROXY", key, fallback=fallback)

    def _proxy_set(self, key: str, value: str) -> None:
        if not self._ini.has_section("PROXY"):
            self._ini.add_section("PROXY")
        self._ini.set("PROXY", key, value)
        self._flush()

    @property
    def proxy_enabled(self) -> bool:
        return self._ini.getboolean("PROXY", "Enabled", fallback=False)

    @proxy_enabled.setter
    def proxy_enabled(self, value: bool) -> None:
        self._proxy_set("Enabled", "1" if value else "0")

    @property
    def proxy_address(self) -> str:
        return self._proxy_get("Address")

    @proxy_address.setter
    def proxy_address(self, value: str) -> None:
        self._proxy_set("Address", value)

    @property
    def proxy_port(self) -> int:
        return self._ini.getint("PROXY", "Port", fallback=0)

    @proxy_port.setter
    def proxy_port(self, value: int) -> None:
        self._proxy_set("Port", str(int(value)))

    @property
    def proxy_username(self) -> str:
        return self._proxy_get("Username")

    @proxy_username.setter
    def proxy_username(self, value: str) -> None:
        self._proxy_set("Username", value)

    @property
    def proxy_password(self) -> str:
        return self._proxy_get("Password")

    @proxy_password.setter
    def proxy_password(self, value: str) -> None:
        self._proxy_set("Password", value)

    #: Taille de la fenêtre au premier lancement, avant qu'on en sache plus.
    FENETRE_DEFAUT = (960, 680)

    @property
    def window_size(self) -> tuple:
        """La taille de la fenêtre à la dernière fermeture.

        Les garde-fous sont dans `_lire_taille`, partagés avec la fenêtre des
        alertes : mêmes bornes, mêmes raisons.
        """
        return self._lire_taille("WindowWidth", "WindowHeight",
                                 self.FENETRE_DEFAUT)

    @window_size.setter
    def window_size(self, value: tuple) -> None:
        self._ecrire_taille("WindowWidth", "WindowHeight", value)

    #: Taille de la fenetre des alertes au premier lancement. Plus large que
    #: les 480 d'avant : un titre d'alerte porte un nom d'objet, sa qualite et
    #: ce qui cloche, et tenait mal sur une seule ligne.
    ALERTES_DEFAUT = (680, 560)

    @property
    def alerts_window_size(self) -> tuple:
        """La taille de la fenêtre des alertes à sa dernière fermeture.

        Elle s'ouvrait jusqu'ici toujours à la même taille, et il fallait
        l'élargir à chaque lancement : les noms d'objets surveillés sont longs,
        et la largeur qu'il faut dépend de ce que l'on surveille.
        """
        return self._lire_taille("AlertsWidth", "AlertsHeight",
                                 self.ALERTES_DEFAUT)

    @alerts_window_size.setter
    def alerts_window_size(self, value: tuple) -> None:
        self._ecrire_taille("AlertsWidth", "AlertsHeight", value)

    def _lire_taille(self, cle_largeur: str, cle_hauteur: str,
                     defaut: tuple) -> tuple:
        """Une taille de fenêtre relue du fichier, ou le défaut si elle ment.

        Une taille aberrante — écran débranché depuis, réglage recopié d'une
        autre machine — ramène au défaut plutôt qu'à une fenêtre de trois
        pixels de haut qu'on ne saurait plus attraper. Une valeur illisible
        aussi : ces réglages sont lus avant que la fenêtre existe, et une
        exception ici empêcherait l'application de démarrer du tout.
        """
        try:
            largeur = self._ini.getint("GENERAL", cle_largeur,
                                       fallback=defaut[0])
            hauteur = self._ini.getint("GENERAL", cle_hauteur,
                                       fallback=defaut[1])
        except ValueError:
            return defaut
        if not (360 <= largeur <= 10000 and 300 <= hauteur <= 10000):
            return defaut
        return (largeur, hauteur)

    #: Tri de la grille d'items au premier lancement : « Type », deuxieme
    #: entree du menu. L'ordre d'origine, lui, est celui que l'API renvoie --
    #: il ne veut rien dire pour personne, la ou un coffre range par famille
    #: se lit d'un coup d'oeil.
    TRI_DEFAUT = (1, False)

    @property
    def sort_order(self) -> tuple:
        """Le tri de la grille d'items : (rang dans le menu, décroissant ?).

        Un rang que le menu ne connaît plus — entrée retirée depuis, fichier
        recopié d'une version ultérieure — n'est pas rattrapé ici : seule la
        fenêtre sait combien d'entrées son menu compte, et c'est elle qui
        retombe alors sur le défaut.
        """
        try:
            rang = self._ini.getint("GENERAL", "SortIndex",
                                    fallback=self.TRI_DEFAUT[0])
            descendant = self._ini.getboolean("GENERAL", "SortDescending",
                                              fallback=self.TRI_DEFAUT[1])
        except ValueError:
            return self.TRI_DEFAUT
        if rang < 0:
            return self.TRI_DEFAUT
        return (rang, descendant)

    @sort_order.setter
    def sort_order(self, value: tuple) -> None:
        rang, descendant = value
        self._ini.set("GENERAL", "SortIndex", str(int(rang)))
        self._ini.set("GENERAL", "SortDescending", "1" if descendant else "0")
        self._flush()

    def _ecrire_taille(self, cle_largeur: str, cle_hauteur: str,
                       valeur: tuple) -> None:
        largeur, hauteur = valeur
        self._ini.set("GENERAL", cle_largeur, str(int(largeur)))
        self._ini.set("GENERAL", cle_hauteur, str(int(hauteur)))
        self._flush()

    @property
    def window_maximized(self) -> bool:
        """Agrandie à la dernière fermeture ? On la rouvre comme on l'a laissée."""
        try:
            return self._ini.getboolean("GENERAL", "WindowMaximized",
                                        fallback=False)
        except ValueError:
            return False

    @window_maximized.setter
    def window_maximized(self, value: bool) -> None:
        self._ini.set("GENERAL", "WindowMaximized", "1" if value else "0")
        self._flush()

    def _flush(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            self._ini.write(fh)


class EntityStore:
    """Liste persistante d'entités (personnages ou guildes) dans un .ini donné."""

    def __init__(self, filename: str) -> None:
        self._path = os.path.join(config_dir(), filename)
        self._seed_from_defaults(filename)
        self._ini = configparser.ConfigParser()
        self._ini.read(self._path, encoding="utf-8")

    def _seed_from_defaults(self, filename: str) -> None:
        """Installe les entités livrées, à la toute première ouverture.

        Ne s'applique que si l'utilisateur n'a pas encore de fichier : dès qu'il
        en a un, même vide, ses choix priment et rien n'est réécrit. Retirer une
        entité pré-configurée la retire donc pour de bon.
        """
        if os.path.exists(self._path):
            return
        template = os.path.join(_DEFAULTS_DIR, filename)
        if not os.path.isfile(template):
            return
        try:
            with open(template, encoding="utf-8") as source:
                content = source.read()
            with open(self._path, "w", encoding="utf-8") as target:
                target.write(content)
        except OSError:
            pass          # une configuration pré-remplie n'est qu'un confort

    def entries(self) -> list[dict]:
        """Renvoie [{id, key, name, server, guild}] trié par nom."""
        out = []
        for section in self._ini.sections():
            out.append({
                "id": section,
                "key": self._ini.get(section, "Key", fallback=""),
                "name": self._ini.get(section, "Name", fallback=section),
                "server": self._ini.get(section, "Server", fallback=""),
                "guild": self._ini.get(section, "Guild", fallback=""),
            })
        out.sort(key=lambda e: e["name"].lower())
        return out

    def save(self, entity_id: str, key: str, name: str,
             server: str = "", guild: str = "") -> None:
        if not self._ini.has_section(entity_id):
            self._ini.add_section(entity_id)
        self._ini.set(entity_id, "Key", key)
        self._ini.set(entity_id, "Name", name)
        self._ini.set(entity_id, "Server", server)
        self._ini.set(entity_id, "Guild", guild)
        self._flush()

    def remove(self, entity_id: str) -> None:
        if self._ini.has_section(entity_id):
            self._ini.remove_section(entity_id)
            self._flush()

    def _flush(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            self._ini.write(fh)
