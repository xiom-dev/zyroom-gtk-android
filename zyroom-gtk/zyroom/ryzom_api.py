"""Client de l'API web Ryzom + parsing des inventaires (personnages ET guildes).

Portage de RyzomApi.pas. Le réseau utilise urllib (bibliothèque standard) pour
n'avoir aucune dépendance hors GTK : idéal pour la distribution et les vieilles
machines. Les appels sont synchrones ; la concurrence (threads) est gérée par
les appelants (voir icons.py, window.py).
"""
from __future__ import annotations

import os
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element, fromstring

from . import volume as volume_mod
from .i18n import _
from .models import ItemInfo, parse_item

API_BASE_URL = "https://api.ryzom.com"

# Modules requis sur la clé API (cf. RyzomApi.pas)
REQUIRED_MODULES_CHAR = ("C01", "C04", "C05", "C06", "A01", "A03")
REQUIRED_MODULES_GUILD = ("G01", "G02", "G03")

KIND_CHARACTER = "character"
KIND_GUILD = "guild"

# Les items d'une guilde sont dans un seul <room> mais répartis en coffres
# par tranche de slot (cf. _CHEST_SEGMENT_SIZE du Delphi) : coffre i = slots
# [i*500, i*500+499]. Chaque <chest> porte le nom et la capacité (bulkmax).
_CHEST_SEGMENT_SIZE = 500

# Coffres dont l'application ne montre pas le contenu, par un fragment de leur
# nom. Le coffre reste dans la liste, avec son nom et sa capacité, mais il
# apparaît **vide** : le faire disparaître amenait les joueurs à demander
# pourquoi il manquait un coffre.
#
# C'est un masque d'affichage : le contenu voyage toujours dans le flux de
# l'API et dort dans le cache. Qui a la clé de la guilde peut l'y lire.
#
# La comparaison se fait sur le nom normalisé et par inclusion, car ces noms
# sont saisis à la main par les joueurs : article en tête, espace en fin, casse
# et accents variables, et l'API les tronque à 31 caractères. Une égalité
# stricte laissait passer « Le petit coffre de Nizy ».
_HIDDEN_CHESTS = ("petit coffre de nizy",)

# Le masque se lève si ZYROOM_SHOW_ALL_CHESTS=1. C'est ce que positionne le
# manifeste de la build de développement (packaging/…dev.yml) : la build
# distribuée à la guilde masque, celle du mainteneur montre tout. La variable
# est relue à chaque appel pour rester testable.
_ENV_SHOW_ALL = "ZYROOM_SHOW_ALL_CHESTS"

_USER_AGENT = "zyroom-gtk/0.1 (+https://github.com/misugi/zyroom)"
_TIMEOUT = 30


class ApiError(Exception):
    """Erreur renvoyée par l'API (dans le XML) ou lors de l'appel réseau."""


@dataclass
class Inventory:
    """Un contenant d'items (sac, salle, coffre, inventaire d'une monture...)."""
    key: str                       # identifiant technique, ex "bag", "chest1"
    label: str                     # libellé affiché, ex "Sac", "Coffre 1"
    items: list[ItemInfo] = field(default_factory=list)
    capacity: int = 0              # volume max (0 = inconnu, pas de jauge)
    # Contenant montré vide (cf. _HIDDEN_CHESTS). Il est exclu des instantanés,
    # sans quoi le journal des mouvements trahirait ce qu'on masque : passer
    # d'un état où le coffre était garni à un état vide produit un retrait par
    # item, nommément.
    masked: bool = False

    @property
    def total_volume(self) -> float:
        return sum(it.volume for it in self.items)


@dataclass
class Entity:
    """Métadonnées + inventaires d'un personnage ou d'une guilde."""
    kind: str = KIND_CHARACTER
    entity_id: str = ""
    name: str = ""
    shard: str = ""
    guild: str = ""                # nom de guilde (pour un personnage)
    modules: str = ""
    money: str = ""                # dappers (personnage ou guilde)
    motd: str = ""                 # message du jour (pour une guilde)
    icon: str = ""                 # icône (pour une guilde)
    portrait_url: str = ""         # URL du portrait (rendu 3D perso / icône guilde)
    inventories: list[Inventory] = field(default_factory=list)
    skills: list = field(default_factory=list)          # arbre des compétences
    skill_points: dict = field(default_factory=dict)    # points par branche

    @property
    def item_count(self) -> int:
        return sum(len(inv.items) for inv in self.inventories)


