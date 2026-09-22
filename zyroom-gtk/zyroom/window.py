"""Fenêtre principale de ZyRoom GTK.

Personnages ET guildes, ajout via clé API, sélection d'inventaire, grille d'items
avec icônes (téléchargées et mises en cache), noms lisibles (string_client.pack)
et barre de recherche/filtres. Les appels réseau se font dans des threads pour
ne pas figer l'interface.
"""
from __future__ import annotations

import os
import re
from datetime import datetime

from gi.repository import (Gdk, GdkPixbuf, GLib, Gio, GObject,
                           Gtk, Pango)

from . import (alerts, backup, carte, chatlog, detail, i18n,
               meteo, movements, outposts, partage, polices, roster, ryzom_api,
               sorting, specialites)
from . import enchantements
from .updater import Updater, Veilleur
from .categorydb import CategoryDb
from .i18n import _
from .config import (CATEGORY_CSV, SHEETID_CSV, EntityStore, data_dir, Settings, detect_pack,
                     detect_save_folder, entity_xml_path, format_api_created,
                     format_last_sync, guard_path, last_sync, movements_path,
                     names_cache_path, noter_erreur, outposts_path,
                     portrait_en_cache, portrait_path, snapshot_path)
from .attente import BarreAttente
from .ui_commun import run_async, _norm
from .page_cartes import CartesCommunes
from .page_betes import PageBetes
from .page_gisements import PageGisements
from .page_roster import PageRoster
from .page_outposts import PageOutposts
from .page_meteo import PageMeteo
from .page_skills import PageSkills
from .page_alertes import PageAlertes
from .icons import IconLoader
from .options import OptionsWindow
from .namedb import NameDb
from .models import (CLASS_NAMES, ECOSYSTEM_NAMES, EQUIP_NAMES, TYPE_NAMES,
                     categorie_item, decouper_recherche,
                     ItemInfo, ItemType)
from .ryzom_api import (KIND_CHARACTER, KIND_GUILD, ApiError, Entity)
from .sheetdb import SheetDb
from .watch import WatchStore

ICON_SIZE = 48

#: Intervalle de vérification des mises à jour de l'application, en secondes.
#: Un quart d'heure, comme la resynchronisation : c'est la cadence à laquelle
#: on regarde déjà si quelque chose a changé ailleurs.
MAJ_INTERVALLE = 15 * 60

#: Vrai dans la variante du mainteneur, qui montre les coffres masqués.
_DEV = (os.environ.get("FLATPAK_ID") or "").endswith(".dev")

# Nom affiché, tenu identique à celui des fichiers .desktop des deux variantes.
# Il ne paraît plus dans la barre de titre, occupée par la bascule d'onglets,
# mais bien dans la liste des fenêtres et l'alternateur de tâches.
#
# **Sans numéro de version.** Il en portait un, et l'application changeait donc
# de nom à chaque livraison : deux joueurs de la même guilde ne parlaient pas de
# la même chose, et le menu du bureau donnait une ligne différente chaque
# semaine. Un nom nomme l'application ; le numéro se lit dans l'À propos et dans
# la logithèque, qui savent l'un et l'autre l'afficher à leur place.
APP_NAME = "ZyRoom-GTK(dev)" if _DEV else "ZyRoom-GTK"

#: La part du nom qui va dans la gothique, en bas de la fenêtre : celle qui
#: vient du zyRoom d'origine. Le reste — « -GTK », « -GTK(dev) » — dit la
#: mouture, et s'écrit dans la police du bureau.
NOM_GRAVE = "ZyRoom"

#: Numéro de la variante lancée. Écrit par `livraison.sh`, jamais à la main :
#: c'est `version.properties` qui fait foi.
VERSION = "1.55" if _DEV else "1.18"

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


class LigneJournal(GObject.Object):
    """Un mouvement, tel que le modèle du tableau le porte.

    Le `Gtk.ColumnView` ne travaille pas sur des `Movement` : il lui faut des
    `GObject`, qu'il garde et compare. Cette enveloppe n'ajoute qu'une chose au
    mouvement — le fait qu'il ouvre une journée, d'où le trait qui sépare deux
    jours dans le journal. Le calculer au remplissage plutôt qu'à l'affichage
    évite de comparer chaque ligne à sa voisine à chaque défilement.
    """

    __gtype_name__ = "ZyLigneJournal"

    def __init__(self, mv, ouvre_le_jour: bool) -> None:
        super().__init__()
        self.mv = mv
        self.ouvre_le_jour = ouvre_le_jour


