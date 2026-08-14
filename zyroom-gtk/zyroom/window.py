"""Fenêtre principale de ZyRoom GTK.

Personnages ET guildes, ajout via clé API, sélection d'inventaire, grille d'items
avec icônes (téléchargées et mises en cache), noms lisibles (string_client.pack)
et barre de recherche/filtres. Les appels réseau se font dans des threads pour
ne pas figer l'interface.
"""
from __future__ import annotations

import os
import threading
import unicodedata
from datetime import datetime, timedelta

from gi.repository import Gdk, GdkPixbuf, GLib, Gio, Gtk, Pango

from . import (alerts, armory, backup, carte, chatlog, detail, gisements, i18n,
               meteo, movements, outposts, polices, roster, ryzom_api, sorting)
from . import skills as skills_mod
from .updater import Updater, Veilleur
from .categorydb import CategoryDb
from .i18n import _
from .config import (CATEGORY_CSV, SHEETID_CSV, EntityStore, data_dir, Settings, detect_pack,
                     detect_save_folder, entity_xml_path, format_last_sync,
                     guard_path, last_sync, movements_path, names_cache_path,
                     portrait_path, snapshot_path)
from .icons import IconLoader
from .options import OptionsWindow
from .namedb import NameDb
from .models import (CLASS_NAMES, ECOSYSTEM_NAMES, EQUIP_NAMES, TYPE_NAMES,
                     ItemInfo, ItemType)
from .ryzom_api import (KIND_CHARACTER, KIND_GUILD, ApiError, Entity)
from .sheetdb import SheetDb
from .watch import WatchStore, watch_kind, KIND_DURABILITY

ICON_SIZE = 48

#: Intervalle de vérification des mises à jour de l'application, en secondes.
#: Un quart d'heure, comme la resynchronisation : c'est la cadence à laquelle
#: on regarde déjà si quelque chose a changé ailleurs.
MAJ_INTERVALLE = 15 * 60

# Nom affiché, tenu identique à celui des fichiers .desktop des deux variantes.
# Il ne paraît plus dans la barre de titre, occupée par la bascule d'onglets,
# mais bien dans la liste des fenêtres et l'alternateur de tâches.
APP_NAME = ("ZyRoom-GTK-dev-0.47"
            if (os.environ.get("FLATPAK_ID") or "").endswith(".dev")
            else "ZyRoom-GTK-0.30")

#: Signature affichée en bas de la fenêtre principale. Cliquable : elle ouvre
#: l'À propos, où vivent le copyright et la licence.
SIGNATURE = "Original by Misugi, fork by Xiom"

#: Où trouver le code de ce portage, et celui dont il dérive. L'AGPL veut que
#: l'interface dise à qui reçoit l'application où prendre ses sources.
DEPOT_SOURCES = "https://github.com/xiom-dev/zyroom-gtk-android"
COURRIEL = "ludopika@ikmail.com"
DEPOT_ORIGINE = "https://github.com/misugi/zyroom"

_KIND_PREFIX = {KIND_CHARACTER: "👤", KIND_GUILD: "🛡"}
_KIND_LABEL = {KIND_CHARACTER: "Personnage", KIND_GUILD: "Guilde"}


def run_async(work, on_done):
    """Exécute `work()` dans un thread, puis `on_done(result, error)` sur le
    thread GTK."""
    def runner():
        try:
            res, err = work(), None
        except Exception as exc:  # noqa: BLE001 — on remonte l'erreur à l'UI
            res, err = None, exc
        GLib.idle_add(on_done, res, err)
    threading.Thread(target=runner, daemon=True).start()