# Opener configuré pour le proxy (None = accès direct, urllib respecte alors
# aussi les variables d'environnement http_proxy/https_proxy).
_opener = None


def configure_proxy(enabled: bool, address: str, port: int,
                    username: str = "", password: str = "") -> None:
    """Configure (ou désactive) le proxy HTTP pour tous les appels réseau."""
    global _opener
    if not enabled or not address:
        _opener = None
        return
    host = f"{address}:{port}" if port else address
    if username:
        proxy_url = f"http://{username}:{password}@{host}"
    else:
        proxy_url = f"http://{host}"
    handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    _opener = urllib.request.build_opener(handler)


def _http_get(url: str) -> bytes:
    """GET simple renvoyant le corps en octets. Utilise le proxy si configuré,
    sinon un accès direct (qui respecte http_proxy/https_proxy)."""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        opener = _opener
        if opener is not None:
            with opener.open(req, timeout=_TIMEOUT) as resp:
                return resp.read()
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(f"HTTP {exc.code} : {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Réseau : {exc.reason}") from exc


def _is_hidden_chest(name: str) -> bool:
    """Vrai si ce nom de coffre figure dans le masque d'affichage."""
    if os.environ.get(_ENV_SHOW_ALL) == "1":
        return False
    decomposed = unicodedata.normalize("NFKD", name)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    normalized = " ".join(plain.lower().split())
    return any(fragment in normalized for fragment in _HIDDEN_CHESTS)


def check_modules(modules: str, required) -> list[str]:
    """Renvoie la liste des modules requis manquants (vide si tout est présent)."""
    present = set(modules.split(":")) if modules else set()
    return [m for m in required if m not in present]


def _check_xml_error(root: Element) -> None:
    """Lève ApiError si le flux contient un noeud <error>."""
    err = root.find(".//error")
    if err is not None:
        code = err.get("code", "?")
        raise ApiError(f"Erreur API {code} : {(err.text or '').strip()}")


def item_icon_url(item: ItemInfo) -> str:
    """URL de l'icône d'un item (item_icon.php), fidèle à ApiItemIcon.

    - couleur NONE (8) -> beige (1) côté API
    - q, s omis si <= 0 ; sap=0 si l'item a une charge de sève, sinon omis
    - destroyed / locked ajoutés si vrais
    """
    from .models import ItemColor
    color = ItemColor.BEIGE if item.color == ItemColor.NONE else item.color
    opts = f"?sheetid={item.sheet}&c={int(color)}"
    if item.quality > 0:
        opts += f"&q={item.quality}"
    if item.stack > 0:
        opts += f"&s={item.stack}"
    if item.sap:                       # IfThen(ItemSap, 0, -1) ; ajouté seulement si >= 0
        opts += "&sap=0"
    if item.destroyed:
        opts += "&destroyed=1"
    if item.locked:
        opts += "&locked=1"
    return f"{API_BASE_URL}/item_icon.php{opts}"


def fetch_item_icon(item: ItemInfo) -> bytes:
    """Télécharge le PNG de l'icône d'un item."""
    return _http_get(item_icon_url(item))


def fetch_url(url: str) -> bytes:
    """Télécharge le contenu d'une URL (portraits, icônes de guilde…)."""
    return _http_get(url)


def _character_portrait_url(char_node: Element) -> str:
    """Construit l'URL du rendu 3D du personnage (Ballistic Mystix)."""
    body = char_node.find("body")
    if body is None:
        return ""
    race = (char_node.findtext("race", default="") or "")[:2]
    gender = char_node.findtext("gender", default="")
    hairtype = body.findtext("hairtype", default="0")
    haircolor = body.findtext("haircolor", default="0")
    tattoo = body.findtext("tattoo", default="0")
    eyes = body.findtext("eyescolor", default="0")
    gab = body.find("gabarit")
    gabarit = (",".join(gab.get(a, "0") for a in
               ("height", "torso", "arms", "legs", "breast"))
               if gab is not None else "")
    mor = body.find("morph")
    morph = (",".join(mor.get(f"target{i}", "0") for i in range(1, 9))
             if mor is not None else "")
    equip = char_node.find("equipment")
    chest_el = equip.find("chest") if equip is not None else None
    chest = (chest_el.text or "") if chest_el is not None else ""
    chest_color = chest_el.get("color", "0") if chest_el is not None else "0"
    return (f"http://api.bmsite.net/char/render/3d/180?race={race}&gender={gender}"
            f"&hair={hairtype}/{haircolor}&tattoo={tattoo}&eyes={eyes}"
            f"&gabarit={gabarit}&morph={morph}&chest={chest}/{chest_color}")


