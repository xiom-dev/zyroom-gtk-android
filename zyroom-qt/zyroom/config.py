"""Chemins de l'application, réglages et persistance des entités.

**Le seul module du noyau qui connaisse le système d'exploitation.** Tout le
reste — l'API, les modèles, les volumes, les mouvements — ne manipule que des
chemins qu'on lui donne. C'est donc ici, et ici seulement, que Linux et Windows
se séparent.

Sous Linux, conventions XDG (standard Debian) :
  - config  : ~/.config/zyroom-qt/  (characters.ini, guilds.ini, settings.ini)
  - cache   : ~/.cache/zyroom-qt/   (icônes, flux XML, noms)
  - données : ~/.local/share/zyroom-qt/  (mouvements, registre, sauvegardes)

Sous Windows, conventions du système :
  - config  : %APPDATA%\\zyroom-qt\\
  - cache   : %LOCALAPPDATA%\\zyroom-qt\\cache\\
  - données : %LOCALAPPDATA%\\zyroom-qt\\

Les fichiers .ini reprennent l'esprit des character.ini / guild.ini d'origine
(une section [id] par entité) mais stockent la clé API **en clair** : chaque
joueur y met sa propre clé, il n'y a donc rien de sensible à chiffrer.
"""
from __future__ import annotations

import configparser
import glob
import hashlib
import os

APP_ID = "zyroom-qt"

#: L'identifiant du portage GTK, dont on reprend la configuration au premier
#: lancement (cf. `_reprendre_gtk`). Les deux applications s'installent cote a
#: cote : elles ne partagent pas leurs dossiers, seulement ce point de depart.
APP_ID_GTK = "zyroom-gtk"

WINDOWS = os.name == "nt"

# Repertoire des donnees embarquees (sheetid.csv)
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SHEETID_CSV = os.path.join(_DATA_DIR, "sheetid.csv")
CATEGORY_CSV = os.path.join(_DATA_DIR, "category.csv")

# Entites pre-configurees, si le paquet en livre. Le mecanisme reste en place
# mais **rien n'est livre** : y mettre la guilde revenait a donner sa cle d'API,
# en clair, a quiconque installe le paquet — et donc a qui saurait l'en extraire.
# La cle se transmet desormais de la main a la main, sur le Discord de la guilde.
_DEFAULTS_DIR = os.path.join(_DATA_DIR, "default")


def _base_windows(variable: str, repli: str) -> str:
    """Un des dossiers d'application de Windows, avec un repli raisonnable.

    Les deux variables existent depuis toujours, mais un environnement
    dépouillé — un service, un Python lancé de travers — peut ne pas les
    porter : on retombe alors sous le profil de l'utilisateur plutôt que
    d'échouer.
    """
    base = os.environ.get(variable)
    if not base:
        base = os.path.join(os.path.expanduser("~"), "AppData", repli)
    return base


def _dossier(env: str, sous_dossier: str, sous_windows: str) -> str:
    """Le dossier de l'application pour un usage donné, créé au besoin.

    Sous Linux on suit XDG : la variable d'environnement si elle est posée,
    sinon le chemin conventionnel sous le répertoire personnel.

    Sous Windows, XDG n'existe pas : la configuration va dans l'itinérant
    (%APPDATA%, qui suit l'utilisateur d'une machine à l'autre dans un
    domaine), le cache et les données dans le local (%LOCALAPPDATA%, qu'on ne
    recopie pas sur le réseau — un cache d'icônes n'a rien à y faire).
    """
    if WINDOWS:
        if sous_windows == "roaming":
            path = os.path.join(_base_windows("APPDATA", "Roaming"), APP_ID)
        elif sous_windows == "local/cache":
            path = os.path.join(_base_windows("LOCALAPPDATA", "Local"),
                                APP_ID, "cache")
        else:
            path = os.path.join(_base_windows("LOCALAPPDATA", "Local"), APP_ID)
    else:
        base = (os.environ.get(env)
                or os.path.join(os.path.expanduser("~"), sous_dossier))
        path = os.path.join(base, APP_ID)
    os.makedirs(path, exist_ok=True)
    return path