def _norm(text: str) -> str:
    """Minuscule sans accents, pour une recherche tolérante."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application)
        self.set_title(APP_NAME)

        self._char_store = EntityStore("characters.ini")
        self._guild_store = EntityStore("guilds.ini")
        self._settings = Settings()
        # La fenêtre se rouvre comme on l'a laissée. Après `Settings` et non
        # avant : c'est lui qui sait de quelle taille il s'agit.
        self.set_default_size(*self._settings.window_size)
        if self._settings.window_maximized:
            self.maximize()
        i18n.set_language(self._settings.language)
        self._apply_proxy()

        self._sheetdb = SheetDb()
        self._sheetdb.load(SHEETID_CSV)
        self._categorydb = CategoryDb()
        self._categorydb.load(CATEGORY_CSV)

        self._names = NameDb(names_cache_path())
        self._load_names(self._settings.pack_file or detect_pack())

        self._icons = IconLoader()
        # Le journal des prises d'avant-postes : un seul jeu de fichiers
        # pour tout le serveur, la carte ne dépendant d'aucune clé.
        self._op_store = outposts.OutpostStore(data_dir())
        # Le registre du personnel : un jeu de fichiers par guilde,
        # reconstruit à chaque changement d'entité.
        self._roster_store = None
        # La dernière guilde et le dernier personnage rencontrés. Les
        # écrans de « Plus » s'ouvrent sur eux quelle que soit l'entité
        # choisie : les avant-postes ne dépendent d'aucune, l'effectif est
        # celui de sa guilde, et l'arbre celui de son personnage — passer
        # de l'un à l'autre pour consulter n'aurait aucun sens.
        self._derniere_guilde = None
        self._dernier_perso = None
        self._skills_de = ""      #: nom rappelé quand l'arbre vient d'ailleurs

        self._entries: list[dict] = []       # entités fusionnées (perso + guilde)
        self._entity: Entity | None = None
        self._rows: list[tuple[Gtk.FlowBoxChild, object, str]] = []  # (child, item, clé recherche)
        self._generation = 0                 # invalide les callbacks d'icônes obsolètes
        self._portrait_gen = 0               # invalide les portraits obsolètes
        self._alerts: list[alerts.Alert] = []
        self._log_entries: list = []         # journal de l'entité affichée
        self._watch: WatchStore | None = None
        # État des filtres/tri
        self._sort_index = 0
        self._sort_desc = False
        self._f_types = set(range(len(TYPE_NAMES)))
        self._f_ecosys = set(range(len(ECOSYSTEM_NAMES)))
        self._f_classes = set(range(len(CLASS_NAMES)))
        self._f_equips = set(range(len(EQUIP_NAMES)))

        # Entités déjà rafraîchies depuis l'ouverture de l'application : on ne
        # resynchronise qu'une fois par entité, pas à chaque aller-retour dans
        # la liste déroulante.
        self._synced: set[tuple[str, str]] = set()
        self._sync_timer: int | None = None
        self._busy = False

        self._build_ui()
        # Le portail décide lui-même quand vérifier, souvent une fois l'heure.
        # On l'écoute quand même — c'est lui qui installe —, mais on regarde
        # aussi le dépôt nous-même : au lancement, puis tous les quarts d'heure.
        # Hors Flatpak, ni l'un ni l'autre ne trouve de quoi travailler.
        self._updater = Updater(self._on_update_available, self._on_update_progress)
        self._veilleur = Veilleur()
        self._verifier_maj()
        GLib.timeout_add_seconds(MAJ_INTERVALLE, self._verifier_maj_tick)
        self._reload_entities()
        self._refresh_season()
        # La météo part au démarrage, et non à l'ouverture de son onglet :
        # ainsi le graphique avance déjà quand on l'affiche, au lieu de
        # faire attendre le réseau. Un document de quelques kilo-octets,
        # sans clé, et une seule fois — c'est ensuite le temps qui passe
        # qui le fait défiler.
        GLib.idle_add(lambda: (self._load_meteo(), False)[1])
        GLib.timeout_add_seconds(180, self._refresh_season_tick)
        self._schedule_sync()
        self.connect("close-request", self._on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text(_("Ajouter un personnage ou une guilde (clé API)"))
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn)

        self._remove_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._remove_btn.set_tooltip_text(_("Retirer l'entité sélectionnée"))
        self._remove_btn.connect("clicked", self._on_remove_clicked)
        self._remove_btn.set_sensitive(False)
        header.pack_start(self._remove_btn)

        self._refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._refresh_btn.set_tooltip_text(_("Resynchroniser depuis l'API"))
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        self._refresh_btn.set_sensitive(False)
        header.pack_end(self._refresh_btn)

        pack_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
        pack_btn.set_tooltip_text(_("Charger string_client.pack (noms d'items lisibles)"))
        pack_btn.connect("clicked", self._on_pack_clicked)
        header.pack_end(pack_btn)

        menu = Gio.Menu()
        menu.append(_("Options…"), "win.options")
        menu.append(_("Analyser un chatlog…"), "win.chatlog")
        menu.append(_("Sauvegarder maintenant"), "win.backup")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_tooltip_text(_("Menu"))
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        for name, handler in (("options", self._on_options),
                              ("chatlog", self._on_chatlog),
                              ("backup", self._on_backup)):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", handler)
            self.add_action(act)

        # Bouton de mise à jour : caché tant qu'il n'y a rien à installer, pour
        # ne pas encombrer la barre d'un bouton qui ne ferait rien.
        self._update_btn = Gtk.Button(label="⬆ Mettre à jour")
        self._update_btn.add_css_class("suggested-action")
        self._update_btn.set_visible(False)
        self._update_btn.connect("clicked", self._on_update_clicked)
        header.pack_end(self._update_btn)

        # La cloche va à gauche, avec l'ajout et le retrait : ce sont les
        # boutons qui parlent de l'entité affichée. À droite, elle se trouvait
        # entre le menu et la mise à jour, deux choses qui parlent de
        # l'application, et sa pastille jaune y attirait l'œil de travers.
        self._bell = Gtk.Button(label="🔔")
        self._bell.set_tooltip_text(_("Alertes"))
        self._bell.set_sensitive(False)
        self._bell.connect("clicked", self._on_bell_clicked)
        header.pack_start(self._bell)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        # Ligne 1 : portrait, sélecteurs d'entité et d'inventaire, dappers
        bar1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        # Le même gris sombre qu'en bas : les deux bandes encadrent le tableau.
        bar1.add_css_class("barre-etat")
        root.append(bar1)
        bar1.append(Gtk.Label(label=_("Entité :")))
        self._entity_dd = Gtk.DropDown(model=Gtk.StringList())
        self._entity_dd.connect("notify::selected", self._on_entity_selected)
        bar1.append(self._entity_dd)
        bar1.append(Gtk.Label(label=_("Inventaire :")))
        self._inv_dd = Gtk.DropDown(model=Gtk.StringList())
        self._inv_dd.connect("notify::selected", self._on_inventory_selected)
        bar1.append(self._inv_dd)
        self._spinner = Gtk.Spinner()
        bar1.append(self._spinner)
        spacer = Gtk.Label(hexpand=True)
        bar1.append(spacer)
        self._season_lbl = Gtk.Label(label="")
        bar1.append(self._season_lbl)

        # MOTD (guilde) — masquée si vide. Encadrée comme sur Android : une
        # ligne grise perdue entre deux rangées ne se remarquait pas, et c'est
        # pourtant ce que les officiers écrivent à toute la guilde. Le mégaphone
        # reste à part du texte pour que celui-ci s'aligne quand il passe à la
        # ligne, au lieu de repartir sous l'icône.
        self._motd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._motd_box.add_css_class("motd")
        self._motd_box.props.margin_start = 8
        self._motd_box.props.margin_end = 8
        self._motd_box.props.margin_top = 2
        self._motd_box.props.margin_bottom = 2
        self._motd_box.append(Gtk.Label(label="📢", valign=Gtk.Align.START))
        self._motd_lbl = Gtk.Label(xalign=0.0, wrap=True, hexpand=True)
        self._motd_box.append(self._motd_lbl)
        self._motd_box.set_visible(False)
        root.append(self._motd_box)
        self._install_motd_css()

        # Deux vues : la grille d'inventaire et le journal des mouvements.
        # Le sélecteur d'entité reste au-dessus, il vaut pour les deux.
        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        inv_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._stack.add_titled(inv_page, "inventory", _("Inventaire"))
        root.append(self._stack)

        # Ligne volume : jauge de remplissage de l'inventaire courant
        barvol = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        barvol.props.margin_start = barvol.props.margin_end = 8
        inv_page.append(barvol)
        barvol.append(Gtk.Label(label=_("Volume :")))
        self._vol_bar = Gtk.LevelBar()
        self._vol_bar.set_min_value(0)
        self._vol_bar.set_max_value(100)
        self._vol_bar.set_hexpand(True)
        self._vol_bar.set_valign(Gtk.Align.CENTER)
        # seuils de couleur de la jauge
        self._vol_bar.add_offset_value("low", 60)
        self._vol_bar.add_offset_value("high", 85)
        self._vol_bar.add_offset_value("full", 100)
        barvol.append(self._vol_bar)
        self._vol_value = Gtk.Label(label="")
        barvol.append(self._vol_value)

        # Ligne 2 : recherche + filtres + tri
        bar2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar2)
        inv_page.append(bar2)
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text(_("Rechercher un item par nom…"))
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda *a: self._apply_filter())
        bar2.append(self._search)

        filter_btn = Gtk.MenuButton(label=_("Filtres"))
        filter_btn.set_popover(self._build_filter_popover())
        bar2.append(filter_btn)

        bar2.append(Gtk.Label(label=_("Trier :")))
        self._sort_dd = Gtk.DropDown.new_from_strings(
            [_("Ordre d'origine"), _("Type"), _("Écosystème"), _("Classe"),
             _("Qualité"), _("Volume"), _("Quantité"), _("Prix"), _("Nom")])
        self._sort_dd.connect("notify::selected", self._on_sort_changed)
        bar2.append(self._sort_dd)
        self._order_btn = Gtk.Button(label="↓")
        self._order_btn.set_tooltip_text(_("Ordre croissant/décroissant"))
        self._order_btn.connect("clicked", self._on_order_toggle)
        bar2.append(self._order_btn)

        reset = Gtk.Button(label=_("Réinit."))
        reset.connect("clicked", self._on_reset_filter)
        bar2.append(reset)

        # Grille d'items
        self._flow = Gtk.FlowBox()
        self._flow.set_valign(Gtk.Align.START)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_max_children_per_line(64)
        self._flow.set_column_spacing(4)
        self._flow.set_row_spacing(4)
        self._pad(self._flow)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._flow)
        inv_page.append(scrolled)

        # Onglet « Journal » + bascule dans la barre de titre.
        #
        # Trois onglets en haut, et non six : la barre de titre partageait sa
        # place avec les boutons, et six titres l'y auraient serrée à
        # l'illisible. Ce qu'on consulte tous les jours reste devant —
        # l'inventaire et le journal des mouvements — et le reste vit sous
        # « Plus », avec sa propre rangée.
        self._stack.add_titled(self._build_log_page(), "log", _("Journal"))
        self._stack.add_titled(self._build_plus_page(), "plus", _("Bonus"))
        header.set_title_widget(self._build_navigation())
        self._stack.connect("notify::visible-child-name", self._on_page_changed)

        # Barre d'état : portrait du personnage + texte
        #
        # Une `CenterBox` et non une boîte : son enfant du milieu est centré sur
        # la fenêtre, quoi que pèsent ses voisins. Avec une boîte ordinaire, la
        # ligne d'état prenait toute la place libre et poussait le nom contre
        # les dappers, à droite — centré sur rien.
        statusbar = Gtk.CenterBox()
        # Les marges passent à l'intérieur : la bande grise doit aller d'un bord
        # à l'autre, comme la barre de titre qui lui répond en haut.
        # La barre d'état et la signature ne font qu'une bande : la signature
        # posée dessous, sur le fond clair, coupait le gris en deux.
        pied = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        pied.add_css_class("barre-etat")
        root.append(pied)
        pied.append(statusbar)
        self._portrait = Gtk.Image()
        # Quarante-quatre, et de l'air au-dessus : c'est une signature, pas une
        # illustration du tableau. Aux tailles précédentes — soixante-douze
        # puis soixante — l'emblème touchait presque la dernière ligne et
        # paraissait lui appartenir.
        self._portrait.set_pixel_size(44)
        self._portrait.props.margin_top = 6
        self._portrait.set_tooltip_text(_("Cliquer pour agrandir"))
        self._portrait_path = ""
        pclick = Gtk.GestureClick()
        pclick.connect("released", self._on_portrait_click)
        self._portrait.add_controller(pclick)
        # Douze pixels et non huit : à huit, le portrait — ou l'emblème de la
        # guilde — et les deux lignes de texte formaient un seul bloc, et l'œil
        # ne savait plus où finissait l'image et où commençait le nom.
        # Douze et pas davantage : ces pixels sont pris sur la largeur du texte,
        # et à treize la ligne de la guilde passe à trois lignes dès 1084 px de
        # fenêtre — mesuré, avec le vrai libellé « Coffre 1 — La Resserre
        # Lunaire · synchro à l'instant ».
        gauche = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        gauche.append(self._portrait)
        # Calée en bas, et non centrée : la seconde ligne se pose alors sur le
        # bas du portrait — ou de l'emblème — au lieu de flotter cinq pixels
        # au-dessus. Centrée, le texte étant moins haut que l'image, ni le haut
        # ni le bas ne s'alignaient sur rien.
        self._status = Gtk.Label(xalign=0.0, valign=Gtk.Align.END)
        # Elle dit qui on regarde, dans quel contenant, et de quand datent les
        # données : c'est le fil que l'œil retrouve en revenant à l'écran.
        self._status.add_css_class("peuple")
        # Elle s'étire pour occuper la moitié gauche, mais ne **réclame** que
        # peu : une `CenterBox` ne centre son enfant du milieu que si les côtés
        # tiennent dans la moitié qui leur revient, et la ligne d'état, laissée
        # à sa largeur naturelle, poussait le nom trente-deux pixels à droite —
        # mesuré. Bornée en demande et étirée en allocation, elle s'affiche en
        # entier sans plus déranger personne, et se coupe si la fenêtre rétrécit.
        # Deux lignes au plus, et la seconde se coupe si elle déborde. La
        # largeur **demandée** reste petite — c'est elle qui décide du centrage
        # du nom, pas la largeur obtenue — tandis que `hexpand` lui donne toute
        # la moitié gauche pour s'afficher.
        self._status.set_wrap(True)
        self._status.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._status.set_lines(2)
        self._status.set_ellipsize(Pango.EllipsizeMode.END)
        self._status.set_max_width_chars(34)
        self._status.set_hexpand(True)
        gauche.append(self._status)
        gauche.set_hexpand(True)
        statusbar.set_start_widget(gauche)

        # Le nom de l'application, au milieu de la barre du bas. Il n'était
        # écrit **nulle part** : la fenêtre s'appelait ZyRoom-GTK dans son
        # titre de bureau, mais rien à l'écran ne le disait. Dans la police du
        # titre d'Android — une gothique de bois gravé — et dans son or.
        nom = Gtk.Label(label="ZyRoom", valign=Gtk.Align.END)
        nom.add_css_class("nom-appli")
        statusbar.set_center_widget(nom)

        self._dappers_lbl = Gtk.Label(label="", valign=Gtk.Align.END)
        statusbar.set_end_widget(self._dappers_lbl)

        # Signature : d'où vient cette application. Pas de traduction, ce sont
        # des noms propres. Cliquable, parce que c'est là qu'on cherche d'où
        # vient un logiciel — et que l'AGPL veut que l'interface porte le
        # copyright, l'absence de garantie et le moyen d'obtenir le code.
        signature = Gtk.Button(label=SIGNATURE)
        signature.set_has_frame(False)
        signature.get_child().add_css_class("dim-label")
        signature.get_child().add_css_class("caption")
        signature.set_tooltip_text(_("À propos de ZyRoom-GTK"))
        signature.connect("clicked", self._on_about)
        signature.props.margin_bottom = 2
        pied.append(signature)

        if not self._names.loaded:
            self._set_status("Astuce : chargez string_client.pack (icône dossier) "
                             "pour afficher les noms d'items.")

    # ------------------------------------------------ Journal des mouvements
    #: Nombre de lignes construites d'un coup. Au-delà, on n'affiche pas tout :
    #: un journal peut compter des milliers de lignes et une grille GTK de cette
    #: taille se construit lentement pour rien — le filtre sert à chercher plus
    #: loin.
    _LOG_PAGE_SIZE = 400

    def _build_log_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._log_search = Gtk.SearchEntry()
        self._log_search.set_placeholder_text(_("Rechercher dans le journal…"))
        self._log_search.set_hexpand(True)
        self._log_search.connect("search-changed", lambda *a: self._refresh_log())
        bar.append(self._log_search)

        self._log_filter = Gtk.DropDown.new_from_strings(
            [_("Tout"), _("Entrées"), _("Sorties")])
        self._log_filter.connect("notify::selected", lambda *a: self._refresh_log())
        bar.append(self._log_filter)

        copy_btn = Gtk.Button(label=_("Copier"))
        copy_btn.set_tooltip_text(_("Copier les lignes affichées"))
        copy_btn.connect("clicked", self._on_log_copy)
        bar.append(copy_btn)

        clear_btn = Gtk.Button(label=_("Vider"))
        clear_btn.set_tooltip_text(_("Effacer le journal de cette entité"))
        clear_btn.connect("clicked", self._on_log_clear)
        bar.append(clear_btn)

        self._log_grid = Gtk.Grid(column_spacing=16, row_spacing=2)
        self._pad(self._log_grid)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._log_grid)
        page.append(scrolled)

        self._log_status = Gtk.Label(xalign=0.0)
        self._log_status.add_css_class("dim-label")
        self._log_status.props.margin_start = 8
        self._log_status.props.margin_bottom = 6
        page.append(self._log_status)
        return page

    # ---------------------------------------------------------- Compétences
    #: Les quatre écrans de « Bonus », dans l'ordre du menu.
    #:
    #: Le nom interne de la page reste `plus` : il ne paraît nulle part, et le
    #: renommer toucherait l'action D-Bus, la pile et six méthodes pour rien.
    PLUS_PAGES = (("skills", "Compétences"), ("roster", "Effectif"),
                  ("betes", "Perdu ?"), ("outposts", "Avant-postes"),
                  ("meteo", "Météo"))

    def _build_navigation(self) -> Gtk.Widget:
        """La navigation de la barre de titre : deux boutons et un menu.

        Six onglets ne tenaient pas ; une rangée de plus mangeait la hauteur
        d'un tableau. Ici, l'inventaire et le journal — ce qu'on consulte tous
        les jours — restent à un clic, et les quatre écrans de consultation
        vivent dans un menu déroulant.
        """
        boite = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        boite.add_css_class("linked")

        self._nav_boutons = {}
        for nom, etiquette in (("inventory", _("Inventaire")), ("log", _("Journal"))):
            bouton = Gtk.ToggleButton(label=etiquette)
            bouton.connect("toggled", self._on_nav_toggled, nom)
            self._nav_boutons[nom] = bouton
            boite.append(bouton)

        menu = Gio.Menu()
        for nom, etiquette in self.PLUS_PAGES:
            menu.append(_(etiquette), f"win.plus::{nom}")
        self._plus_btn = Gtk.MenuButton(label=_("Bonus"))
        self._plus_btn.set_menu_model(menu)
        self._plus_btn.set_always_show_arrow(True)
        boite.append(self._plus_btn)

        action = Gio.SimpleAction.new("plus", GLib.VariantType.new("s"))
        action.connect("activate", self._on_plus_choisi)
        self.add_action(action)
        return boite

    def _on_nav_toggled(self, bouton, nom: str) -> None:
        if bouton.get_active():
            self._stack.set_visible_child_name(nom)

    def _on_plus_choisi(self, _action, parametre) -> None:
        page = parametre.get_string()
        self._stack.set_visible_child_name("plus")
        self._plus_stack.set_visible_child_name(page)

    def _refresh_navigation(self) -> None:
        """Aligne les boutons sur la page réellement visible.

        Le clavier, le code et la souris peuvent tous changer de page : c'est la
        pile qui fait foi, jamais l'état d'un bouton."""
        page = self._stack.get_visible_child_name()
        for nom, bouton in self._nav_boutons.items():
            actif = nom == page
            if bouton.get_active() != actif:
                bouton.handler_block_by_func(self._on_nav_toggled)
                bouton.set_active(actif)
                bouton.handler_unblock_by_func(self._on_nav_toggled)
        # Le bouton s'appelle « Bonus », toujours : c'est un menu, et un menu ne
        # prend pas le nom de ce qu'on y a choisi. Seul son état enfoncé dit
        # qu'on est dans l'une de ses pages.
        if page == "plus":
            self._plus_btn.add_css_class("suggested-action")
        else:
            self._plus_btn.remove_css_class("suggested-action")

    # -------------------------------------------------------------- Bonus
    #
    # Quatre écrans de consultation, derrière un seul onglet : les compétences
    # d'un personnage, la carte des avant-postes, la météo d'Atys et le
    # registre du personnel d'une guilde. Chacun a sa propre pile, avec sa
    # rangée de boutons — celle du haut porte déjà l'inventaire et le journal.

    def _build_plus_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._plus_stack = Gtk.Stack()
        self._plus_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self._plus_stack.add_titled(self._build_skills_page(), "skills",
                                    _("Compétences"))
        self._plus_stack.add_titled(self._build_roster_page(), "roster",
                                    _("Effectif"))
        self._plus_stack.add_titled(self._build_betes_page(), "betes",
                                    _("Perdu ?"))
        self._plus_stack.add_titled(self._build_outposts_page(), "outposts",
                                    _("Avant-postes"))
        self._plus_stack.add_titled(self._build_meteo_page(), "meteo", _("Météo"))

        # Aucune rangée de boutons ici : c'est le menu déroulant de la barre de
        # titre qui commande cette pile, et il porte le nom de l'écran affiché.
        page.append(self._plus_stack)
        self._plus_stack.set_vexpand(True)
        self._plus_stack.connect("notify::visible-child-name",
                                 lambda *a: self._on_plus_changed())
        return page

    def _on_plus_changed(self) -> None:
        self._refresh_navigation()
        page = self._plus_stack.get_visible_child_name()
        if page == "skills":
            self._refresh_skills()
        elif page == "roster":
            self._refresh_roster()
        elif page == "betes":
            self._remplir_betes(self._entity)
        # Ces deux-là vont chercher sur le réseau : elles ne le font qu'à la
        # première ouverture, et sur demande ensuite. L'annuaire des guildes
        # pèse un demi-méga-octet, il n'a pas à partir au démarrage.
        elif page == "outposts":
            self._load_outposts()
        elif page == "meteo":
            self._load_meteo()

    # -------------------------------------------------- Registre du personnel

    def _build_roster_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._roster_vue = Gtk.DropDown.new_from_strings(
            [_("Effectif"), _("Arrivées et départs")])
        self._roster_vue.connect("notify::selected",
                                 lambda *a: self._refresh_roster())
        bar.append(self._roster_vue)

        self._roster_status = Gtk.Label(xalign=0.0)
        self._roster_status.add_css_class("dim-label")
        self._roster_status.set_hexpand(True)
        bar.append(self._roster_status)

        self._roster_box = Gtk.ListBox()
        self._roster_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._roster_box.add_css_class("survol")
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._roster_box)
        page.append(scrolled)
        return page

    def _refresh_roster(self) -> None:
        while (child := self._roster_box.get_first_child()) is not None:
            self._roster_box.remove(child)
        # L'effectif s'ouvre quelle que soit l'entité choisie : c'est celui de
        # la dernière guilde rencontrée, et consulter un registre ne devrait pas
        # obliger à changer d'entité. Le nom de la guilde est rappelé quand ce
        # n'est pas celle qu'on regarde.
        ent = self._entity
        if ent is None or ent.kind != KIND_GUILD or not ent.members:
            ent = self._derniere_guilde or self._entite_en_cache(KIND_GUILD)
            self._derniere_guilde = self._derniere_guilde or ent
            ailleurs = ent is not None
        else:
            ailleurs = False
        if ent is None:
            self._roster_status.set_text(
                _("Aucune guilde consultée pour l'instant : ouvrez-en une une "
                  "fois, et son effectif restera consultable d'ici."))
            return

        store = (self._roster_store if not ailleurs
                 else roster.RosterStore(data_dir(), ent.entity_id))
        changements = store.history() if store else []
        self._roster_status.set_text(
            (_("%s · ") % ent.name if ailleurs else "") +
            _("%d membres") % len(ent.members) +
            (_("  ·  %d mouvements sur un mois") % len(changements)
             if changements else ""))

        if self._roster_vue.get_selected() == 1:
            self._remplir_mouvements_roster(changements)
        else:
            self._remplir_effectif_roster(ent)

    def _remplir_effectif_roster(self, ent) -> None:
        """L'effectif, par grade, en autant de colonnes que la fenêtre en tient.

        Cent soixante-dix noms sur une seule colonne faisaient un ruban plus
        haut que dix écrans, où l'on ne trouvait rien. Ils se rangent sur six
        colonnes, et **c'est le grade qui est teinté, non la ligne** : le
        zébrage sert ici à séparer les groupes, pas à suivre une ligne — un
        nom n'a rien à droite de lui qu'on doive relier."""
        # Le chef d'abord, les membres ensuite : on lit une liste de guilde par
        # le haut, et l'API la rend dans un ordre qui n'en est pas un.
        membres = sorted(ent.members,
                         key=lambda nm: (roster.rang_grade(nm[1]), nm[0].lower()))
        par_grade: dict[str, list[str]] = {}
        for nom, grade in membres:
            par_grade.setdefault(grade, []).append(nom)

        for rang_groupe, (grade, noms) in enumerate(par_grade.items()):
            teinte = rang_groupe % 2 == 0
            entete = Gtk.ListBoxRow()
            entete.set_activatable(False)
            if teinte:
                entete.add_css_class("zebre")
            titre = Gtk.Label(label=f"{roster.nom_grade(grade)} · {len(noms)}",
                              xalign=0.0)
            titre.add_css_class("title-4")
            titre.add_css_class("peuple")
            titre.props.margin_top = 10
            titre.props.margin_start = 8
            titre.props.margin_bottom = 2
            entete.set_child(titre)
            self._roster_box.append(entete)

            # Une grille et non une boîte à flot : le zébrage suppose des
            # rangées, et une boîte à flot n'en a que le jour où elle se
            # dessine. Six colonnes, comme elle en tenait au large.
            for depart in range(0, len(noms), self.ROSTER_COLONNES):
                tranche = noms[depart:depart + self.ROSTER_COLONNES]
                row = Gtk.ListBoxRow()
                row.set_activatable(False)
                if teinte:
                    row.add_css_class("zebre")
                grille = Gtk.Grid(column_spacing=4, column_homogeneous=True)
                self._pad(grille)
                grille.props.margin_top = 1
                grille.props.margin_bottom = 1
                # La rangée est toujours remplie jusqu'à six, au besoin de
                # cases vides : une grille homogène ne répartit que les colonnes
                # qui existent, et la dernière rangée d'un grade — deux noms —
                # s'étalait sur toute la largeur au lieu de s'aligner sur celles
                # du dessus.
                for colonne in range(self.ROSTER_COLONNES):
                    nom = tranche[colonne] if colonne < len(tranche) else ""
                    label = Gtk.Label(label=nom, xalign=0.0)
                    label.add_css_class("compact")
                    label.set_ellipsize(Pango.EllipsizeMode.END)
                    grille.attach(label, colonne, 0, 1, 1)
                row.set_child(grille)
                self._roster_box.append(row)

    #: Le signe de chaque mouvement : forme, classe de couleur, et sens.
    #:
    #: La couleur porte le sens — vert pour ce qui entre, rouge pour ce qui
    #: sort, blanc pour ce qui bouge à l'intérieur — et la direction du triangle
    #: le confirme, pour qui distingue mal les deux teintes.
    SIGNES = {
        ("arrivee", True): ("▲", "tri-arrivee", "arrivée"),
        ("depart", True): ("▼", "tri-depart", "départ"),
        ("grade", True): ("▲", "tri-grade", "montée de grade"),
        ("grade", False): ("▼", "tri-grade", "rétrogradation"),
    }

    def _signe_mouvement(self, c) -> tuple:
        if c.kind == "grade":
            return self.SIGNES[("grade", c.promotion)]
        return self.SIGNES[(c.kind, True)]

    def _remplir_mouvements_roster(self, changements: list) -> None:
        self._roster_box.append(self._legende_roster())
        if not changements:
            self._roster_box.append(self._ligne_simple(
                _("Aucun mouvement depuis le premier relevé. Le registre "
                  "compare l'effectif d'une synchronisation à l'autre : l'API "
                  "ne garde aucune histoire, seule l'application en tient une."),
                dim=True))
            return
        for rang, c in enumerate(changements):
            row = Gtk.ListBoxRow()
            if rang % 2 == 0:
                row.add_css_class("zebre")
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            self._pad(line)
            line.props.margin_top = 2
            line.props.margin_bottom = 2

            quand = Gtk.Label(label=datetime.fromtimestamp(c.at)
                              .strftime("%d/%m %H:%M"), xalign=0.0)
            quand.add_css_class("dim-label")
            quand.add_css_class("compact")
            line.append(quand)

            forme, classe, _sens = self._signe_mouvement(c)
            triangle = Gtk.Label(label=forme)
            triangle.add_css_class(classe)
            line.append(triangle)

            line.append(Gtk.Label(label=roster.decrire(c), xalign=0.0))
            row.set_child(line)
            self._roster_box.append(row)

    def _legende_roster(self) -> Gtk.ListBoxRow:
        """Quatre signes et leur sens, en tête du journal.

        Sans elle, un triangle rouge vers le bas se lit comme une alarme plutôt
        que comme un départ."""
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self._pad(line)
        for (forme, classe, sens) in (self.SIGNES[("arrivee", True)],
                                      self.SIGNES[("depart", True)],
                                      self.SIGNES[("grade", True)],
                                      self.SIGNES[("grade", False)]):
            paire = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            triangle = Gtk.Label(label=forme)
            triangle.add_css_class(classe)
            paire.append(triangle)
            texte = Gtk.Label(label=_(sens))
            texte.add_css_class("dim-label")
            texte.add_css_class("compact")
            paire.append(texte)
            line.append(paire)
        row.set_child(line)
        return row

    # ------------------------------------------------------- Avant-postes
    #
    # Qui tient quoi sur Atys, et le journal des prises. L'annuaire public des
    # guildes ne demande aucune clé, mais pèse un demi-méga-octet : il n'est
    # donc demandé qu'à l'ouverture de l'onglet, et rafraîchi à la main.

    #: Les quatre peuples, dans l'ordre de la carte.
    PEUPLES = (("fyros", "Fyros"), ("matis", "Matis"),
               ("tryker", "Tryker"), ("zorai", "Zoraï"))

    def _build_outposts_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._op_vue = Gtk.DropDown.new_from_strings(
            [_("Qui tient quoi"), _("Journal des prises")])
        self._op_vue.connect("notify::selected", lambda *a: self._refresh_outposts())
        bar.append(self._op_vue)

        self._op_refresh = Gtk.Button(label=_("Actualiser"))
        self._op_refresh.set_tooltip_text(_("Redemander l'annuaire des guildes"))
        self._op_refresh.connect("clicked", lambda *a: self._load_outposts(force=True))
        bar.append(self._op_refresh)

        self._op_status = Gtk.Label(xalign=0.0)
        self._op_status.add_css_class("dim-label")
        self._op_status.set_hexpand(True)
        bar.append(self._op_status)

        # Deux colonnes : Fyros et Matis à gauche, Tryker et Zoraï à droite.
        # Les vingt-neuf avant-postes tenaient sur une colonne plus haute que
        # l'écran, et il fallait faire défiler pour comparer deux peuples.
        # Chacune défile pour son compte, les quatre listes n'ayant pas la même
        # longueur.
        colonnes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                           homogeneous=True)
        self._op_gauche = Gtk.ListBox()
        self._op_gauche.add_css_class("survol")
        self._op_droite = Gtk.ListBox()
        self._op_droite.add_css_class("survol")
        for colonne in (self._op_gauche, self._op_droite):
            colonne.set_selection_mode(Gtk.SelectionMode.NONE)
            defilement = Gtk.ScrolledWindow()
            defilement.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            defilement.set_vexpand(True)
            defilement.set_child(colonne)
            colonnes.append(defilement)
        # Le journal, lui, se lit sur toute la largeur : ses lignes sont des
        # phrases, pas un tableau.
        self._op_box = Gtk.ListBox()
        self._op_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._op_box.add_css_class("survol")
        journal = Gtk.ScrolledWindow()
        journal.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        journal.set_vexpand(True)
        journal.set_child(self._op_box)

        self._op_pile = Gtk.Stack()
        self._op_pile.set_transition_type(Gtk.StackTransitionType.NONE)
        self._op_pile.add_named(colonnes, "carte")
        self._op_pile.add_named(journal, "journal")
        self._op_pile.set_vexpand(True)
        page.append(self._op_pile)

        self._op_carte: list = []
        self._op_changements: list = []
        self._op_premier = False
        self._op_charge = False
        return page

    def _load_outposts(self, force: bool = False) -> None:
        """Va chercher l'annuaire, journalise les changements de main."""
        if self._op_charge and not force:
            return
        self._op_charge = True
        self._op_refresh.set_sensitive(False)
        self._op_status.set_text(_("Lecture de l'annuaire des guildes…"))

        def work():
            xml = ryzom_api.fetch_guild_directory_xml()
            carte = outposts.parse_outposts(xml)
            premier = self._op_store.jamais_releve()
            self._op_store.record(carte)
            return carte, self._op_store.history(), premier

        def done(res, err):
            self._op_refresh.set_sensitive(True)
            if err:
                self._op_status.set_text(_("Annuaire indisponible : %s") % err)
                return
            self._op_carte, self._op_changements, self._op_premier = res
            self._op_status.set_text("")
            self._refresh_outposts()

        run_async(work, done)

    def _refresh_outposts(self) -> None:
        for boite in (self._op_gauche, self._op_droite, self._op_box):
            while (child := boite.get_first_child()) is not None:
                boite.remove(child)
        if not self._op_carte:
            return
        if self._op_vue.get_selected() == 1:
            self._op_pile.set_visible_child_name("journal")
            self._remplir_journal_outposts()
        else:
            self._op_pile.set_visible_child_name("carte")
            self._remplir_carte_outposts()

    def _remplir_carte_outposts(self) -> None:
        carte = self._op_carte
        # Sur une guilde, c'est son nom ; sur un personnage, celui de sa guilde.
        # Sans cela, ouvrir la carte depuis son personnage ne mettait rien en
        # vert, alors que c'est justement là qu'on se demande « et nous ? ».
        ent = self._entity
        ma_guilde = ""
        if ent is not None:
            ma_guilde = (ent.name if ent.kind == KIND_GUILD else ent.guild) or ""
        miens = sum(1 for o in carte if o.guild == ma_guilde)
        entete = _("%d avant-postes tenus sur Atys") % len(carte)
        if miens:
            entete += _(", dont %d à %s") % (miens, ma_guilde)
        self._op_status.set_text(entete + ".")

        connus = {c for c, _n in self.PEUPLES}
        # Deux peuples par colonne, dans l'ordre de la carte.
        for colonne, peuples in ((self._op_gauche, self.PEUPLES[:2]),
                                 (self._op_droite, self.PEUPLES[2:])):
            # Un jeu de groupes de taille par colonne : ils imposent à tous
            # leurs membres la largeur du plus large, ce qui aligne les trois
            # colonnes d'une ligne à l'autre. Un jeu par côté, et non un seul :
            # les deux colonnes n'ont pas les mêmes noms, et leur imposer une
            # largeur commune gâcherait la place de l'une.
            groupes = tuple(Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
                            for _ in range(3))
            rang = 0
            for code, nom in peuples:
                # Du plus haut niveau au plus bas, comme on lit une carte de
                # conquête : les enjeux d'abord.
                siens = sorted((o for o in carte if o.people == code),
                               key=lambda o: (-o.level, self._names.name(o.name_key)))
                if not siens:
                    continue
                colonne.append(self._entete_peuple(nom))
                for avant_poste in siens:
                    colonne.append(self._ligne_outpost(
                        avant_poste, avant_poste.guild == ma_guilde,
                        rang % 2 == 0, groupes))
                    rang += 1
        orphelins = [o for o in carte if o.people not in connus]
        if orphelins:
            # L'annuaire contient parfois un code qui n'est pas un avant-poste
            # — « #15 ». Le taire ferait un total qui ne tombe pas juste.
            self._op_droite.append(self._ligne_simple(
                _("Hors carte : ") + ", ".join(f"{o.code} ({o.guild})"
                                               for o in orphelins), dim=True))

    def _remplir_journal_outposts(self) -> None:
        if self._op_premier and not self._op_changements:
            self._op_box.append(self._ligne_simple(
                _("Premier relevé : rien à comparer. Les changements de main "
                  "apparaîtront à partir du prochain."), dim=True))
            return
        if not self._op_changements:
            self._op_box.append(self._ligne_simple(
                _("Aucun changement de main depuis le premier relevé."), dim=True))
            return
        for rang, c in enumerate(self._op_changements):
            quand = datetime.fromtimestamp(c.at).strftime("%d/%m %H:%M")
            nom = self._names.name(f"{c.outpost}.outpost")
            if c.taken:
                texte = _("%s — pris par %s") % (nom, c.to)
            elif c.lost:
                texte = _("%s — perdu par %s") % (nom, c.frm)
            else:
                texte = _("%s — %s ▸ %s") % (nom, c.frm, c.to)
            self._op_box.append(self._ligne_simple(f"{quand}   {texte}",
                                                   zebre=rang % 2 == 0))

    def _entete_peuple(self, nom: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=nom, xalign=0.0)
        label.add_css_class("title-4")
        label.add_css_class("peuple")
        label.props.margin_top = 10
        label.props.margin_bottom = 2
        # Aligné sur le bloc des lignes, qui est centré : un titre resté contre
        # le bord gauche n'aurait plus rien coiffé.
        label.set_halign(Gtk.Align.CENTER)
        label.set_size_request(456, -1)
        row.set_child(label)
        return row

    def _ligne_outpost(self, avant_poste, mien: bool, zebre: bool,
                       groupes) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        # Les trois colonnes forment un bloc centré, à largeur fixe. Le nom
        # tenait auparavant toute la largeur disponible, ce qui repoussait le
        # niveau et la guilde contre le bord droit : sur un écran large, l'œil
        # devait traverser vingt centimètres de vide pour relier un
        # avant-poste à son propriétaire.
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        line.set_halign(Gtk.Align.CENTER)
        line.props.margin_top = 3
        line.props.margin_bottom = 3

        # L'emblème de la guilde, chargé en tâche de fond et mis en cache.
        image = Gtk.Image()
        image.set_pixel_size(20)
        self._icons.request_emblem(
            avant_poste.icon,
            lambda chemin, img=image: img.set_from_file(chemin) if chemin else None)
        line.append(image)

        # `set_size_request` ne fixe qu'un **minimum** : un nom long débordait et
        # poussait le niveau et la guilde plus loin, si bien qu'aucune colonne
        # n'était alignée d'une ligne à l'autre. Les groupes de taille, eux,
        # imposent à tous leurs membres la largeur du plus large — c'est
        # exactement ce qu'on veut d'une colonne.
        # Pas de largeur maximale : le groupe prend la largeur du nom le plus
        # long, et tous s'affichent en entier tant que la fenêtre le permet.
        # L'abrègement ne sert plus que de secours, quand on la rétrécit.
        nom = Gtk.Label(label=self._names.name(avant_poste.name_key), xalign=0.0)
        nom.set_ellipsize(Pango.EllipsizeMode.END)
        nom.add_css_class("compact")
        if mien:
            nom.add_css_class("fini")     # le vert de l'application
        groupes[0].add_widget(nom)
        line.append(nom)

        niveau = Gtk.Label(label=str(avant_poste.level) if avant_poste.level else "—",
                           xalign=1.0)
        niveau.add_css_class("dim-label")
        niveau.add_css_class("compact")
        groupes[1].add_widget(niveau)
        line.append(niveau)

        guilde = Gtk.Label(label=avant_poste.guild, xalign=0.0)
        guilde.set_ellipsize(Pango.EllipsizeMode.END)
        guilde.set_max_width_chars(24)
        guilde.add_css_class("compact")
        if mien:
            guilde.add_css_class("fini")
        groupes[2].add_widget(guilde)
        line.append(guilde)

        row.set_child(line)
        return row

    def _ligne_simple(self, texte: str, dim: bool = False,
                      zebre: bool = False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        label = Gtk.Label(label=texte, xalign=0.0, wrap=True)
        if dim:
            label.add_css_class("dim-label")
        self._pad(label)
        row.set_child(label)
        return row

    # -------------------------------------------------------------- Météo
    #
    # La météo d'Atys en courbe, et les matières qu'elle fait sortir. Deux
    # sources : l'API officielle pour le temps — calculé par le jeu, donc connu
    # quarante cycles à l'avance — et un relevé de Ryzom Armory figé dans
    # `armory.py`, qui ne changera qu'avec le jeu.

    #: Taille des symboles de familles de matières, en points.
    #:
    #: Fixée, et non demandée : une taille demandée n'est qu'un plancher, et les
    #: symboles grossissaient au gré de la place laissée par le nom de leur
    #: famille.
    #:
    #: Vingt-six et non vingt : sur un écran de bureau, à côté d'un nom de
    #: famille et d'une ligne de matières, vingt points faisaient une vignette
    #: qu'on devinait plus qu'on ne la reconnaissait. Au-delà, le symbole
    #: prendrait le pas sur le texte qu'il accompagne.
    TAILLE_SYMBOLE = 26

    #: Colonnes du bloc « ce qui sort » — une par zone des Primes, pour les
    #: avoir toutes les quatre sous les yeux à la fois. Sur deux colonnes, il
    #: fallait comparer une rangée avec celle du dessous alors que le geste
    #: utile est de choisir entre les quatre.
    COLONNES_POP = 4

    #: Le rouge du point. Il n'existe nulle part ailleurs sur la carte à ce ton.
    POINT = (1.0, 0.18, 0.18)

    #: Le noir des cernes et des liserés, jamais tout à fait noir pour l'œil.
    CERNE = (0.06, 0.08, 0.09)

    #: Le bleu du repère du joueur, distinct du rouge des bêtes.
    POINT_JOUEUR = (0.23, 0.61, 1.0)

    #: En deçà de cette distance à l'écran, deux bêtes n'en font qu'une.
    #:
    #: Quarante pixels : de quoi séparer deux troupeaux laissés dans deux
    #: régions, sans écrire quatre fois le même nom pour quatre mektoubs
    #: attachés ensemble.
    SEUIL_GROUPE = 40.0

    def _build_betes_page(self) -> Gtk.Widget:
        """Où sont les bêtes du joueur.

        Un mektoub de bât laissé en pleine terre y reste, et son propriétaire
        finit par oublier où. L'API donne sa position à chaque relevé ; c'est la
        seule chose qu'elle sache dire d'un animal qu'on ne retrouve plus.

        Seule la carte dit où : les coordonnées ne sont pas affichées. Le jeu ne
        permet pas d'en saisir pour poser un repère, donc deux nombres de plus
        n'auraient servi à rien.
        """
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self._betes_carte = Gtk.DrawingArea()
        self._betes_carte.set_content_height(300)
        self._betes_carte.set_draw_func(self._dessiner_carte_betes)
        self._betes_zoom = 1.0
        self._betes_glissement = [0.0, 0.0]

        # Trois façons d'agrandir, parce que trois matériels : le pincement du
        # pavé tactile, la molette de la souris, et le glissement au bouton pour
        # se déplacer une fois agrandi. Le monde entier tient dans la hauteur
        # d'une carte de visite : sans agrandissement, deux bêtes séparées de
        # cinq cents mètres sont au même endroit.
        pincement = Gtk.GestureZoom()
        pincement.connect("scale-changed", self._on_betes_pincement)
        self._betes_carte.add_controller(pincement)

        molette = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL)
        molette.connect("scroll", self._on_betes_molette)
        self._betes_carte.add_controller(molette)

        glisse = Gtk.GestureDrag()
        glisse.connect("drag-update", self._on_betes_glisse)
        glisse.connect("drag-end", self._on_betes_glisse_fin)
        self._betes_carte.add_controller(glisse)
        self._betes_glisse_depart = [0.0, 0.0]

        page.append(self._betes_carte)

        self._betes_entete = Gtk.Label(xalign=0.0)
        self._betes_entete.add_css_class("dim-label")
        self._pad(self._betes_entete)
        page.append(self._betes_entete)

        # Deux colonnes : les mektoubs à gauche — de monte comme de bât —, les
        # zigs à droite. On cherche rarement les uns en pensant aux autres, et
        # les zigs sont souvent nombreux.
        defilement = Gtk.ScrolledWindow(vexpand=True)
        colonnes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                           homogeneous=True)
        self._pad(colonnes)
        self._betes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._betes_zigs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        colonnes.append(self._betes_box)
        colonnes.append(self._betes_zigs)
        defilement.set_child(colonnes)
        page.append(defilement)

        self._betes_pixbuf = None
        return page

    def _rafraichir_betes_si_visible(self) -> None:
        """Recharge la liste si on la regarde : changer d'entité change de bêtes."""
        if (self._stack.get_visible_child_name() == "plus"
                and self._plus_stack.get_visible_child_name() == "betes"):
            self._remplir_betes(self._entity)

    #: Jusqu'où l'agrandissement va. Au-delà, on n'ajoute plus que du flou.
    ZOOM_MAX = 6.0

    def _borner_glissement(self) -> None:
        """Empêche la carte des bêtes de s'échapper de son cadre.

        Le débord se mesurait sur la largeur du cadre — `largeur × (zoom − 1)`
        — alors que la carte y tient en boîte aux lettres : on pouvait donc la
        pousser dans le vide. `_borner_carte` le mesure sur l'image telle
        qu'elle est dessinée."""
        self._borner_carte(self._betes_carte, self._betes_zoom,
                           self._betes_glissement)

    def _regler_zoom_betes(self, facteur: float) -> None:
        avant = self._betes_zoom
        self._betes_zoom = max(1.0, min(self.ZOOM_MAX, self._betes_zoom * facteur))
        if self._betes_zoom == avant:
            return
        rapport = self._betes_zoom / avant
        self._betes_glissement[0] *= rapport
        self._betes_glissement[1] *= rapport
        self._borner_glissement()
        self._betes_carte.queue_draw()

    def _on_betes_pincement(self, gesture, echelle) -> None:
        # Le geste rend une échelle absolue depuis son début ; on la ramène à un
        # facteur relatif pour la composer avec l'agrandissement en cours.
        depart = getattr(self, "_betes_pince_depart", None)
        if depart is None or not gesture.is_active():
            self._betes_pince_depart = self._betes_zoom
            depart = self._betes_zoom
        avant = self._betes_zoom
        self._betes_zoom = max(1.0, min(self.ZOOM_MAX, depart * echelle))
        # Le déplacement suit l'agrandissement, sinon la vue part sur le côté :
        # l'image grandit autour de son propre milieu, pas autour du nôtre.
        if avant > 0:
            rapport = self._betes_zoom / avant
            self._betes_glissement[0] *= rapport
            self._betes_glissement[1] *= rapport
        self._borner_glissement()
        self._betes_glisse_depart = list(self._betes_glissement)
        self._betes_carte.queue_draw()

    def _on_betes_molette(self, _controller, _dx, dy) -> bool:
        self._regler_zoom_betes(
            1 / self.PAS_ZOOM if dy > 0 else self.PAS_ZOOM)
        return True

    def _on_betes_glisse(self, _gesture, dx, dy) -> None:
        self._betes_glissement[0] = self._betes_glisse_depart[0] + dx
        self._betes_glissement[1] = self._betes_glisse_depart[1] + dy
        self._borner_glissement()
        self._betes_carte.queue_draw()

    def _on_betes_glisse_fin(self, _gesture, _dx, _dy) -> None:
        self._betes_glisse_depart = list(self._betes_glissement)

    def _remplir_betes(self, ent) -> None:
        for boite in (self._betes_box, self._betes_zigs):
            while (child := boite.get_first_child()) is not None:
                boite.remove(child)
        betes = list(getattr(ent, "betes", []))
        dehors = [b for b in betes if b.dehors]
        self._betes_entete.set_text(
            _("Aucune bête dehors : toutes sont rangées.") if not dehors
            else _("%d bête dehors") % len(dehors) if len(dehors) == 1
            else _("%d bêtes dehors") % len(dehors))
        self._remplir_colonne_betes(self._betes_box, _("Mektoubs"),
                                    [b for b in betes if not b.zig])
        self._remplir_colonne_betes(self._betes_zigs, _("Zigs"),
                                    [b for b in betes if b.zig])
        self._betes_carte.queue_draw()

    def _remplir_colonne_betes(self, boite, titre: str, betes: list) -> None:
        """Une colonne de bêtes, avec son titre. Vide, elle le dit."""
        entete = Gtk.Label(label=f"{titre} · {len(betes)}", xalign=0.0)
        entete.add_css_class("title-4")
        entete.add_css_class("peuple")
        entete.props.margin_bottom = 4
        boite.append(entete)
        for rang, bete in enumerate(betes):
            ligne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            if rang % 2 == 0:
                ligne.add_css_class("zebre")
            self._pad(ligne)
            nom = Gtk.Label(label=bete.nom or bete.etiquette, xalign=0.0)
            nom.add_css_class("heading")
            ligne.append(nom)
            detail = Gtk.Label(label=self._etat_bete(bete), xalign=0.0, wrap=True)
            detail.add_css_class("dim-label")
            ligne.append(detail)
            boite.append(ligne)
        if not betes:
            vide = Gtk.Label(label=_("aucune"), xalign=0.0)
            vide.add_css_class("dim-label")
            self._pad(vide)
            boite.append(vide)

    @staticmethod
    def _etat_bete(bete) -> str:
        """L'état d'une bête, en français.

        La satiété n'a pas d'échelle documentée — les valeurs relevées vont de
        54 à 933 — donc on la donne telle quelle plutôt que d'inventer un
        pourcentage qui serait faux."""
        lieux = {"landscape": _("dehors"), "stable": _("à l'écurie"),
                 "": _("état inconnu")}
        lieu = lieux.get(bete.statut, bete.statut)
        detail = f"{bete.etiquette} · {lieu}" if bete.nom else lieu
        if bete.satiete > 0:
            detail += _(" · satiété %d") % int(bete.satiete)
        return detail

    def _peindre_carte(self, cr, largeur: float, hauteur: float, zoom: float,
                       glissement: list):
        """Peint la carte d'Atys, agrandie et déplacée, et rend sa pose.

        Rend `(échelle, marge_x, marge_y)` — de quoi placer un point de la carte
        à l'écran — ou None si l'image manque. Partagé par l'écran des bêtes et
        par les cartes de gisements : c'est la même image, la même mise à
        l'échelle et le même découpage.
        """
        if self._betes_pixbuf is None:
            try:
                self._betes_pixbuf = GdkPixbuf.Pixbuf.new_from_file(carte.CHEMIN)
            except GLib.Error:
                return None
        pb = self._betes_pixbuf
        echelle = min(largeur / pb.get_width(),
                      hauteur / pb.get_height()) * zoom
        marge_x = (largeur - pb.get_width() * echelle) / 2 + glissement[0]
        marge_y = (hauteur - pb.get_height() * echelle) / 2 + glissement[1]
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        cr.translate(marge_x, marge_y)
        cr.scale(echelle, echelle)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.paint()
        cr.restore()
        return (echelle, marge_x, marge_y)

    def _marqueur(self, cr, x: float, y: float, texte: str, couleur) -> None:
        """Un point cerné et son nom, lisible sur n'importe quel fond.

        Le blanc cerné de noir sur ses huit côtés : l'or du thème se perd sur
        les zones sableuses, c'est la solution des cartes de toujours.
        """
        for rayon, teinte in ((6.5, self.CERNE), (4.0, couleur)):
            cr.set_source_rgb(*teinte)
            cr.arc(x, y, rayon, 0, 6.2832)
            cr.fill()
        if not texte:
            return
        cr.select_font_face("Sans")
        cr.set_font_size(13)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    cr.set_source_rgb(*self.CERNE)
                    cr.move_to(x + 10 + dx * 1.2, y - 6 + dy * 1.2)
                    cr.show_text(texte)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.move_to(x + 10, y - 6)
        cr.show_text(texte)

    def _dessiner_carte_betes(self, _area, cr, largeur, hauteur) -> None:
        """La carte d'Atys, et les bêtes qui y sont.

        Ce n'est pas une carte de navigation : elle sert à comprendre d'un coup
        d'œil dans quelle région une bête a été laissée."""
        ent = self._entity
        betes = [b for b in getattr(ent, "betes", [])
                 if b.dehors and carte.contient(b.x, b.y)] if ent else []
        # La carte s'affiche aussi quand seul le joueur est plaçable : savoir où
        # l'on est vaut d'être montré, même sans bête dehors.
        if ent is None or (not betes and not carte.contient(ent.x, ent.y)):
            return
        pose = self._peindre_carte(cr, largeur, hauteur, self._betes_zoom,
                                   self._betes_glissement)
        if pose is None:
            return
        echelle, marge_x, marge_y = pose

        # Le joueur d'abord, sous les bêtes : c'est un repère, pas ce qu'on
        # cherche. Sa position est celle de sa dernière déconnexion.
        p = carte.pixel(ent.x, ent.y) if (ent.x or ent.y) else None
        if p is not None:
            jx, jy = marge_x + p[0] * echelle, marge_y + p[1] * echelle
            if 0 <= jx <= largeur and 0 <= jy <= hauteur:
                for rayon, couleur in ((7.0, self.CERNE), (5.5, (1.0, 1.0, 1.0)),
                                       (3.0, self.POINT_JOUEUR)):
                    cr.set_source_rgb(*couleur)
                    cr.arc(jx, jy, rayon, 0, 6.2832)
                    cr.fill()
                cr.select_font_face("Sans")
                cr.set_font_size(13)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx or dy:
                            cr.set_source_rgb(*self.CERNE)
                            cr.move_to(jx + 11 + dx * 1.2, jy - 7 + dy * 1.2)
                            cr.show_text(ent.name)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.move_to(jx + 11, jy - 7)
                cr.show_text(ent.name)

        # Les bêtes trop proches n'en font qu'une : quatre mektoubs attachés
        # ensemble tombent sur le même pixel, et quatre noms superposés ne se
        # lisent plus.
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        groupes: dict[tuple[int, int], list] = {}
        for b in betes:
            p = carte.pixel(b.x, b.y)
            if p is None:
                continue
            px, py = p
            cle = (int((marge_x + px * echelle) / self.SEUIL_GROUPE),
                   int((marge_y + py * echelle) / self.SEUIL_GROUPE))
            groupes.setdefault(cle, []).append(b)
        cr.select_font_face("Sans")
        cr.set_font_size(13)
        for groupe in groupes.values():
            px, py = carte.pixel(groupe[0].x, groupe[0].y)
            x, y = marge_x + px * echelle, marge_y + py * echelle
            # Une cible, pas un anneau : cerne noir, disque blanc, cœur rouge.
            # La carte passe du vert sombre des forêts au sable clair, au rouge
            # du désert et au violet des zones corrompues — aucune teinte unique
            # ne s'y détache partout, mais le contraste noir sur blanc, lui,
            # tient sur tout.
            for rayon, couleur in ((7.0, self.CERNE), (5.5, (1.0, 1.0, 1.0)),
                                   (3.0, self.POINT)):
                cr.set_source_rgb(*couleur)
                cr.arc(x, y, rayon, 0, 6.2832)
                cr.fill()
            nom = groupe[0].nom or groupe[0].etiquette
            if len(groupe) > 1:
                nom += f" +{len(groupe) - 1}"
            # Le nom en blanc, cerné de noir sur ses huit côtés : c'est la
            # solution des cartes de toujours, et la seule qui tienne ici. L'or
            # du thème se perdait sur le sable ; deux décalages en diagonale
            # laissaient le liseré manquant au-dessus et sur les côtés.
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        cr.set_source_rgb(*self.CERNE)
                        cr.move_to(x + 11 + dx * 1.2, y - 7 + dy * 1.2)
                        cr.show_text(nom)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.move_to(x + 11, y - 7)
            cr.show_text(nom)
        cr.restore()

    def _build_meteo_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._meteo_entete = Gtk.Label(xalign=0.0, use_markup=True)
        self._meteo_entete.set_hexpand(True)
        bar.append(self._meteo_entete)

        self._meteo_refresh = Gtk.Button(label=_("Actualiser"))
        self._meteo_refresh.connect("clicked", lambda *a: self._load_meteo(force=True))
        bar.append(self._meteo_refresh)

        self._meteo_courbe = Gtk.DrawingArea()
        self._meteo_courbe.set_content_height(190)
        self._meteo_courbe.set_draw_func(self._dessiner_courbe)
        self._pad(self._meteo_courbe)
        page.append(self._meteo_courbe)

        # Deux colonnes, et **un seul défilement pour tout**. Chacune a d'abord
        # eu le sien, de peur que la colonne de gauche — plus longue — n'entraîne
        # la droite et ne laisse une moitié d'écran vide. À l'usage, deux barres
        # sont pires : on ne sait plus laquelle on tient, et comparer deux
        # tableaux qui glissent séparément demande de les recaler à la main.
        defilement = Gtk.ScrolledWindow()
        defilement.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        defilement.set_vexpand(True)
        dedans = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._pad(dedans)
        defilement.set_child(dedans)

        # Ce qui sort maintenant, en tête et sur toute la largeur : c'est la
        # seule chose de cet écran qui dépende de l'instant, et donc la seule
        # sur laquelle on agit tout de suite.
        self._meteo_pop_titre = Gtk.Label(xalign=0.0)
        self._meteo_pop_titre.add_css_class("title-4")
        self._meteo_pop_titre.add_css_class("peuple")
        dedans.append(self._meteo_pop_titre)
        pop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      homogeneous=True)
        self._meteo_pop_colonnes = []
        # Surtout pas `for _ in range(...)` : `_` est la fonction de traduction,
        # et l'écraser ici la rendrait locale à la méthode — tous les `_("…")`
        # de l'écran météo lèveraient alors une UnboundLocalError au démarrage.
        for _rang in range(self.COLONNES_POP):
            colonne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            self._meteo_pop_colonnes.append(colonne)
            pop.append(colonne)
        dedans.append(pop)

        # Le tableau des suprêmes de la saison a été retiré : « ce qui sort »
        # les donne déjà, et au temps qu'il fait plutôt qu'à la saison entière.
        # Il ne reste que les excellentes : les titres, puis le jour et la nuit
        # côte à côte, puis la note.
        self._meteo_excellentes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                          spacing=2)
        dedans.append(self._meteo_excellentes)

        # Jour à gauche, nuit à droite. L'un sous l'autre, il fallait dérouler
        # la liste de jour pour atteindre celle de nuit — alors que le seul
        # geste utile est de les comparer.
        moments = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                          homogeneous=True)
        self._meteo_jour = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._meteo_nuit = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        moments.append(self._meteo_jour)
        moments.append(self._meteo_nuit)
        dedans.append(moments)

        self._meteo_note = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        dedans.append(self._meteo_note)
        page.append(defilement)

        self._meteo_releve = None      #: ce que l'API a rendu, tel quel
        self._meteo_affiche = None     #: le même, recalé sur l'instant présent
        self._meteo_charge = False
        self._meteo_en_cours = False   #: une requête est-elle en vol ?
        self._meteo_timer = None
        return page

    def _meteo_tick(self) -> bool:
        """Fait avancer l'heure d'Atys, sans rien demander à personne.

        Les cycles reçus couvrent plusieurs heures réelles : tant que le trait
        du « maintenant » reste dans la série, il n'y a aucune raison de
        redemander quoi que ce soit. Quand il approche du bout, on redemande —
        **une fois**, et sans cesser d'avancer pendant ce temps.

        Les deux tenaient dans le même `if`, et c'était le gel : arrivé près du
        bout de la prévision, chaque battement relançait une requête et rendait
        la main sans rien recaler. La courbe s'arrêtait donc net, définitivement
        si l'API ne répondait pas — et une requête partait toutes les dix
        secondes pour rien.
        """
        if self._meteo_releve is None:
            self._meteo_timer = None
            return False
        avance = self._meteo_releve.a_present()
        cycles = avance.cycles_des_primes()
        if (cycles and not self._meteo_en_cours
                and avance.cycle_courant > cycles[-1].cycle - 4):
            self._load_meteo(force=True)
        # Quoi qu'il arrive, on avance : la prévision manquante ne concerne que
        # la droite du graphique, pas le trait du présent.
        self._meteo_affiche = avance
        self._refresh_meteo()
        return True

    def _load_meteo(self, force: bool = False) -> None:
        if self._meteo_charge and not force:
            return
        self._meteo_charge = True
        self._meteo_en_cours = True
        self._meteo_refresh.set_sensitive(False)
        self._meteo_entete.set_text(_("Lecture de la météo…"))

        def work():
            continents = sorted(set(meteo.CONTINENT_DE_ZONE.values()))
            # Quelques cycles déjà écoulés en plus : sans eux la courbe
            # commencerait à l'instant présent, et le trait du « maintenant »
            # se collerait au bord gauche.
            brut = ryzom_api.fetch_weather_json(continents, cycles=20, passes=6)
            releve = meteo.parse_weather(brut)
            # La saison vient d'un autre appel : le flux météo ne la porte pas,
            # et c'est elle qui dit quelle page du relevé regarder.
            try:
                saison = ryzom_api.parse_time(
                    ryzom_api.fetch_time_xml())["season_index"]
            except Exception:                           # noqa: BLE001
                saison = -1
            return meteo.MeteoAtys(releve.cycle_courant, releve.heure_atys,
                                   saison, releve.continents, releve.pris_a)

        def done(res, err):
            self._meteo_en_cours = False
            self._meteo_refresh.set_sensitive(True)
            if err:
                self._meteo_entete.set_text(_("Météo indisponible : %s") % err)
                return
            self._meteo_releve = res
            self._meteo_affiche = res
            self._refresh_meteo()
            # Le temps d'Atys avance tout seul : on ne redemande rien, on
            # recale l'affichage. Toutes les dix secondes, soit un pas de trois
            # heures et vingt d'Atys — le trait glisse au lieu de sauter.
            if self._meteo_timer is None:
                self._meteo_timer = GLib.timeout_add_seconds(
                    10, self._meteo_tick)

        run_async(work, done)

    def _refresh_meteo(self) -> None:
        releve = self._meteo_affiche or self._meteo_releve
        if releve is None:
            return
        maintenant = releve.maintenant()
        if maintenant is not None:
            suite = [c for c in releve.cycles_des_primes()
                     if c.cycle > releve.cycle_courant]
            prochain = next((c for c in suite
                             if c.condition != maintenant.condition), None)
            meilleur = next((c for c in suite if c.condition == "best"), None)
            # Chaque morceau est échappé pour lui-même, et le gras posé ensuite :
            # échapper la phrase entière puis remettre les balises à la main
            # marchait, mais aurait cédé au premier nom de matière contenant un
            # « & ».
            def gras(texte: str) -> str:
                return f"<b>{GLib.markup_escape_text(texte)}</b>"

            def clair(texte: str) -> str:
                return GLib.markup_escape_text(texte)

            morceaux = [
                gras(f"{meteo.texte_meteo(maintenant.text)} · "
                     f"{int(maintenant.value * 100)} %"),
                clair("  →  "),
                gras(meteo.texte_condition(maintenant.condition)),
            ]
            if prochain is not None:
                morceaux.append(clair(
                    f"   {meteo.texte_condition(prochain.condition)} dans "
                    f"{meteo.duree(releve.minutes_avant(prochain.cycle))}"))
            # La fenêtre excellente, sauf si elle est déjà annoncée juste
            # au-dessus : les deux mentions se vaudraient mot pour mot.
            if (maintenant.condition != "best" and meilleur is not None
                    and (prochain is None or meilleur.cycle != prochain.cycle)):
                morceaux.append(clair(
                    "   ✦ Excellente dans "
                    f"{meteo.duree(releve.minutes_avant(meilleur.cycle))}"))
            morceaux.append(clair(
                f"   ·   {meteo.nom_saison(releve.saison)}, "
                f"{releve.heure_du_jour} h sur Atys, "
                f"{'nuit' if releve.nuit else 'jour'}"))
            self._meteo_entete.set_markup("".join(morceaux))
        self._meteo_courbe.queue_draw()

        for colonne in (self._meteo_excellentes, self._meteo_jour,
                        self._meteo_nuit, self._meteo_note,
                        *self._meteo_pop_colonnes):
            while (child := colonne.get_first_child()) is not None:
                colonne.remove(child)
        cle = releve.saison_cle
        saison = meteo.nom_saison(releve.saison)

        # Ce qui sort maintenant, une colonne par zone : l'humidité décide de la
        # condition de gisement, la condition décide de ce qu'on trouve, et le
        # bloc change tout seul à chaque bascule de cycle — sans rien redemander.
        # Les quatre zones des Primes tiennent ainsi sur une seule rangée, ce
        # qu'on demande d'un tableau qu'on lit pour choisir où aller forer.
        actuelle = releve.maintenant()
        if actuelle is None:
            self._meteo_pop_titre.set_text("")
        else:
            self._meteo_pop_titre.set_text(
                _("Suprêmes — ce qui sort : %(condition)s, %(taux)d %%")
                % {"condition": meteo.texte_condition(actuelle.condition),
                   "taux": round(actuelle.value * 100)})
            remplies = [(zone, meteo.pop_de(releve.saison, zone,
                                            actuelle.condition))
                        for zone in meteo.ZONES]
            remplies = [(z, g) for z, g in remplies if g]
            for rang, (zone, groupes) in enumerate(remplies):
                colonne = self._meteo_pop_colonnes[rang % self.COLONNES_POP]
                # Les quatre zones des Primes sont les seules où sortent les
                # suprêmes : c'est cette qualité-là qu'on montre en carte.
                colonne.append(self._bloc_matieres(
                    zone, groupes, rang // self.COLONNES_POP % 2 == 0,
                    qualite="supreme"))

        self._meteo_excellentes.append(self._entete_colonne(_("Cette saison")))
        self._meteo_excellentes.append(
            self._entete_colonne(_("Excellentes — %s") % saison))
        for rang, (moment, groupes) in enumerate(
                armory.EXCELLENTES.get(cle, {}).items()):
            # Il fait nuit sur Atys de 22 h à 3 h : dire laquelle des deux
            # listes vaut en ce moment évite d'aller forer ce qui ne sortira
            # que dans huit heures.
            actuel = (moment == "NUIT") == releve.nuit
            titre = _("De jour") if moment == "JOUR" else _("De nuit")
            if actuel:
                titre += _("  ·  en ce moment")
            # Les deux teintés pareil : côte à côte, un seul des deux le serait
            # ferait croire à une différence de nature, alors qu'ils ne sont que
            # les deux moitiés d'une même journée.
            colonne = (self._meteo_jour if moment == "JOUR"
                       else self._meteo_nuit)
            colonne.append(self._bloc_matieres(titre, groupes, True, actuel,
                                               qualite="excellent"))
        self._meteo_note.append(self._note(
            _("Les Primes partagent une seule météo : celle-ci vaut pour les "
              "quatre zones.")))

    def _entete_colonne(self, titre: str) -> Gtk.Widget:
        label = Gtk.Label(label=titre, xalign=0.0)
        label.add_css_class("title-4")
        label.add_css_class("peuple")
        label.props.margin_bottom = 4
        return label

    def _note(self, texte: str) -> Gtk.Widget:
        label = Gtk.Label(label=texte, xalign=0.0, wrap=True)
        label.add_css_class("dim-label")
        label.props.margin_top = 10
        return label

    def _bloc_matieres(self, titre: str, groupes: dict, zebre: bool,
                       souligne: bool = False,
                       qualite: str = "supreme") -> Gtk.Widget:
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        if zebre:
            boite.add_css_class("zebre")
        self._pad(boite)
        entete = Gtk.Label(label=titre, xalign=0.0)
        entete.add_css_class("heading")
        if souligne:
            entete.add_css_class("fini")
        boite.append(entete)
        grille = Gtk.Grid(column_spacing=12, row_spacing=1)
        for ligne, (groupe, matieres) in enumerate(sorted(groupes.items())):
            # Le nom de la famille, et sous lui son symbole du jeu : une
            # coquille pour la carapace, une goutte pour la sève. Ce sont ceux
            # qu'on a sous les yeux en forant, et l'œil les reconnaît plus vite
            # qu'il ne lit « Carapace ».
            cellule = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            cellule.set_size_request(90, -1)
            g = Gtk.Label(label=groupe, xalign=0.0)
            g.add_css_class("dim-label")
            cellule.append(g)
            chemin = meteo.symbole(groupe)
            if chemin:
                # `Gtk.Image` et non `Gtk.Picture` : la seconde s'étire pour
                # remplir ce qu'on lui donne, et `set_size_request` n'est qu'un
                # **minimum** — d'où des symboles de tailles différentes d'une
                # colonne à l'autre, selon la place laissée par le nom de la
                # famille. `set_pixel_size` fixe la taille pour de bon.
                image = Gtk.Image.new_from_file(chemin)
                image.set_pixel_size(self.TAILLE_SYMBOLE)
                image.set_halign(Gtk.Align.START)
                cellule.append(image)
            grille.attach(cellule, 0, ligne, 1, 1)
            m = Gtk.Label(xalign=0.0, wrap=True)
            m.set_markup(self._matieres_markup(qualite, groupe, matieres))
            m.connect("activate-link", self._on_gisement)
            grille.attach(m, 1, ligne, 1, 1)
        boite.append(grille)
        return boite

    @staticmethod
    def _matieres_markup(qualite: str, famille: str, matieres: list) -> str:
        """La liste des matières, celles qu'on sait situer devenant des liens.

        Un lien plutôt qu'un bouton : la liste garde son allure de phrase et
        continue de se replier toute seule quand la colonne rétrécit. Une
        matière sans carte reste du texte ordinaire — rien n'invite à cliquer
        sur ce qui ne répondrait pas.
        """
        morceaux = []
        for matiere in matieres:
            texte = GLib.markup_escape_text(matiere)
            if gisements.points(qualite, famille, matiere):
                cible = GLib.markup_escape_text(f"{qualite}|{famille}|{matiere}")
                morceaux.append(f'<a href="{cible}">{texte}</a>')
            else:
                morceaux.append(texte)
        return ", ".join(morceaux)

    def _on_gisement(self, _label, adresse: str) -> bool:
        self._montre_gisement(*adresse.split("|", 2))
        return True         # sinon GTK tente d'ouvrir l'adresse dans un navigateur

    def _montre_gisement(self, qualite: str, famille: str, matiere: str) -> None:
        """Où sort cette matière : nos propres marqueurs sur la carte d'Atys.

        On embarquait les vues rendues par le tracker — trois mégaoctets
        d'images figées. Ballistic Mystix a donné les coordonnées : sept
        kilooctets, notre carte, et un zoom libre. Le nom du lieu est écrit
        aussi, parce qu'un point ne dit pas où aller.
        """
        points = gisements.points(qualite, famille, matiere)
        if not points:
            return
        win = Gtk.Window(title=f"{matiere} — {famille}", transient_for=self)
        win.set_default_size(720, 640)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(boite)

        mot = _("Suprême") if qualite == "supreme" else _("Excellente")
        fourchettes = gisements.humidites(qualite, famille, matiere)
        # Sans espace autour du tiret, et la virgule décimale du français : deux
        # fourchettes doivent tenir sur la ligne du titre.
        humidite = ", ".join(f"{bas:g}–{haut:g} %".replace(".", ",")
                             for bas, haut in fourchettes)
        entete = Gtk.Label(xalign=0.0, wrap=True)
        entete.set_markup(
            f"<b>{GLib.markup_escape_text(mot)}</b>"
            + (f"  ·  {_('humidité')} {GLib.markup_escape_text(humidite)}"
               if humidite else "")
            + f"  ·  {len(points)} "
            + (_("gisements") if len(points) > 1 else _("gisement")))
        boite.append(entete)

        # L'état du zoom vit sur la fenêtre : deux gisements ouverts en même
        # temps ne doivent pas se déplacer ensemble.
        etat = {"zoom": 1.0, "glissement": [0.0, 0.0], "depart": [0.0, 0.0]}
        zone = Gtk.DrawingArea(vexpand=True)
        zone.set_content_height(340)
        zone.set_draw_func(
            lambda _a, cr, l, h: self._dessiner_gisement(cr, l, h, points, etat))

        pincement = Gtk.GestureZoom()
        pincement.connect("scale-changed",
                          lambda g, e: self._gisement_zoom(zone, etat, e,
                                                           pincement=True))
        pincement.connect("end", lambda g, s: self._gisement_pince_fin(etat))
        zone.add_controller(pincement)
        molette = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL)
        molette.connect(
            "scroll",
            lambda c, dx, dy: self._gisement_zoom(
                zone, etat,
                1 / self.PAS_ZOOM if dy > 0 else self.PAS_ZOOM))
        zone.add_controller(molette)
        glisse = Gtk.GestureDrag()
        glisse.connect("drag-update",
                       lambda g, dx, dy: self._gisement_glisse(zone, etat, dx, dy))
        glisse.connect("drag-end",
                       lambda g, dx, dy: etat["depart"].__setitem__(
                           slice(None), list(etat["glissement"])))
        zone.add_controller(glisse)
        boite.append(zone)

        # Les lieux, sans leurs coordonnées : le jeu ne permet pas de taper une
        # position pour y poser un repère — je l'avais cru, Ludo l'a corrigé —
        # et deux nombres qu'on ne peut ni saisir ni recopier nulle part
        # n'apprennent rien. Le nom du lieu, lui, dit où aller.
        # Sur deux colonnes : les gisements vont jusqu'à cinq lieux, et une
        # colonne unique repoussait la ligne d'attribution hors de la fenêtre.
        lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
        grille = Gtk.Grid(column_spacing=24, row_spacing=2)
        grille.set_column_homogeneous(True)
        rangs = (len(lieux) + 1) // 2
        for rang, lieu in enumerate(lieux):
            ligne = Gtk.Label(xalign=0.0)
            ligne.add_css_class("compact")
            ligne.set_text(lieu)
            grille.attach(ligne, rang // rangs, rang % rangs, 1, 1)
        boite.append(grille)

        credit = Gtk.Label(xalign=0.0, wrap=True)
        credit.add_css_class("dim-label")
        credit.add_css_class("caption")
        credit.set_text(_("Positions : relevé de ballisticmystix.net, avec "
                          "l'accord de son auteur"))
        boite.append(credit)

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(boite)
        win.set_child(scroll)
        win.present()

    def _gisement_zoom(self, zone, etat: dict, facteur: float,
                       pincement: bool = False) -> None:
        """Agrandit **autour du centre de la vue**, pas du centre de l'image.

        C'était le défaut : le déplacement restait tel quel pendant que l'image
        grandissait autour de son propre milieu, et la vue partait sur le côté.
        Le déplacement suit maintenant l'agrandissement — ce qui est au centre y
        reste, en agrandissant comme en rapetissant.

        Le pincement rend une échelle absolue depuis le début du geste : on la
        compose avec l'agrandissement qu'on avait alors, sinon le premier
        frémissement des doigts ramenait brutalement à l'échelle 1.
        """
        avant = etat["zoom"]
        if pincement:
            if etat.get("pince_depart") is None:
                etat["pince_depart"] = avant
            apres = etat["pince_depart"] * facteur
        else:
            apres = avant * facteur
        etat["zoom"] = min(self.ZOOM_MAX, max(1.0, apres))
        if etat["zoom"] == avant:
            return
        rapport = etat["zoom"] / avant
        etat["glissement"][0] *= rapport
        etat["glissement"][1] *= rapport
        self._borner_carte(zone, etat["zoom"], etat["glissement"])
        etat["depart"][:] = list(etat["glissement"])
        zone.queue_draw()

    def _gisement_pince_fin(self, etat: dict) -> None:
        """Le geste fini, le prochain repartira de l'agrandissement courant."""
        etat["pince_depart"] = None

    def _borner_carte(self, zone, zoom: float, glissement: list) -> None:
        """Empêche la carte de s'échapper de son cadre.

        Le débord se mesure sur l'image telle qu'elle est dessinée, et non sur
        la largeur du cadre : la carte y tient en boîte aux lettres, et un
        débord calculé sur le cadre laissait la pousser dans le vide.
        """
        if self._betes_pixbuf is None:
            return
        pb = self._betes_pixbuf
        largeur, hauteur = zone.get_width(), zone.get_height()
        if largeur <= 0 or hauteur <= 0:
            return
        echelle = min(largeur / pb.get_width(), hauteur / pb.get_height()) * zoom
        debord_x = max(0.0, (pb.get_width() * echelle - largeur) / 2)
        debord_y = max(0.0, (pb.get_height() * echelle - hauteur) / 2)
        glissement[0] = max(-debord_x, min(debord_x, glissement[0]))
        glissement[1] = max(-debord_y, min(debord_y, glissement[1]))


    def _gisement_glisse(self, zone, etat: dict, dx: float, dy: float) -> None:
        # Agrandie seulement : à l'échelle 1 la carte tient entière dans son
        # cadre, et la déplacer ne montrerait que du vide.
        if etat["zoom"] <= 1.0:
            return
        etat["glissement"][:] = [etat["depart"][0] + dx, etat["depart"][1] + dy]
        self._borner_carte(zone, etat["zoom"], etat["glissement"])
        zone.queue_draw()

    #: Un cran de molette. On agrandit de ce facteur, et on rapetisse de son
    #: **inverse** : avec 1,1 et 0,9, trois crans dans un sens puis trois dans
    #: l'autre laissaient la carte à 97 % de sa taille, et on ne retrouvait
    #: jamais tout à fait la vue qu'on avait.
    PAS_ZOOM = 1.1

    #: Part du cadre que les gisements doivent occuper au premier affichage.
    #:
    #: Les quatre zones des Primes tiennent dans un dixième de la carte du
    #: monde : sans cadrage, on voyait quatre points collés au milieu d'Atys et
    #: leurs noms se chevauchaient. On garde de la marge autour, pour situer la
    #: zone dans le continent plutôt que de la montrer hors contexte.
    CADRAGE_GISEMENT = 0.55

    def _cadre_gisement(self, largeur, hauteur, points, etat) -> None:
        """Cadre la vue sur les gisements, une fois, au premier dessin.

        On ne peut pas le faire à la construction : il faut connaître la taille
        du cadre, et elle n'existe qu'à la mesure."""
        etat["cadre"] = True
        pixels = [carte.pixel(x, y) for x, y, _l in points]
        pixels = [p for p in pixels if p is not None]
        if not pixels:
            return
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        # Un seul gisement n'a pas d'étendue : on lui en donne une, sinon le
        # zoom partirait au maximum sur un point.
        large = max(max(xs) - min(xs), 300.0)
        haute = max(max(ys) - min(ys), 260.0)
        base = min(largeur / carte.LARGEUR, hauteur / carte.HAUTEUR)
        if base <= 0:
            return
        voulue = min(self.CADRAGE_GISEMENT * largeur / large,
                     self.CADRAGE_GISEMENT * hauteur / haute)
        etat["zoom"] = min(self.ZOOM_MAX, max(1.0, voulue / base))
        echelle = base * etat["zoom"]
        debord_x = max(0.0, (carte.LARGEUR * echelle - largeur) / 2)
        debord_y = max(0.0, (carte.HAUTEUR * echelle - hauteur) / 2)
        etat["glissement"][:] = [
            max(-debord_x, min(debord_x, echelle * (carte.LARGEUR / 2 - cx))),
            max(-debord_y, min(debord_y, echelle * (carte.HAUTEUR / 2 - cy))),
        ]
        etat["pince_depart"] = None
        etat["depart"][:] = list(etat["glissement"])

    def _dessiner_gisement(self, cr, largeur, hauteur, points, etat) -> None:
        """La carte d'Atys, et les gisements d'une matière."""
        if not etat.get("cadre"):
            self._cadre_gisement(largeur, hauteur, points, etat)
        pose = self._peindre_carte(cr, largeur, hauteur, etat["zoom"],
                                   etat["glissement"])
        if pose is None:
            return
        echelle, marge_x, marge_y = pose
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        # Les points trop proches n'en font qu'un : deux gisements d'une même
        # zone tombent sur le même pixel à l'échelle 1, et deux noms superposés
        # ne se lisent plus.
        vus = {}
        for x, y, lieu in points:
            p = carte.pixel(x, y)
            if p is None:
                continue
            px, py = marge_x + p[0] * echelle, marge_y + p[1] * echelle
            cle = (int(px / self.SEUIL_GROUPE), int(py / self.SEUIL_GROUPE))
            vus.setdefault(cle, (px, py, lieu, 0))
            ex, ey, elieu, n = vus[cle]
            vus[cle] = (ex, ey, elieu, n + 1)
        for px, py, lieu, n in vus.values():
            if not (-40 <= px <= largeur + 40 and -40 <= py <= hauteur + 40):
                continue
            self._marqueur(cr, px, py, lieu if n == 1 else f"{lieu} ×{n}",
                           self.POINT)
        cr.restore()

    #: Combien de noms par rangée dans l'effectif.
    #:
    #: Six : c'est ce qui tient sur une fenêtre au large, et le zébrage a besoin
    #: d'un nombre fixe — une boîte à flot n'a de rangées que le jour où elle se
    #: dessine, et on ne saurait pas laquelle teinter.
    ROSTER_COLONNES = 6

    #: Ce que la courbe montre, en heures d'Atys, et où s'y tient le présent.
    #:
    #: Vingt-quatre heures d'Atys valent soixante-douze minutes réelles : de
    #: quoi voir une heure d'avance et un bon quart d'heure de passé. Le trait
    #: du présent se tient à un sixième de la largeur — c'est ce qui vient qui
    #: compte, le passé ne sert qu'à comprendre d'où l'on sort. Pas contre le
    #: bord pour autant : on veut voir le palier qu'on quitte.
    #: Minutes réelles entre deux repères d'heure sous le graphique.
    #:
    #: La fenêtre ne couvre que soixante-douze minutes réelles — vingt-quatre
    #: heures d'Atys : à l'heure ronde, il n'y aurait qu'un repère, parfois
    #: zéro. Le quart d'heure en donne quatre ou cinq, assez pour situer un
    #: creux sans encombrer l'axe.
    MINUTES_ENTRE_REPERES = 15

    #: Combien de repères on essaie de poser, de part et d'autre.
    #:
    #: On part d'une heure en arrière pour attraper le passé qui reste visible,
    #: et ceux qui tombent hors de la fenêtre sont simplement écartés.
    PAS_DE_TEMPS = 16

    FENETRE_HEURES = 24.0
    ANCRE = 0.15

    #: Durée de la bascule d'un palier au suivant, en heures d'Atys.
    #:
    #: L'API ne donne qu'une valeur par cycle : le palier, lui, est exact, et
    #: c'est lui qui décide de la condition de gisement. Le temps que met le
    #: taux à passer d'un palier au suivant, en revanche, **n'est pas mesuré**
    #: — l'API n'en dit rien. Une heure d'Atys, soit trois minutes réelles, est
    #: un choix de tracé : le trait vertical laissait croire à une bascule
    #: instantanée, alors que le taux monte et descend graduellement.
    #:
    #: Rien d'autre n'en dépend : les comptes à rebours (« Excellente dans
    #: 22 min ») se calculent sur les cycles, pas sur ce tracé. Même valeur que
    #: dans le portage Android, pour que les deux courbes se ressemblent.
    TRANSITION_HEURES = 1.0

    def _dessiner_courbe(self, _area, cr, largeur, hauteur) -> None:
        """L'humidité dans le temps, **en paliers reliés par des obliques**.

        Une valeur vaut pour tout un cycle — trois heures d'Atys, neuf minutes
        réelles : c'est le palier, et c'est lui qui décide de la condition de
        gisement. Relier simplement les points par des obliques dessinerait des
        crêtes qui n'existent pas, et déplacerait les moments intéressants : la
        fenêtre excellente n'est pas un sommet qu'on rate, c'est un palier qui
        dure.

        La bascule d'un palier au suivant, elle, n'est pas instantanée : le taux
        monte et descend graduellement, et le trait vertical laissait croire au
        contraire. Elle se dessine donc en oblique — voir `TRANSITION_HEURES`,
        qui dit ce qui est mesuré et ce qui ne l'est pas.

        **C'est le graphique qui défile, pas le trait.** Le présent se tient
        près du bord gauche et la courbe glisse dessous, comme un sismographe :
        on garde ainsi toujours la même avance sous les yeux, au lieu de voir
        le trait dériver vers le bord jusqu'à sortir de la vue.

        Les trois traits en pointillé sont les seuils du jeu, qui découpent les
        conditions de gisement ; les deux traits pleins à 30 et 70 % ne sont que
        des graduations, pour situer un taux entre deux seuils écartés de trente
        points. Les bandes sombres sont les nuits d'Atys, que le jeu compte de
        22 h à 3 h.
        """
        releve = self._meteo_affiche or self._meteo_releve
        if releve is None:
            return
        cycles = releve.cycles_des_primes()
        if len(cycles) < 2:
            return

        marge_g, marge_b = 34.0, 20.0
        large = largeur - marge_g
        haut = hauteur - marge_b
        if large <= 0 or haut <= 0:
            return

        # Tout se repère en heures d'Atys, et non en indices de cycle : c'est ce
        # qui permet à la fenêtre de glisser continûment sous un trait fixe.
        gauche = releve.heure_atys - self.ANCRE * self.FENETRE_HEURES

        def x(heure: float) -> float:
            return marge_g + large * (heure - gauche) / self.FENETRE_HEURES

        def y(valeur: float) -> float:
            return haut * (1.0 - min(1.0, max(0.0, valeur)))

        cr.save()
        cr.rectangle(marge_g, 0, large, haut)
        cr.clip()

        # Les nuits, comptées par heure et non par cycle : un cycle de trois
        # heures enjambe volontiers le lever du jour.
        cr.set_source_rgba(1, 1, 1, 0.06)
        premiere = int(gauche) - 1
        for h in range(premiere, int(gauche + self.FENETRE_HEURES) + 2):
            if meteo.est_la_nuit(h % 24):
                cr.rectangle(x(h), 0, large / self.FENETRE_HEURES, haut)
                cr.fill()

        # La courbe et son aire. Un cycle couvre trois heures ; le palier occupe
        # le milieu, et la demi-heure de part et d'autre sert à rejoindre le
        # palier voisin en oblique.
        def parcourir():
            demi = self.TRANSITION_HEURES / 2
            for m in cycles:
                debut = m.cycle * meteo.HEURES_PAR_CYCLE
                yield (x(debut + demi),
                       x(debut + meteo.HEURES_PAR_CYCLE - demi),
                       y(m.value))

        cr.set_source_rgba(0.25, 0.48, 0.41, 0.35)
        cr.move_to(x(cycles[0].cycle * meteo.HEURES_PAR_CYCLE), haut)
        for gx, dx, py in parcourir():
            cr.line_to(gx, py)
            cr.line_to(dx, py)
        cr.line_to(x((cycles[-1].cycle + 1) * meteo.HEURES_PAR_CYCLE), haut)
        cr.close_path()
        cr.fill()

        cr.set_source_rgb(0.35, 0.68, 0.58)
        cr.set_line_width(2.0)
        for gx, dx, py in parcourir():
            cr.line_to(gx, py)
            cr.line_to(dx, py)
        cr.stroke()
        cr.restore()

        cr.select_font_face("Sans")
        cr.set_font_size(10)

        # Deux graduations, plus discrètes que les seuils : elles ne veulent
        # rien dire pour le jeu, elles servent seulement à situer un taux à
        # l'œil entre deux seuils écartés de trente points. Traits pleins et
        # non pointillés, pour qu'on ne les confonde pas avec les seuils.
        # L'application Android les a depuis toujours ; celle-ci ne les avait
        # pas, et les deux courbes ne se lisaient pas pareil.
        cr.set_line_width(1.0)
        for graduation, etiquette in ((0.30, "30"), (0.70, "70")):
            yy = y(graduation)
            cr.set_source_rgba(1, 1, 1, 0.18)
            cr.move_to(marge_g, yy)
            cr.line_to(largeur, yy)
            cr.stroke()
            cr.set_source_rgba(1, 1, 1, 0.35)
            cr.move_to(2, yy - 3)
            cr.show_text(etiquette)

        # Les seuils, par-dessus la courbe, et leur étiquette dans la marge.
        cr.set_dash([4.0, 4.0])
        for seuil, etiquette in zip(meteo.SEUILS, ("16", "50", "83")):
            yy = y(seuil)
            cr.set_source_rgba(0.9, 0.4, 0.4, 0.55)
            cr.move_to(marge_g, yy)
            cr.line_to(largeur, yy)
            cr.stroke()
            cr.set_source_rgba(1, 1, 1, 0.55)
            cr.move_to(2, yy - 3)
            cr.show_text(etiquette)
        cr.set_dash([])

        # Le présent, immobile près du bord gauche.
        px = x(releve.heure_atys)
        cr.set_source_rgb(0.91, 0.76, 0.35)
        cr.set_line_width(2.0)
        cr.move_to(px, 0)
        cr.line_to(px, haut)
        cr.stroke()

        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.set_line_width(1.0)
        cr.move_to(marge_g, haut)
        cr.line_to(largeur, haut)
        cr.stroke()

        # L'heure réelle, tous les quarts d'heure. Une heure d'Atys valant trois
        # minutes, la fenêtre ne couvre que soixante-douze minutes réelles : à
        # l'heure ronde, il n'y aurait qu'un repère, parfois zéro — et à la
        # demie, trois pour une heure entière de prévision.
        maintenant = datetime.now()
        repere = maintenant.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        for _ in range(self.PAS_DE_TEMPS):
            repere += timedelta(minutes=self.MINUTES_ENTRE_REPERES)
            minutes = (repere - maintenant).total_seconds() / 60.0
            atys = releve.heure_atys + minutes / meteo.MINUTES_PAR_HEURE_ATYS
            if not gauche <= atys <= gauche + self.FENETRE_HEURES:
                continue
            # Un trait court sous l'axe, puis l'heure : sans lui, on lit bien
            # l'heure mais on ne sait pas au pixel près où elle tombe.
            cr.set_source_rgba(1, 1, 1, 0.35)
            cr.set_line_width(1.0)
            cr.move_to(x(atys), haut)
            cr.line_to(x(atys), haut + 3)
            cr.stroke()
            cr.set_source_rgba(1, 1, 1, 0.55)
            texte = repere.strftime("%Hh") if repere.minute == 0 \
                else repere.strftime("%Hh%M")
            cr.move_to(min(largeur - 30, max(0.0, x(atys) - 14)), hauteur - 6)
            cr.show_text(texte)

    def _build_skills_page(self) -> Gtk.Widget:
        """L'arbre des compétences : quatre branches qui se plient à tous les
        échelons, avec le niveau et l'avancement du niveau en cours."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._skills_search = Gtk.SearchEntry()
        self._skills_search.set_placeholder_text(_("Rechercher une compétence…"))
        self._skills_search.set_hexpand(True)
        self._skills_search.connect("search-changed", lambda *a: self._refresh_skills())
        bar.append(self._skills_search)

        self._skills_filter = Gtk.DropDown.new_from_strings([_("Tout"), _("En cours")])
        self._skills_filter.set_tooltip_text(
            _("« En cours » ne garde que les niveaux entamés"))
        self._skills_filter.connect("notify::selected", lambda *a: self._refresh_skills())
        bar.append(self._skills_filter)

        # Un seul bouton : son nom dit ce qu'il va faire, et il n'y a jamais
        # qu'une action sensée à proposer.
        self._skills_toggle = Gtk.Button(label=_("Tout déplier"))
        self._skills_toggle.connect("clicked", self._on_skills_toggle_all)
        bar.append(self._skills_toggle)

        self._skills_box = Gtk.ListBox()
        self._skills_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._skills_box.add_css_class("survol")
        self._skills_box.connect("row-activated", self._on_skill_row)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._skills_box)
        page.append(scrolled)

        self._skills_status = Gtk.Label(xalign=0.0)
        self._skills_status.add_css_class("dim-label")
        self._skills_status.props.margin_start = 8
        self._skills_status.props.margin_bottom = 6
        page.append(self._skills_status)

        self._skills_expanded: set[str] = set()
        self._skills_finies: set[str] = set()
        self._skills_tree: list = []
        return page

    def _on_skills_toggle_all(self, _btn) -> None:
        if self._skills_expanded:
            self._skills_expanded = set()
        else:
            self._skills_expanded = {n.skill.code for n in self._skills_tree
                                     if n.has_children}
        self._refresh_skills()

    def _on_skill_row(self, _box, row) -> None:
        code = getattr(row, "_code", "")
        if not code:
            return
        if code in self._skills_expanded:
            self._skills_expanded.discard(code)
        else:
            self._skills_expanded.add(code)
        self._refresh_skills()

    def _entite_en_cache(self, kind: str):
        """La première entité de ce genre, relue du cache disque.

        Sert aux écrans de « Plus » : ils doivent s'ouvrir quelle que soit
        l'entité choisie, y compris au tout premier lancement où rien n'a
        encore été affiché. Le cache est celui qui rend déjà l'application
        consultable hors ligne — **aucun appel réseau ici**.
        """
        for entry in self._entries:
            if entry["kind"] != kind:
                continue
            chemin = entity_xml_path(kind, entry["id"])
            if not os.path.isfile(chemin):
                continue
            try:
                with open(chemin, "rb") as fh:
                    brut = fh.read()
                parse = (ryzom_api.parse_character if kind == KIND_CHARACTER
                         else ryzom_api.parse_guild)
                return parse(brut, self._sheetdb.name)
            except Exception:                           # noqa: BLE001
                continue
        return None

    def _refresh_skills(self) -> None:
        """Redessine l'arbre : ce qui est visible dépend des replis, sauf quand
        une recherche ou un filtre est actif — la liste est alors plate, car
        chercher « épée » et ne rien voir parce que la branche est fermée serait
        absurde."""
        while (child := self._skills_box.get_first_child()) is not None:
            self._skills_box.remove(child)

        # L'arbre s'ouvre quelle que soit l'entité choisie : c'est celui du
        # dernier personnage rencontré. Une guilde n'a pas de compétences, et
        # devoir rebasculer d'entité pour consulter un arbre n'aurait aucun sens.
        ent = self._entity
        ailleurs = False
        if not getattr(ent, "skills", None):
            ent = self._dernier_perso or self._entite_en_cache(KIND_CHARACTER)
            self._dernier_perso = self._dernier_perso or ent
            ailleurs = ent is not None
        skills = getattr(ent, "skills", []) if ent else []
        if not skills:
            self._skills_status.set_text(
                _("Aucun personnage consulté pour l'instant : ouvrez-en un une "
                  "fois, et son arbre restera consultable d'ici. L'API ne donne "
                  "les compétences que pour un personnage, et seulement si la "
                  "clé accorde ce module."))
            self._skills_toggle.set_sensitive(False)
            return
        self._skills_toggle.set_sensitive(True)
        self._skills_de = ent.name if ailleurs else ""

        self._skills_tree = skills_mod.build_tree(skills)
        # Ce qui est monté au maximum, y compris les pères dont tout ce qu'ils
        # portent est fini : c'est ce qu'on cherche en parcourant l'arbre.
        self._skills_finies = skills_mod.finished(self._skills_tree)
        needle = _norm(self._skills_search.get_text().strip())
        en_cours = self._skills_filter.get_selected() == 1
        filtering = bool(needle) or en_cours

        if filtering:
            rows = [n for n in self._skills_tree
                    if (not en_cours or n.skill.progress)
                    and (not needle or needle in _norm(self._names.name(n.skill.code)))]
        else:
            rows = skills_mod.visible(self._skills_tree, self._skills_expanded)

        self._skills_toggle.set_label(
            _("Tout replier") if self._skills_expanded else _("Tout déplier"))
        self._skills_toggle.set_visible(not filtering)

        for index, node in enumerate(rows):
            self._skills_box.append(
                self._skill_row(node, index, filtering))

        montrees = len(rows)
        # Le nom du personnage n'est rappelé que si ce n'est pas celui qu'on
        # regarde : sinon il serait déjà deux fois à l'écran.
        prefixe = f"{self._skills_de} · " if self._skills_de else ""
        self._skills_status.set_text(
            prefixe + _("%d compétences, %d affichées") % (len(skills), montrees))

    def _skill_row(self, node, index: int, filtering: bool) -> Gtk.ListBoxRow:
        racine = node.depth == 0 and not filtering
        row = Gtk.ListBoxRow()
        row._code = node.skill.code if (node.has_children and not filtering) else ""
        row.set_activatable(bool(row._code))
        # Une ligne sur deux teintée, comme les tableaux de l'application
        # Android : sur des colonnes étroites l'œil perd sa ligne.
        if index % 2 == 0:
            row.add_css_class("zebre")

        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        line.props.margin_top = 4
        line.props.margin_bottom = 4
        line.props.margin_end = 8
        # Un cran par échelon, à partir du retrait de la flèche des racines.
        line.props.margin_start = 8 + (0 if filtering else node.depth * 14)

        fleche = Gtk.Label(label=("▾" if node.skill.code in self._skills_expanded
                                  else "▸") if row._code else " ", xalign=0.0)
        fleche.set_size_request(14, -1)
        line.append(fleche)

        nom = Gtk.Label(label=self._names.name(node.skill.code), xalign=0.0)
        nom.set_hexpand(True)
        if racine:
            nom.add_css_class("heading")
        # Toute la ligne au vert quand il n'y a plus rien à monter : c'est ce
        # qui se voit de loin en faisant défiler, et le père compte autant que
        # sa feuille — il plafonne à 100 alors que tout dessous est à 250.
        finie = node.skill.code in self._skills_finies
        if finie:
            nom.add_css_class("fini")
        line.append(nom)

        if node.skill.progress:
            barre = Gtk.LevelBar()
            barre.set_min_value(0)
            barre.set_max_value(100)
            barre.set_value(node.skill.progress)
            barre.set_size_request(90, -1)
            barre.set_valign(Gtk.Align.CENTER)
            line.append(barre)

        niveau = Gtk.Label(
            label=(f"{node.skill.level} · {node.skill.progress} %"
                   if node.skill.progress else str(node.skill.level)),
            xalign=1.0)
        niveau.set_size_request(90, -1)
        if finie:
            niveau.add_css_class("fini")
        line.append(niveau)

        if racine:
            points = getattr(self._entity, "skill_points", {}).get(node.skill.code)
            if points:
                # Le niveau d'une racine plafonne bas — Combat vaut 20 : c'est
                # le plus haut de ses descendants qui dit où en est la branche.
                niveau.set_label(str(skills_mod.branch_level(self._skills_tree,
                                                             node.skill.code)))
                detail = Gtk.Label(
                    label=_("%s pts · %s dépensés") % (f"{points[0]:,}".replace(",", " "),
                                                       f"{points[1]:,}".replace(",", " ")),
                    xalign=0.0)
                detail.add_css_class("dim-label")
                detail.add_css_class("caption")
                colonne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                colonne.append(line)
                detail.props.margin_start = 8 + 14
                detail.props.margin_bottom = 4
                colonne.append(detail)
                row.set_child(colonne)
                return row

        row.set_child(line)
        return row

    def _load_log(self) -> None:
        """Relit le journal de l'entité courante depuis le disque."""
        entry = self._current_entry()
        self._log_entries = []
        if entry:
            self._log_entries = movements.load(
                movements_path(entry["kind"], entry["id"]))
        self._refresh_log()

    def _filtered_log(self) -> list:
        needle = _norm(self._log_search.get_text().strip())
        mode = self._log_filter.get_selected()
        out = []
        for mv in self._log_entries:
            if mode == 1 and mv.delta <= 0:
                continue
            if mode == 2 and mv.delta >= 0:
                continue
            if needle:
                hay = _norm(f"{self._names.name(mv.sheet)} {mv.sheet} {mv.inv_label}")
                if needle not in hay:
                    continue
            out.append(mv)
        return out

    #: Taille des icônes du journal, en pixels.
    #:
    #: Vingt-quatre : la hauteur d'une ligne de texte. Plus grand, chaque
    #: mouvement occupait deux lignes et on en voyait deux fois moins d'un
    #: coup d'œil — or le journal se parcourt.
    TAILLE_ICONE_JOURNAL = 24

    def _icone_journal(self, generation: int, image):
        """Pose l'icône si le journal n'a pas été redessiné entre-temps.

        Il l'est à chaque frappe dans la recherche : sans ce garde, une icône
        demandée pour l'ancienne liste viendrait se poser sur la ligne qui a
        pris sa place, et le journal afficherait l'icône du voisin."""
        def arrivee(chemin):
            if generation == self._log_generation and chemin:
                image.set_from_file(chemin)
                image.set_pixel_size(self.TAILLE_ICONE_JOURNAL)
            return False
        return arrivee

    #: L'or du thème, celui d'Android — repris ici pour le balisage Pango,
    #: qui ne sait pas lire une classe CSS.
    OR = "#e8c15a"

    @staticmethod
    def _sans_parenthese(libelle: str) -> str:
        """« Coffre 15 — La Lune Des Maraudeurs(Gh Armure » -> sans la fin.

        Les coffres de guilde portent, après leur nom, ce que la guilde y range
        — et l'API tronque le tout à quarante-quatre signes, si bien que la
        parenthèse ne se referme presque jamais. Ce reste de phrase coupée
        n'apprend rien dans un journal et pousse les colonnes ; le nom du coffre
        suffit à savoir d'où l'objet vient."""
        coupe = libelle.split("(", 1)[0]
        return coupe.strip() or libelle

    def _refresh_log(self) -> None:
        self._log_generation = getattr(self, "_log_generation", 0) + 1
        generation = self._log_generation
        child = self._log_grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._log_grid.remove(child)
            child = nxt

        shown = self._filtered_log()
        # Un trait entre deux journées. Le journal se lit du plus récent au plus
        # ancien, et trois relèves d'affilée y produisent trois paquets de
        # lignes à la même seconde : sans séparation, on ne voyait plus où
        # finissait une journée. Le jour se prend sur les dix premiers signes de
        # l'horodatage — « 2026-08-12 22:44:35 » — plutôt que d'analyser une
        # date pour la recomparer aussitôt.
        row = 0
        jour_precedent = None
        for mv in shown[:self._LOG_PAGE_SIZE]:
            jour = mv.when[:10]
            if jour_precedent is not None and jour != jour_precedent:
                trait = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                trait.add_css_class("separation-jour")
                trait.props.margin_top = 6
                trait.props.margin_bottom = 6
                self._log_grid.attach(trait, 0, row, 6, 1)
                row += 1
            jour_precedent = jour

            when = Gtk.Label(label=mv.when, xalign=0.0, selectable=True)
            when.add_css_class("dim-label")
            when.add_css_class("monospace")
            self._log_grid.attach(when, 0, row, 1, 1)

            where = Gtk.Label(label=self._sans_parenthese(mv.inv_label),
                              xalign=0.0)
            where.add_css_class("dim-label")
            self._log_grid.attach(where, 1, row, 1, 1)

            # Vert pour ce qui entre, rouge pour ce qui sort : la couleur est
            # ce qu'on lit en premier en parcourant une colonne de chiffres.
            qty = Gtk.Label(xalign=1.0)
            qty.set_markup('<span foreground="{}"><tt>{:+d}</tt></span>'.format(
                "#4caf50" if mv.delta > 0 else "#e05252", mv.delta))
            self._log_grid.attach(qty, 2, row, 1, 1)

            name = Gtk.Label(label=self._names.name(mv.sheet), xalign=0.0,
                             selectable=True)
            self._log_grid.attach(name, 3, row, 1, 1)

            # L'icône de l'objet, sur la ligne, juste avant sa qualité : c'est
            # elle qu'on reconnaît en parcourant le journal, bien avant de lire
            # un nom. Elle arrive quand elle arrive — le chargement est en
            # arrière-plan — et une image générique tient la place en attendant,
            # pour que la colonne ne se décale pas à l'arrivée.
            icone = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
            icone.set_pixel_size(self.TAILLE_ICONE_JOURNAL)
            self._log_grid.attach(icone, 4, row, 1, 1)
            self._icons.request(ItemInfo(sheet=mv.sheet, quality=mv.quality),
                                self._icone_journal(generation, icone))

            quality = Gtk.Label(label=f"Q{mv.quality}" if mv.quality else "",
                                xalign=0.0)
            quality.add_css_class("dim-label")
            self._log_grid.attach(quality, 5, row, 1, 1)
            row += 1

        total = len(self._log_entries)
        if not total:
            self._log_status.set_text(
                "Aucun mouvement enregistré. Le journal se remplit à chaque "
                "synchronisation où quelque chose a bougé.")
        elif len(shown) > self._LOG_PAGE_SIZE:
            self._log_status.set_text(
                f"{self._LOG_PAGE_SIZE} lignes affichées sur {len(shown)} "
                f"retenues ({total} au journal) — affinez la recherche.")
        else:
            self._log_status.set_text(f"{len(shown)} lignes sur {total} au journal")

    def _on_page_changed(self, *_args) -> None:
        page = self._stack.get_visible_child_name()
        self._refresh_navigation()
        if page == "log":
            self._load_log()
        elif page == "plus":
            # C'est la sous-page visible qui décide ce qu'il faut charger.
            self._on_plus_changed()

    def _on_log_copy(self, _btn) -> None:
        lines = [movements.describe(mv, self._names.name)
                 for mv in self._filtered_log()]
        if not lines:
            return
        self.get_clipboard().set("\n".join(lines))
        self._log_status.set_text(f"{len(lines)} lignes copiées.")

    def _on_log_clear(self, _btn) -> None:
        entry = self._current_entry()
        if not entry:
            return
        dlg = Gtk.AlertDialog()
        dlg.set_message(_("Vider le journal ?"))
        dlg.set_detail(
            f"Les {len(self._log_entries)} mouvements enregistrés pour "
            f"{entry['name']} seront perdus. L'API ne permet pas de les "
            f"reconstruire.")
        dlg.set_buttons([_("Annuler"), _("Vider")])
        dlg.set_cancel_button(0)
        dlg.set_default_button(0)

        def done(source, result):
            try:
                if source.choose_finish(result) != 1:
                    return
            except GLib.Error:
                return
            movements.clear(movements_path(entry["kind"], entry["id"]))
            self._load_log()

        dlg.choose(self, None, done)

    @staticmethod
    def _pad(widget) -> None:
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            setattr(widget.props, m, 8)

    def _load_names(self, pack_path: str) -> None:
        """Noms lisibles : le pack s'il est là, sinon ce qu'on en avait tiré.

        Le chemin enregistré désigne un fichier de l'installation du jeu, qui
        peut avoir été déplacé depuis. On le cherche alors ailleurs, puis on se
        rabat sur le cache : des noms d'hier valent mieux que des identifiants
        de fiches.
        """
        if pack_path and self._names.load(pack_path):
            if pack_path != self._settings.pack_file:
                self._settings.pack_file = pack_path
            return

        found = detect_pack()
        if found and found != pack_path and self._names.load(found):
            self._settings.pack_file = found
            return

        self._names.load_cache()

    # -------------------------------------------------------- Entités
    def _reload_entities(self, select_id: str | None = None) -> None:
        self._entries = []
        for entry in self._char_store.entries():
            entry = dict(entry, kind=KIND_CHARACTER)
            self._entries.append(entry)
        for entry in self._guild_store.entries():
            entry = dict(entry, kind=KIND_GUILD)
            self._entries.append(entry)

        model = Gtk.StringList()
        for entry in self._entries:
            label = f"{_KIND_PREFIX.get(entry['kind'], '')} {entry['name']}"
            if entry["server"]:
                label += f" ({entry['server']})"
            model.append(label)

        self._entity_dd.handler_block_by_func(self._on_entity_selected)
        self._entity_dd.set_model(model)
        self._entity_dd.handler_unblock_by_func(self._on_entity_selected)

        if self._entries:
            idx = 0
            if select_id:
                for i, e in enumerate(self._entries):
                    if e["id"] == select_id:
                        idx = i
                        break
            self._entity_dd.set_selected(idx)
            self._on_entity_selected(self._entity_dd, None)
        else:
            self._remove_btn.set_sensitive(False)
            self._refresh_btn.set_sensitive(False)
            self._entity = None
            self._alerts = []
            self._update_bell()
            self._populate_inventories()
            self._set_status("Aucune entité — cliquez sur « + » pour ajouter un "
                             "personnage ou une guilde.")

    def _current_entry(self) -> dict | None:
        idx = self._entity_dd.get_selected()
        if 0 <= idx < len(self._entries):
            return self._entries[idx]
        return None

    def _on_entity_selected(self, _dd, _param) -> None:
        entry = self._current_entry()
        if not entry:
            return
        self._remove_btn.set_sensitive(True)
        self._refresh_btn.set_sensitive(True)

        xml_path = entity_xml_path(entry["kind"], entry["id"])
        token = (entry["kind"], entry["id"])

        # Sans cache, la synchronisation est de toute façon obligatoire.
        if not os.path.isfile(xml_path):
            self._synced.add(token)
            self._sync_entity(entry)
            return

        # Avec cache, on l'affiche aussitôt — c'est instantané et cela marche
        # hors ligne — puis on interroge l'API la première fois qu'on ouvre
        # cette entité dans la session. Sans quoi on montrerait des stocks
        # vieux de plusieurs jours sans que rien ne le signale.
        try:
            with open(xml_path, "rb") as fh:
                self._load_entity_from_xml(fh.read(), entry)
        except Exception:
            self._synced.add(token)
            self._sync_entity(entry)
            return

        if self._settings.sync_on_start and token not in self._synced:
            self._synced.add(token)
            self._sync_entity(entry)

    def _on_refresh_clicked(self, _btn) -> None:
        entry = self._current_entry()
        if entry:
            self._sync_entity(entry)

    def _on_remove_clicked(self, _btn) -> None:
        entry = self._current_entry()
        if not entry:
            return
        store = self._char_store if entry["kind"] == KIND_CHARACTER else self._guild_store
        store.remove(entry["id"])
        self._reload_entities()

    def _sync_entity(self, entry: dict) -> None:
        """Récupère le flux API (dans un thread)."""
        self._set_busy(True, f"Synchronisation de {entry['name']}…")
        key = entry["key"]
        kind = entry["kind"]
        fetch = (ryzom_api.fetch_character_xml if kind == KIND_CHARACTER
                 else ryzom_api.fetch_guild_xml)

        def work():
            xml = fetch(key)
            with open(entity_xml_path(kind, entry["id"]), "wb") as fh:
                fh.write(xml)
            time_data = None
            try:  # saison serveur (pour l'alerte de changement de saison)
                time_data = ryzom_api.parse_time(ryzom_api.fetch_time_xml())
            except Exception:
                pass
            return xml, time_data

        def done(result, err):
            self._set_busy(False)
            if err:
                self._set_status(f"Échec de la synchro : {err}")
                return
            xml, time_data = result
            self._load_entity_from_xml(xml, entry, from_sync=True, time_data=time_data)

        run_async(work, done)

    def _load_entity_from_xml(self, xml: bytes, entry: dict, from_sync: bool = False,
                              time_data: dict | None = None) -> None:
        parse = (ryzom_api.parse_character if entry["kind"] == KIND_CHARACTER
                 else ryzom_api.parse_guild)
        try:
            ent = parse(xml, self._sheetdb.name)
        except ApiError as exc:
            self._set_status(f"Erreur : {exc}")
            return
        self._entity = ent
        self._watch = WatchStore(guard_path(entry["kind"], entry["id"]))
        # Le registre suit la guilde affichée. Chaque lecture du flux journalise
        # les arrivées, les départs et les changements de grade : l'API ne rend
        # qu'un effectif, jamais son histoire.
        if ent.kind == KIND_GUILD:
            self._roster_store = roster.RosterStore(data_dir(), ent.entity_id)
            self._roster_store.record(ent.members)
            if ent.members:
                self._derniere_guilde = ent
        else:
            self._roster_store = None
            if ent.skills:
                self._dernier_perso = ent
        self._update_entity_header(ent, entry)
        self._rafraichir_betes_si_visible()
        self._populate_inventories()
        self._check_alerts(ent, entry, from_sync, time_data)
        if self._stack.get_visible_child_name() == "log":
            self._load_log()      # le journal suit l'entité sélectionnée
        elif self._stack.get_visible_child_name() == "plus":
            # Les compétences suivent aussi : un personnage n'a pas l'arbre d'un
            # autre, et une guilde n'en a pas du tout.
            self._skills_expanded = set()
            self._on_plus_changed()

    # -------------------------------------------------------- Inventaires
    def _populate_inventories(self) -> None:
        ent = self._entity
        model = Gtk.StringList()
        if ent:
            for inv in ent.inventories:
                model.append(f"{inv.label} ({len(inv.items)})")
        self._inv_dd.handler_block_by_func(self._on_inventory_selected)
        self._inv_dd.set_model(model)
        self._inv_dd.handler_unblock_by_func(self._on_inventory_selected)
        if ent and ent.inventories:
            self._inv_dd.set_selected(0)
            self._display_inventory(0)
        else:
            self._clear_flow()

    def _on_inventory_selected(self, _dd, _param) -> None:
        idx = self._inv_dd.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self._display_inventory(idx)

    def _display_inventory(self, index: int) -> None:
        ent = self._entity
        if not ent or not (0 <= index < len(ent.inventories)):
            return
        inv = ent.inventories[index]
        self._update_volume_gauge(inv)

        self._generation += 1
        gen = self._generation
        self._clear_flow()
        self._rows = []

        for item in self._sorted(inv.items):
            image = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
            image.set_pixel_size(ICON_SIZE)
            image.set_tooltip_text(self._item_tooltip(item))
            child = Gtk.FlowBoxChild()
            child.set_child(image)
            self._flow.append(child)
            search_key = _norm(f"{self._names.name(item.sheet)} {item.sheet}")
            self._rows.append((child, item, search_key))
            self._icons.request(item, self._make_icon_cb(gen, image))
            gesture = Gtk.GestureClick()
            gesture.set_button(Gdk.BUTTON_SECONDARY)  # clic droit
            gesture.connect("released", self._on_item_right_click, item, image)
            image.add_controller(gesture)
            dclick = Gtk.GestureClick()
            dclick.set_button(Gdk.BUTTON_PRIMARY)     # double-clic gauche
            dclick.connect("released", self._on_item_activate, item)
            image.add_controller(dclick)

        self._apply_filter()

    def _make_icon_cb(self, gen: int, image: Gtk.Image):
        def cb(path):
            if gen != self._generation:
                return False
            if path:
                image.set_from_file(path)
                image.set_pixel_size(ICON_SIZE)
            return False
        return cb

    def _item_tooltip(self, item) -> str:
        # `name()` rend l'identifiant de fiche quand le nom est inconnu : une
        # seule ligne suffit donc, et l'identifiant ne s'affiche qu'à défaut.
        lines = [self._names.name(item.sheet)]
        if item.quality:
            lines.append(f"Qualité : {item.quality}")
        if item.stack:
            lines.append(f"Quantité : {item.stack}")
        if item.item_type == ItemType.EQUIPMENT and item.hp:
            lines.append(f"Durabilité : {item.hp}")
        if item.volume:
            lines.append(f"Volume : {item.volume:.2f}")
        if item.price:
            lines.append(f"Prix : {item.price:,.0f} dappers".replace(",", " "))
        if item.continent:
            lines.append(f"Continent : {item.continent}")
        if item.locked:
            lines.append("🔒 Protégé")
        if self._watch is not None and self._watch.is_watched(item):
            lines.append("👁 Surveillé")
        return "\n".join(lines)

    def _clear_flow(self) -> None:
        child = self._flow.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._flow.remove(child)
            child = nxt

    def _update_volume_gauge(self, inv) -> None:
        total = inv.total_volume
        if inv.capacity > 0:
            pct = total / inv.capacity * 100.0
            self._vol_bar.set_visible(True)
            self._vol_bar.set_value(min(pct, 100.0))
            warn = " ⚠" if pct >= self._settings.volume_threshold else ""
            self._vol_value.set_text(f"{total:.0f} / {inv.capacity}  ({pct:.0f}%){warn}")
        else:
            self._vol_bar.set_visible(False)
            self._vol_value.set_text(f"{total:.0f}  (capacité inconnue)")

    # ------------------------------------------------------------- Filtres
    def _build_filter_popover(self) -> Gtk.Popover:
        self._all_checks: list[Gtk.CheckButton] = []
        pop = Gtk.Popover()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(440)
        scroll.set_propagate_natural_height(True)
        scroll.set_propagate_natural_width(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            setattr(content.props, m, 8)
        scroll.set_child(content)
        pop.set_child(scroll)

        qbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        qbox.append(Gtk.Label(label=_("Qualité")))
        self._qmin = Gtk.SpinButton.new_with_range(0, 500, 10)
        self._qmin.connect("value-changed", lambda *a: self._apply_filter())
        qbox.append(self._qmin)
        qbox.append(Gtk.Label(label=_("à")))
        self._qmax = Gtk.SpinButton.new_with_range(0, 500, 10)
        self._qmax.set_value(500)
        self._qmax.connect("value-changed", lambda *a: self._apply_filter())
        qbox.append(self._qmax)
        content.append(qbox)

        self._locked_only = Gtk.CheckButton(label=_("Cadenas"))
        self._locked_only.connect("toggled", lambda *a: self._apply_filter())
        content.append(self._locked_only)
        self._bonus_only = Gtk.CheckButton(label=_("Avec bonus"))
        self._bonus_only.connect("toggled", lambda *a: self._apply_filter())
        content.append(self._bonus_only)
        self._sale_only = Gtk.CheckButton(label=_("En vente"))
        self._sale_only.connect("toggled", lambda *a: self._apply_filter())
        content.append(self._sale_only)

        content.append(self._check_group("Type d'objet", TYPE_NAMES, self._f_types))
        content.append(self._check_group("Classe", CLASS_NAMES, self._f_classes))
        content.append(self._check_group("Écosystème", ECOSYSTEM_NAMES, self._f_ecosys))
        content.append(self._check_group("Équipement", EQUIP_NAMES, self._f_equips))
        return pop

    def _check_group(self, title: str, names, state_set: set) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        header = Gtk.Label(xalign=0.0)
        header.set_markup(f"<b>{_(title)}</b>")
        header.props.margin_top = 4
        box.append(header)
        for i, name in enumerate(names):
            cb = Gtk.CheckButton(label=_(name))
            cb.set_active(i in state_set)
            cb.connect("toggled", self._on_group_toggle, state_set, i)
            box.append(cb)
            self._all_checks.append(cb)
        return box

    def _on_group_toggle(self, cb, state_set, i) -> None:
        if cb.get_active():
            state_set.add(i)
        else:
            state_set.discard(i)
        self._apply_filter()

    def _apply_filter(self) -> None:
        needle = _norm(self._search.get_text().strip())
        qmin = int(self._qmin.get_value())
        qmax = int(self._qmax.get_value())
        locked_only = self._locked_only.get_active()
        bonus_only = self._bonus_only.get_active()
        sale_only = self._sale_only.get_active()

        visible = 0
        for child, item, search_key in self._rows:
            ok = True
            if needle and needle not in search_key:
                ok = False
            elif not (qmin <= item.quality <= qmax):
                ok = False
            elif int(item.item_type) not in self._f_types:
                ok = False
            elif int(item.ecosystem) not in self._f_ecosys:
                ok = False
            elif int(item.item_class) not in self._f_classes:
                ok = False
            elif (item.item_type == ItemType.EQUIPMENT
                  and int(item.equip) not in self._f_equips):
                ok = False
            elif locked_only and not item.locked:
                ok = False
            elif bonus_only and not (item.hp_buff or item.sap_buff
                                     or item.sta_buff or item.focus_buff):
                ok = False
            elif sale_only and item.expires <= 0:
                ok = False
            child.set_visible(ok)
            if ok:
                visible += 1

        self._update_status()

    def _on_reset_filter(self, _btn) -> None:
        self._search.set_text("")
        self._qmin.set_value(0)
        self._qmax.set_value(500)
        self._locked_only.set_active(False)
        self._bonus_only.set_active(False)
        self._sale_only.set_active(False)
        for cb in getattr(self, "_all_checks", []):
            cb.set_active(True)
        self._sort_dd.set_selected(0)
        self._apply_filter()

    # ------------------------------------------------------------- Tri
    _SORT_KEYS = {
        # Regroupement par famille : catalyseurs ensemble, feux d'artifice
        # ensemble, et les matières réunies par matériau du plus bas niveau au
        # plus haut. Voir sorting.py — le type brut du jeu ne s'y prête pas,
        # la moitié d'un coffre y étant classée « autre ».
        1: lambda self, it: sorting.sort_key(it, _norm(self._names.name(it.sheet))),
        2: lambda self, it: int(it.ecosystem),
        3: lambda self, it: int(it.item_class),
        4: lambda self, it: it.quality,
        5: lambda self, it: it.volume,
        6: lambda self, it: it.stack,
        7: lambda self, it: it.price,
        8: lambda self, it: _norm(self._names.name(it.sheet)),
    }

    def _sorted(self, items):
        keyfn = self._SORT_KEYS.get(self._sort_index)
        if keyfn is None:
            return list(items)
        return sorted(items, key=lambda it: keyfn(self, it), reverse=self._sort_desc)

    def _on_sort_changed(self, _dd, _param) -> None:
        self._sort_index = self._sort_dd.get_selected()
        self._redisplay_current()

    def _on_order_toggle(self, _btn) -> None:
        self._sort_desc = not self._sort_desc
        self._order_btn.set_label("↑" if self._sort_desc else "↓")
        self._redisplay_current()

    def _update_status(self) -> None:
        """Ligne du bas : qui, quel contenant, et de quand datent les données.

        Les décomptes d'items en ont été retirés : la ligne devenait illisible,
        et le nombre figure déjà dans le sélecteur d'inventaire, à côté de
        chaque contenant.
        """
        ent = self._entity
        if not ent:
            return
        idx = self._inv_dd.get_selected()
        inv_label = ""
        if 0 <= idx < len(ent.inventories):
            inv_label = ent.inventories[idx].label
        # Deux lignes plutôt qu'une : qui l'on regarde d'abord, puis dans quoi
        # et de quand. Sur une seule, le nom de l'application venant se centrer
        # au milieu de la barre, la fin — l'heure de synchro — se coupait dès
        # qu'on n'avait pas mille deux cent quatre-vingts pixels de large.
        extra = f" - {ent.guild}" if ent.guild else ""
        line = f"{ent.name}{extra}\n{self._sans_parenthese(inv_label)}"

        # Dater les stocks affichés : sans cela, rien ne distingue une donnée
        # de l'instant d'une donnée vieille de plusieurs jours.
        entry = self._current_entry()
        if entry:
            when = last_sync(entry["kind"], entry["id"])
            line += f" · synchro {format_last_sync(when)}"
            self._refresh_btn.set_tooltip_text(
                _("Resynchroniser depuis l'API") + f"\n{_('Dernière synchro')} : "
                f"{format_last_sync(when)}")
        self._set_status(line)

    # ------------------------------------------------------------- Alertes
    def _check_alerts(self, ent, entry: dict, from_sync: bool,
                      time_data: dict | None = None) -> None:
        result = alerts.volume_alerts(ent, self._settings.volume_threshold)
        if self._watch is not None:
            result += alerts.watch_alerts(ent, self._watch, self._names.name)
        result += alerts.sales_alerts(ent, self._settings.sales_count, self._names.name)
        if from_sync:
            path = snapshot_path(entry["kind"], entry["id"])
            old = alerts.load_snapshot(path)
            new = alerts.build_snapshot(ent)
            if old:
                moves = movements.diff(old, new, ent)
                # Le journal garde la trace, les alertes ne signalent que le coup
                # présent : les deux décrivent les mêmes faits.
                movements.append(movements_path(entry["kind"], entry["id"]), moves)
                result.extend(alerts.movement_alerts(moves, ent, self._names.name))
                if self._stack.get_visible_child_name() == "log":
                    self._load_log()
            alerts.save_snapshot(path, new)
            if time_data:
                season = alerts.season_alert(time_data, self._settings.season_count)
                if season:
                    result.append(season)
        self._alerts = result
        self._update_bell()
        if from_sync and result:
            self._notify(result)

    def _recompute_alerts(self) -> None:
        """Recalcule les alertes (hors mouvements/saison) après un changement
        de surveillance, sans appel réseau."""
        entry = self._current_entry()
        if self._entity and entry:
            self._check_alerts(self._entity, entry, from_sync=False)

    def _redisplay_current(self) -> None:
        idx = self._inv_dd.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self._display_inventory(idx)

    # --------------------------------------- En-tête entité + saison serveur
    @staticmethod
    def _install_motd_css() -> None:
        """La palette de l'application, la même que sur le téléphone.

        L'écran était terne : le portage suivait le thème du système, et les
        deux applications ne se ressemblaient plus que par leur contenu. Les
        couleurs sont donc celles d'Android, à l'octet près — le sarcelle du
        coffre de l'icône, l'or du titre, et le fond bleu-nuit qui les tient.

        **Sobre volontairement.** Le fond reste presque noir et les surfaces
        n'en sont qu'à un cheveu : la couleur ne sert qu'aux accents, aux
        titres et à ce qui se choisit. Un tableau de cent soixante-dix lignes se
        lit longtemps, et un fond teinté fatigue.

        On redéfinit les couleurs nommées d'Adwaita plutôt que de peindre chaque
        widget : les listes, les champs, les menus déroulants et les boîtes de
        dialogue suivent alors tout seuls, y compris ceux qu'on n'a pas écrits.
        Les anciens noms — `theme_bg_color` — sont posés à côté des nouveaux,
        car les deux ont cours selon la version d'Adwaita installée.
        """
        # Le thème sombre est demandé explicitement : la palette est faite pour
        # lui, et sur un bureau réglé en clair les widgets seraient restés
        # blancs sous un fond bleu-nuit.
        # La police du nom, ajoutée au catalogue du processus avant que Pango
        # ne la cherche.
        polices.charger()

        reglages = Gtk.Settings.get_default()
        if reglages is not None:
            reglages.set_property("gtk-application-prefer-dark-theme", True)

        provider = Gtk.CssProvider()
        provider.load_from_data("""
            /* Les cinq couleurs d'Android, telles quelles. */
            @define-color zy_fond        #10171a;   /* background */
            @define-color zy_surface     #172226;   /* surface    */
            @define-color zy_variante    #1e2c31;   /* surfaceVariant */
            @define-color zy_texte       #e2e8e6;   /* onSurface  */
            @define-color zy_texte_faible #bcc8c6;  /* onSurfaceVariant */
            @define-color zy_sarcelle    #3f7a68;   /* primary    */
            @define-color zy_sarcelle_sombre #2b5648;
            @define-color zy_or          #e8c15a;   /* secondary  */
            @define-color zy_erreur      #e2696a;   /* error      */
            /* Les bandes du haut et du bas, un cran sous le fond : elles
               tiennent le tableau entre elles au lieu de s'y fondre. */
            @define-color zy_bande       #0b1113;

            @define-color window_bg_color @zy_fond;
            @define-color window_fg_color @zy_texte;
            @define-color view_bg_color @zy_surface;
            @define-color view_fg_color @zy_texte;
            @define-color card_bg_color @zy_surface;
            @define-color popover_bg_color @zy_surface;
            @define-color popover_fg_color @zy_texte;
            @define-color dialog_bg_color @zy_surface;
            @define-color dialog_fg_color @zy_texte;
            @define-color headerbar_bg_color @zy_bande;
            @define-color headerbar_fg_color @zy_texte;
            @define-color accent_bg_color @zy_sarcelle;
            @define-color accent_fg_color #06120e;
            /* Le sarcelle éclairci : sur du presque noir, celui des aplats
               serait illisible en texte. */
            @define-color accent_color #7fb3a2;
            @define-color destructive_bg_color @zy_erreur;
            @define-color error_color @zy_erreur;
            @define-color success_color #4caf50;

            /* Les mêmes sous leurs anciens noms : selon la version d'Adwaita,
               ce sont les uns ou les autres qui sont consultés. */
            @define-color theme_bg_color @zy_fond;
            @define-color theme_fg_color @zy_texte;
            @define-color theme_base_color @zy_surface;
            @define-color theme_text_color @zy_texte;
            @define-color theme_selected_bg_color @zy_sarcelle;
            @define-color theme_selected_fg_color #06120e;
            @define-color insensitive_fg_color @zy_texte_faible;

            /* **Les couleurs nommées ne suffisent plus.** Depuis GTK 4.16,
               Adwaita n'interroge plus `@define-color` pour son propre fond :
               vérifié à l'octet près sur 4.18, une fenêtre reste grise malgré
               la redéfinition. Les blocs ci-dessus servent encore aux versions
               plus anciennes et aux widgets qui les consultent ; ce qui suit
               peint pour de bon, sélecteur par sélecteur. */

            /* `.background` en plus de `window` : c'est la classe que GTK
               pose sur le nœud effectivement peint, et `window` seul laissait
               le fond gris d'Adwaita — mesuré à (40, 40, 40) au lieu du
               (16, 23, 26) attendu. */
            window, .background { background-color: @zy_fond; color: @zy_texte; }
            headerbar { background: @zy_bande; }
            .barre-etat { background: @zy_bande; padding: 4px 8px; }

            /* Les surfaces où l'on lit : un cheveu au-dessus du fond, pour
               qu'un tableau se détache sans qu'on voie une boîte. */
            scrolledwindow, viewport, listview, list, columnview, textview,
            textview > text, .view {
                background-color: @zy_surface; color: @zy_texte; }
            entry, entry text, spinbutton:not(.vertical) {
                background-color: @zy_variante; color: @zy_texte; }
            popover > contents, popover > arrow, .background.popup {
                background-color: @zy_variante; color: @zy_texte; }

            /* Tout ce qui était bleu passe au sarcelle : la jauge de volume,
               les barres de progression, les cases cochées, ce qui est
               sélectionné. C'est le seul endroit où la couleur est franche. */
            levelbar > trough > block.filled,
            progressbar > trough > progress {
                background-color: @zy_sarcelle; }
            /* `background-image: none` en plus de la couleur : Adwaita peint
               ces cases avec une image, qui l'emporterait sur un simple fond
               et laissait la coche bleue au milieu d'une fenêtre sarcelle. */
            check:checked, check:indeterminate,
            radio:checked, radio:indeterminate, switch:checked {
                background-image: none; background-color: @zy_sarcelle;
                color: #06120e; }
            switch:checked > slider { background-color: @zy_texte; }
            :selected, row:selected, .view:selected {
                background-color: @zy_sarcelle_sombre; color: @zy_texte; }
            button.suggested-action {
                background-image: none; background-color: @zy_sarcelle;
                color: #06120e; }
            button:checked, togglebutton:checked {
                background-image: none; background-color: @zy_sarcelle_sombre;
                color: @zy_texte; }
            entry:focus-within, entry:focus {
                outline-color: @zy_sarcelle; box-shadow: inset 0 0 0 1px @zy_sarcelle; }

            /* Les liens des matières : le bleu d'Adwaita jurait seul dans
               une fenêtre sarcelle et or. Sur Android ils portent la couleur
               primaire, c'est-à-dire le sarcelle — éclairci ici pour rester
               lisible sur presque noir. Le soulignement suffit à dire qu'on
               peut cliquer ; la couleur n'a pas à hurler. */
            link, *:link { color: mix(@zy_sarcelle, white, 0.45); }
            link:hover, *:link:hover { color: mix(@zy_sarcelle, white, 0.65); }
            link:visited, *:link:visited { color: mix(@zy_sarcelle, white, 0.45); }

            /* Le trait entre deux journées du journal : l'or du thème, mais
               à peine — c'est un repère qu'on longe, pas une information à
               lire. Plein plutôt que dégradé : un trait d'un pixel dégradé
               disparaît sur un écran à forte densité. */
            .separation-jour { background-color: alpha(@zy_or, 0.55);
                               min-height: 1px; }

            /* Le nom de l'application : la gothique du titre d'Android, et
               son or. La police est embarquée — voir `zyroom/polices` — car
               elle n'est installée nulle part et le bac à sable ne voit pas
               celles de l'hôte. Si son chargement échouait, `font-family`
               retomberait sur la police courante : laid, mais pas cassé. */
            .nom-appli { font-family: "Pirata One"; font-size: 2.4em;
                         color: @zy_or; padding: 0 18px; }

            .motd { background: @zy_variante;
                    border-radius: 8px; padding: 8px 10px; }
            /* `.zebre` et non `row.zebre` : le zébrage sert aussi aux blocs de
               matières, qui sont des boîtes et non des lignes de liste. Une
               pointe de sarcelle plutôt qu'un gris : c'est ce qui fait la
               différence entre un tableau terne et un tableau habillé. */
            .zebre { background: mix(@zy_surface, @zy_sarcelle, 0.14); }
            /* Le vert de l'application pour ce qui est monté au maximum. */
            .fini { color: mix(@zy_sarcelle, white, 0.35); font-weight: bold; }
            /* L'or du titre et du logo, pour les intitulés de section. */
            .peuple { color: @zy_or; }
            /* Un cran sous le corps courant : trois colonnes doivent tenir
               dans une moitié de fenêtre, et un nom d'avant-poste va jusqu'à
               quarante signes. */
            .compact { font-size: 0.92em; }
            /* Le survol. Ces listes ne se sélectionnent pas — on n'y clique
               rien —, et GTK n'éclaire alors plus la ligne sous le pointeur :
               on perdait sa ligne en traversant un tableau de vingt-neuf
               avant-postes. */
            .survol row:hover { background: alpha(@zy_sarcelle, 0.28); }
            /* Les triangles du registre : la couleur porte le sens, la
               direction le confirme. */
            .tri-arrivee { color: #4caf50; font-weight: bold; }
            .tri-depart  { color: @zy_erreur; font-weight: bold; }
            .tri-grade   { color: @zy_texte; font-weight: bold; }
        """.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _update_entity_header(self, ent, entry) -> None:
        if ent.money:
            try:
                amount = f"{int(ent.money):,}".replace(",", " ")
            except ValueError:
                amount = ent.money
            self._dappers_lbl.set_text(f"💰 {amount} dappers")
        else:
            self._dappers_lbl.set_text("")
        if ent.motd:
            self._motd_lbl.set_text(ent.motd)
            self._motd_box.set_visible(True)
        else:
            self._motd_box.set_visible(False)
        self._load_portrait(ent, entry)

    #: Hauteur du portrait de la barre d'état.
    #:
    #: C'est **elle** qui commande, et non le `set_pixel_size` du widget : le
    #: portrait est posé comme une texture déjà mise à l'échelle, et la taille
    #: du widget ne fait alors que suivre. Quarante-quatre au lieu de
    #: soixante-douze : c'est une signature sous le tableau, pas une
    #: illustration.
    _PORTRAIT_HEIGHT = 44

    def _set_portrait_file(self, path: str) -> None:
        """Affiche le portrait. Un rendu de personnage (image haute, corps
        entier) est recadré en tête/épaules pour un vrai portrait."""
        self._portrait_path = path
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(path)
            w, h = pb.get_width(), pb.get_height()
            # rendu corps entier (nettement plus haut que large) -> tête/épaules
            if h > w * 1.4:
                pb = pb.new_subpixbuf(int(w * 0.25), int(h * 0.02),
                                      int(w * 0.5), int(h * 0.36))
            target = self._PORTRAIT_HEIGHT
            if pb.get_height() != target:
                new_w = max(1, round(pb.get_width() * target / pb.get_height()))
                pb = pb.scale_simple(new_w, target, GdkPixbuf.InterpType.BILINEAR)
            self._portrait.set_from_paintable(Gdk.Texture.new_for_pixbuf(pb))
            self._portrait.set_pixel_size(target)
        except Exception:
            self._portrait.set_from_file(path)
            self._portrait.set_pixel_size(self._PORTRAIT_HEIGHT)

    def _load_portrait(self, ent, entry) -> None:
        self._portrait_gen += 1
        gen = self._portrait_gen
        self._portrait_path = ""
        if not ent.portrait_url:
            self._portrait.set_from_icon_name("avatar-default-symbolic")
            return
        path = portrait_path(entry["kind"], entry["id"], ent.portrait_url)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            self._set_portrait_file(path)
            return
        self._portrait.set_from_icon_name("content-loading-symbolic")
        url = ent.portrait_url

        def work():
            data = ryzom_api.fetch_url(url)
            with open(path, "wb") as fh:
                fh.write(data)
            return path

        def done(p, err):
            if gen != self._portrait_gen:
                return
            if err or not p:
                self._portrait.set_from_icon_name("avatar-default-symbolic")
                return
            self._set_portrait_file(p)

        run_async(work, done)

    def _on_portrait_click(self, _gesture, _n, _x, _y) -> None:
        if not self._portrait_path:
            return
        win = Gtk.Window(title="Portrait", transient_for=self)
        pic = Gtk.Picture.new_for_filename(self._portrait_path)
        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
        pic.set_size_request(200, 400)
        win.set_child(pic)
        win.present()

    def _refresh_season(self) -> None:
        def work():
            return ryzom_api.parse_time(ryzom_api.fetch_time_xml())

        def done(td, err):
            if err or not td:
                return
            h = td["minutes_to_next"] // 60
            text = f"{td['season_name']} · {td['next_season_name']} dans {h} h"
            # L'or du thème, celui des titres : cette ligne dit la saison
            # d'Atys, qui commande tout le reste de l'écran météo.
            self._season_lbl.set_markup(
                f'<span foreground="{self.OR}">'
                f'{GLib.markup_escape_text(text)}</span>')

        run_async(work, done)

    def _refresh_season_tick(self) -> bool:
        self._refresh_season()
        return True  # répéter (toutes les 3 min)

    # ------------------------------------------ Resynchronisation périodique
    def _schedule_sync(self) -> None:
        """(Re)programme la resynchronisation automatique.

        Appelée au démarrage et après un changement d'options, pour prendre en
        compte le nouvel intervalle sans redémarrer.
        """
        if self._sync_timer is not None:
            GLib.source_remove(self._sync_timer)
            self._sync_timer = None

        minutes = self._settings.sync_interval
        if minutes > 0:
            self._sync_timer = GLib.timeout_add_seconds(minutes * 60, self._sync_tick)

    def _sync_tick(self) -> bool:
        """Relève toutes les entités suivies, pas seulement celle qu'on regarde.

        Les journaux — mouvements de coffres, effectif d'une guilde — se
        déduisent de deux instantanés rapprochés. Ne rafraîchir que l'entité
        affichée laissait donc des trous de plusieurs heures dans les autres :
        rester sur son personnage une soirée, puis ouvrir la guilde, et les
        allées et venues de la soirée se résumaient à un seul écart constaté.

        L'entité affichée passe par le chemin ordinaire, qui met l'écran à jour.
        Les autres sont relevées en silence : on écrit leur cache et on
        journalise, sans rien changer à ce qu'on regarde.
        """
        if self._busy:
            return True
        courante = self._current_entry()
        if courante:
            self._sync_entity(courante)
        for entry in list(self._entries):
            if courante and (entry["kind"], entry["id"]) == (courante["kind"],
                                                             courante["id"]):
                continue
            self._relever_en_silence(entry)
        return True

    def _relever_en_silence(self, entry: dict) -> None:
        """Va chercher le flux d'une entité et journalise, sans toucher à l'écran.

        Aucune alerte n'en sort : la cloche parle de ce qu'on regarde, et douze
        notifications au retour d'une soirée ne rendraient service à personne.
        Le journal, lui, garde tout — c'est là qu'on va voir.
        """
        kind, key = entry["kind"], entry["key"]
        fetch = (ryzom_api.fetch_character_xml if kind == KIND_CHARACTER
                 else ryzom_api.fetch_guild_xml)

        def work():
            xml = fetch(key)
            with open(entity_xml_path(kind, entry["id"]), "wb") as fh:
                fh.write(xml)
            parse = (ryzom_api.parse_character if kind == KIND_CHARACTER
                     else ryzom_api.parse_guild)
            ent = parse(xml, self._sheetdb.name)

            # Le journal des mouvements, comme pour l'entité affichée.
            chemin = snapshot_path(kind, entry["id"])
            avant = alerts.load_snapshot(chemin)
            apres = alerts.build_snapshot(ent)
            if avant:
                movements.append(movements_path(kind, entry["id"]),
                                 movements.diff(avant, apres, ent))
            alerts.save_snapshot(chemin, apres)

            # Et le registre du personnel, pour une guilde.
            if kind == KIND_GUILD and ent.members:
                roster.RosterStore(data_dir(), ent.entity_id).record(ent.members)
            return ent.name

        def done(_nom, err):
            # Un échec est sans conséquence : on réessaiera au prochain quart
            # d'heure, et le dire volerait la barre d'état à ce qu'on regarde.
            if err:
                return
            page = self._stack.get_visible_child_name()
            if page == "plus" and self._plus_stack.get_visible_child_name() == "roster":
                self._refresh_roster()

        run_async(work, done)

    # -------------------------------------------- Surveillance par item
    def _on_item_right_click(self, _gesture, _n, x, y, item, image) -> None:
        pop = Gtk.Popover()
        pop.set_parent(image)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            setattr(box.props, m, 4)

        def row(label, handler):
            btn = Gtk.Button(label=label)
            btn.set_has_frame(False)
            btn.set_halign(Gtk.Align.FILL)
            btn.get_child().set_xalign(0.0)
            btn.connect("clicked", handler)
            box.append(btn)

        row("Détails…", lambda *_: (pop.popdown(), self._show_details(item)))
        if item.item_id:
            row("Copier l'identifiant", lambda *_: (pop.popdown(), self._copy_id(item)))
        if self._watch is not None:
            if self._watch.is_watched(item):
                row("Ne plus surveiller", lambda *_: self._on_unwatch(None, item, pop))
            else:
                label = ("Surveiller la durabilité…"
                         if watch_kind(item) == KIND_DURABILITY
                         else "Surveiller la quantité…")
                row(label, lambda *_: self._on_watch(None, item, pop))
        row("Réinitialiser l'icône", lambda *_: (pop.popdown(), self._reset_icon(item)))

        pop.set_child(box)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        pop.set_pointing_to(rect)
        pop.popup()

    def _on_item_activate(self, _gesture, n_press, _x, _y, item) -> None:
        if n_press >= 2:
            self._show_details(item)

    def _show_details(self, item) -> None:
        detail.show_detail(self, item, self._names.name, self._categorydb)

    def _copy_id(self, item) -> None:
        self.get_clipboard().set(item.item_id)
        self._set_status(f"Identifiant copié : {item.item_id}")

    def _reset_icon(self, item) -> None:
        path = self._icons.cached_path(item)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
        self._redisplay_current()

    def _on_watch(self, _btn, item, pop) -> None:
        pop.popdown()
        self._open_watch_dialog(item)

    def _on_unwatch(self, _btn, item, pop) -> None:
        pop.popdown()
        if self._watch is not None:
            self._watch.remove(item)
            self._recompute_alerts()
            self._redisplay_current()

    def _open_watch_dialog(self, item) -> None:
        is_dur = watch_kind(item) == KIND_DURABILITY
        dlg = Gtk.Window(title="Surveiller un objet", transient_for=self, modal=True)
        dlg.set_default_size(420, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.props.margin_top = box.props.margin_bottom = 14
        box.props.margin_start = box.props.margin_end = 14
        dlg.set_child(box)

        name = self._names.name(item.sheet)
        header = Gtk.Label(xalign=0.0)
        header.set_markup(f"<b>{GLib.markup_escape_text(name)}</b> (Q{item.quality})")
        box.append(header)
        box.append(Gtk.Label(
            label=("Alerte si la durabilité descend sous ce seuil :" if is_dur
                   else "Alerte si la quantité descend sous ce seuil :"),
            xalign=0.0, wrap=True))

        spin = Gtk.SpinButton.new_with_range(0, 100000, 1)
        spin.set_value(item.hp if is_dur else item.stack)
        box.append(spin)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Annuler")
        cancel.connect("clicked", lambda *_: dlg.destroy())
        ok = Gtk.Button(label="Surveiller")
        ok.add_css_class("suggested-action")

        def do_ok(*_):
            self._watch.add(item, int(spin.get_value()))
            dlg.destroy()
            self._recompute_alerts()
            self._redisplay_current()

        ok.connect("clicked", do_ok)
        buttons.append(cancel)
        buttons.append(ok)
        box.append(buttons)
        dlg.present()

    def _update_bell(self) -> None:
        n = len(self._alerts)
        self._bell.set_label(f"🔔 {n}" if n else "🔔")
        self._bell.set_sensitive(n > 0)
        self._bell.set_tooltip_text(f"{n} alerte(s)" if n else "Aucune alerte")

    def _on_bell_clicked(self, _btn) -> None:
        dlg = Gtk.Window(title="Alertes", transient_for=self, modal=True)
        dlg.set_default_size(480, 420)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._pad(box)
        dlg.set_child(box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scroll.set_child(listbox)
        box.append(scroll)

        if not self._alerts:
            listbox.append(Gtk.Label(label="Aucune alerte.", xalign=0.0))
        for al in self._alerts:
            icon = "📦" if al.kind == "volume" else "🔄"
            title = Gtk.Label(xalign=0.0)
            title.set_markup(f"{icon} <b>{GLib.markup_escape_text(al.title)}</b>")
            listbox.append(title)
            detail = Gtk.Label(label=al.detail, xalign=0.0, wrap=True)
            detail.add_css_class("dim-label")
            detail.props.margin_start = 18
            listbox.append(detail)

        close = Gtk.Button(label="Fermer", halign=Gtk.Align.END)
        close.connect("clicked", lambda *_: dlg.destroy())
        box.append(close)
        dlg.present()

    def _notify(self, result) -> None:
        try:
            app = self.get_application()
            notif = Gio.Notification.new("ZyRoom — alertes")
            notif.set_body("\n".join(a.title for a in result[:6]))
            app.send_notification("zyroom-alerts", notif)
        except Exception:
            pass

    # ----------------------------------------------- Dialogue « Ajouter »
    def _on_add_clicked(self, _btn) -> None:
        dlg = Gtk.Window(title="Ajouter", transient_for=self, modal=True)
        dlg.set_default_size(480, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(box)
        box.props.margin_top = box.props.margin_bottom = 14
        box.props.margin_start = box.props.margin_end = 14
        dlg.set_child(box)

        # Type : personnage ou guilde
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        rb_char = Gtk.CheckButton(label="Personnage")
        rb_char.set_active(True)
        rb_guild = Gtk.CheckButton(label="Guilde")
        rb_guild.set_group(rb_char)
        type_box.append(rb_char)
        type_box.append(rb_guild)
        box.append(type_box)

        hint = Gtk.Label(xalign=0.0, wrap=True)
        hint.add_css_class("dim-label")
        box.append(hint)

        def update_hint(*_):
            required = (ryzom_api.REQUIRED_MODULES_CHAR if rb_char.get_active()
                        else ryzom_api.REQUIRED_MODULES_GUILD)
            hint.set_text("Clé API sur https://app.ryzom.com/app_ryzomapi "
                          "(modules requis : " + ", ".join(required) + ")")
        update_hint()
        rb_char.connect("toggled", update_hint)

        key_entry = Gtk.Entry(placeholder_text="Clé API")
        box.append(key_entry)
        name_entry = Gtk.Entry(placeholder_text="Nom affiché (optionnel)")
        box.append(name_entry)

        status = Gtk.Label(xalign=0.0, wrap=True)
        box.append(status)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Annuler")
        cancel.connect("clicked", lambda *_: dlg.destroy())
        add = Gtk.Button(label="Ajouter")
        add.add_css_class("suggested-action")
        buttons.append(cancel)
        buttons.append(add)
        box.append(buttons)

        def do_add(*_):
            key = key_entry.get_text().strip()
            if not key:
                status.set_text("Veuillez saisir une clé API.")
                return
            is_char = rb_char.get_active()
            kind = KIND_CHARACTER if is_char else KIND_GUILD
            fetch = (ryzom_api.fetch_character_xml if is_char
                     else ryzom_api.fetch_guild_xml)
            parse = (ryzom_api.parse_character if is_char
                     else ryzom_api.parse_guild)
            required = (ryzom_api.REQUIRED_MODULES_CHAR if is_char
                        else ryzom_api.REQUIRED_MODULES_GUILD)
            store = self._char_store if is_char else self._guild_store

            add.set_sensitive(False)
            cancel.set_sensitive(False)
            status.set_text("Vérification de la clé…")

            def work():
                xml = fetch(key)
                return parse(xml, self._sheetdb.name), xml

            def done(result, err):
                if err:
                    status.set_text(f"Échec : {err}")
                    add.set_sensitive(True)
                    cancel.set_sensitive(True)
                    return
                ent, xml = result
                missing = ryzom_api.check_modules(ent.modules, required)
                if missing:
                    status.set_text("Modules manquants : " + ", ".join(missing))
                    add.set_sensitive(True)
                    cancel.set_sensitive(True)
                    return
                name = name_entry.get_text().strip() or ent.name
                store.save(ent.entity_id, key, name, ent.shard, ent.guild)
                with open(entity_xml_path(kind, ent.entity_id), "wb") as fh:
                    fh.write(xml)
                dlg.destroy()
                self._reload_entities(select_id=ent.entity_id)

            run_async(work, done)

        add.connect("clicked", do_add)
        key_entry.connect("activate", do_add)
        dlg.present()

    # -------------------------------------------- Chargement du pack (noms)
    def _on_pack_clicked(self, _btn) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Choisir string_client.pack")
        dialog.open(self, None, self._on_pack_chosen)

    def _on_pack_chosen(self, dialog, result) -> None:
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path() if gfile else ""
        if path and self._names.load(path):
            self._settings.pack_file = path
            self._set_status(f"Noms chargés depuis {os.path.basename(path)}.")
            # Ré-affiche l'inventaire courant pour rafraîchir noms et recherche
            idx = self._inv_dd.get_selected()
            if idx != Gtk.INVALID_LIST_POSITION:
                self._display_inventory(idx)
        else:
            self._set_status("Impossible de lire ce fichier string_client.pack.")

    # ------------------------------------------------------------- À propos
    def _on_about(self, *_) -> None:
        """L'origine de l'application, et les avis que la licence demande.

        L'AGPL ne se contente pas d'un remerciement : quand un programme qu'elle
        couvre a une interface, celle-ci doit porter le copyright, l'absence de
        garantie, le droit de redistribuer et le moyen de lire la licence. Le
        dépôt et le README le disent déjà — mais un joueur n'ira jamais les
        lire, et c'est à lui que l'obligation s'adresse.

        La filiation est écrite ici : cette application traduit le zyRoom Delphi
        de Misugi. C'est une œuvre dérivée, et l'AGPL interdit d'en effacer la
        paternité d'origine.
        """
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name(APP_NAME)
        about.set_comments(
            "Vos inventaires Ryzom et les coffres de la guilde, hors du jeu.\n"
            "Dérivée du zyRoom de Misugi, écrit en Delphi pour Windows :\n"
            "ZyRoom-GTK en reprend les algorithmes et la lecture de l'API,\n"
            "et hérite donc de sa licence.")
        about.set_copyright("© Misugi pour le zyRoom d'origine\n"
                            "© 2026 Xiom pour ce portage")
        # GTK affiche le texte complet de la licence, celui du dépôt.
        about.set_license_type(Gtk.License.AGPL_3_0)
        about.set_website(DEPOT_SOURCES)
        about.set_website_label("Code source, licence et signalement de défauts")
        about.add_credit_section("Projet d'origine", [DEPOT_ORIGINE])
        # L'adresse est celle que Xiom a choisi de publier. Le dépôt reste le
        # meilleur endroit pour signaler un défaut — il garde une trace, et il
        # est lu par d'autres — mais une adresse permet d'écrire sans compte
        # GitHub, ce que tout le monde n'a pas.
        about.add_credit_section("Écrire à l'auteur", [COURRIEL])
        # Ce qui n'est pas de nous et qu'on embarque. Deux de ces relevés sont
        # sous LGPL, qui **oblige** à nommer leur auteur : ils manquaient ici
        # alors que l'application Android les cite depuis toujours.
        about.add_credit_section("Données et images", [
            "Lettrage : Pirata One, © Rodrigo Fuenzalida et Nicolas Massi,"
            " SIL Open Font License 1.1",
            "Matières suprêmes et excellentes : Ryzom Armory",
            "Noms des avant-postes : RyzomExtra, © Meelis Mägi, GNU LGPL v3",
            "Carte d'Atys : Ryzom Map Tiles, © Meelis Mägi, GNU LGPL v3",
            "Positions des gisements : relevé de ballisticmystix.net,"
            " avec l'accord de son auteur",
            "Symboles des familles et fonds de carte : images du jeu,"
            " © Winch Gate",
        ])
        about.set_logo_icon_name(
            os.environ.get("FLATPAK_ID") or "net.ryzom.zyroomgtk")
        about.present()

    # ---------------------------------------- Menu : options / chatlog / backup
    def _on_options(self, *_):
        OptionsWindow(self, self._settings, self._on_options_saved).present()

    def _apply_proxy(self) -> None:
        s = self._settings
        ryzom_api.configure_proxy(s.proxy_enabled, s.proxy_address, s.proxy_port,
                                  s.proxy_username, s.proxy_password)

    def _on_options_saved(self) -> None:
        self._apply_proxy()
        self._load_names(self._settings.pack_file)
        self._schedule_sync()          # nouvel intervalle, sans redémarrer
        self._redisplay_current()
        self._set_status("Options enregistrées.")

    def _on_chatlog(self, *_):
        dialog = Gtk.FileDialog()
        dialog.set_title("Choisir un fichier de chatlog")
        dialog.open(self, None, self._on_chatlog_chosen)

    def _on_chatlog_chosen(self, dialog, result) -> None:
        try:
            gfile = dialog.open_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path() if gfile else ""
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            self._set_status(f"Impossible de lire le fichier : {exc}")
            return
        lines = chatlog.parse_log(text)
        chatlog.LogWindow(self, lines).present()

    def _on_backup(self, *_):
        folder = self._settings.save_folder or detect_save_folder()
        if not folder:
            self._set_status("Dossier « save » de Ryzom non configuré (voir Options).")
            return
        ok, msg = backup.run_backup(folder)
        self._set_status(("Sauvegarde : " if ok else "") + msg)

    # ------------------------------------------------- Mise à jour de l'app
    def _verifier_maj(self) -> None:
        """Demande au dépôt s'il annonce autre chose que ce qu'on exécute.

        La lecture part dans un fil : le lancement de l'application ne doit pas
        attendre le réseau, et une coupure ne doit pas figer la fenêtre.
        """
        if not self._veilleur.possible:
            return

        def travail():
            return self._veilleur.mise_a_jour_disponible()

        def fini(commit, err):
            if err or not commit:
                return
            self._on_update_available(commit[:12])

        run_async(travail, fini)

    def _verifier_maj_tick(self) -> bool:
        # Une fois le bouton affiché, plus rien à demander : il n'y a pas deux
        # façons d'être en retard, et la mise à jour est déjà proposée.
        if not self._update_btn.get_visible():
            self._verifier_maj()
        return True

    def _on_update_available(self, version: str) -> None:
        if self._update_btn.get_visible():
            return          # le portail et la veille disent la même chose
        self._update_btn.set_visible(True)
        self._update_btn.set_tooltip_text(
            _("Une nouvelle version est disponible") + f" ({version})")
        self._set_status(f"Une nouvelle version est disponible ({version}).")

    def _on_update_clicked(self, _btn) -> None:
        self._update_btn.set_sensitive(False)
        self._set_status("Mise à jour demandée — le système va confirmer.")
        self._updater.update()

    def _on_update_progress(self, message: str, done: bool, failed: bool) -> None:
        self._set_status(message)
        if done:
            # Réussie, le bouton n'a plus lieu d'être. Échouée, on le rend pour
            # permettre un second essai.
            self._update_btn.set_visible(failed)
            self._update_btn.set_sensitive(True)
            if not failed:
                self._proposer_redemarrage()

    def _proposer_redemarrage(self) -> None:
        """Une mise à jour installée ne tourne qu'au prochain lancement.

        On le propose plutôt que de le faire : fermer la fenêtre sous les doigts
        de quelqu'un qui consulte un coffre serait une drôle de façon de le
        remercier d'avoir mis à jour. Le portail sait relancer la version
        fraîche ; s'il refuse, on laisse l'application ouverte en le disant,
        plutôt que de la fermer sans rien relancer.
        """
        dlg = Gtk.AlertDialog()
        dlg.set_message(_("Mise à jour installée"))
        dlg.set_detail(_("Elle ne prendra effet qu'au prochain lancement. "
                         "Relancer maintenant ?"))
        dlg.set_buttons([_("Plus tard"), _("Relancer")])
        dlg.set_default_button(1)
        dlg.set_cancel_button(0)

        def repondu(source, resultat):
            try:
                choix = source.choose_finish(resultat)
            except GLib.Error:
                return
            if choix != 1:
                return
            if self._updater.relancer():
                self.close()
            else:
                self._set_status(
                    _("Impossible de relancer automatiquement : fermez et "
                      "rouvrez l'application pour utiliser la nouvelle version."))

        dlg.choose(self, None, repondu)

    # ------------------------------------------------------------- États
    def _set_busy(self, busy: bool, message: str = "") -> None:
        self._busy = busy
        if busy:
            self._spinner.start()
            if message:
                self._set_status(message)
        else:
            self._spinner.stop()

    def _set_status(self, text: str) -> None:
        self._status.set_text(text)

    def _on_close(self, *_):
        # La taille qu'on retrouvera au prochain lancement. `get_default_size`
        # et non `get_width` : agrandie, la fenêtre doit se souvenir de la
        # taille qu'elle avait avant de l'être, sinon on ne peut plus la
        # réduire qu'à la main.
        self._settings.window_size = self.get_default_size()
        self._settings.window_maximized = self.is_maximized()
        self._icons.shutdown()
        self._updater.close()
        if self._settings.backup_auto:
            folder = self._settings.save_folder or detect_save_folder()
            if folder:
                backup.run_backup(folder)
        return False