#: Les quatre branches de l'API, sous le code de leur racine dans le pack.
_BRANCHES = {"fight": "sf", "magic": "sm", "craft": "sc", "harvest": "sh"}


def _parse_skills(node: Element) -> list:
    """L'arbre des compétences : une balise par compétence, nommée par son code.

    Le bloc peut manquer — c'est un module de l'API, et toutes les clés ne
    l'accordent pas. L'écran des compétences s'efface alors de lui-même."""
    from .skills import Skill, parse_level
    block = node.find("skills")
    if block is None:
        return []
    out = []
    for child in block:
        level, progress = parse_level((child.text or "").strip())
        out.append(Skill(code=child.tag, level=level, progress=progress))
    return out


def _parse_skill_points(node: Element) -> dict:
    """Points de compétence par branche : disponibles, et déjà dépensés."""
    block = node.find("skillpoints")
    if block is None:
        return {}
    out = {}
    for child in block:
        code = _BRANCHES.get(child.tag)
        if not code:
            continue
        try:
            available = int((child.text or "0").strip())
        except ValueError:
            available = 0
        try:
            spent = int(child.get("spent", "0"))
        except ValueError:
            spent = 0
        out[code] = (available, spent)
    return out


def _build_items(container: Element, resolve_sheet, tag: str = "item") -> list[ItemInfo]:
    """Parse les items d'un conteneur, détermine leur type et leur volume."""
    items = []
    for node in container.findall(tag):
        it = parse_item(node, resolve_sheet)
        volume_mod.classify(it)
        items.append(it)
    return items


# ---------------------------------------------------------------- Personnage
def fetch_character_xml(api_key: str) -> bytes:
    """Appelle character.php et renvoie le XML brut (octets)."""
    return _http_get(f"{API_BASE_URL}/character.php?apikey={api_key}")


def parse_character(xml_bytes: bytes, resolve_sheet=None) -> Entity:
    """Analyse le flux character.php en une Entity avec ses inventaires."""
    root = fromstring(xml_bytes)
    _check_xml_error(root)

    node = root.find("./character")
    if node is None:
        raise ApiError("Flux XML invalide : noeud <character> absent")

    ent = Entity(kind=KIND_CHARACTER)
    ent.entity_id = node.findtext("id", default="")
    ent.name = node.findtext("name", default="")
    ent.shard = node.findtext("shard", default="")
    ent.guild = node.findtext("guild/name", default="")
    ent.modules = node.get("modules", "")
    ent.money = node.findtext("money", default="")
    ent.portrait_url = _character_portrait_url(node)
    ent.skills = _parse_skills(node)
    ent.skill_points = _parse_skill_points(node)

    bag = node.find("bag")
    if bag is not None:
        ent.inventories.append(Inventory("bag", _("Sac"), _build_items(bag, resolve_sheet),
                                         volume_mod.CAP_BAG))
    room = node.find("room")
    if room is not None:
        ent.inventories.append(Inventory("room", _("Appartement"), _build_items(room, resolve_sheet),
                                         volume_mod.CAP_ROOM))

    pets = node.find("pets")
    if pets is not None:
        _labels = {"mektoub": _("Mektoub"), "mount": _("Monture"), "zig": _("Zig")}
        counters = {"mektoub": 0, "mount": 0, "zig": 0}
        for animal in pets.findall("animal"):
            index = animal.get("index", "?")
            inv_node = animal.find("inventory")
            items = _build_items(inv_node, resolve_sheet) if inv_node is not None else []
            creature = animal.findtext("sheet", default="")
            capacity, kind = volume_mod.animal_capacity(creature)
            counters[kind] += 1
            label = f"{_labels[kind]} {counters[kind]}"
            ent.inventories.append(Inventory(f"animal{index}", label, items, capacity))

    # Ventes (items en vente à l'hôtel des ventes)
    shop = node.find("shop")
    if shop is not None:
        sales = _build_items(shop, resolve_sheet, tag="shopitem")
        if sales:
            ent.inventories.append(Inventory("shop", _("Ventes"), sales))

    return ent