class MainWindow(PageAlertes, PageBetes, PageGisements, PageMeteo,
                 PageOutposts, PageRoster, PageSkills, CartesCommunes,
                 Gtk.ApplicationWindow):
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
        self._rows: list[tuple[Gtk.FlowBoxChild, object, str, str]] = []  # (child, item, clé recherche, catégorie)
        self._generation = 0                 # invalide les callbacks d'icônes obsolètes
        self._portrait_gen = 0               # invalide les portraits obsolètes
        self._alerts: list[alerts.Alert] = []
        self._log_entries: list = []         # journal de l'entité affichée
        self._watch: WatchStore | None = None
        # Le mouvement du tresor rapporte par le dernier releve, garde jusqu'au
        # suivant. Sans cela, l'alerte disparaitrait au premier recalcul sans
        # reseau -- ouvrir les options suffisait a la faire taire.
        self._mouvements_argent: list = []
        # Etat des filtres/tri. Le tri se retrouve comme on l'a laisse : c'est
        # un reglage qu'on pose une fois pour toutes, pas a chaque lancement.
        # Le menu n'existe pas encore -- il sera regle dessus a sa creation.
        self._sort_index, self._sort_desc = self._settings.sort_order
        # **Le filtre par type descend jusqu'a la famille de matiere.** Le
        # type d'item ne connait que le regne -- « Matiere naturelle » couvre
        # la resine comme la graine, l'ecorce comme la fibre. La famille, elle,
        # se lit dans le nom : voir `models.categorie_item`. La liste n'est
        # donc plus figee, elle est refaite a chaque inventaire avec les seules
        # familles qui s'y trouvent.
        self._categories = list(TYPE_NAMES)
        self._cat_rang = {nom: i for i, nom in enumerate(self._categories)}
        self._f_types = set(range(len(self._categories)))
        self._f_ecosys = set(range(len(ECOSYSTEM_NAMES)))
        self._f_classes = set(range(len(CLASS_NAMES)))
        self._f_equips = set(range(len(EQUIP_NAMES)))
        self._f_bonus = set(range(len(specialites.SPECIALITES)))
        #: Le contenant qu'on regarde : ((genre, identifiant), cle du coffre).
        #: Sert a le retrouver quand la releve automatique rebatit la liste.
        self._inv_courant: tuple | None = None

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
        # Ce que le depot publie du journal de guilde, verse sans rien
        # demander. Apres `_reload_entities` : c'est lui qui dit quelles
        # entites suivre.
        self._relire_journaux_publies()
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
        #: Les images posées sur les boutons et les bandeaux, avec la part de
        #: taille que chacune demande : les boutons de zoom les retrouvent là.
        #:
        #: Déclarée ici et non dans la navigation : le message de guilde se
        #: monte avant elle, et y ajoutait son mégaphone dans une liste qui
        #: n'existait pas encore.
        self._images_boutons = []
        #: Les images des boutons d'action de la barre du haut -- l'ajout, le
        #: retrait, la relecture du pack, la resynchronisation. Retenues pour
        #: que `_appliquer_taille_icones_barre` les retaille ensemble.
        self._icones_barre = []

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self._icones_barre.append(add_btn.get_child())
        add_btn.set_tooltip_text(_("Clés API : en ajouter une, relire ou "
                                   "remplacer celles qu'on a"))
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn)

        self._remove_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        self._icones_barre.append(self._remove_btn.get_child())
        self._remove_btn.set_tooltip_text(_("Retirer l'entité sélectionnée"))
        self._remove_btn.connect("clicked", self._on_remove_clicked)
        self._remove_btn.set_sensitive(False)
        header.pack_start(self._remove_btn)

        menu = Gio.Menu()
        menu.append(_("Options…"), "win.options")
        menu.append(_("Analyser un chatlog…"), "win.chatlog")
        menu.append(_("Sauvegarder maintenant"), "win.backup")
        # L'A propos ne se trouvait qu'en cliquant la signature du pied de
        # page -- personne ne devine qu'elle est un bouton. Il est dans le
        # menu de la version Qt depuis toujours, et c'est la qu'on le cherche.
        menu.append(_("À propos…"), "win.apropos")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu_btn.set_tooltip_text(_("Menu"))
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        for name, handler in (("options", self._on_options),
                              ("chatlog", self._on_chatlog),
                              ("backup", self._on_backup),
                              ("apropos", self._on_about)):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", handler)
            self.add_action(act)

        self._refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self._icones_barre.append(self._refresh_btn.get_child())
        self._refresh_btn.set_tooltip_text(_("Resynchroniser depuis l'API"))
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        self._refresh_btn.set_sensitive(False)
        header.pack_end(self._refresh_btn)

        pack_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
        self._icones_barre.append(pack_btn.get_child())
        pack_btn.set_tooltip_text(_("Charger string_client.pack (noms d'items lisibles)"))
        pack_btn.connect("clicked", self._on_pack_clicked)
        header.pack_end(pack_btn)

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
        # **Le remplissage d'un bouton d'icone, et non celui d'un bouton de
        # texte.** La cloche est un emoji pose comme un libelle : Adwaita lui
        # donnait donc les larges marges qu'il reserve aux mots, et le bouton
        # faisait cinquante et un pixels de large quand celui de la version Qt
        # en fait trente-huit -- mesure sur les deux fenetres photographiees
        # cote a cote. Elle n'a pourtant rien d'un mot : c'est un pictogramme,
        # comme l'ajout et le retrait a sa gauche.
        self._bell.add_css_class("cloche")
        self._bell.set_tooltip_text(_("Alertes"))
        self._bell.set_sensitive(False)
        self._bell.connect("clicked", self._on_bell_clicked)
        header.pack_start(self._bell)

        # Le zoom des icones, du cote gauche : il agit sur la grille,
        # comme l'ajout et le retrait agissent sur l'entite. A droite se
        # tient ce qui parle de l'application : synchro, fichier de
        # noms, menu.
        #: Les deux boutons de zoom, retenus pour que le controle de parite
        #: puisse mesurer ce qui les separe.
        self._boutons_zoom = []
        for signe, pas, mot in (("\u2212", -8, _("Réduire les icônes")),
                                ("+", 8, _("Agrandir les icônes"))):
            bouton = Gtk.Button(label=signe)
            bouton.set_tooltip_text(mot)
            bouton.add_css_class("flat")
            # **Un signe plus gros que le texte des autres boutons.** Le moins
            # et le plus sont deux traits maigres au milieu d'une barre pleine
            # d'images : au corps ordinaire, on les cherchait. Voir la regle
            # `button.zoom-icones` de la feuille, ou le facteur est ecrit.
            bouton.add_css_class("zoom-icones")
            bouton.connect("clicked", self._on_zoom_icones, pas)
            header.pack_start(bouton)
            self._boutons_zoom.append(bouton)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # **Pas de barre de defilement horizontale.** Il y en a eu une, pour
        # que la fenetre reste utilisable une fois reduite. A deux cents pour
        # cent elle devenait la regle, et l'on faisait glisser la fenetre
        # entiere pour lire la saison -- qui n'est jamais qu'un mot au bout
        # d'une ligne. La version Qt, elle, refuse simplement de se reduire
        # sous la largeur de son contenu, et l'on voit toujours tout. Rien a
        # ecrire pour cela : c'est ce que GTK fait de lui-meme des qu'on ne
        # lui offre plus de quoi glisser.
        self._racine = root
        self.set_child(root)

        # Ligne 1 : portrait, sélecteurs d'entité et d'inventaire, dappers
        bar1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        # Le même gris sombre qu'en bas : les deux bandes encadrent le tableau.
        bar1.add_css_class("barre-etat")
        self._ligne_entite = bar1
        root.append(bar1)
        bar1.append(Gtk.Label(label=_("Entité :")))
        self._entity_dd = Gtk.DropDown(model=Gtk.StringList())
        # La fabrique dès la création, et non au premier remplissage : une
        # `Gtk.DropDown` neuve en a déjà une — celle qui n'affiche que du
        # texte —, si bien qu'un test « n'en a-t-elle pas ? » ne posait jamais
        # la nôtre, et le sélecteur restait sans image.
        fabrique = Gtk.SignalListItemFactory()
        fabrique.connect("setup", self._entite_setup)
        fabrique.connect("bind", self._entite_bind)
        self._entity_dd.set_factory(fabrique)
        self._entity_dd.connect("notify::selected", self._on_entity_selected)
        bar1.append(self._entity_dd)
        bar1.append(Gtk.Label(label=_("Inventaire :")))
        self._inv_dd = Gtk.DropDown(model=Gtk.StringList())
        # Comme le sélecteur d'entités : une fabrique, sans quoi une
        # `Gtk.DropDown` ne montre que du texte.
        fabrique_inv = Gtk.SignalListItemFactory()
        fabrique_inv.connect("setup", self._entite_setup)
        fabrique_inv.connect("bind", self._contenant_bind)
        self._inv_dd.set_factory(fabrique_inv)
        #: Les clés des contenants affichés, dans l'ordre du modèle : c'est
        #: elle qui dit quelle image poser, et non le libellé traduit.
        self._inv_keys = []
        self._inv_dd.connect("notify::selected", self._on_inventory_selected)
        bar1.append(self._inv_dd)
        # Une barre qui va et vient plutot qu'un cercle : le cercle d'Adwaita
        # fait seize pixels et se perd dans la barre, au point qu'on croyait
        # l'application figee pendant qu'elle attendait l'API.
        #
        # Soixante pixels, et non cent vingt : le curseur d'une barre pulsee
        # occupe la fraction dite par `set_pulse_step`, et rien de plus. Sur
        # une barre longue, ce bloc devient un trait perdu au milieu du vide,
        # qu'on ne voit pas avancer. Courte, avec un curseur d'un cran plus
        # large, le va-et-vient se lit d'un coup d'oeil. La version Qt tient
        # la meme largeur -- deux applications qui se ressemblent.
        # Peinte a la main : la ProgressBar pulsee rebondit au bord, et la
        # renvoyer au depart interrompait son animation interne -- le curseur
        # finissait par se bloquer. Voir `attente.py`, dont la version Qt est
        # le jumeau, nombre pour nombre.
        self._spinner = BarreAttente()
        bar1.append(self._spinner)
        #: Les raisons d'attendre en cours. La barre tient son propre rythme.
        self._attentes = 0
        #: Les icones encore en vol pour la grille affichee.
        self._icones_en_vol = 0
        #: Vrai pendant qu'une mise a jour se telecharge et s'installe.
        self._maj_en_cours = False
        spacer = Gtk.Label(hexpand=True)
        bar1.append(spacer)
        self._season_lbl = Gtk.Label(label="")
        # Sélectionnable à la souris, comme la MOTD. La ligne porte désormais
        # une date et une heure de changement de saison : c'est ce qu'on colle
        # dans le canal de guilde pour donner rendez-vous, et le retaper à la
        # main était le plus sûr moyen de se tromper d'un chiffre.
        self._season_lbl.set_selectable(True)
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
        # Le mégaphone en image, et non en emoji : posé comme du texte, il
        # suivait le corps de la police et non les boutons de zoom — il restait
        # donc plus petit que les autres logos, qui prennent tous la même part.
        # L'image est celle du même emoji, dessinée une fois.
        self._motd_img = Gtk.Image.new_from_file(
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "symboles", "megaphone.png"))
        self._motd_img.set_pixel_size(
            self._settings.icone(self.PART_ICONE_BOUTON))
        self._motd_img.set_valign(Gtk.Align.START)
        self._images_boutons.append((self._motd_img, self.PART_ICONE_BOUTON))
        self._motd_box.append(self._motd_img)
        # Selectionnable : le message de guilde donne des rendez-vous, des
        # noms de lieux et des heures qu'on veut recopier ailleurs plutot
        # que de les retaper.
        self._motd_lbl = Gtk.Label(xalign=0.0, wrap=True, hexpand=True,
                                   selectable=True)
        self._motd_box.append(self._motd_lbl)
        self._motd_box.set_visible(False)
        root.append(self._motd_box)
        self._install_motd_css()
        # Apres la feuille, et non avant : la taille se mesure sur un libelle,
        # dont le corps vient justement d'elle.
        self._appliquer_taille_icones_barre()

        # Deux vues : la grille d'inventaire et le journal des mouvements.
        # Le sélecteur d'entité reste au-dessus, il vaut pour les deux.
        self._stack = Gtk.Stack()
        self._stack.set_vexpand(True)
        # La pile est dans la glissière posée plus haut : c'est elle qui
        # permet à la fenêtre de descendre sous la largeur que réclament les
        # pages.
        inv_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._stack.add_titled(inv_page, "inventory", _("Inventaire"))
        root.append(self._stack)

        # Ligne volume : jauge de remplissage de l'inventaire courant
        barvol = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        barvol.props.margin_start = barvol.props.margin_end = 8
        inv_page.append(barvol)
        barvol.append(Gtk.Label(label=_("Volume :")))
        self._vol_bar = Gtk.LevelBar()
        # Sa classe a elle : le vert des jauges vaut pour toutes -- celles des
        # competences comprises --, et celle-ci seule prend le vert de
        # l'onglet choisi.
        self._vol_bar.add_css_class("volume")
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
        self._search.set_placeholder_text(_("Rechercher : nom, ou qualité (ex. œil 220)"))
        self._search.set_hexpand(True)
        self._search.connect("search-changed", lambda *a: self._apply_filter())
        bar2.append(self._search)

        filter_btn = self._filter_btn = Gtk.MenuButton(label=_("Filtres"))
        filter_btn.set_popover(self._build_filter_popover())
        bar2.append(filter_btn)

        bar2.append(Gtk.Label(label=_("Trier :")))
        self._sort_dd = Gtk.DropDown.new_from_strings(
            [_("Ordre d'origine"), _("Type"), _("Écosystème"), _("Classe"),
             _("Qualité"), _("Volume"), _("Quantité"), _("Prix"), _("Nom")])
        # Un rang relu que le menu ne connait pas -- entree retiree depuis,
        # fichier venu d'ailleurs -- retombe sur le defaut : mieux vaut un tri
        # qui n'est pas celui qu'on avait qu'un menu vide.
        if self._sort_index >= self._sort_dd.get_model().get_n_items():
            self._sort_index = Settings.TRI_DEFAUT[0]
        # Regle avant de brancher le signal : le branchement d'abord ferait
        # appeler `_redisplay_current` sur une fenetre a moitie construite.
        self._sort_dd.set_selected(self._sort_index)
        self._sort_dd.connect("notify::selected", self._on_sort_changed)
        bar2.append(self._sort_dd)
        self._order_btn = Gtk.Button(label="↑" if self._sort_desc else "↓")
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
        # Et une fois, tout de suite : la pile s'ouvre sur l'inventaire sans
        # changer de page, donc sans emettre le signal ci-dessus. Le bouton
        # restait eteint au-dessus de la page qu'il designe, jusqu'au premier
        # aller-retour vers le journal.
        self._refresh_navigation()

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
        #
        # Le nom entier, pas un raccourci : c'est ici qu'on lit à quelle des
        # deux variantes on a affaire, et « ZyRoom » tout court ne le disait
        # pas. Mais en deux polices : la gothique porte « ZyRoom », qui est le
        # nom de l'application d'origine ; « -GTK » et « (dev) » disent de
        # quelle mouture il s'agit, et ce sont des mots d'ingénieur — gravés
        # dans le bois, ils faisaient partie du titre.
        #
        # Les deux morceaux s'alignent sur la ligne d'écriture et non sur le
        # bas de leur boîte : deux polices de tailles différentes posées sur le
        # même bord flotteraient l'une par rapport à l'autre.
        nom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                      valign=Gtk.Align.END)
        nom.add_css_class("nom-appli")
        grave = Gtk.Label(label=NOM_GRAVE, valign=Gtk.Align.BASELINE)
        grave.add_css_class("nom-appli-grave")
        # Coupable — non pour être coupé, ce qui n'arrivera pas, mais pour
        # cesser d'imposer sa largeur : entier, il réclamait 439 pixels que la
        # fenêtre ne pouvait plus rendre en rétrécissant.
        grave.set_ellipsize(Pango.EllipsizeMode.END)
        nom.append(grave)
        mouture = Gtk.Label(label=APP_NAME.removeprefix(NOM_GRAVE),
                            valign=Gtk.Align.BASELINE)
        mouture.add_css_class("nom-appli-mouture")
        # Coupable elle aussi, et pour la même raison : à la taille de la
        # gravure, « -GTK(dev) » interdisait à la fenêtre de descendre sous
        # 1054 pixels de large — plus que ce qu'elle mesure d'ordinaire.
        mouture.set_ellipsize(Pango.EllipsizeMode.END)
        nom.append(mouture)
        statusbar.set_center_widget(nom)

        self._dappers_lbl = Gtk.Label(label="", valign=Gtk.Align.END)
        self._dappers_lbl.add_css_class("dappers")
        # La bourse et la somme, côte à côte : un `Gtk.Label` ne sait pas
        # porter d'image, Pango n'ayant pas de balise pour cela.
        self._bourse_img = Gtk.Image.new_from_file(self.BOURSE)
        self._bourse_img.set_pixel_size(
            self._settings.icone(self.PART_BOURSE))
        self._bourse_img.set_valign(Gtk.Align.END)
        self._bourse_img.set_visible(False)
        somme = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        somme.append(self._bourse_img)
        somme.append(self._dappers_lbl)
        statusbar.set_end_widget(somme)

        # Signature : d'où vient cette application. Pas de traduction, ce sont
        # des noms propres. Cliquable, parce que c'est là qu'on cherche d'où
        # vient un logiciel — et que l'AGPL veut que l'interface porte le
        # copyright, l'absence de garantie et le moyen d'obtenir le code.
        signature = Gtk.Button(label=SIGNATURE)
        signature.set_has_frame(False)
        signature.get_child().add_css_class("dim-label")
        signature.get_child().add_css_class("caption")
        signature.set_tooltip_text(_("À propos de {}").format(APP_NAME))
        signature.connect("clicked", self._on_about)
        signature.props.margin_bottom = 2
        pied.append(signature)

        if not self._names.loaded:
            self._set_status("Astuce : chargez string_client.pack (icône dossier) "
                             "pour afficher les noms d'items.")

    # ------------------------------------------------ Journal des mouvements
    #: La mémoire du journal, en jours. Tout ce qui est plus récent s'affiche,
    #: quel qu'en soit le nombre de lignes.
    #:
    #: Il se coupait a quatre cents lignes, et une guilde active en produit
    #: huit cents en deux jours : on ne voyait donc jamais l'avant-veille.
    #: Une semaine a suivi, puis un mois -- le fichier, lui, gardait deja tout,
    #: c'etait l'affichage qui tronquait.
    #:
    #: **Le mois n'a ete possible qu'avec le tableau.** La grille de widgets
    #: d'avant demandait une seconde entiere pour six mille lignes et quatre-
    #: vingts megaoctets ; le `Gtk.ColumnView` ne peint que le visible et s'en
    #: tire en quarante millisecondes. Sans lui, trente jours auraient rendu le
    #: journal collant a chaque frappe dans la recherche.
    _LOG_JOURS = 30

    #: Ce qu'on montre malgre tout apres un mois calme : une page vide
    #: n'apprend rien, et un petit coffre peut ne bouger qu'une fois par mois.
    _LOG_MINIMUM = 400

    #: Plafond dur, pour un journal qu'on aurait laisse courir.
    #:
    #: Huit mille, comme la version Qt : le coffre le plus actif de Ludo ecrit
    #: cent quatre-vingt-dix-huit lignes par jour, un mois en fait pres de six
    #: mille, et trois mille coupaient donc le mois demande en son milieu.
    #: Le tableau les tient sans effort -- c'est le nombre de lignes retenues
    #: qu'il borne, plus le cout de l'affichage.
    _LOG_MAX = 8000

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

        # **Un tableau, et non plus une grille de widgets.** La grille posait
        # six etiquettes par ligne, toutes construites d'avance : a trois mille
        # lignes cela faisait dix-huit mille widgets, trois cent soixante
        # millisecondes a batir, deux cent vingt a mettre en page et quatre-
        # vingts megaoctets de memoire -- mesure. Le `Gtk.ColumnView` ne peint
        # que ce qu'on voit et recycle ses lignes au defilement : quarante
        # millisecondes et une memoire qui ne bouge pas, a six mille lignes
        # comme a dix mille. C'est ce qui permet au journal de montrer un mois
        # entier au lieu d'une semaine, comme la version Qt avec sa table.
        #
        # Il rend aussi tout ce qu'on avait ecrit a la main : `MultiSelection`
        # fait le clic, le Maj+clic et le Ctrl+clic, et `enable_rubberband` le
        # glisse. Les quatre gestionnaires de gestes et les trois methodes qui
        # tenaient les rangs a jour disparaissent avec la grille.
        self._log_modele = Gio.ListStore(item_type=LigneJournal)
        self._log_choix = Gtk.MultiSelection(model=self._log_modele)
        self._log_vue = Gtk.ColumnView(model=self._log_choix)
        self._log_vue.set_enable_rubberband(True)
        self._log_vue.set_vexpand(True)
        self._log_vue.add_css_class("journal")
        # Les cellules savent a quelle ligne elles servent : c'est ce que le
        # clic droit consulte pour savoir ce qu'on montre du doigt.
        self._log_cellules: dict = {}
        for colonne in self._colonnes_du_journal():
            self._log_vue.append_column(colonne)
        # **La rangee d'en-tetes se cache.** Les titres sont vides -- la grille
        # n'en avait pas, et la table de la version Qt cache les siens --, mais
        # la rangee garde sa hauteur : dix-huit pixels de vide entre la barre
        # de recherche et la premiere ligne, que Qt n'a pas. `Gtk.ColumnView`
        # n'offre pas d'interrupteur ; son premier enfant est cette rangee.
        entetes = self._log_vue.get_first_child()
        if entetes is not None:
            entetes.set_visible(False)

        raccourci = Gtk.ShortcutController()
        raccourci.set_scope(Gtk.ShortcutScope.GLOBAL)
        raccourci.add_shortcut(Gtk.Shortcut(
            trigger=Gtk.ShortcutTrigger.parse_string("<Control>c"),
            action=Gtk.CallbackAction.new(
                lambda *_a: self._copier_journal_choisi())))
        self.add_controller(raccourci)

        scrolled = self._log_defilant = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._log_vue)
        page.append(scrolled)

        self._log_status = Gtk.Label(xalign=0.0)
        self._log_status.add_css_class("dim-label")
        self._log_status.props.margin_start = 8
        self._log_status.props.margin_bottom = 6
        page.append(self._log_status)
        return page

    #: Les six colonnes du journal : leur titre, et ce qu'elles savent faire.
    #:
    #: Le titre reste vide : la grille n'en avait pas, et une ligne d'en-tetes
    #: au-dessus du journal ferait une difference de plus avec la version Qt,
    #: dont la table cache les siens.
    def _colonnes_du_journal(self) -> list:
        colonnes = []
        self._log_colonnes = {}
        for rang, (nom, poser, lier) in enumerate((
                ("date", self._cellule_texte, self._lier_date),
                ("contenant", self._cellule_texte, self._lier_contenant),
                ("quantite", self._cellule_nombre, self._lier_quantite),
                ("objet", self._cellule_texte, self._lier_nom),
                ("icone", self._cellule_image, self._lier_icone),
                ("qualite", self._cellule_texte, self._lier_qualite))):
            fabrique = Gtk.SignalListItemFactory()
            fabrique.connect("setup", poser)
            fabrique.connect("bind", lier)
            fabrique.connect("unbind", self._delier_cellule)
            colonne = Gtk.ColumnViewColumn(title="", factory=fabrique)
            # La derniere prend l'espace libre, comme dans la version Qt : la
            # qualite se pose alors juste apres l'icone, et le vide reste a sa
            # droite.
            colonne.set_expand(nom == "qualite")
            self._log_colonnes[nom] = colonne
            colonnes.append(colonne)
        return colonnes

    #: L'air que le CSS met de chaque cote d'une cellule du journal.
    _AIR_CELLULE = 16

    def _caler_colonnes_journal(self, lignes: list) -> None:
        """Fige la largeur des colonnes sur le contenu du journal entier.

        **Sinon elles bougent toutes seules en défilant.** Un `Gtk.ColumnView`
        ne connaît que les lignes qu'il a réalisées : il cale ses colonnes sur
        ce qui passe à l'écran, et la première ligne plus longue qui arrive les
        élargit — l'œil voit alors le tableau glisser latéralement sans qu'on
        ait rien touché. La grille d'avant ne le faisait pas : elle construisait
        tout, donc mesurait tout.

        La version Qt a rencontré le même écueil et y répond pareil : une seule
        mesure, la dernière ligne posée, puis les colonnes ne bougent plus (voir
        `_rafraichir_journal`, côté Qt).

        **On ne mesure pas six mille textes.** Pour chaque colonne, les dix
        plus longs en signes suffisent : le plus large en pixels est
        forcément parmi eux, et dix mesures Pango coûtent moins d'une
        milliseconde là où six mille en coûteraient cent.
        """
        if not lignes:
            return
        cote = self._cote_icone_journal
        colonnes = {
            "date": [l.mv.when for l in lignes],
            "contenant": [self._sans_parenthese(l.mv.inv_label)
                          for l in lignes],
            "quantite": [f"{l.mv.delta:+,}".replace(",", " ")
                         if l.mv.inv_key == movements.MONEY_KEY
                         else f"{l.mv.delta:+d}" for l in lignes],
            "objet": [_("Dappers") if l.mv.inv_key == movements.MONEY_KEY
                      else self._names.name(l.mv.sheet) for l in lignes],
        }
        for nom, textes in colonnes.items():
            colonne = self._log_colonnes.get(nom)
            if colonne is None:
                continue
            candidats = sorted(set(textes), key=len, reverse=True)[:10]
            largeur = 0
            for texte in candidats:
                mise = self._log_vue.create_pango_layout(texte)
                # **L'horodatage est a chasse fixe.** Mesure avec la police du
                # tableau, il sortait neuf pixels trop etroit et toutes les
                # colonnes suivantes remontaient d'autant : le journal ne se
                # superposait plus a celui de la version Qt.
                if nom == "date":
                    police = mise.get_context().get_font_description().copy()
                    police.set_family("monospace")
                    mise.set_font_description(police)
                largeur = max(largeur, mise.get_pixel_size().width)
            colonne.set_fixed_width(largeur + self._AIR_CELLULE)
        icone = self._log_colonnes.get("icone")
        if icone is not None:
            icone.set_fixed_width(cote + self._AIR_CELLULE)

    # ----------------------------------------------- Les cellules du journal
    def _cellule_texte(self, _fabrique, cellule) -> None:
        etiquette = Gtk.Label(xalign=0.0)
        self._armer_clic_droit(etiquette)
        cellule.set_child(etiquette)

    def _cellule_nombre(self, _fabrique, cellule) -> None:
        etiquette = Gtk.Label(xalign=1.0)
        self._armer_clic_droit(etiquette)
        cellule.set_child(etiquette)

    def _cellule_image(self, _fabrique, cellule) -> None:
        image = Gtk.Image()
        self._armer_clic_droit(image)
        cellule.set_child(image)

    def _armer_clic_droit(self, widget) -> None:
        """Le menu contextuel, pose une fois pour toutes sur la cellule.

        Sur la cellule et non sur le tableau : un `Gtk.ColumnView` ne sait pas
        dire quelle ligne se trouve sous une ordonnee, la ou une cellule, elle,
        connait la sienne. C'est `_log_cellules` qui la retient, tenue a jour a
        chaque `bind` -- les cellules etant recyclees au defilement, celle qui
        servait la ligne 12 sert la 340 trois secondes plus tard.
        """
        geste = Gtk.GestureClick(button=3)
        geste.connect("pressed", self._on_journal_clic_droit, widget)
        widget.add_controller(geste)

    def _delier_cellule(self, _fabrique, cellule) -> None:
        self._log_cellules.pop(cellule.get_child(), None)

    def _cellule_de(self, cellule, ligne) -> Gtk.Label:
        """Le widget d'une cellule, sa position retenue, son trait de jour pose.

        Le trait qui separe deux journees etait une rangee a lui seul dans la
        grille. Ici c'est une bordure haute posee sur les six cellules de la
        premiere ligne du jour : mises bout a bout, elles tracent le meme trait
        d'un pixel, sans rien couter au modele.
        """
        widget = cellule.get_child()
        self._log_cellules[widget] = cellule.get_position()
        if ligne.ouvre_le_jour:
            widget.add_css_class("debut-de-jour")
        else:
            widget.remove_css_class("debut-de-jour")
        return widget

    def _lier_date(self, _fabrique, cellule) -> None:
        ligne = cellule.get_item()
        etiquette = self._cellule_de(cellule, ligne)
        etiquette.set_text(ligne.mv.when)
        etiquette.add_css_class("dim-label")
        etiquette.add_css_class("monospace")

    def _lier_contenant(self, _fabrique, cellule) -> None:
        ligne = cellule.get_item()
        etiquette = self._cellule_de(cellule, ligne)
        etiquette.set_text(self._sans_parenthese(ligne.mv.inv_label))
        etiquette.add_css_class("dim-label")

    def _lier_quantite(self, _fabrique, cellule) -> None:
        ligne = cellule.get_item()
        etiquette = self._cellule_de(cellule, ligne)
        mv = ligne.mv
        # Le tresor n'est pas un objet : des montants a sept chiffres qu'on ne
        # lit pas d'un bloc. Vert pour ce qui entre, rouge pour ce qui sort :
        # la couleur est ce qu'on lit en premier en parcourant une colonne de
        # chiffres.
        argent = mv.inv_key == movements.MONEY_KEY
        etiquette.set_markup('<span foreground="{}"><tt>{}</tt></span>'.format(
            "#4caf50" if mv.delta > 0 else "#e05252",
            f"{mv.delta:+,}".replace(",", " ") if argent
            else f"{mv.delta:+d}"))

    def _lier_nom(self, _fabrique, cellule) -> None:
        ligne = cellule.get_item()
        etiquette = self._cellule_de(cellule, ligne)
        mv = ligne.mv
        etiquette.set_text(_("Dappers") if mv.inv_key == movements.MONEY_KEY
                           else self._names.name(mv.sheet))

    def _lier_qualite(self, _fabrique, cellule) -> None:
        ligne = cellule.get_item()
        etiquette = self._cellule_de(cellule, ligne)
        etiquette.set_text(f"Q{ligne.mv.quality}" if ligne.mv.quality else "")
        etiquette.add_css_class("dim-label")

    def _lier_icone(self, _fabrique, cellule) -> None:
        """L'icône de l'objet, demandée à chaque liaison.

        **Et verifiee a l'arrivee.** Les cellules etant recyclees, l'icone
        demandee pour la ligne 12 peut revenir alors que la cellule sert
        maintenant la 340 : on la pose seulement si la cellule montre toujours
        la meme fiche. La generation, elle, protege du cas ou tout le journal a
        ete refait entre-temps -- une frappe dans la recherche suffit.
        """
        ligne = cellule.get_item()
        image = self._cellule_de(cellule, ligne)
        mv = ligne.mv
        cote = self._cote_icone_journal
        image.set_pixel_size(cote)
        if mv.inv_key == movements.MONEY_KEY:
            image.set_from_file(self.BOURSE)
            self._poser_icone(image, self.BOURSE, cote)
            return
        # Une image generique tient la place en attendant, pour que la colonne
        # ne se decale pas a l'arrivee.
        image.set_from_icon_name("image-x-generic-symbolic")
        attendue = (mv.sheet, mv.quality)
        generation = self._log_generation

        def arrivee(chemin, img=image, attendue=attendue, gen=generation):
            if not chemin or gen != self._log_generation:
                return False
            actuelle = getattr(img, "_fiche_journal", None)
            if actuelle != attendue:
                return False
            self._poser_icone(img, chemin, self._cote_icone_journal)
            return False

        image._fiche_journal = attendue
        self._icons.request(ItemInfo(sheet=mv.sheet, quality=mv.quality),
                            arrivee)

    # ---------------------------------------------------------- Compétences
    #: Les quatre écrans de « Bonus », dans l'ordre du menu.
    #:
    #: Le nom interne de la page reste `plus` : il ne paraît nulle part, et le
    #: renommer toucherait l'action D-Bus, la pile et six méthodes pour rien.
    PLUS_PAGES = (("skills", "Compétences"), ("roster", "Effectif"),
                  ("betes", "Perdu ?"), ("outposts", "Avant-postes"),
                  ("meteo", "Météo / forage"))

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
        for nom, etiquette in (("inventory", _("Inventaire")),
                               ("log", _("Journal"))):
            bouton = Gtk.ToggleButton()
            bouton.set_child(self._image_et_texte(nom, etiquette))
            bouton.connect("toggled", self._on_nav_toggled, nom)
            self._nav_boutons[nom] = bouton
            boite.append(bouton)

        # **Un popover de boutons, et non un `Gio.Menu`.** GTK4 n'affiche pas
        # les icônes d'un menu — c'est un parti pris d'Adwaita, et aucun
        # attribut ne le fléchit. Les cinq écrans sont donc des boutons posés
        # dans un popover : ils portent leur image comme les deux onglets, et
        # activent la même action que le menu activait.
        self._plus_btn = Gtk.MenuButton()
        self._plus_btn.set_child(self._image_et_texte("plus", _("Bonus"),
                                                      chevron=True))
        popover = Gtk.Popover()
        popover.add_css_class("menu")
        liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        for nom, etiquette in self.PLUS_PAGES:
            entree = Gtk.Button()
            entree.add_css_class("flat")
            entree.set_child(self._image_et_texte(nom, _(etiquette)))
            entree.connect("clicked", self._on_plus_bouton, nom, popover)
            liste.append(entree)
        popover.set_child(liste)
        self._plus_btn.set_popover(popover)
        boite.append(self._plus_btn)

        action = Gio.SimpleAction.new("plus", GLib.VariantType.new("s"))
        action.connect("activate", self._on_plus_choisi)
        self.add_action(action)
        return boite

    def _image_et_texte(self, page: str, etiquette: str,
                        chevron: bool = False) -> Gtk.Widget:
        """Un bouton de navigation : son image, son nom, parfois un chevron.

        L'image est retenue dans `_images_boutons` : les boutons de zoom la
        retrouvent là pour la faire grandir avec le reste.
        """
        boite = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fichier = self.ICONES_PAGES.get(page)
        if fichier:
            chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "symboles", fichier)
            if os.path.exists(chemin):
                image = Gtk.Image.new_from_file(chemin)
                part = (self.PART_BOURSE if page in self.PAGES_AGRANDIES
                        else self.PART_ICONE_BOUTON)
                image.set_pixel_size(self._settings.icone(part))
                self._images_boutons.append((image, part))
                boite.append(image)
        boite.append(Gtk.Label(label=etiquette))
        if chevron:
            boite.append(Gtk.Image.new_from_icon_name("pan-down-symbolic"))
        return boite

    def _on_plus_bouton(self, _bouton, nom: str, popover) -> None:
        """Une entrée du popover : elle ouvre son écran et referme le menu.

        Elle fait exactement ce que faisait l'entrée de menu qu'elle remplace
        — l'action `win.plus` reste d'ailleurs en place, le clavier et D-Bus
        s'en servent encore.
        """
        popover.popdown()
        self._stack.set_visible_child_name("plus")
        self._plus_stack.set_visible_child_name(nom)

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
        self._plus_stack.add_titled(self._build_meteo_page(), "meteo",
                                    _("Météo / forage"))

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


    def _load_log(self) -> None:
        """Relit le journal de l'entité courante depuis le disque."""
        entry = self._current_entry()
        self._log_entries = []
        if entry:
            self._log_entries = movements.load(
                movements_path(entry["kind"], entry["id"]))
        self._refresh_log()

    def _filtered_log(self) -> list:
        saisie = self._log_search.get_text().strip()
        # « Q250 », « q150 » : la qualité, et non le nom. Elle ne figure dans
        # aucun des textes fouillés — elle a sa propre colonne —, si bien que
        # la chercher ne rendait rien. La recette est dans `movements`, pour
        # que les deux portages répondent au même mot.
        qualite = movements.qualite_cherchee(saisie)
        needle = "" if qualite is not None else _norm(saisie)
        mode = self._log_filter.get_selected()
        out = []
        for mv in self._log_entries:
            if mode == 1 and mv.delta <= 0:
                continue
            if mode == 2 and mv.delta >= 0:
                continue
            if qualite is not None and mv.quality != qualite:
                continue
            if needle:
                hay = _norm(f"{self._names.name(mv.sheet)} {mv.sheet} {mv.inv_label}")
                if needle not in hay:
                    continue
            out.append(mv)
        return out

    #: La part de l'icone d'inventaire que prend celle du journal.
    #:
    #: La moitie : a la taille normale cela fait vingt-quatre pixels, la
    #: hauteur d'une ligne de texte. Plus grand, chaque mouvement occupait
    #: deux lignes et on en voyait deux fois moins d'un coup d'oeil -- or le
    #: journal se parcourt.
    #:
    #: **Une part, et non un nombre de pixels.** Vingt-quatre etaient ecrits
    #: en dur : les lignes grandissaient avec le zoom, l'icone restait, et
    #: elle paraissait retrecir a mesure qu'on grossissait le reste. La meme
    #: part que dans la version Qt.
    PART_ICONE_JOURNAL = 0.5

    @property
    def _cote_icone_journal(self) -> int:
        """Le côté d'une icône du journal, au zoom courant."""
        return self._settings.icone(self.PART_ICONE_JOURNAL)

    #: L'icône du sort gravé dans un objet, posée sur la sienne.
    #:
    #: Vingt : l'API la rend en vingt-quatre, mais sur une case de quarante-huit
    #: elle mangeait le quart de l'objet. Vingt se reconnaît encore — un éclair,
    #: une goutte, un missile — sans qu'on cherche ce qu'il y a dessous.
    TAILLE_ICONE_SORT = 20

    def _icone_journal(self, generation: int, image):
        """Pose l'icône si le journal n'a pas été redessiné entre-temps.

        Il l'est à chaque frappe dans la recherche : sans ce garde, une icône
        demandée pour l'ancienne liste viendrait se poser sur la ligne qui a
        pris sa place, et le journal afficherait l'icône du voisin."""
        def arrivee(chemin):
            if generation == self._log_generation and chemin:
                self._poser_icone(image, chemin, self._cote_icone_journal)
            return False
        return arrivee

    @staticmethod
    def _poser_icone(image, chemin: str, cote: int) -> None:
        """Pose une image de fichier à une taille imposée, au pixel près.

        **`set_pixel_size` ne suffit pas.** Il ne commande vraiment que les
        icônes nommées ; sur une image chargée d'un fichier, GTK garde la main
        et certaines sortaient plus petites que leurs voisines — la recharge en
        sève du journal, la même à toutes les échelles, alors que les matières
        suivaient le zoom. Mise a l'echelle ici, le carre est exact et toutes
        les lignes s'alignent.
        """
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                chemin, cote, cote, False)
        except Exception:                               # noqa: BLE001
            image.set_from_file(chemin)
            image.set_pixel_size(cote)
            return
        image.set_from_pixbuf(pixbuf)

    #: La bourse de dappers, celle du jeu.
    #:
    #: Elle remplace l'emoji du sac de billets : un sac vert de dollars n'a
    #: rien à faire dans Atys, et la bourse est ce que le joueur voit dans son
    #: inventaire. Trente-deux pixels de côté, avec sa transparence ; elle vit
    #: dans `zyroom/symboles/`, que le Makefile recopie et que la
    #: synchronisation du noyau porte jusqu'à la version Qt.
    BOURSE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "symboles", "dappers.png")

    #: L'image de chaque écran, par le nom que porte sa page.
    #:
    #: Les fichiers vivent dans `zyroom/symboles/`, que la synchronisation du
    #: noyau porte jusqu'à la version Qt : les deux fenêtres montrent les mêmes
    #: images, et il n'y a qu'un endroit où les remplacer.
    ICONES_PAGES = {
        "inventory": "inventaire.png",
        "log": "journal.png",
        "plus": "bonus.png",
        "skills": "competences.png",
        "roster": "effectif.png",
        "betes": "perdu.png",
        "outposts": "avant-poste.png",
        "meteo": "meteo-forage.png",
    }

    #: La part qu'occupe un logo — les deux onglets, le menu « Bonus » et ses
    #: cinq entrées, les contenants du sélecteur, la bourse du pied.
    #:
    #: Les boutons de zoom valent pour eux aussi : une icône de vingt pixels à
    #: côté d'un texte grossi paraîtrait perdue. Trente pixels au réglage par
    #: défaut — une fois et demie ce qu'ils faisaient d'abord, la hauteur
    #: d'une ligne de texte s'étant révélée trop chiche pour des dessins
    #: pleins. La même part que dans la version Qt.
    #:
    #: Les icones d'items suivent le zoom elles aussi, mais par leur propre
    #: part : la grille prend l'icone entiere, le journal la moitie.
    PART_ICONE_BOUTON = 0.63

    #: La bourse, quinze pour cent au-dessus des autres logos.
    #:
    #: Non par caprice, mais parce qu'elle est étroite : le sac est plus haut
    #: que large — vingt-quatre sur trente —, là où les autres remplissent un
    #: carré. À hauteur égale il peignait quatre cent soixante-trois pixels
    #: contre six cents en moyenne, et paraissait donc plus petit. Le facteur
    #: est la racine de ce rapport : c'est la surface qu'on égalise, pas la
    #: hauteur.
    PART_BOURSE = PART_ICONE_BOUTON * 1.15

    #: L'image d'un contenant, par le début de sa clé technique.
    #:
    #: `bag`, `room`, `chest1`, `chest2`… : la clé dit ce qu'est le contenant
    #: bien mieux que son libellé, qui est traduit et que le joueur renomme.
    #: Les montures — `animal1`, `animal2`… — n'en ont pas : le jeu ne fournit
    #: d'icône ni pour le mektoub ni pour le zig.
    IMAGES_CONTENANTS = (("bag", "sac.png"), ("room", "appartement.png"),
                         ("chest", "coffre.png"))

    PAGES_AGRANDIES = ()

    #: L'or du thème, celui d'Android — repris ici pour le balisage Pango,
    #: qui ne sait pas lire une classe CSS.
    OR = "#e8c15a"

    #: Le journal et les alertes coupent le libelle au meme endroit -- la
    #: recette est dans `movements`, qui ne connait pas d'interface.
    _sans_parenthese = staticmethod(movements.sans_parenthese)

    def _refresh_log(self) -> None:
        self._log_generation = getattr(self, "_log_generation", 0) + 1
        # Les cellules vont etre reliees a d'autres lignes : ce que le clic
        # droit savait d'elles ne vaut plus rien.
        self._log_cellules.clear()

        shown = self._filtered_log()
        montrees = movements.lignes_recentes(
            shown, self._LOG_JOURS, self._LOG_MINIMUM, self._LOG_MAX)

        # Le jour se prend sur les dix premiers signes de l'horodatage --
        # « 2026-08-12 22:44:35 » -- plutot que d'analyser une date pour la
        # recomparer aussitot. Le journal se lit du plus recent au plus ancien,
        # et trois releves d'affilee y produisent trois paquets de lignes a la
        # meme seconde : sans separation, on ne voyait plus ou finissait une
        # journee.
        lignes = []
        jour_precedent = None
        for mv in shown[:montrees]:
            jour = mv.when[:10]
            lignes.append(LigneJournal(
                mv, jour_precedent is not None and jour != jour_precedent))
            jour_precedent = jour
        # D'un seul coup, et non ligne a ligne : `splice` ne previent qu'une
        # fois, la ou mille `append` feraient mille recalculs de la vue.
        self._log_modele.splice(0, self._log_modele.get_n_items(), lignes)
        self._caler_colonnes_journal(lignes)
        self._journal_en_haut()

        total = len(self._log_entries)
        if not total:
            self._log_status.set_text(
                "Aucun mouvement enregistré. Le journal se remplit à chaque "
                "synchronisation où quelque chose a bougé.")
        elif len(shown) > montrees:
            self._log_status.set_text(
                f"{montrees} lignes affichées sur {len(shown)} "
                f"retenues ({total} au journal) — affinez la recherche.")
        else:
            self._log_status.set_text(f"{len(shown)} lignes sur {total} au journal")

    # ------------------------------------------- Choisir et copier des lignes
    def _journal_en_haut(self) -> None:
        """Ramène le journal sur sa première ligne après un remplissage.

        **La grille le faisait sans qu'on le demande.** Elle etait videe puis
        reconstruite : l'ascenseur retombait a zero faute de contenu. Un
        `Gtk.ColumnView` garde sa position d'un remplissage a l'autre, et le
        journal s'ouvrait tout en bas de la liste -- sur le mouvement le plus
        ancien, le moins interessant, quand la premiere ligne est justement le
        dernier releve.

        En differe, et non tout de suite : au retour de `splice`, la vue n'a
        pas encore recalcule sa hauteur, et l'ascenseur qu'on remettrait a
        zero serait repousse par la mise en page qui suit.
        """
        def poser():
            ajustement = self._log_defilant.get_vadjustment()
            if ajustement is not None:
                ajustement.set_value(0)
            return False
        GLib.idle_add(poser)

    def _texte_du_mouvement(self, mv) -> str:
        """Les mots d'une ligne du journal, dans l'ordre des colonnes.

        Lu dans le mouvement et non dans les widgets : les cellules d'un
        tableau ne sont construites que pour ce qu'on voit, et une ligne
        choisie puis sortie de l'ecran n'en a plus aucune. C'est d'ailleurs
        plus sur -- ce qui se copie ne depend plus de ce qui est peint.
        """
        argent = mv.inv_key == movements.MONEY_KEY
        mots = [mv.when,
                self._sans_parenthese(mv.inv_label),
                f"{mv.delta:+,}".replace(",", " ") if argent
                else f"{mv.delta:+d}",
                _("Dappers") if argent else self._names.name(mv.sheet)]
        if mv.quality:
            mots.append(f"Q{mv.quality}")
        return "  ".join(m for m in mots if m)

    def _lignes_journal_choisies(self) -> list:
        """Le texte des lignes choisies, du plus récent au plus ancien.

        L'ordre du journal lui-même : `Gtk.Bitset` rend les positions par
        ordre croissant, et le modèle est trié du mouvement le plus récent au
        plus ancien.
        """
        choix = self._log_choix.get_selection()
        textes = []
        for rang in range(choix.get_size()):
            ligne = self._log_modele.get_item(choix.get_nth(rang))
            if ligne is not None:
                textes.append(self._texte_du_mouvement(ligne.mv))
        return textes

    def _copier_journal_choisi(self) -> bool:
        """Ctrl+C : met les lignes choisies dans le presse-papiers.

        Sans effet hors du journal : le raccourci est pose sur la fenetre, et
        il n'a pas a repondre quand on est ailleurs.
        """
        bouton = getattr(self, "_nav_boutons", {}).get("log")
        if bouton is not None and not bouton.get_active():
            return False
        textes = self._lignes_journal_choisies()
        if not textes:
            return False
        self.get_clipboard().set("\n".join(textes))
        self._set_status(_("%d ligne(s) copiée(s).") % len(textes))
        return True

    def _on_journal_clic_droit(self, _geste, _n, x, y, widget) -> None:
        """Propose de copier la ligne sous le pointeur."""
        position = self._log_cellules.get(widget)
        if position is None:
            return
        # Un clic droit hors de ce qui est choisi prend la ligne visee : sinon
        # le menu proposerait de copier des lignes qu'on ne montre pas du
        # doigt.
        if not self._log_choix.is_selected(position):
            self._log_choix.select_item(position, True)
        textes = self._lignes_journal_choisies()
        if not textes:
            return
        texte = "\n".join(textes)
        bouton = Gtk.Button(label=_("Copier la ligne") if len(textes) == 1
                            else _("Copier les %d lignes") % len(textes))
        bouton.add_css_class("flat")
        popover = Gtk.Popover()
        popover.add_css_class("menu")
        popover.set_child(bouton)
        # **Accroche a la cellule cliquee.** Du temps de la grille, le menu
        # etait accroche au defilant et visait un point converti a la main :
        # la grille faisait des milliers de pixels de haut, et le point vise
        # tombait hors de la zone affichee. Une cellule, elle, mesure ce qu'on
        # voit, et les coordonnees du geste sont deja dans son repere -- le
        # menu s'ouvre sous le pointeur sans conversion.
        #
        # **Le rectangle se remplit champ par champ.** `Gdk.Rectangle(x=…, y=…)`
        # ne pose rien : PyGObject ignore les arguments d'une structure boxed et
        # rend (0,0,0,0), avec un avertissement qu'on ne voit jamais.
        vise = Gdk.Rectangle()
        vise.x = int(x)
        vise.y = int(y)
        vise.width = vise.height = 1
        popover.set_parent(widget)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_pointing_to(vise)
        # Un popover parente doit etre detache a sa fermeture, sinon il reste
        # accroche a la cellule et s'accumule a chaque clic droit.
        popover.connect("closed", lambda pop: pop.unparent())

        def copier(_b):
            self.get_clipboard().set(texte)
            popover.popdown()
            self._set_status(_("%d ligne(s) copiée(s).") % len(textes))
        bouton.connect("clicked", copier)
        popover.popup()

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
    def _relire_journaux_publies(self) -> None:
        """Verse dans les journaux d'ici ceux que la page publie.

        Au lancement, en tâche de fond, et sans rien dire : c'est un confort,
        pas une opération. L'API ne rend qu'un état — chaque installation ne
        connaît que ce qu'elle a regardé elle-même, et un officier qui relève
        une fois par semaine voit d'un bloc ce qu'un autre a vu en trois fois.
        Ce que la page publie comble ces trous, et `movements.fusionner` garde
        le récit le plus fin.

        Rien ne remonte : la page se lit, elle ne s'écrit pas depuis ici.
        """
        entrees = list(self._entries)
        if not entrees:
            return

        def work():
            total = 0
            for entree in entrees:
                total += partage.recuperer(
                    entree["kind"], entree["id"],
                    movements_path(entree["kind"], entree["id"]))
                # Le registre du personnel se reprend de la meme page, et il
                # ne l'etait pas ici : `partage.recuperer_registre` existait,
                # personne ne l'appelait. Le releve horaire voit passer tout
                # le monde ; une application ouverte deux fois par semaine ne
                # voit qu'un membre sur trois, et l'ecart devenait, sur six
                # mois, l'essentiel du registre.
                if entree["kind"] == KIND_GUILD:
                    total += partage.recuperer_registre(
                        entree["id"],
                        os.path.join(data_dir(),
                                     f"roster-{entree['id']}.jsonl"))
            return total

        def done(total, err):
            if err or not total:
                return          # rien de neuf, ou pas de reseau : on se tait
            # Le journal affiche peut etre celui qu'on vient d'enrichir.
            if self._stack.get_visible_child_name() == "log":
                self._load_log()
            self._set_status(
                _("Journal de la guilde : {} mouvement(s) repris de la page.")
                .format(total))

        run_async(work, done)

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
            # Le nom seul, sans le serveur entre parenthèses : tout ce qui
            # se relève vient d'Atys, et la mention se répétait sur chaque
            # ligne du menu sans jamais distinguer quoi que ce soit. La place
            # gagnée va au nom, qui, lui, peut être long.
            #
            # Le pictogramme non plus : c'est l'image de l'entité qui le
            # remplace, posée par la fabrique — l'emblème de la guilde ou le
            # portrait du personnage, les mêmes qu'en bas de la fenêtre.
            model.append(entry["name"])

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
        """Le bouton relève l'entité **et** demande s'il existe mieux.

        Les deux questions se ressemblent — « qu'y a-t-il de neuf ? » — et
        c'est le geste qu'on fait en revenant devant l'application. La veille
        automatique passe au quart d'heure ; qui vient de livrer, ou qui a lu
        l'annonce sur le Discord, n'a pas envie d'attendre le prochain tour.

        Hors du `if` : sans entité choisie il n'y a rien à relever, mais la
        version, elle, se compare toujours. La vérification part dans un fil
        et ne retarde pas la synchronisation.
        """
        self._verifier_maj()
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
        self._mouvements_argent = []
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
        self._inv_keys = []
        if ent:
            for inv in ent.inventories:
                self._inv_keys.append(inv.key)
                # Le numero du coffre, son nom, son taux -- et rien du reste
                # de phrase que l'API laisse pendre apres une parenthese
                # jamais refermee. Le journal et les alertes coupent deja la.
                model.append(f"{movements.sans_parenthese(inv.label)}"
                             f"{self._remplissage(inv)}")
        self._inv_dd.handler_block_by_func(self._on_inventory_selected)
        self._inv_dd.set_model(model)
        self._inv_dd.handler_unblock_by_func(self._on_inventory_selected)
        if ent and ent.inventories:
            rang = self._rang_du_contenant(ent)
            self._inv_dd.set_selected(rang)
            self._display_inventory(rang)
        else:
            self._clear_flow()

    def _rang_du_contenant(self, ent) -> int:
        """Le contenant à réafficher après un rechargement de la liste.

        La relève automatique rebâtit cette liste toutes les quinze minutes, et
        elle ramenait au premier : on consultait le coffre onze, on regardait
        ailleurs, et l'on retrouvait le coffre un — sans rien avoir demandé.

        Le repère est la **clé** du contenant et non son rang : l'API peut en
        rendre un de plus ou de moins d'une relève à l'autre, et un rang
        désignerait alors le voisin. Changer d'entité fait repartir du premier,
        ce qui est le bon comportement : les coffres d'une guilde n'ont rien à
        voir avec le sac d'un personnage.
        """
        if not self._inv_courant:
            return 0
        entite, cle = self._inv_courant
        if entite != (ent.kind, ent.entity_id):
            return 0
        for rang, inv in enumerate(ent.inventories):
            if inv.key == cle:
                return rang
        return 0

    @staticmethod
    def _remplissage(inv) -> str:
        """Le taux de remplissage d'un contenant, prêt à coller en fin de ligne.

        Le menu annonçait un nombre d'objets, qui ne dit pas si l'on peut
        encore ranger quelque chose : cent matières tiennent où dix armures
        débordent. Le taux le dit, et l'on voit quel coffre est plein sans
        avoir à l'ouvrir.

        Vide quand la capacité est inconnue — l'API ne la donne pas pour tous
        les contenants, et « (0%) » ferait croire à un coffre vide.
        """
        if getattr(inv, "capacity", 0) <= 0:
            return ""
        pct = inv.total_volume / inv.capacity * 100.0
        return f" ({pct:.0f}%)"

    def _on_inventory_selected(self, _dd, _param) -> None:
        idx = self._inv_dd.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self._display_inventory(idx)

    def _display_inventory(self, index: int) -> None:
        ent = self._entity
        if not ent or not (0 <= index < len(ent.inventories)):
            return
        inv = ent.inventories[index]
        self._inv_courant = ((ent.kind, ent.entity_id), inv.key)
        self._update_volume_gauge(inv)

        self._generation += 1
        gen = self._generation
        self._clear_flow()
        self._rows = []

        for item in self._sorted(inv.items):
            image = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
            image.set_pixel_size(self._settings.icon_size)
            # Infobulle construite au survol, et non a la creation : elle
            # porte maintenant des gouttes dessinees, et un coffre en compte
            # jusqu'a quatre cents.
            image.set_has_tooltip(True)
            image.connect("query-tooltip", self._on_item_tooltip, item)
            child = Gtk.FlowBoxChild()
            # Les gouttes de specialite, dessinees par-dessus l'icone. Pas
            # d'Overlay quand il n'y a rien a poser : c'est le cas de la
            # plupart des items d'un coffre, et un widget de plus par case
            # pese sur une grille qui en compte des centaines.
            gouttes = specialites.bandeau(item)
            sort = enchantements.brique_icone(item)
            if gouttes is None and not sort:
                child.set_child(image)
            else:
                pile = Gtk.Overlay()
                pile.set_child(image)
                if gouttes is not None:
                    pile.add_overlay(gouttes)
                if sort:
                    pile.add_overlay(self._icone_sort(gen, sort))
                child.set_child(pile)
            self._flow.append(child)
            nom = self._names.name(item.sheet)
            search_key = _norm(f"{nom} {item.sheet}")
            self._rows.append((child, item, search_key,
                               categorie_item(item, nom)))

            self._icones_en_vol += 1
            self._attendre(True)
            self._icons.request(item, self._make_icon_cb(gen, image))
            gesture = Gtk.GestureClick()
            gesture.set_button(Gdk.BUTTON_SECONDARY)  # clic droit
            gesture.connect("released", self._on_item_right_click, item, image)
            image.add_controller(gesture)
            dclick = Gtk.GestureClick()
            dclick.set_button(Gdk.BUTTON_PRIMARY)     # double-clic gauche
            dclick.connect("released", self._on_item_activate, item)
            image.add_controller(dclick)

        self._maj_categories()
        self._apply_filter()

    def _maj_categories(self) -> None:
        """Refait la liste du filtre par type avec ce que l'inventaire contient.

        **Seulement les familles presentes.** Le pack en connait quatre cent
        onze ; un joueur en tient quelques dizaines. Une liste figee obligerait
        a chercher « Resine » parmi des centaines de lignes vides.

        Tout est recoche des que la liste change : une case retenue par son
        rang designerait une autre famille au prochain inventaire, et le joueur
        verrait disparaitre des items sans avoir rien touche.
        """
        trouvees = sorted({categorie for _c, _i, _k, categorie in self._rows})
        if trouvees == self._categories:
            return
        self._categories = trouvees
        self._cat_rang = {nom: i for i, nom in enumerate(trouvees)}
        self._f_types = set(range(len(trouvees)))
        # Le popover est bati une fois pour toutes a la construction de la
        # barre : il faut le refaire pour qu'il montre la nouvelle liste.
        if getattr(self, "_filter_btn", None) is not None:
            self._filter_btn.set_popover(self._build_filter_popover())

    def _make_icon_cb(self, gen: int, image: Gtk.Image):
        """Le retour d'une icône : elle se pose, et l'attente diminue d'autant.

        Les icônes d'un coffre arrivent d'un pool de fils, parfois du réseau :
        c'est le seul moment où l'application travaille visiblement sans rien
        en dire. La barre le dit maintenant, et s'éteint quand la dernière est
        arrivée.

        L'attente est retirée même quand la grille a changé entre-temps
        (`gen` périmé) : elle a bien été comptée au départ, et l'oublier ici
        laisserait la barre tourner pour une image dont plus personne ne veut.
        """
        def cb(path):
            self._icone_arrivee()
            if gen != self._generation:
                return False
            if path:
                image.set_from_file(path)
                image.set_pixel_size(self._settings.icon_size)
            return False
        return cb

    def _icone_arrivee(self) -> None:
        """Une icône de moins à attendre."""
        if self._icones_en_vol <= 0:
            return
        self._icones_en_vol -= 1
        self._attendre(False)

    def _item_tooltip(self, item) -> str:
        # `name()` rend l'identifiant de fiche quand le nom est inconnu : une
        # seule ligne suffit donc, et l'identifiant ne s'affiche qu'à défaut.
        lines = [self._names.name(item.sheet)]
        if item.quality:
            lines.append(f"Qualité : {item.quality}")
        if item.stack:
            lines.append(f"Quantité : {item.stack}")
        if item.item_type == ItemType.EQUIPMENT and item.hp:
            # " 75 / 154 " : un nombre seul ne dit pas si l'objet est neuf ou
            # a bout de course. Le maximum vient du craft (`durability`), et
            # manque sur les items que l'API ne detaille pas.
            lines.append(f"Durabilité : {item.hp} / {item.hp_max}"
                         if item.hp_max else f"Durabilité : {item.hp}")
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

    def _icone_sort(self, gen: int, brique: str) -> Gtk.Widget:
        """L'icône du sort gravé dans l'objet, à poser en haut à droite.

        Vide en attendant l'image : un objet enchanté n'est pas plus rare qu'un
        autre dans un sac de mêlée, et une image d'attente ferait clignoter la
        grille à chaque affichage. L'API la rend en 24×24 ; on la montre un peu
        plus petite, pour laisser voir l'objet en dessous."""
        vue = Gtk.Image()
        vue.set_pixel_size(self.TAILLE_ICONE_SORT)
        vue.set_halign(Gtk.Align.END)
        vue.set_valign(Gtk.Align.START)
        # Comme les gouttes : le dessin ne prend pas le clic de l'icone.
        vue.set_can_target(False)
        self._icons.request_brique(brique, self._recevoir_sort(gen, vue))
        return vue

    def _recevoir_sort(self, gen: int, vue: Gtk.Image):
        def callback(path):
            if gen == self._generation and path:
                vue.set_from_file(path)
                vue.set_pixel_size(self.TAILLE_ICONE_SORT)
            return False
        return callback

    def _on_item_tooltip(self, _widget, _x, _y, _clavier, infobulle, item) -> bool:
        """Le survol d'un item : son infobulle, gouttes comprises."""
        infobulle.set_custom(self._item_tooltip_widget(item))
        return True

    def _item_tooltip_widget(self, item) -> Gtk.Widget:
        """L'infobulle d'un item : le texte, puis les spécialités en couleur.

        Un widget et non du texte, parce qu'une goutte ne s'écrit pas. Le jeu
        fait de même : le nom, la goutte et son nombre, la durabilité."""
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        texte = Gtk.Label(label=self._item_tooltip(item), xalign=0.0)
        boite.append(texte)
        gouttes = specialites.bloc_infobulle(item)
        if gouttes is not None:
            boite.append(gouttes)
        sort = enchantements.resume(item, self._names.name)
        if sort:
            # Les charges disent combien de fois le sort part encore ; le cout,
            # ce qu'un lancer prend. Les deux viennent du meme noeud.
            ligne = f"Enchantement : {sort}"
            if item.sap_charges:
                ligne += f"\nCharges de sève : {item.sap_charges}"
            if item.enchant_cost:
                ligne += f" (coût {abs(item.enchant_cost)})"
            etiquette = Gtk.Label(label=ligne, xalign=0.0)
            etiquette.set_wrap(True)
            etiquette.set_max_width_chars(40)
            boite.append(etiquette)
        return boite

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

        # Les bonus d'abord : c'est le tri qu'on vient chercher le plus souvent
        # dans un coffre d'équipement, et le panneau tient sur quatre cent
        # quarante pixels — plus bas, il fallait dérouler pour l'atteindre.
        content.append(self._groupe_bonus())

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

        content.append(self._check_group("Type d'objet", self._categories,
                                        self._f_types))
        content.append(self._check_group("Classe", CLASS_NAMES, self._f_classes))
        content.append(self._check_group("Écosystème", ECOSYSTEM_NAMES, self._f_ecosys))
        content.append(self._check_group("Équipement", EQUIP_NAMES, self._f_equips))
        return pop

    def _groupe_bonus(self) -> Gtk.Widget:
        """Les quatre bonus, chacun derrière sa goutte.

        Un groupe à part plutôt qu'un `_check_group` : la couleur est ce qui
        fait le lien avec la grille, où c'est elle — et non un nom — qui marque
        les objets. Une case portant « Sève » sans sa goutte verte obligerait à
        traduire de tête à chaque coup d'œil.

        Toutes cochées, le groupe ne filtre rien, **objets sans bonus compris**.
        Dès qu'une case tombe, il ne reste que les objets portant l'un des
        bonus encore cochés : décocher trois cases sur quatre, c'est demander
        « montre-moi ce qui est monté en sève », pas « montre-moi tout sauf ».
        """
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        header = Gtk.Label(xalign=0.0)
        header.set_markup(f"<b>{_('Bonus')}</b>")
        header.props.margin_top = 4
        box.append(header)
        for rang, (_attribut, libelle, couleur) in enumerate(specialites.SPECIALITES):
            ligne = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            ligne.append(specialites.pastille(couleur))
            ligne.append(Gtk.Label(label=_(libelle), xalign=0.0))
            cb = Gtk.CheckButton()
            cb.set_child(ligne)
            cb.set_active(rang in self._f_bonus)
            cb.connect("toggled", self._on_group_toggle, self._f_bonus, rang)
            box.append(cb)
            self._all_checks.append(cb)
        return box

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
        # Un nombre isole dans la recherche vaut une qualite : « oeil 220 »
        # trouve les yeux de 220 sans passer par les bornes du menu.
        needle, qualites = decouper_recherche(_norm(self._search.get_text()))
        qmin = int(self._qmin.get_value())
        qmax = int(self._qmax.get_value())
        locked_only = self._locked_only.get_active()
        bonus_only = self._bonus_only.get_active()
        sale_only = self._sale_only.get_active()

        visible = 0
        for child, item, search_key, categorie in self._rows:
            ok = True
            if needle and needle not in search_key:
                ok = False
            elif qualites and item.quality not in qualites:
                ok = False
            elif not (qmin <= item.quality <= qmax):
                ok = False
            elif self._cat_rang.get(categorie, -1) not in self._f_types:
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
            elif not specialites.passe_le_filtre(item, self._f_bonus):
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
        # « Reinit. » rend la fenetre telle qu'elle se presente au lancement,
        # et c'est desormais le tri par type -- pas l'ordre d'origine, qu'on
        # ne verrait sinon jamais autrement qu'en le demandant.
        self._sort_dd.set_selected(Settings.TRI_DEFAUT[0])
        # Le sens aussi : il ne se voyait pas tant qu'il repartait a zero a
        # chaque lancement, mais une fleche montante survivant a « Reinit. »
        # se remarque tout de suite.
        if self._sort_desc != Settings.TRI_DEFAUT[1]:
            self._on_order_toggle(None)
        self._apply_filter()

    # ------------------------------------------------------------- Tri
    _SORT_KEYS = {
        # Regroupement par famille : catalyseurs ensemble, feux d'artifice
        # ensemble, et les matieres reunies par sorte puis par materiau, du
        # plus bas niveau au plus haut. Voir sorting.py -- le type brut du jeu
        # ne s'y prete pas, la moitie d'un coffre y etant classee « autre ».
        # La sorte vient de category.csv : rien d'autre ne dit qu'une matiere
        # est une resine ou une huile, le nom de fiche n'en souffle mot.
        1: lambda self, it: sorting.sort_key(
            it, _norm(self._names.name(it.sheet)), self._categorydb.categories),
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
        self._retenir_tri()
        self._redisplay_current()

    def _on_order_toggle(self, _btn) -> None:
        self._sort_desc = not self._sort_desc
        self._order_btn.set_label("↑" if self._sort_desc else "↓")
        self._retenir_tri()
        self._redisplay_current()

    def _retenir_tri(self) -> None:
        """Enregistre le tri dès maintenant, et non à la fermeture.

        La taille des fenêtres, elle, attend `_on_close` : on ne la connaît
        qu'à la fin. Le tri est su dès le clic, et une application tuée — ou
        une session fermée sous elle — ne doit pas le faire oublier.
        """
        self._settings.sort_order = (self._sort_index, self._sort_desc)

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
        # La présence va sur la ligne du nom, et non sur celle du contenant :
        # elle parle du personnage, et cette ligne-là est la plus courte des
        # deux — la seconde porte déjà le coffre et l'heure de synchro, et se
        # coupe la première quand la fenêtre rétrécit.
        presence = self._presence(ent)
        vu = f" · {presence[0]}" if presence else ""
        self._status.set_tooltip_text(presence[1] if presence else None)
        line = f"{ent.name}{extra}{vu}\n{self._sans_parenthese(inv_label)}"

        # Dater les stocks affichés : sans cela, rien ne distingue une donnée
        # de l'instant d'une donnée vieille de plusieurs jours.
        entry = self._current_entry()
        if entry:
            when = last_sync(entry["kind"], entry["id"])
            line += f" · synchro {format_last_sync(when)}"
            bulle = (_("Resynchroniser depuis l'API")
                     + f"\n{_('Dernière synchro')} : {format_last_sync(when)}")
            # L'heure ci-dessus dit quand on a telecharge, pas de quand datent
            # les donnees : l'API ne recalcule pas a la demande, elle sert un
            # instantane deja calcule. Sans cette seconde ligne, un message du
            # jour ecrit en jeu et absent du flux passait pour un bouton casse.
            calcul = format_api_created(ent.created)
            if calcul:
                libelle = _("Données calculées par l'API")
                bulle += f"\n{libelle} : {calcul}"
            self._refresh_btn.set_tooltip_text(bulle)
        self._set_status(line)

    @staticmethod
    def _presence(ent) -> tuple[str, str] | None:
        """« en ligne » ou « vu il y a… », et l'infobulle qui dit d'où ça sort.

        Renvoie None quand l'API se tait : une guilde, ou une clé sans le module
        qui porte la connexion.

        Le mot est « vu » et non « déconnecté » à dessein. On lit un instantané
        de la sauvegarde du personnage, écrit à la déconnexion : ce que la ligne
        affirme, c'est la dernière fois qu'on l'a vu, pas l'état du serveur à la
        seconde présente. L'infobulle le dit en toutes lettres, pour que
        personne ne conclue d'un « vu il y a 10 min » que la place est vide.
        """
        etat = ent.en_ligne
        if etat is None:
            return None

        def date(horodatage: int) -> str:
            return (f"{datetime.fromtimestamp(horodatage):%d/%m à %Hh%M}"
                    if horodatage else "—")

        detail = (f"{_('Dernière connexion')} : {date(ent.lastlogin)}\n"
                  f"{_('Dernière déconnexion')} : {date(ent.lastlogout)}\n"
                  + _("L'API ne montre que la dernière sauvegarde du "
                      "personnage, écrite à la déconnexion : une connexion "
                      "toute fraîche peut ne pas s'y voir encore."))
        if etat:
            return "🟢 " + _("en ligne"), detail

        minutes = int((datetime.now()
                       - datetime.fromtimestamp(ent.lastlogout)).total_seconds() // 60)
        if minutes < 1:
            vu = _("vu à l'instant")
        elif minutes < 60:
            vu = _("vu il y a {} min").format(minutes)
        elif minutes < 24 * 60:
            vu = _("vu il y a {} h").format(minutes // 60)
        elif minutes < 7 * 24 * 60:
            vu = _("vu il y a {} j").format(minutes // (24 * 60))
        else:
            vu = _("vu le {}").format(f"{datetime.fromtimestamp(ent.lastlogout):%d/%m}")
        return vu, detail


    # --------------------------------------- En-tête entité + saison serveur
    def _corps_de_base(self) -> float:
        """Le corps du texte avant le zoom, en points.

        Celui du bureau, sauf si le fichier de réglages en impose un autre.
        GNOME écrit sa police en une chaîne, « Cantarell 11 », dont le corps
        est le dernier mot ; onze en dernier recours, sa valeur par défaut.

        **`FontSize` n'a plus de réglage dans les Options** : le zoom a pris
        sa place, et deux nombres pour une seule chose — voir plus gros —
        n'avaient pas de sens. La clé reste lue : elle sert au banc de parité,
        qui doit poser le même corps aux deux applications, et elle laisse
        leur choix à ceux qui l'avaient déjà réglée.
        """
        if self._settings.font_size > 0:
            return float(self._settings.font_size)
        reglages = Gtk.Settings.get_default()
        nom = reglages.get_property("gtk-font-name") if reglages else ""
        dernier = (nom or "").rsplit(" ", 1)[-1]
        try:
            return float(dernier)
        except ValueError:
            return 11.0

    def _corps_courant(self) -> float:
        """Le corps du texte à l'écran : celui de base, multiplié par le zoom."""
        return self._corps_de_base() * self._settings.zoom

    def _au_zoom(self, feuille: str) -> str:
        """La feuille de style, toutes ses longueurs multipliées par le zoom.

        **Sans cela, seul le texte grossirait.** Les hauteurs minimales, les
        remplissages, les rayons et les bordures sont écrits en pixels : à
        deux cents pour cent, un texte deux fois plus grand se serait retrouvé
        rogné dans des boutons restés à leur taille. Ludo l'a demandé
        explicitement — « je veux que le zoom grossisse entièrement les
        appli ».

        Les nombres sans unité sont laissés tels quels : ce sont des poids et
        des opacités, qui n'ont pas de taille.
        """
        zoom = self._settings.zoom
        if abs(zoom - 1.0) < 0.01:
            return feuille
        return re.sub(r"(\d+)px",
                      lambda m: f"{max(1, round(int(m.group(1)) * zoom))}px",
                      feuille)

    def _install_motd_css(self) -> None:
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

        # Un seul fournisseur pour toute la vie de la fenêtre, rechargé au
        # lieu d'être empilé : c'est ce qui permet de rejouer cette feuille
        # quand le corps du texte change, sans redémarrer et sans accumuler
        # une couche de style par passage aux options.
        provider = getattr(self, "_css_provider", None)
        premier_passage = provider is None
        if premier_passage:
            provider = self._css_provider = Gtk.CssProvider()
        # Le corps du texte, s'il a été réglé. En tête de la feuille et sur
        # `*` : GTK le résout comme n'importe quelle autre propriété, et tout
        # ce qui n'en demande pas d'autre en hérite.
        # Le corps s'ecrit toujours, et non plus seulement quand un reglage
        # l'impose : c'est par lui que le zoom agrandit le texte.
        corps = f"* {{ font-size: {self._corps_courant():.1f}pt; }}\n"
        # La somme en dappers, un point au-dessus du reste. C'est le nombre
        # qu'on vient lire dans cette barre, et au corps courant il s'y
        # perdait. En points et non en `em` : la version Qt ne sait pas lire
        # les unites relatives, et les deux barres doivent s'ecrire pareil.
        corps += f".dappers {{ font-size: {self._corps_courant() + 1:.0f}pt; }}\n"
        feuille = (corps + """
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
            /* Aucune jauge n'a de lisere. Adwaita en pose un d'un pixel
               autour du bloc rempli, bleu, et sa couleur y disait le palier.
               Il ne disait rien d'une competence, qui n'a pas de palier, et
               il cachait le sarcelle des faibles avancements : a 3 %, le bloc
               mesure 2,7 pixels et ses deux bords le remplissaient
               entierement -- la jauge paraissait bleue.

               La couleur du bord plutot que `border: none` : la bordure
               compte dans la hauteur du bloc, et la retirer amincirait la
               jauge d'un pixel de chaque cote.

               Le dernier palier du volume garde sa difference, mais c'est
               tout son bloc qui passe au vert au lieu de son seul contour --
               un coffre plein se voit ainsi de plus loin qu'avant. */
            levelbar > trough > block.filled {
                border-color: @zy_sarcelle; }
            levelbar > trough > block.full {
                background-color: #26ab62; border-color: #26ab62; }
            /* La jauge de volume, elle, prend le vert d'un onglet choisi.
               C'est la barre qu'on a sous les yeux toute la journee, juste
               sous la rangee des onglets : deux verts voisins et differents
               s'y lisaient comme une difference de sens, alors qu'il n'y en a
               aucune. Le sarcelle franc reste aux jauges de competences, ou
               rien ne le jouxte.

               Le dernier palier repasse apres, et non avant : les deux
               regles pesent le meme poids -- deux classes chacune -- et c'est
               donc la derniere ecrite qui l'emporte. Sans elle, un coffre
               plein cessait de se voir de loin. */
            levelbar.volume > trough > block.filled {
                background-color: @zy_sarcelle_sombre;
                border-color: @zy_sarcelle_sombre; }
            levelbar.volume > trough > block.full {
                background-color: #26ab62; border-color: #26ab62; }
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
            /* Les deux boutons de zoom, « − » et « + ». Deux traits maigres
               au milieu d'une barre pleine d'images : au corps ordinaire on
               les cherchait, et Ludo a demande qu'ils se voient.

               **Cent trente pour cent, et pas un de plus.** Au-dela, le signe
               depasse la hauteur d'un bouton de barre de titre et pousse la
               barre entiere : mesure a la capture, elle passait de cent a
               cent sept pixels a 160 %, cent vingt-cinq a 190 %, cent
               soixante-dix-neuf a 260 %. C'est la graisse qui fait voir ces
               deux traits maigres, et elle ne coute aucune hauteur.

               Le facteur de la version Qt vaut 1,3 et non 130 % du meme
               corps : les deux ne partent pas du meme point, et le nombre y
               est cale sur la mesure -- c'est l'un des rares
               endroits ou les deux feuilles disent la meme chose de deux
               facons. Un pourcentage et non des pixels : le corps suit celui
               du theme, et le zoom de l'application par-dessus. */
            /* Le remplissage sur le bouton seul : pose aussi sur le
               label, il s'ajoutait a celui du bouton et les deux signes se
               retrouvaient a cent seize pixels l'un de l'autre au lieu de
               trente-six. Le corps et la graisse, eux, doivent atteindre le
               label -- un `button` ne les transmet pas au sien. */
            button.zoom-icones { padding: 0 6px; }
            /* La cloche : un pictogramme, pas un mot. Sans cela Adwaita lui
               donne les marges d'un bouton de texte, et elle s'etalait treize
               pixels de plus que celle de Qt -- cinquante et un contre
               trente-huit. Dix et non six comme les boutons de zoom : a six
               elle tombait a trente et un, et passait d'un exces a l'autre. */
            button.cloche { padding: 0 10px; }
            button.zoom-icones, button.zoom-icones > label {
                font-size: 130%; font-weight: bold; }
            button.suggested-action {
                background-image: none; background-color: @zy_sarcelle;
                color: #06120e; }
            /* Un GtkMenuButton n'est pas un `button` : c'est un `menubutton`
               qui en contient un. La classe se pose sur le parent -- c'est lui
               qu'on tient en Python -- et la regle ci-dessus ne l'atteignait
               donc jamais. Le bouton « Bonus » restait gris au-dessus de ses
               propres pages, ou l'onglet doit dire ou l'on est. */
            menubutton.suggested-action > button {
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
            /* **Les lignes des listes déroulantes, resserrées.** Adwaita
               ajoute seize pixels autour du contenu d'une ligne : avec un
               texte seul cela se voyait à peine, mais depuis que chaque
               contenant porte son image de trente pixels, les lignes en
               réclamaient quarante-six et la liste s'étirait — huit coffres
               ou huit montures y prenaient une demi-fenêtre. Quatre pixels
               suffisent : l'image tient, et les lignes se suivent. */
            dropdown > popover listview > row {
                min-height: 0; padding-top: 2px; padding-bottom: 2px; }

            /* **Le survol prend le vert du theme, et non le voile d'Adwaita.**
               Une deroulante survolee virait au gris clair -- la seule touche
               neutre d'une barre par ailleurs sarcelle, et la seule aussi a
               s'ecarter du portage Qt, ou ce vert etait deja en place : son
               `QMenu::item:selected` et le `Highlight` de sa palette sont
               tous deux la sarcelle sombre. Les trois selecteurs couvrent les
               trois endroits ou l'on survole un menu : le bouton de la
               deroulante fermee, une ligne de la liste ouverte, et les
               boutons des popovers de menu -- « Bonus » et la cloche.

               `background-image: none` en plus de la couleur, comme pour les
               cases a cocher plus haut : Adwaita peint son survol avec une
               image, qui l'emporterait sur un simple fond. */
            dropdown > button:hover,
            dropdown > popover listview > row:hover,
            popover.menu button:hover {
                background-image: none;
                background-color: @zy_sarcelle_sombre; }

            /* Le trait qui separe deux journees du journal. C'etait une
               rangee entiere dans la grille ; dans le tableau, c'est une
               bordure haute posee sur les six cellules de la premiere ligne
               du jour -- mises bout a bout, elles tracent le meme trait. */
            .debut-de-jour { border-top: 1px solid alpha(@zy_or, 0.55);
                             margin-top: 13px; padding-top: 6px; }
            /* Les cellules du journal. Le `Gtk.ColumnView` leur donne, par
               defaut, de quoi accueillir une case a cocher : quarante pixels
               par rangee la ou la grille d'avant en tenait vingt-six, et six
               mouvements de moins par ecran. On lui reprend cet air, et on
               pose l'ecartement des colonnes que la grille declarait par
               `column_spacing`. */
            columnview.journal > listview > row > cell {
                padding-top: 1px; padding-bottom: 1px;
                padding-left: 8px; padding-right: 8px; }
            /* L'air sous la barre de recherche, une fois la rangee d'en-tetes
               cachee : sept pixels pour retomber sur le depart de la premiere
               ligne de la version Qt. */
            columnview.journal > listview { padding-top: 7px; }

            /* Le nom de l'application : la gothique du titre d'Android, et
               son or. La police est embarquée — voir `zyroom/polices` — car
               elle n'est installée nulle part et le bac à sable ne voit pas
               celles de l'hôte. Si son chargement échouait, `font-family`
               retomberait sur la police courante : laid, mais pas cassé.

               L'or et la marge tiennent sur la boîte, qui les donne à ses deux
               morceaux — sinon la marge intérieure se glisserait entre eux. La
               mouture reste dans une police d'imprimerie : « GTK » et « dev »
               sont des mots d'ingénieur, la gothique les rendait illisibles.

               Une **étroite**, et grasse, d'un corps en dessous. La police du
               bureau écrivait « -GTK(dev) » sur 193 pixels quand la gothique
               n'en prend que 153 pour le même texte : à côté d'elle, elle
               avait l'air plus grosse alors que ses capitales sont plus
               courtes — c'était la chasse, pas le corps. La Heros Cn, une
               Helvetica resserrée, tombe à 163 ; la graisse lui rend la
               densité du blackletter, sans quoi elle paraît maigre et étirée ;
               et le corps du dessous l'empêche de disputer la vedette au nom.
               Elle vient du runtime GNOME, comme la Liberation qui la remplace
               si jamais elle manquait — rien de plus à embarquer. */
            .nom-appli { color: @zy_or; padding: 0 18px; }
            .nom-appli-grave { font-family: "Pirata One"; font-size: 2.4em; }
            .nom-appli-mouture { font-family: "TeX Gyre Heros Cn",
                                              "Liberation Sans Narrow", sans-serif;
                                 font-size: 2.2em; font-weight: bold;
                                 padding-left: 4px; }

            .motd { background: @zy_variante;
                    border-radius: 8px; padding: 8px 10px; }

            /* La barre d'attente. Le filet de trois pixels d'Adwaita disparait
               dans une barre d'outils, et son curseur -- un gris clair sur un
               gris sombre -- ne se voit pas courir. Huit pixels de haut et la
               sarcelle de l'application le rendent lisible sans le rendre
               tapageur : on demande a l'oeil de constater que ca travaille,
               pas de suivre une progression, puisqu'il n'y en a pas a suivre. */
            progressbar.attente trough,
            progressbar.attente progress { min-height: 8px; border-radius: 4px; }
            progressbar.attente progress { background: @zy_sarcelle; }
            /* Et sans ce `min-width`, rien de ce qui precede ne se voit :
               Adwaita pose un plancher de cent cinquante-deux pixels sur la
               gouttiere, et `set_size_request` ne descend jamais sous le
               minimum du theme -- il prend le plus grand des deux. La largeur
               demandee en Python etait donc lettre morte, a cent vingt comme a
               soixante. On leve le plancher ici, le nombre reste la-bas. */
            progressbar.attente,
            progressbar.attente trough { min-width: 0; }
            /* `.zebre` et non `row.zebre` : le zébrage sert aussi aux blocs de
               matières, qui sont des boîtes et non des lignes de liste. Une
               pointe de sarcelle plutôt qu'un gris : c'est ce qui fait la
               différence entre un tableau terne et un tableau habillé. */
            .zebre { background: mix(@zy_surface, @zy_sarcelle, 0.14); }
            /* Le vert de l'application pour ce qui est monté au maximum. */
            /* Sans gras : la police epaissie a la volee rend le vert flou. La couleur
               suffit a dire que c'est monte au maximum. */
            .fini { color: mix(@zy_sarcelle, white, 0.35); }
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
            /* Les lignes choisies du journal. Le meme sarcelle que le survol,
               un peu plus soutenu : c'est un etat qui dure, pas un passage. */
            .ligne-choisie { background: alpha(@zy_sarcelle, 0.38); }
            /* Les triangles du registre : la couleur porte le sens, la
               direction le confirme. */
            .tri-arrivee { color: #4caf50; font-weight: bold; }
            .tri-depart  { color: @zy_erreur; font-weight: bold; }
            .tri-grade   { color: @zy_or; font-weight: bold; }
            /* La retrogradation garde la couleur du texte : seule la montee
               se signale. */
            .tri-retro   { color: @zy_texte; font-weight: bold; }
        """)
        provider.load_from_data(self._au_zoom(feuille).encode("utf-8"))
        if premier_passage:
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _update_entity_header(self, ent, entry) -> None:
        if ent.money:
            try:
                amount = f"{int(ent.money):,}".replace(",", " ")
            except ValueError:
                amount = ent.money
            self._dappers_lbl.set_text(f"{amount} dappers")
            self._bourse_img.set_visible(True)
        else:
            self._dappers_lbl.set_text("")
            self._bourse_img.set_visible(False)
        # **Le cadre reste, meme sans message.** Il disparaissait avec lui, et
        # la fenetre entiere remontait de trois lignes : on croyait l'avoir
        # perdu. Un message de guilde va et vient -- il s'efface en jeu, et
        # l'API l'a rendu vide deux jours durant sans qu'on sache pourquoi --
        # alors que le porte-voix, lui, dit ou le lire quand il revient.
        #
        # Pour une guilde seulement : un personnage n'a pas de message du
        # jour, et un cadre vide sur sa fiche ne dirait rien.
        if ent.kind == KIND_GUILD:
            if ent.motd:
                self._motd_lbl.set_text(ent.motd)
                self._motd_lbl.remove_css_class("dim-label")
            else:
                self._motd_lbl.set_text(_("Aucun message de guilde"))
                self._motd_lbl.add_css_class("dim-label")
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

    def _entite_setup(self, _fabrique, item) -> None:
        """Une ligne du sélecteur : une image, puis un nom.

        Une `Gtk.DropDown` ne montre que du texte tant qu'on ne lui donne pas
        de fabrique. Celle-ci sert aussi bien au bouton fermé qu'à la liste
        ouverte — c'est la même par défaut.
        """
        boite = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        boite.append(Gtk.Image())
        boite.append(Gtk.Label(xalign=0.0))
        item.set_child(boite)

    def _contenant_bind(self, _fabrique, item) -> None:
        """Remplit une ligne du sélecteur d'inventaire : image, puis libellé.

        Le sac, l'appartement et les coffres ont la leur ; les montures n'en
        ont pas, et gardent une case vide de la même largeur pour que les
        libellés restent alignés.
        """
        boite = item.get_child()
        image = boite.get_first_child()
        etiquette = image.get_next_sibling()
        chaine = item.get_item()
        etiquette.set_text(chaine.get_string() if chaine is not None else "")

        image.set_pixel_size(self._settings.icone(self.PART_ICONE_BOUTON))
        rang = item.get_position()
        cle = (self._inv_keys[rang]
               if 0 <= rang < len(self._inv_keys) else "")
        if cle.startswith("animal"):
            # Les montures partagent la clé `animal1`, `animal2`… : c'est leur
            # libellé qui dit laquelle — « Zig 1 », « Mektoub 2 », « Monture
            # 3 ». Le mektoub et la monture montrent la même bête, le jeu n'en
            # distingue pas le dessin.
            libelle = chaine.get_string() if chaine is not None else ""
            fichier = "zig.png" if "zig" in libelle.lower() else "mektoub.png"
        else:
            fichier = next((f for prefixe, f in self.IMAGES_CONTENANTS
                            if cle.startswith(prefixe)), "")
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "symboles", fichier) if fichier else ""
        if chemin and os.path.exists(chemin):
            image.set_from_file(chemin)
        else:
            image.clear()

    def _entite_bind(self, _fabrique, item) -> None:
        """Remplit la ligne : l'image de l'entité, ou son genre à défaut."""
        boite = item.get_child()
        image = boite.get_first_child()
        etiquette = image.get_next_sibling()
        chaine = item.get_item()
        etiquette.set_text(chaine.get_string() if chaine is not None else "")

        cote = self._settings.icone(self.PART_ICONE_BOUTON)
        image.set_pixel_size(cote)
        rang = item.get_position()
        entree = (self._entries[rang]
                  if 0 <= rang < len(self._entries) else None)
        portrait = (portrait_en_cache(entree["kind"], str(entree["id"]))
                    if entree else "")
        if portrait:
            image.set_from_file(portrait)
        elif entree is not None and entree["kind"] == KIND_GUILD:
            image.set_from_icon_name("system-users-symbolic")
        else:
            image.set_from_icon_name("avatar-default-symbolic")

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
            # **La minute et la date, et non l'heure seule.** « dans 21 h »
            # laissait ignorer s'il restait une minute ou cinquante-neuf, et
            # obligeait a poser l'addition pour savoir quand se tenir pret --
            # une saison peut changer quatre jours plus tard. Demande des
            # joueurs de la guilde.
            minutes = int(round(td["minutes_to_next"]))
            text = (f"{td['season_name']} · {td['next_season_name']} dans "
                    f"{meteo.duree(minutes, unite=True)}"
                    f" — {meteo.moment_du_changement(minutes)}")
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


    # ----------------------------------------------- Dialogue « Ajouter »
    # ----------------------------------------------------------- Cles API
    def _on_add_clicked(self, _btn) -> None:
        """La fenêtre des clés : on en pose dans un onglet, on les relit dans l'autre.

        Les deux gestes vont ensemble — remplacer une clé expirée, c'est en
        saisir une nouvelle là où l'on vient de lire l'ancienne — et une clé
        qu'on ne peut pas relire est une clé qu'il faut aller rechercher sur le
        site de Ryzom à chaque fois qu'on veut la vérifier.
        """
        dlg = Gtk.Window(title=_("Clés API"), transient_for=self, modal=True)
        dlg.set_default_size(620, 540)
        racine = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        racine.props.margin_top = racine.props.margin_bottom = 14
        racine.props.margin_start = racine.props.margin_end = 14
        dlg.set_child(racine)

        pile = Gtk.Stack()
        pile.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        racine.append(Gtk.StackSwitcher(stack=pile, halign=Gtk.Align.CENTER))
        racine.append(pile)

        pile.add_titled(self._page_ajout_cle(dlg), "ajout", _("Ajouter"))
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pile.add_titled(page, "modif", _("Modifier"))
        self._remplir_page_cles(page, dlg)

        pied = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END)
        fermer = Gtk.Button(label=_("Fermer"))
        fermer.connect("clicked", lambda *_: dlg.close())
        pied.append(fermer)
        racine.append(pied)
        dlg.present()

    # ------------------------------------------------- Onglet « Ajouter »
    def _page_ajout_cle(self, dlg) -> Gtk.Box:
        """Le formulaire d'ajout, tel qu'il était avant d'avoir un voisin."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.props.margin_top = 10

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

        def update_hint(*_args):
            required = (ryzom_api.REQUIRED_MODULES_CHAR if rb_char.get_active()
                        else ryzom_api.REQUIRED_MODULES_GUILD)
            hint.set_text(_("Une clé fait 41 signes. Celles de personnage "
                            "commencent par « c », celles de guilde par « g ». "
                            "Modules requis : ") + ", ".join(required))
        update_hint()
        rb_char.connect("toggled", update_hint)

        key_entry = Gtk.Entry(placeholder_text="Clé API")
        box.append(key_entry)

        # Aller chercher sa cle et la coller : les deux gestes que le
        # telephone offrait deja, et qu'il fallait faire a la main ici --
        # recopier l'adresse du site depuis un texte d'aide non cliquable,
        # puis passer par le menu contextuel du champ.
        gestes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        obtenir = Gtk.LinkButton(uri=ryzom_api.KEY_PAGE,
                                 label=_("Obtenir ma clé"))
        obtenir.set_tooltip_text(ryzom_api.KEY_PAGE)
        gestes.append(obtenir)
        coller = Gtk.Button(label=_("Coller"))
        coller.set_tooltip_text(_("Coller la clé depuis le presse-papiers"))
        gestes.append(coller)
        box.append(gestes)

        def colle(_btn):
            """Le presse-papiers se lit de façon asynchrone en GTK4."""
            def recu(presse, resultat):
                try:
                    texte = presse.read_text_finish(resultat) or ""
                except GLib.Error:
                    return
                key_entry.set_text(texte.strip())
            key_entry.get_clipboard().read_text_async(None, recu)

        coller.connect("clicked", colle)

        name_entry = Gtk.Entry(placeholder_text="Nom affiché (optionnel)")
        box.append(name_entry)

        status = Gtk.Label(xalign=0.0, wrap=True)
        box.append(status)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        add = Gtk.Button(label="Ajouter")
        add.add_css_class("suggested-action")
        buttons.append(add)
        box.append(buttons)

        def do_add(*_args):
            key = key_entry.get_text().strip()
            if not key:
                status.set_text("Veuillez saisir une clé API.")
                return
            if not ryzom_api.is_api_key(key):
                # Ce qui se voit a l'oeil ne vaut pas un aller-retour reseau :
                # une cle tronquee au copier-coller partait quand meme, et l'on
                # attendait la reponse de Ryzom pour l'apprendre.
                status.set_text(_("Cette clé n'a pas la forme d'une clé d'API : "
                                  "41 signes, commençant par « c » ou « g »."))
                return
            is_char = rb_char.get_active()
            kind = KIND_CHARACTER if is_char else KIND_GUILD
            store = self._char_store if is_char else self._guild_store
            add.set_sensitive(False)
            status.set_text("Vérification de la clé…")

            def apres(ent, xml, souci):
                if souci:
                    status.set_text(souci)
                    add.set_sensitive(True)
                    return
                name = name_entry.get_text().strip() or ent.name
                store.save(ent.entity_id, key, name, ent.shard, ent.guild)
                with open(entity_xml_path(kind, ent.entity_id), "wb") as fh:
                    fh.write(xml)
                dlg.destroy()
                self._reload_entities(select_id=ent.entity_id)

            self._verifier_cle(key, kind, apres)

        add.connect("clicked", do_add)
        key_entry.connect("activate", do_add)
        return box

    def _verifier_cle(self, cle: str, kind: str, apres) -> None:
        """Demande à l'API ce que vaut cette clé, puis `apres(ent, xml, souci)`.

        `souci` est le message à afficher, ou une chaîne vide si tout va bien.
        Le même chemin sert à l'ajout et au remplacement : une clé qu'on pose
        sans la vérifier est une entité qui ne se synchronisera jamais, et l'on
        ne le découvre qu'au relevé suivant.
        """
        is_char = kind == KIND_CHARACTER
        fetch = (ryzom_api.fetch_character_xml if is_char
                 else ryzom_api.fetch_guild_xml)
        parse = (ryzom_api.parse_character if is_char
                 else ryzom_api.parse_guild)
        required = (ryzom_api.REQUIRED_MODULES_CHAR if is_char
                    else ryzom_api.REQUIRED_MODULES_GUILD)

        def work():
            xml = fetch(cle)
            return parse(xml, self._sheetdb.name), xml

        def done(result, err):
            if err:
                apres(None, None, f"Échec : {err}")
                return
            ent, xml = result
            missing = ryzom_api.check_modules(ent.modules, required)
            if missing:
                apres(None, None, "Modules manquants : " + ", ".join(missing))
                return
            apres(ent, xml, "")

        run_async(work, done)

    # ------------------------------------------------ Onglet « Modifier »
    def _remplir_page_cles(self, page: Gtk.Box, dlg) -> None:
        """Refait la liste des clés enregistrées, à l'ouverture et après coup."""
        enfant = page.get_first_child()
        while enfant is not None:
            suivant = enfant.get_next_sibling()
            page.remove(enfant)
            enfant = suivant

        scroll = Gtk.ScrolledWindow(vexpand=True)
        liste = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        liste.props.margin_top = 10
        scroll.set_child(liste)
        page.append(scroll)

        vide = True
        for kind, store, mot in ((KIND_CHARACTER, self._char_store, _("personnage")),
                                 (KIND_GUILD, self._guild_store, _("guilde"))):
            for entry in store.entries():
                vide = False
                liste.append(self._ligne_cle(entry, kind, store, mot, page, dlg))
        if vide:
            vide_lbl = Gtk.Label(label=_("Aucune clé enregistrée — l'onglet "
                                         "« Ajouter » est à côté."),
                                 xalign=0.0, wrap=True)
            vide_lbl.add_css_class("dim-label")
            liste.append(vide_lbl)

    def _ligne_cle(self, entry: dict, kind: str, store, mot: str,
                   page: Gtk.Box, dlg) -> Gtk.Box:
        """Une entité : son nom, sa clé en entier, et ce qu'on peut en faire."""
        ligne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        ligne.props.margin_bottom = 10

        titre = Gtk.Label(xalign=0.0)
        titre.set_markup(
            f"<b>{GLib.markup_escape_text(entry['name'])}</b>"
            f"  <span alpha='60%'>{GLib.markup_escape_text(mot)}</span>")
        ligne.append(titre)

        # La cle en entier et selectionnable : la lire est tout l'objet de cet
        # onglet, et une clef tronquee ne se recopie pas a la main. En chasse
        # fixe, ou l'oeil distingue le 0 du O et le 1 du l.
        cle = Gtk.Label(xalign=0.0, selectable=True, wrap=True,
                        wrap_mode=Pango.WrapMode.CHAR)
        cle.set_markup(f"<tt>{GLib.markup_escape_text(entry['key'])}</tt>")
        ligne.append(cle)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                          halign=Gtk.Align.END)
        copier = Gtk.Button(label=_("Copier"))
        copier.set_tooltip_text(_("Copier la clé dans le presse-papiers"))
        copier.connect("clicked", lambda *_: dlg.get_clipboard().set(entry["key"]))
        actions.append(copier)

        changer = Gtk.Button(label="✎")
        changer.set_tooltip_text(_("Remplacer la clé"))
        changer.connect("clicked", lambda *_: self._dialogue_changer_cle(
            entry, kind, store, page, dlg))
        actions.append(changer)

        retirer = Gtk.Button(label="🗑")
        retirer.set_tooltip_text(_("Retirer cette entité"))
        retirer.add_css_class("destructive-action")
        retirer.connect("clicked", lambda *_: self._confirmer_retrait(
            entry, store, page, dlg))
        actions.append(retirer)
        ligne.append(actions)

        ligne.append(Gtk.Separator())
        return ligne

    def _dialogue_changer_cle(self, entry: dict, kind: str, store,
                              page: Gtk.Box, dlg) -> None:
        """Remplace la clé d'une entité déjà connue, après l'avoir vérifiée.

        La nouvelle clé peut désigner une autre entité — on s'est trompé de
        ligne, ou l'on a repris la clé d'un autre personnage. L'ancienne entrée
        est alors retirée : sans quoi la liste porterait deux fois la même
        entité, l'une avec une clé qui n'est plus la sienne.
        """
        petit = Gtk.Window(title=_("Remplacer la clé"), transient_for=dlg,
                           modal=True)
        petit.set_default_size(460, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.props.margin_top = box.props.margin_bottom = 14
        box.props.margin_start = box.props.margin_end = 14
        petit.set_child(box)

        box.append(Gtk.Label(xalign=0.0, wrap=True, label=_(
            "Nouvelle clé pour « {} ». Elle est vérifiée auprès de Ryzom avant "
            "d'être enregistrée.").format(entry["name"])))
        saisie = Gtk.Entry(placeholder_text=_("Clé API"), text=entry["key"])
        box.append(saisie)
        etat = Gtk.Label(xalign=0.0, wrap=True)
        box.append(etat)

        boutons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        annuler = Gtk.Button(label=_("Annuler"))
        annuler.connect("clicked", lambda *_: petit.close())
        valider = Gtk.Button(label=_("Remplacer"))
        valider.add_css_class("suggested-action")
        boutons.append(annuler)
        boutons.append(valider)
        box.append(boutons)

        def poser(*_args):
            cle = saisie.get_text().strip()
            if not cle:
                etat.set_text(_("Veuillez saisir une clé API."))
                return
            if not ryzom_api.is_api_key(cle):
                etat.set_text(_("Cette clé n'a pas la forme d'une clé d'API : "
                                "41 signes, commençant par « c » ou « g »."))
                return
            valider.set_sensitive(False)
            etat.set_text(_("Vérification de la clé…"))

            def apres(ent, xml, souci):
                if souci:
                    etat.set_text(souci)
                    valider.set_sensitive(True)
                    return
                if ent.entity_id != entry["id"]:
                    store.remove(entry["id"])
                store.save(ent.entity_id, cle, entry["name"] or ent.name,
                           ent.shard, ent.guild)
                with open(entity_xml_path(kind, ent.entity_id), "wb") as fh:
                    fh.write(xml)
                petit.close()
                self._remplir_page_cles(page, dlg)
                self._reload_entities(select_id=ent.entity_id)

            self._verifier_cle(cle, kind, apres)

        valider.connect("clicked", poser)
        saisie.connect("activate", poser)
        petit.present()

    def _confirmer_retrait(self, entry: dict, store, page: Gtk.Box, dlg) -> None:
        """Le retrait se demande deux fois : les trois boutons sont voisins.

        Celui de la barre principale ne demande rien, mais il porte sur
        l'entité qu'on est en train de regarder. Ici on vise une ligne dans une
        liste, et la corbeille est à un centimètre de « Copier ».
        """
        question = Gtk.AlertDialog()
        question.set_message(_("Retirer « {} » ?").format(entry["name"]))
        question.set_detail(_("Sa clé sera oubliée. Rien n'est supprimé chez "
                              "Ryzom, et la remettre suffit à la retrouver."))
        question.set_buttons([_("Annuler"), _("Retirer")])
        question.set_cancel_button(0)
        question.set_default_button(0)

        def repondu(source, resultat):
            try:
                if source.choose_finish(resultat) != 1:
                    return
            except GLib.Error:
                return          # fenetre fermee sans repondre
            store.remove(entry["id"])
            self._remplir_page_cles(page, dlg)
            self._reload_entities()

        question.choose(dlg, None, repondu)

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
        # Le numéro n'est plus dans le nom : c'est ici qu'on vient le lire quand
        # on demande à un joueur « tu as laquelle ? ».
        about.set_version(VERSION)
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
        # Le corps du texte prend effet sur-le-champ, comme dans la version
        # Qt : il fallait fermer et rouvrir la fenêtre pour voir le réglage,
        # et on croyait qu'il ne marchait pas. La feuille est rejouée avec la
        # nouvelle taille, sur le fournisseur déjà en place.
        self._install_motd_css()
        self._apply_proxy()
        self._load_names(self._settings.pack_file)
        self._schedule_sync()          # nouvel intervalle, sans redémarrer
        if not self._settings.notifications:
            self._retirer_notification()
        self._update_bell()
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
        # Une mise a jour se compte en dizaines de secondes, portail compris :
        # c'est la plus longue attente de l'application, et c'etait la seule
        # que la barre ne disait pas. La version Qt la montrait deja.
        self._maj_en_cours = True
        self._attendre(True)
        self._updater.update()

    def _on_update_progress(self, message: str, done: bool, failed: bool) -> None:
        self._set_status(message)
        if done and self._maj_en_cours:
            self._maj_en_cours = False
            self._attendre(False)
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
        """L'application est occupée à une tâche qui interdit les autres.

        Distinct de l'attente : `_busy` empêche une seconde synchronisation et
        grise le bouton, l'attente ne fait que montrer que ça travaille. Une
        grille dont les icônes arrivent est en attente sans être occupée — on
        peut la trier, la filtrer, en changer.
        """
        self._busy = busy
        self._attendre(busy)
        if busy and message:
            self._set_status(message)

    def _attendre(self, oui: bool) -> None:
        """Une raison d'attendre de plus, ou de moins.

        Un compteur, et non un drapeau : plusieurs travaux se recouvrent — une
        synchronisation pendant que les icônes d'un coffre arrivent, une mise à
        jour qui se télécharge pendant qu'on change d'inventaire. Le premier
        arrivé allume la barre, le dernier parti l'éteint ; avec un drapeau, le
        premier fini l'éteignait au nez des autres.

        **La barre tient seule son animation** : elle démarre son minuteur en
        devenant visible, l'arrête en se cachant. Le piloter d'ici demandait de
        tenir un identifiant à jour depuis deux endroits, et il s'y perdait —
        la barre restait alors visible, et figée.
        """
        self._attentes = max(0, self._attentes + (1 if oui else -1))
        self._spinner.set_visible(self._attentes > 0)

    def _on_zoom_icones(self, _btn, pas: int) -> None:
        """Agrandit ou réduit **toute** l'application, et la redessine.

        Images, texte, bordures, hauteurs de rangées : le zoom est le seul
        réglage d'apparence depuis qu'il a remplacé la taille du texte. Tout
        prend effet sur-le-champ — la feuille de style est rejouée ici même,
        et non au prochain lancement : l'ancien réglage de police, lui,
        demandait de fermer l'application, et l'on croyait qu'il ne marchait
        pas.
        """
        reglages = self._settings
        voulu = reglages.zoom_voisin(1 if pas > 0 else -1)
        if voulu == reglages.zoom:
            return
        reglages.zoom = voulu
        self._install_motd_css()
        self._appliquer_taille_boutons()
        self._redisplay_current()
        # **Et les écrans de « Bonus », que `_redisplay_current` ne voit pas :
        # il ne refait que la grille de l'inventaire.** Leurs images ne sont
        # pas des boutons — l'emblème d'un avant-poste, le symbole d'une
        # famille de matières sont posés à la construction de la ligne, et
        # rien ne les retaille ensuite. Sans ce rappel, ils restaient seuls à
        # leur taille pendant que tout le reste grossissait, jusqu'au prochain
        # « Actualiser ». C'est ce que fait la version Qt au même endroit.
        # Les deux sortent d'elles-mêmes tant que rien n'a été chargé.
        self._refresh_outposts()
        self._refresh_meteo()
        # **Et le journal, oublie jusqu'ici.** Ses icones sont posees a la
        # taille du zoom au moment ou la ligne se construit, et ses colonnes se
        # calent sur ce que mesurent ses etiquettes. Sans le refaire, la grille
        # restait a l'echelle precedente : le zoom decalait les colonnes, et le
        # retour en arriere ne les remettait pas -- la qualite restait collee
        # aux noms. Il sort de lui-meme tant qu'aucune entite n'est chargee.
        self._refresh_log()
        self._set_status(_("Zoom : {} %").format(round(reglages.zoom * 100)))

    def _cote_icone_barre(self) -> int:
        """Le cote des icones de la barre du haut, en pixels.

        **Une fois et demie rien : la meme formule que la version Qt**, qui
        prend `1,1 fois la hauteur d'une ligne de texte`. Les boutons de la
        barre GTK s'en tenaient aux seize pixels que `Gtk.Button` donne par
        defaut, quel que soit le corps : le plus de l'ajout et la corbeille y
        paraissaient plus petits qu'en face, et ne bougeaient pas d'un cheveu
        quand tout le reste doublait.

        La hauteur se mesure sur un libelle plutot que sur la police du
        contexte : c'est la feuille de style qui pose le corps, et le contexte
        Pango, lui, rend encore celui du theme.
        """
        temoin = Gtk.Label(label="Hg")
        _mini, naturel, _a, _b = temoin.measure(Gtk.Orientation.VERTICAL, -1)
        return max(1, round(naturel * 1.1))

    def _appliquer_taille_icones_barre(self) -> None:
        """Pose cette taille sur les images des boutons d'action."""
        cote = self._cote_icone_barre()
        for image in getattr(self, "_icones_barre", ()):
            if image is not None:
                image.set_pixel_size(cote)

    def _appliquer_taille_boutons(self) -> None:
        """Les images des boutons suivent elles aussi les boutons de zoom.

        Les deux onglets, le menu « Bonus », ses cinq entrées et la bourse du
        pied : tout ce qui porte une image la voit grandir avec le reste.
        """
        for image, part in getattr(self, "_images_boutons", ()):
            image.set_pixel_size(self._settings.icone(part))
        # Les icones de la barre du haut suivent le corps du texte, et non la
        # part des icones : c'est ainsi que la version Qt les mesure.
        self._appliquer_taille_icones_barre()
        if hasattr(self, "_bourse_img"):
            self._bourse_img.set_pixel_size(
                self._settings.icone(self.PART_BOURSE))

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