def config_dir() -> str:
    path = _dossier("XDG_CONFIG_HOME", ".config", "roaming")
    _reprendre_gtk(path)
    return path


def cache_dir() -> str:
    path = _dossier("XDG_CACHE_HOME", ".cache", "local/cache")
    # Les instantanes d'inventaire : sans eux, la premiere synchro ne verrait
    # aucun mouvement (elle n'aurait rien a comparer) et le journal repartirait
    # de zero. Cf. `_reprendre_dossier_gtk`.
    _reprendre_dossier_gtk("XDG_CACHE_HOME", ".cache", path, "watch")
    return path


def data_dir() -> str:
    path = _dossier("XDG_DATA_HOME", ".local/share", "local")
    # L'historique des mouvements. C'est la seule donnee de l'application que
    # l'API ne sait pas reconstruire : la perdre en changeant de portage
    # serait perdre des mois de journal.
    _reprendre_dossier_gtk("XDG_DATA_HOME", ".local/share", path, "movements")
    # Le registre du personnel ne vit pas dans un sous-dossier : ses fichiers
    # sont poses ici meme, un jeu par guilde. Sans cette reprise-la,
    # l'effectif repartait de zero alors que le journal, lui, etait complet.
    _reprendre_fichiers_gtk("XDG_DATA_HOME", ".local/share", path, "roster-")
    return path


#: Vrai une fois la reprise tentee : elle ne regarde le disque qu'une fois par
#: execution, alors que `config_dir()` est appelee a tout bout de champ.
_reprise_faite = False


def _reprendre_gtk(path: str) -> None:
    """Reprend la configuration du portage GTK, au tout premier lancement.

    Les clés d'API se saisissent à la main, une par personnage et une par
    guilde. Demander à quelqu'un qui a déjà ZyRoom-GTK de les ressaisir pour
    retrouver exactement les mêmes inventaires serait une brimade : on recopie
    donc ses fichiers de configuration s'il en a.

    **Une copie, pas un partage.** Les deux applications gardent chacune la
    sienne ensuite : régler l'une ne dérègle pas l'autre, et retirer un
    personnage ici ne le retire pas là-bas. Et la reprise ne se fait qu'une
    fois — dès que ce dossier contient quelque chose, il fait foi.
    """
    global _reprise_faite
    if _reprise_faite:
        return
    _reprise_faite = True
    if WINDOWS:
        return                    # le portage GTK ne tourne pas sous Windows
    if any(os.scandir(path)):
        return                    # deja configure : on ne touche a rien
    base = (os.environ.get("XDG_CONFIG_HOME")
            or os.path.join(os.path.expanduser("~"), ".config"))
    source = os.path.join(base, APP_ID_GTK)
    if not os.path.isdir(source):
        return
    import shutil
    for nom in ("characters.ini", "guilds.ini", "settings.ini"):
        origine = os.path.join(source, nom)
        if os.path.isfile(origine):
            try:
                shutil.copy2(origine, os.path.join(path, nom))
            except OSError:
                pass              # une reprise ratee n'empeche pas de demarrer


#: Les dossiers deja repris du portage GTK, pour ne regarder le disque qu'une
#: fois par execution : `cache_dir()` et `data_dir()` sont appelees a tout
#: bout de champ.
_dossiers_repris: set = set()