# --------------------------------------------------------------------- Guilde
def fetch_guild_xml(api_key: str) -> bytes:
    """Appelle guild.php et renvoie le XML brut (octets)."""
    return _http_get(f"{API_BASE_URL}/guild.php?apikey={api_key}")


def parse_guild(xml_bytes: bytes, resolve_sheet=None) -> Entity:
    """Analyse le flux guild.php en une Entity (salle + coffres)."""
    root = fromstring(xml_bytes)
    _check_xml_error(root)

    node = root.find("./guild")
    if node is None:
        raise ApiError("Flux XML invalide : noeud <guild> absent")

    ent = Entity(kind=KIND_GUILD)
    ent.entity_id = node.findtext("gid", default="")
    ent.name = node.findtext("name", default="")
    ent.shard = node.findtext("shard", default="")
    ent.modules = node.get("modules", "")
    ent.money = node.findtext("money", default="")
    ent.motd = node.findtext("motd", default="")
    ent.icon = node.findtext("icon", default="")
    if ent.icon:
        ent.portrait_url = f"{API_BASE_URL}/guild_icon.php?icon={ent.icon}&size=b"

    # Métadonnées des coffres (nom + capacité bulkmax)
    chest_meta = []
    chests = node.find("chests")
    if chests is not None:
        for c in chests.findall("chest"):
            try:
                bulkmax = int(c.findtext("bulkmax", default="0") or 0)
            except ValueError:
                bulkmax = 0
            chest_meta.append((c.findtext("name", default=""), bulkmax))

    # Items de la salle répartis en coffres par tranche de slot de 500
    room = node.find("room")
    segments: dict[int, list] = {}
    if room is not None:
        for it in _build_items(room, resolve_sheet):
            segments.setdefault(it.slot // _CHEST_SEGMENT_SIZE, []).append(it)

    n_chests = max(len(chest_meta), (max(segments) + 1) if segments else 0)
    for i in range(n_chests):
        items = segments.get(i, [])
        name, bulkmax = chest_meta[i] if i < len(chest_meta) else ("", 0)
        if not items and bulkmax <= 0:
            continue  # coffre inexistant
        # Le coffre masqué garde sa place et son nom, mais se présente vide.
        masked = _is_hidden_chest(name)
        if masked:
            items = []
        label = f"{_('Coffre')} {i + 1}"
        if name and name != ent.name:
            label += f" — {name}"
        ent.inventories.append(
            Inventory(f"chest{i + 1}", label, items, bulkmax, masked=masked))

    return ent


# ------------------------------------------------------------- Saison serveur
_SEASONS = ("Été", "Automne", "Hiver", "Printemps")  # index 0..3 (cf. Delphi)


def fetch_time_xml() -> bytes:
    """Appelle time.php (format xml) et renvoie le flux brut."""
    return _http_get(f"{API_BASE_URL}/time.php?format={_FORMAT_XML}")


def parse_time(xml_bytes: bytes) -> dict:
    """Analyse le flux time.php : saison courante et temps avant changement.

    minutes avant la prochaine saison = ((89 - jour) * 24 + (23 - heure)) * 3
    (une saison = 90 jours de 24 h, 1 h de jeu = 3 min réelles)."""
    root = fromstring(xml_bytes)

    def _int(path, default=0):
        txt = root.findtext(path, default="")
        try:
            return int(txt)
        except (ValueError, TypeError):
            return default

    season = _int("season", -1)
    day = _int("day_of_season")
    hour = _int("time_of_day")
    minutes_to_next = ((89 - day) * 24 + (23 - hour)) * 3
    return {
        "season_index": season,
        "season_name": _SEASONS[season] if 0 <= season < 4 else "-",
        "next_season_name": _SEASONS[(season + 1) % 4] if 0 <= season < 4 else "-",
        "minutes_to_next": minutes_to_next,
    }


_FORMAT_XML = "xml"
