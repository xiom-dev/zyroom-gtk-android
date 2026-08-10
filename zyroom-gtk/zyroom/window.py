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

from . import (alerts, armory, backup, chatlog, detail, i18n, meteo, movements,
               outposts, ryzom_api, sorting)
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
                     ItemType)
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
APP_NAME = ("ZyRoom-GTK-dev-0.8"
            if (os.environ.get("FLATPAK_ID") or "").endswith(".dev")
            else "ZyRoom-GTK-0.7")

#: Signature affichée en bas de la fenêtre principale. Cliquable : elle ouvre
#: l'À propos, où vivent le copyright et la licence.
SIGNATURE = "Original by Misugi, fork by Xiom"

#: Où trouver le code de ce portage, et celui dont il dérive. L'AGPL veut que
#: l'interface dise à qui reçoit l'application où prendre ses sources.
DEPOT_SOURCES = "https://github.com/xiom-dev/zyroom-gtk-android"
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
        self.set_default_size(960, 680)

        self._char_store = EntityStore("characters.ini")
        self._guild_store = EntityStore("guilds.ini")
        self._settings = Settings()
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

        self._bell = Gtk.Button(label="🔔")
        self._bell.set_tooltip_text(_("Alertes"))
        self._bell.set_sensitive(False)
        self._bell.connect("clicked", self._on_bell_clicked)
        header.pack_end(self._bell)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        # Ligne 1 : portrait, sélecteurs d'entité et d'inventaire, dappers
        bar1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar1)
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

        # Onglet « Journal » + bascule dans la barre de titre
        self._stack.add_titled(self._build_log_page(), "log", _("Journal"))
        self._stack.add_titled(self._build_skills_page(), "skills", _("Compétences"))
        self._stack.add_titled(self._build_outposts_page(), "outposts",
                               _("Avant-postes"))
        self._stack.add_titled(self._build_meteo_page(), "meteo", _("Météo"))
        header.set_title_widget(Gtk.StackSwitcher(stack=self._stack))
        self._stack.connect("notify::visible-child-name", self._on_page_changed)

        # Barre d'état : portrait du personnage + texte
        statusbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        statusbar.props.margin_start = 8
        statusbar.props.margin_end = 8
        statusbar.props.margin_bottom = 6
        root.append(statusbar)
        self._portrait = Gtk.Image()
        self._portrait.set_pixel_size(72)
        self._portrait.set_tooltip_text(_("Cliquer pour agrandir"))
        self._portrait_path = ""
        pclick = Gtk.GestureClick()
        pclick.connect("released", self._on_portrait_click)
        self._portrait.add_controller(pclick)
        statusbar.append(self._portrait)
        self._status = Gtk.Label(xalign=0.0, valign=Gtk.Align.END, hexpand=True)
        statusbar.append(self._status)
        self._dappers_lbl = Gtk.Label(label="", valign=Gtk.Align.END)
        statusbar.append(self._dappers_lbl)

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
        signature.props.margin_bottom = 6
        root.append(signature)

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

        self._op_box = Gtk.ListBox()
        self._op_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._op_box)
        page.append(scrolled)

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
        while (child := self._op_box.get_first_child()) is not None:
            self._op_box.remove(child)
        if not self._op_carte:
            return
        if self._op_vue.get_selected() == 1:
            self._remplir_journal_outposts()
        else:
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
        self._op_box.append(self._ligne_simple(entete + ".", dim=True))

        rang = 0
        connus = {c for c, _n in self.PEUPLES}
        for code, nom in self.PEUPLES:
            # Du plus haut niveau au plus bas, comme on lit une carte de
            # conquête : les enjeux d'abord.
            siens = sorted((o for o in carte if o.people == code),
                           key=lambda o: (-o.level, self._names.name(o.name_key)))
            if not siens:
                continue
            self._op_box.append(self._entete_peuple(nom))
            for avant_poste in siens:
                self._op_box.append(self._ligne_outpost(
                    avant_poste, avant_poste.guild == ma_guilde, rang % 2 == 0))
                rang += 1
        orphelins = [o for o in carte if o.people not in connus]
        if orphelins:
            # L'annuaire contient parfois un code qui n'est pas un avant-poste
            # — « #15 ». Le taire ferait un total qui ne tombe pas juste.
            self._op_box.append(self._ligne_simple(
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
        label.props.margin_start = 8
        label.props.margin_bottom = 2
        row.set_child(label)
        return row

    def _ligne_outpost(self, avant_poste, mien: bool, zebre: bool) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        line.props.margin_start = 8
        line.props.margin_end = 8
        line.props.margin_top = 3
        line.props.margin_bottom = 3

        # L'emblème de la guilde, chargé en tâche de fond et mis en cache.
        image = Gtk.Image()
        image.set_pixel_size(20)
        self._icons.request_emblem(
            avant_poste.icon,
            lambda chemin, img=image: img.set_from_file(chemin) if chemin else None)
        line.append(image)

        nom = Gtk.Label(label=self._names.name(avant_poste.name_key), xalign=0.0)
        nom.set_hexpand(True)
        if mien:
            nom.add_css_class("fini")     # le vert de l'application
        line.append(nom)

        niveau = Gtk.Label(label=str(avant_poste.level) if avant_poste.level else "—",
                           xalign=1.0)
        niveau.set_size_request(48, -1)
        niveau.add_css_class("dim-label")
        line.append(niveau)

        guilde = Gtk.Label(label=avant_poste.guild, xalign=1.0)
        guilde.set_size_request(220, -1)
        guilde.set_ellipsize(Pango.EllipsizeMode.END)
        if mien:
            guilde.add_css_class("fini")
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

        self._meteo_box = Gtk.ListBox()
        self._meteo_box.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._meteo_box)
        page.append(scrolled)

        self._meteo_releve = None
        self._meteo_charge = False
        return page

    def _load_meteo(self, force: bool = False) -> None:
        if self._meteo_charge and not force:
            return
        self._meteo_charge = True
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
                                   saison, releve.continents)

        def done(res, err):
            self._meteo_refresh.set_sensitive(True)
            if err:
                self._meteo_entete.set_text(_("Météo indisponible : %s") % err)
                return
            self._meteo_releve = res
            self._refresh_meteo()

        run_async(work, done)

    def _refresh_meteo(self) -> None:
        releve = self._meteo_releve
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

        while (child := self._meteo_box.get_first_child()) is not None:
            self._meteo_box.remove(child)
        cle = releve.saison_cle
        self._meteo_box.append(self._ligne_simple(
            _("Les Primes partagent une seule météo : celle-ci vaut pour les "
              "quatre zones."), dim=True))
        self._meteo_box.append(self._entete_peuple(
            _("Suprêmes — %s") % meteo.nom_saison(releve.saison)))
        for rang, (zone, groupes) in enumerate(armory.SUPREMES.get(cle, {}).items()):
            self._meteo_box.append(self._bloc_matieres(zone, groupes, rang % 2 == 0))
        self._meteo_box.append(self._entete_peuple(
            _("Excellentes — %s") % meteo.nom_saison(releve.saison)))
        for rang, (moment, groupes) in enumerate(armory.EXCELLENTES.get(cle, {}).items()):
            # Il fait nuit sur Atys de 22 h à 3 h : dire laquelle des deux
            # listes vaut en ce moment évite d'aller forer ce qui ne sortira
            # que dans huit heures.
            actuel = (moment == "NUIT") == releve.nuit
            titre = _("De jour") if moment == "JOUR" else _("De nuit")
            if actuel:
                titre += _("  ·  en ce moment")
            self._meteo_box.append(
                self._bloc_matieres(titre, groupes, rang % 2 == 0, actuel))

    def _bloc_matieres(self, titre: str, groupes: dict, zebre: bool,
                       souligne: bool = False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._pad(boite)
        entete = Gtk.Label(label=titre, xalign=0.0)
        entete.add_css_class("heading")
        if souligne:
            entete.add_css_class("fini")
        boite.append(entete)
        grille = Gtk.Grid(column_spacing=12, row_spacing=1)
        for ligne, (groupe, matieres) in enumerate(sorted(groupes.items())):
            g = Gtk.Label(label=groupe, xalign=0.0)
            g.add_css_class("dim-label")
            g.set_size_request(90, -1)
            grille.attach(g, 0, ligne, 1, 1)
            m = Gtk.Label(label=", ".join(matieres), xalign=0.0, wrap=True)
            grille.attach(m, 1, ligne, 1, 1)
        boite.append(grille)
        row.set_child(boite)
        return row

    def _dessiner_courbe(self, _area, cr, largeur, hauteur) -> None:
        """L'humidité dans le temps, **en marches d'escalier**.

        Le jeu ne fait pas varier la météo en continu : une valeur vaut pour
        tout un cycle — trois heures d'Atys, neuf minutes réelles — puis saute
        à la suivante. Relier les points par des obliques dessinerait des
        crêtes qui n'existent pas, et déplacerait les moments intéressants : la
        fenêtre excellente n'est pas un sommet qu'on rate, c'est un palier qui
        dure.

        Les trois traits en pointillé sont les seuils du jeu, qui découpent les
        conditions de gisement ; les bandes sombres sont les nuits d'Atys, que
        le jeu compte de 22 h à 3 h.
        """
        releve = self._meteo_releve
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
        cases = float(len(cycles))

        def x(position: float) -> float:
            return marge_g + large * position / cases

        def y(valeur: float) -> float:
            return haut * (1.0 - min(1.0, max(0.0, valeur)))

        # Les nuits, comptées par heure et non par cycle : un cycle de trois
        # heures enjambe volontiers le lever du jour.
        cr.set_source_rgba(1, 1, 1, 0.06)
        heure0 = cycles[0].cycle * meteo.HEURES_PAR_CYCLE
        par_cycle = 1.0 / meteo.HEURES_PAR_CYCLE
        for h in range(len(cycles) * meteo.HEURES_PAR_CYCLE):
            if meteo.est_la_nuit(int((heure0 + h) % 24)):
                cr.rectangle(x(h * par_cycle), 0, large * par_cycle / cases, haut)
                cr.fill()

        # Les seuils, et leur étiquette.
        cr.set_line_width(1.0)
        cr.set_dash([4.0, 4.0])
        cr.select_font_face("Sans")
        cr.set_font_size(10)
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

        # La courbe en marches, et son aire.
        cr.set_source_rgba(0.25, 0.48, 0.41, 0.35)
        cr.move_to(x(0), haut)
        for i, m in enumerate(cycles):
            cr.line_to(x(i), y(m.value))
            cr.line_to(x(i + 1), y(m.value))
        cr.line_to(x(cases), haut)
        cr.close_path()
        cr.fill()

        cr.set_source_rgb(0.35, 0.68, 0.58)
        cr.set_line_width(2.0)
        for i, m in enumerate(cycles):
            cr.line_to(x(i), y(m.value))
            cr.line_to(x(i + 1), y(m.value))
        cr.stroke()

        # Le trait du « maintenant », posé à l'intérieur du cycle en cours.
        indice = next((i for i, m in enumerate(cycles)
                       if m.cycle == releve.cycle_courant), -1)
        if indice >= 0:
            px = x(indice + releve.avancement_du_cycle)
            cr.set_source_rgb(0.91, 0.76, 0.35)
            cr.move_to(px, 0)
            cr.line_to(px, haut)
            cr.stroke()

        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.move_to(marge_g, haut)
        cr.line_to(largeur, haut)
        cr.stroke()

        # L'heure réelle, à chaque heure ronde : les étiquettes se posent au
        # temps qu'elles annoncent, non au cycle le plus proche — un cycle vaut
        # neuf minutes, et six cycles font cinquante-quatre minutes.
        if indice >= 0:
            cr.set_source_rgba(1, 1, 1, 0.55)
            depart = datetime.now() - timedelta(
                minutes=(indice + releve.avancement_du_cycle) * meteo.MINUTES_PAR_CYCLE)
            heure = (depart.replace(minute=0, second=0, microsecond=0)
                     + timedelta(hours=1))
            total = len(cycles) * meteo.MINUTES_PAR_CYCLE
            while (decalage := (heure - depart).total_seconds() / 60) < total:
                px = min(largeur - 22, max(0.0,
                                           x(decalage / meteo.MINUTES_PAR_CYCLE) - 10))
                cr.move_to(px, hauteur - 6)
                cr.show_text(heure.strftime("%Hh"))
                heure += timedelta(hours=1)

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

    def _refresh_skills(self) -> None:
        """Redessine l'arbre : ce qui est visible dépend des replis, sauf quand
        une recherche ou un filtre est actif — la liste est alors plate, car
        chercher « épée » et ne rien voir parce que la branche est fermée serait
        absurde."""
        while (child := self._skills_box.get_first_child()) is not None:
            self._skills_box.remove(child)

        ent = self._entity
        skills = getattr(ent, "skills", []) if ent else []
        if not skills:
            self._skills_status.set_text(
                _("Aucune compétence : l'API ne les donne que pour un personnage, "
                  "et seulement si la clé accorde ce module."))
            self._skills_toggle.set_sensitive(False)
            return
        self._skills_toggle.set_sensitive(True)

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
        self._skills_status.set_text(
            _("%d compétences, %d affichées") % (len(skills), montrees))

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

    def _refresh_log(self) -> None:
        child = self._log_grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._log_grid.remove(child)
            child = nxt

        shown = self._filtered_log()
        for row, mv in enumerate(shown[:self._LOG_PAGE_SIZE]):
            when = Gtk.Label(label=mv.when, xalign=0.0, selectable=True)
            when.add_css_class("dim-label")
            when.add_css_class("monospace")
            self._log_grid.attach(when, 0, row, 1, 1)

            where = Gtk.Label(label=mv.inv_label, xalign=0.0)
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

            quality = Gtk.Label(label=f"Q{mv.quality}" if mv.quality else "",
                                xalign=0.0)
            quality.add_css_class("dim-label")
            self._log_grid.attach(quality, 4, row, 1, 1)

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
        if page == "log":
            self._load_log()
        elif page == "skills":
            self._refresh_skills()
        # Ces deux-là vont chercher sur le réseau : elles ne le font qu'à la
        # première ouverture de l'onglet, et sur demande ensuite. L'annuaire des
        # guildes pèse un demi-méga-octet, il n'a pas à partir au démarrage.
        elif page == "outposts":
            self._load_outposts()
        elif page == "meteo":
            self._load_meteo()

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
        self._update_entity_header(ent, entry)
        self._populate_inventories()
        self._check_alerts(ent, entry, from_sync, time_data)
        if self._stack.get_visible_child_name() == "log":
            self._load_log()      # le journal suit l'entité sélectionnée
        elif self._stack.get_visible_child_name() == "skills":
            # Les compétences aussi : un personnage n'a pas l'arbre d'un autre,
            # et une guilde n'en a pas du tout.
            self._skills_expanded = set()
            self._refresh_skills()

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
        extra = f" - {ent.guild}" if ent.guild else ""
        line = f"{ent.name}{extra} · {inv_label}"

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
        """Le cadre du message du jour, dans les teintes de la fenêtre.

        Une couleur fixe jurerait avec un thème clair : `@theme_bg_color`
        mélangé de blanc suit celui du système, comme le fait l'encadré de
        l'application Android avec son fond de surface."""
        provider = Gtk.CssProvider()
        provider.load_from_data(
            b".motd { background: mix(@theme_bg_color, @theme_fg_color, 0.13);"
            b" border-radius: 8px; padding: 8px 10px; }"
            b" row.zebre { background: mix(@theme_bg_color, @theme_selected_bg_color, 0.10); }"
            # Le vert de l'application — celui du coffre de l'icône, le même que
            # sur Android — pour ce qui est monté au maximum. Éclairci sur fond
            # sombre, assombri sur fond clair : mélangé au texte du thème, il
            # reste lisible dans les deux sens.
            b" .fini { color: mix(#3f7a68, @theme_fg_color, 0.35); font-weight: bold; }")
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

    _PORTRAIT_HEIGHT = 72

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
        path = portrait_path(entry["kind"], entry["id"])
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
            self._season_lbl.set_markup(
                f'<span foreground="#ffffff">{GLib.markup_escape_text(text)}</span>')

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
        """Rafraîchit l'entité affichée, si l'application n'est pas déjà occupée."""
        entry = self._current_entry()
        if entry and not self._busy:
            self._sync_entity(entry)
        return True

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
            # Réussie, le bouton n'a plus lieu d'être : la version installée
            # n'est reprise qu'au prochain lancement. Échouée, on le rend pour
            # permettre un second essai.
            self._update_btn.set_visible(failed)
            self._update_btn.set_sensitive(True)

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
        self._icons.shutdown()
        self._updater.close()
        if self._settings.backup_auto:
            folder = self._settings.save_folder or detect_save_folder()
            if folder:
                backup.run_backup(folder)
        return False