def _reprendre_dossier_gtk(env: str, defaut: str, cible: str,
                           sous_dossier: str) -> None:
    """Recopie un sous-dossier de données du portage GTK, une fois.

    Même esprit que `_reprendre_gtk` pour la configuration : au tout premier
    lancement, et seulement si l'on n'a rien encore, on part de ce que
    ZyRoom-GTK avait. Ensuite les deux applications divergent — vider le
    journal ici ne le vide pas là-bas.
    """
    if sous_dossier in _dossiers_repris:
        return
    _dossiers_repris.add(sous_dossier)
    if WINDOWS:
        return                    # le portage GTK ne tourne pas sous Windows
    destination = os.path.join(cible, sous_dossier)
    if os.path.isdir(destination) and any(os.scandir(destination)):
        return                    # deja quelque chose ici : il fait foi
    import shutil
    for base_gtk in _sources_gtk(env, defaut):
        source = os.path.join(base_gtk, sous_dossier)
        if not os.path.isdir(source):
            continue
        try:
            os.makedirs(destination, exist_ok=True)
            for nom in os.listdir(source):
                origine = os.path.join(source, nom)
                cible_f = os.path.join(destination, nom)
                if os.path.isfile(origine) and not os.path.exists(cible_f):
                    shutil.copy2(origine, cible_f)
        except OSError:
            pass                  # une reprise ratee n'empeche pas de demarrer


def backup_dir() -> str:
    path = os.path.join(data_dir(), "backup")
    os.makedirs(path, exist_ok=True)
    return path


def _racines_ryzom() -> list[str]:
    """Les endroits où le client Ryzom s'installe, selon le système.

    Sous Windows, le client écrit ses profils dans l'itinérant et s'installe
    soit à la main dans « Program Files », soit par Steam. Les deux variantes
    de « Program Files » sont citées : un client 32 bits sur un Windows 64
    bits atterrit dans celle qui porte « (x86) ».
    """
    home = os.path.expanduser("~")
    if WINDOWS:
        programmes = [os.environ.get("ProgramFiles(x86)"),
                      os.environ.get("ProgramFiles"),
                      r"C:\Program Files (x86)", r"C:\Program Files"]
        racines = [os.path.join(_base_windows("APPDATA", "Roaming"), "Ryzom")]
        for base in programmes:
            if not base:
                continue
            racines.append(os.path.join(base, "Ryzom"))
            racines.append(os.path.join(base, "Steam", "steamapps", "common",
                                        "Ryzom"))
        racines.append(os.path.join(home, "Ryzom"))
        return racines
    return [
        os.path.join(home, ".local", "share", "Ryzom"),
        os.path.join(home, ".ryzom"),
        os.path.join(home, "Ryzom"),
        os.path.join(home, "jeu", "ryzom"),
    ]


def detect_save_folder() -> str:
    """Cherche le dossier « save » de Ryzom à des emplacements plausibles.

    **Les profils comptent aussi.** Le client range son `save` sous le profil
    courant — `~/.local/share/Ryzom/<profil>/save/` — et il y a souvent
    plusieurs profils. ZyRoom-GTK ne regardait que `<racine>/save`, et ne
    trouvait donc rien sur une installation ordinaire : la sauvegarde restait
    à configurer à la main sans que rien ne dise pourquoi. À défaut d'un
    dossier à la racine, on prend le profil le plus récemment écrit — le même
    choix que `detect_pack`, juste au-dessous.
    """
    for racine in _racines_ryzom():
        path = os.path.join(racine, "save")
        if os.path.isdir(path):
            return path
    for racine in _racines_ryzom():
        profils = glob.glob(os.path.join(racine, "*", "save"))
        profils = [p for p in profils if os.path.isdir(p)]
        if profils:
            return max(profils, key=os.path.getmtime)
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
    candidates = [os.path.join(home, "Downloads", "string_client.pack"),
                  os.path.join(home, "Téléchargements", "string_client.pack")]
    for racine in _racines_ryzom():
        candidates.append(os.path.join(racine, "string_client.pack"))
        candidates.append(os.path.join(racine, "data", "string_client.pack"))
    if not WINDOWS:
        candidates.append("/usr/share/ryzom/string_client.pack")
    for path in candidates:
        if os.path.isfile(path):
            return path

    # A defaut, le fichier d'un profil : il y en a souvent plusieurs, on
    # prend le plus recent.
    for racine in _racines_ryzom():
        saves = glob.glob(os.path.join(racine, "*", "save",
                                       "string_client.pack"))
        if saves:
            return max(saves, key=os.path.getmtime)
    return ""


def _sources_gtk(env: str, defaut: str) -> list:
    """Où ZyRoom-GTK range ses données, dans l'ordre où on les préfère.

    **Deux endroits, pas un.** Installé par le paquet ou lancé depuis les
    sources, il écrit sous le répertoire personnel ; livré en Flatpak — c'est
    le cas de la variante du mainteneur —, il écrit dans le bac à sable, sous
    `~/.var/app/<identifiant>/data/`. Ne regarder que le premier, c'est
    reprendre un registre de sept mouvements quand celui qui compte en a
    cinquante : vérifié, et c'est exactement ce qui est arrivé.
    """
    import glob
    base = (os.environ.get(env)
            or os.path.join(os.path.expanduser("~"), defaut))
    trouves = [os.path.join(base, APP_ID_GTK)]
    trouves += sorted(glob.glob(os.path.join(
        os.path.expanduser("~"), ".var", "app", "net.ryzom.zyroomgtk*",
        "data", APP_ID_GTK)))
    return [d for d in trouves if os.path.isdir(d)]


def _reprendre_fichiers_gtk(env: str, defaut: str, cible: str,
                            prefixe: str) -> None:
    """Recopie les fichiers du portage GTK dont le nom commence par `prefixe`.

    Comme `_reprendre_dossier_gtk`, mais pour ce qui est posé à plat plutôt
    que rangé dans un sous-dossier. Un fichier déjà présent ici n'est jamais
    écrasé : ce qu'on a écrit soi-même prime toujours sur ce qu'on reprend.
    """
    if prefixe in _dossiers_repris:
        return
    _dossiers_repris.add(prefixe)
    if WINDOWS:
        return
    import shutil
    for source in _sources_gtk(env, defaut):
        try:
            for nom in os.listdir(source):
                if not nom.startswith(prefixe):
                    continue
                arrivee = os.path.join(cible, nom)
                if os.path.exists(arrivee):
                    continue
                shutil.copy2(os.path.join(source, nom), arrivee)
        except OSError:
            pass


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

    #: Le corps du texte, en points. Zero laisse celui du bureau.
    #:
    #: Une taille et non un ecart : "+5" ne dit rien a personne, alors qu'un
    #: nombre de points se lit comme dans un traitement de texte, et se
    #: retrouve d'une machine a l'autre. La police du bureau tourne autour de
    #: neuf ou dix points ; cette interface serre beaucoup d'information --
    #: des colonnes de noms, des tableaux de mouvements -- et douze ou
    #: quatorze s'y lisent bien mieux.
    @property
    def font_size(self) -> int:
        taille = self._ini.getint("GENERAL", "FontSize", fallback=0)
        if taille:
            return taille
        # Reprise du reglage precedent, qui s'exprimait en points ajoutes :
        # sans cela, celui qui avait demande du texte plus gros le verrait
        # rapetisser sans comprendre pourquoi.
        ancien = self._ini.getint("GENERAL", "FontOffset", fallback=0)
        return 10 + ancien if ancien else 0

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._ini.set("GENERAL", "FontSize", str(int(value)))
        self._flush()

    #: Le cote des icones de la grille, en pixels. Quarante-huit est la
    #: taille que l'API rend et celle de la version GTK ; au-dela, l'image est
    #: agrandie et se ramollit, mais une grille de deux cents objets se
    #: parcourt mieux quand chacun se reconnait sans se pencher.
    @property
    def icon_size(self) -> int:
        return max(24, min(128, self._ini.getint("GENERAL", "IconSize",
                                                 fallback=48)))

    @icon_size.setter
    def icon_size(self, value: int) -> None:
        self._ini.set("GENERAL", "IconSize", str(int(value)))
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

    #: Taille de la fenetre au premier lancement, avant qu'on en sache plus.
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

    #: Tri de la grille d'items au premier lancement : "Type", deuxieme
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
