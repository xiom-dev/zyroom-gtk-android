"""Fenêtre principale de ZyRoom Qt.

**La mise en page est celle de ZyRoom-GTK**, à l'identique : une barre de
titre qui porte les actions et la navigation, une bande sombre pour les deux
sélecteurs, la ligne de volume, la ligne de recherche et de tri, la grille
d'objets, et en bas la bande d'état — portrait, nom de l'application gravé au
centre, dappers à droite, signature dessous. Les écarts tiennent tous à ce que
Qt ne sait pas faire comme GTK, et sont commentés sur place.

Ce qui fonctionne de bout en bout : configuration, ajout de clé, relevé de
l'API, affichage hors-ligne du cache, contenants, volume, grille avec icônes
et gouttes de bonus, recherche, filtres et tri. Le journal des mouvements et
les cinq écrans du menu « Bonus » ont leur place dans la fenêtre mais restent
à porter.

**Ce fichier ne calcule rien.** Volumes, tri, noms lisibles, analyse XML
viennent du noyau partagé avec ZyRoom-GTK, qui ne connaît ni Qt ni GTK.
"""
from __future__ import annotations

import html
import os
import threading
import unicodedata
from datetime import datetime

from PySide6.QtCore import QEvent, QSize, Qt, QObject, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QGuiApplication, QIcon,
                           QPainter, QPixmap)
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog,
                               QFileDialog, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow,
                               QMenu, QMessageBox, QProgressBar, QPushButton,
                               QScrollArea, QSpinBox, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction)

from . import (alerts, apropos, backup, chatlog, cles, detail, enchantements,
               i18n, movements, notifications, outposts, partage, polices,
               roster, ryzom_api, sorting, specialites, theme, updater)
from .categorydb import CategoryDb
from .config import (CATEGORY_CSV, SHEETID_CSV, EntityStore, Settings,
                     data_dir, detect_pack, detect_save_folder,
                     entity_xml_path, format_last_sync,
                     guard_path, last_sync, movements_path, names_cache_path,
                     portrait_path, snapshot_path)
from .i18n import _
from .icones import ChargeurIcones
from .models import (CLASS_NAMES, ECOSYSTEM_NAMES, EQUIP_NAMES, TYPE_NAMES,
                     ItemInfo, ItemType)
from .namedb import NameDb
from .options import FenetreOptions
from .page_alertes import DialogueSurveillance, FenetreAlertes
from .page_betes import PageBetes
from .page_meteo import PageMeteo
from .page_outposts import PageAvantPostes
from .page_roster import PageEffectif
from .page_skills import PageCompetences
from .ryzom_api import KIND_CHARACTER, KIND_GUILD, ApiError, Entity
from .sheetdb import SheetDb
from .watch import KIND_DURABILITY, WatchStore, watch_kind

#: Taille des icones de la grille, en pixels. La meme que dans la version GTK.
TAILLE_ICONE = 48

#: Intervalle de verification des mises a jour, en secondes. Un quart
#: d'heure, comme la resynchronisation.
MAJ_INTERVALLE = 15 * 60

#: L'icone du sort grave dans un objet, posee sur la sienne.
#:
#: Vingt : l'API la rend en vingt-quatre, mais sur une case de quarante-huit
#: elle mangerait le quart de l'objet. Vingt se reconnait encore -- un eclair,
#: une goutte, un missile -- sans qu'on cherche ce qu'il y a dessous.
TAILLE_ICONE_SORT = 20

#: Cadence du rafraichissement de la saison d'Atys, en secondes. Elle avance
#: toute seule : sans cela, la ligne du haut se perime entre deux releves.
SAISON_INTERVALLE = 180

from . import __version__ as VERSION

#: Vrai dans la variante du mainteneur, celle qui montre les coffres masques.
#:
#: La version GTK se reconnait a son FLATPAK_ID, qui finit par ".dev" ; ici il
#: n'y a pas de bac a sable pour le dire. C'est donc la variable qui leve le
#: masque des coffres qui fait foi : la seule difference entre les deux
#: variantes est justement celle-la, et un lanceur qui la pose lance bien la
#: mouture du mainteneur.
_DEV = os.environ.get("ZYROOM_SHOW_ALL_CHESTS") == "1"

# Nom affiche, tenu identique a celui des fichiers .desktop des deux
# variantes. Sans numero de version : un nom nomme l'application, le numero se
# lit dans l'A propos.
APP_NAME = "ZyRoom-Qt(dev)" if _DEV else "ZyRoom-Qt"

#: La part du nom qui va dans la gothique, en bas de la fenetre : celle qui
#: vient du zyRoom d'origine. Le reste -- "-Qt" -- dit la mouture, et s'ecrit
#: dans une etroite d'imprimerie.
NOM_GRAVE = "ZyRoom"

SIGNATURE = "Original by Misugi, fork by Xiom"

#: Hauteur du portrait de la barre d'etat. Une signature sous la grille, pas
#: une illustration.
HAUTEUR_PORTRAIT = 44

_PREFIXE_GENRE = {KIND_CHARACTER: "👤", KIND_GUILD: "🛡"}

#: Le role ou chaque case de la grille range l'objet qu'elle montre. Qt sait
#: porter un objet Python tel quel : le menu contextuel et le double-clic le
#: reprennent sans avoir a chercher dans une liste parallele.
_ROLE_OBJET = Qt.ItemDataRole.UserRole + 1

#: Les cinq ecrans de consultation du menu "Bonus", comme dans la version
#: GTK : six onglets ne tenaient pas dans une barre de titre.
PLUS_PAGES = (("skills", "Compétences"), ("roster", "Effectif"),
              ("betes", "Perdu ?"), ("outposts", "Avant-postes"),
              ("meteo", "Météo"))

TRI_LIBELLES = ("Ordre d'origine", "Type", "Écosystème", "Classe", "Qualité",
                "Volume", "Quantité", "Prix", "Nom")

#: Taille des icones du journal, en pixels.
#:
#: Vingt-quatre : la hauteur d'une ligne de texte. Plus grand, chaque mouvement
#: occuperait deux lignes et l'on en verrait deux fois moins d'un coup d'oeil
#: -- or le journal se parcourt.
TAILLE_ICONE_JOURNAL = 24

#: La memoire du journal, en jours. Tout ce qui est plus recent s'affiche,
#: quel qu'en soit le nombre de lignes. Une semaine est ce qu'il faut pour
#: retrouver "qui a pris quoi" apres un week-end.
JOURNAL_JOURS = 7

#: Ce qu'on montre malgre tout apres une semaine calme : une page vide
#: n'apprend rien, et un petit coffre peut ne bouger qu'une fois par mois.
JOURNAL_MINIMUM = 400

#: Plafond dur, pour un journal qu'on aurait laisse courir.
JOURNAL_MAX = 3000

#: Le vert de ce qui entre et le rouge de ce qui sort : la couleur est ce
#: qu'on lit en premier en parcourant une colonne de chiffres.
VERT_ENTREE = "#4caf50"
ROUGE_SORTIE = "#e05252"


class _Passerelle(QObject):
    """Ramène le résultat d'un thread vers le thread de l'interface.

    L'équivalent exact du `run_async` de la version GTK, qui reposait sur
    `GLib.idle_add`. Ici c'est un signal en `QueuedConnection` : émis depuis
    n'importe quel thread, il se déclenche sur celui qui possède l'objet.
    """

    fini = Signal(object, object, object)     # rappel, resultat, erreur

    def __init__(self) -> None:
        super().__init__()
        self.fini.connect(self._livrer, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _livrer(rappel, resultat, erreur) -> None:
        rappel(resultat, erreur)

    def lancer(self, travail, apres) -> None:
        """Exécute `travail()` dans un thread, puis `apres(resultat, erreur)`."""
        def coureur():
            try:
                res, err = travail(), None
            except Exception as exc:          # noqa: BLE001 -- remonte a l'UI
                res, err = None, exc
            self.fini.emit(apres, res, err)
        threading.Thread(target=coureur, daemon=True).start()


def _norm(texte: str) -> str:
    """Minuscule sans accents, pour une recherche tolérante."""
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c)).lower()


def _bouton_icone(nom_theme: str, repli: str, infobulle: str) -> QToolButton:
    """Un bouton d'action de la barre du haut.

    `QIcon.fromTheme` sert les icônes symboliques du bureau sous Linux, comme
    le fait GTK. Sous Windows il n'existe pas de thème d'icônes : le repli
    textuel prend alors la place, et c'est pourquoi chaque appel en fournit un.
    """
    bouton = QToolButton()
    icone = QIcon.fromTheme(nom_theme)
    if icone.isNull():
        bouton.setText(repli)
    else:
        bouton.setIcon(icone)
        # Sans cela l'icone reste au seize pixels par defaut de Qt, quelle que
        # soit la taille du texte : la fleche de synchro et la corbeille
        # restaient minuscules a cote de libelles grossis.
        cote = theme.largeur(bouton, 1.1)
        bouton.setIconSize(QSize(cote, cote))
    bouton.setToolTip(infobulle)
    bouton.setAutoRaise(True)
    return bouton


class FenetrePrincipale(QMainWindow):
    #: L'avancement du telechargement, emis depuis le fil de travail. Un
    #: signal et non un appel direct : toucher a l'interface depuis un autre
    #: fil est interdit, ici comme partout.
    _progres = Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self._progres.connect(self._on_progres_maj)
        self.setWindowTitle(APP_NAME)

        self._char_store = EntityStore("characters.ini")
        self._guild_store = EntityStore("guilds.ini")
        self._settings = Settings()
        self.resize(*self._settings.window_size)
        i18n.set_language(self._settings.language)

        self._sheetdb = SheetDb()
        self._sheetdb.load(SHEETID_CSV)
        self._categorydb = CategoryDb()
        self._categorydb.load(CATEGORY_CSV)

        self._names = NameDb(names_cache_path())
        self._charger_noms(self._settings.pack_file or detect_pack())

        self._icones = ChargeurIcones()
        self._passerelle = _Passerelle()

        self._entrees: list[dict] = []
        self._entite: Entity | None = None
        #: (case, objet, cle de recherche) pour chaque objet de la grille.
        self._cases: list[tuple[QListWidgetItem, object, str]] = []
        #: Invalide les icones et portraits en vol : quand on change de
        #: contenant, ceux qui arrivent encore sont d'un affichage perime.
        self._generation = 0
        self._generation_portrait = 0
        self._chemin_portrait = ""
        #: Les entites deja relevees depuis l'ouverture : on ne resynchronise
        #: qu'une fois par entite, pas a chaque aller-retour dans la liste.
        self._relevees: set[tuple[str, str]] = set()
        self._occupe = False

        # Etat des filtres et du tri. Le tri se retrouve comme on l'a laisse :
        # c'est un reglage qu'on pose une fois pour toutes.
        self._tri_index, self._tri_desc = self._settings.sort_order
        if self._tri_index >= len(TRI_LIBELLES):
            self._tri_index = Settings.TRI_DEFAUT[0]
        self._f_types = set(range(len(TYPE_NAMES)))
        self._f_ecosys = set(range(len(ECOSYSTEM_NAMES)))
        self._f_classes = set(range(len(CLASS_NAMES)))
        self._f_equips = set(range(len(EQUIP_NAMES)))
        self._f_bonus = set(range(len(specialites.SPECIALITES)))
        self._toutes_cases: list[QCheckBox] = []

        #: Ce que la cloche annonce, et la liste des objets surveilles de
        #: l'entite affichee. Le mouvement du tresor rapporte par le dernier
        #: releve est garde jusqu'au suivant : sans cela, l'alerte
        #: disparaitrait au premier recalcul sans reseau -- ouvrir les options
        #: suffisait a la faire taire.
        self._alertes: list = []
        self._watch: WatchStore | None = None
        self._mouvements_argent: list = []

        #: Le journal de l'entite affichee, relu du disque a chaque ouverture
        #: de l'onglet. Sa propre generation d'icones : il se redessine a
        #: chaque frappe dans sa recherche.
        self._journal: list = []
        self._generation_journal = 0
        #: Les icones du journal restant a chercher, par numero de ligne, et
        #: celles deja lues -- un journal repete beaucoup les memes objets.
        self._icones_a_venir: dict = {}
        self._cache_icones: dict = {}

        #: La derniere guilde et le dernier personnage rencontres. Les ecrans
        #: de "Bonus" s'ouvrent sur eux quelle que soit l'entite choisie :
        #: les avant-postes ne dependent d'aucune, l'effectif est celui de sa
        #: guilde, et l'arbre celui de son personnage -- passer de l'un a
        #: l'autre pour consulter n'aurait aucun sens.
        self.derniere_guilde = None
        self.dernier_perso = None
        #: Le journal des prises d'avant-postes : un seul jeu de fichiers pour
        #: tout le serveur, la carte ne dependant d'aucune cle.
        self.magasin_avant_postes = outposts.OutpostStore(data_dir())

        #: La releve automatique. Un seul minuteur, reprogramme quand les
        #: options changent d'intervalle -- sans redemarrer l'application.
        self._minuteur = QTimer(self)
        self._minuteur.timeout.connect(self._tour_de_releve)

        #: La veille des mises a jour. Le nettoyage d'abord : c'est au
        #: lancement, et a ce moment seulement, que plus rien ne tient
        #: l'installation precedente.
        updater.nettoyer_ancienne()
        self._veilleur = updater.Veilleur()
        self._minuteur_maj = QTimer(self)
        self._minuteur_maj.timeout.connect(self._verifier_maj)
        self._minuteur_saison = QTimer(self)
        self._minuteur_saison.timeout.connect(self._rafraichir_saison)

        # Le proxy avant tout appel reseau : la premiere synchro part des
        # `_recharger_entites` ci-dessous.
        self._appliquer_proxy()
        self._construire_ui()
        self._recharger_entites()
        self._programmer_releve()
        # Au lancement, puis tous les quarts d'heure -- la meme cadence a
        # laquelle on regarde deja si quelque chose a change ailleurs.
        self._verifier_maj()
        self._minuteur_maj.start(MAJ_INTERVALLE * 1000)
        # Ce que le depot publie du journal de guilde, verse sans rien
        # demander. Apres `_recharger_entites` : c'est elle qui dit quelles
        # entites suivre.
        self._relire_journaux_publies()
        # La saison d'Atys avance toute seule : on la redemande, plutot que de
        # la laisser se perimer jusqu'au prochain releve.
        self._rafraichir_saison()
        self._minuteur_saison.start(SAISON_INTERVALLE * 1000)

    # ------------------------------------ Ce que les pages de "Bonus" lisent
    #
    # Elles vivent dans leurs propres modules et ne connaissent de la fenetre
    # que ces quelques noms : de quoi lire l'entite affichee, les noms
    # d'objets, le chargeur d'icones et la passerelle vers les threads.

    @property
    def entite(self):
        return self._entite

    @property
    def noms(self):
        return self._names

    @property
    def icones(self):
        return self._icones

    @property
    def passerelle(self):
        return self._passerelle

    def entite_en_cache(self, genre: str):
        """La première entité de ce genre, relue du cache disque.

        Sert aux écrans de « Bonus » : ils doivent s'ouvrir quelle que soit
        l'entité choisie, y compris au tout premier lancement où rien n'a
        encore été affiché. Le cache est celui qui rend déjà l'application
        consultable hors ligne — **aucun appel réseau ici**.
        """
        for entree in self._entrees:
            if entree["kind"] != genre:
                continue
            chemin = entity_xml_path(genre, entree["id"])
            if not os.path.isfile(chemin):
                continue
            try:
                with open(chemin, "rb") as fh:
                    brut = fh.read()
                analyser = (ryzom_api.parse_character if genre == KIND_CHARACTER
                            else ryzom_api.parse_guild)
                return analyser(brut, self._sheetdb.name)
            except Exception:                           # noqa: BLE001
                continue
        return None

    # ------------------------------------------------------------------ UI
    def _construire_ui(self) -> None:
        central = QWidget()
        colonne = QVBoxLayout(central)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(0)

        colonne.addWidget(self._entete())
        colonne.addWidget(self._barre_entite())
        colonne.addWidget(self._motd())

        self._pile = QStackedWidget()
        self._pages = {}
        for nom, page in (("inventory", self._page_inventaire()),
                          ("log", self._page_journal()),
                          ("plus", self._page_bonus())):
            self._pages[nom] = self._pile.addWidget(page)
        colonne.addWidget(self._pile, 1)

        colonne.addWidget(self._pied())
        self.setCentralWidget(central)
        self._montrer_page("inventory")

    def _entete(self) -> QWidget:
        """La barre du haut, à l'image de la `Gtk.HeaderBar` de la version GTK.

        **Un widget, et non la vraie barre de titre.** GTK4 dessine lui-même
        la décoration de la fenêtre et y loge des boutons ; Qt laisse cela au
        gestionnaire de fenêtres, et le lui reprendre demanderait une fenêtre
        sans cadre — donc de redessiner à la main le déplacement, le
        redimensionnement et les boutons système, différemment sous Linux et
        sous Windows. On garde donc la décoration native, et cette bande juste
        dessous porte le même contenu, dans le même ordre.
        """
        barre = QWidget()
        barre.setObjectName("entete")
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(6, 4, 6, 4)
        ligne.setSpacing(4)

        # A gauche : ce qui parle de l'entite affichee.
        btn_ajout = _bouton_icone("list-add-symbolic", "+",
                                  _("Clés API : en ajouter une, relire ou "
                                    "remplacer celles qu'on a"))
        btn_ajout.clicked.connect(self._on_ajouter)
        ligne.addWidget(btn_ajout)

        self._btn_retirer = _bouton_icone("user-trash-symbolic", "🗑",
                                          _("Retirer l'entité sélectionnée"))
        self._btn_retirer.clicked.connect(self._on_retirer)
        self._btn_retirer.setEnabled(False)
        ligne.addWidget(self._btn_retirer)

        # La cloche va a gauche, avec l'ajout et le retrait : ce sont les
        # boutons qui parlent de l'entite affichee.
        self._cloche = QToolButton()
        self._cloche.setText("🔔")
        self._cloche.setToolTip(_("Alertes"))
        self._cloche.setAutoRaise(True)
        self._cloche.clicked.connect(self._on_cloche)
        ligne.addWidget(self._cloche)

        ligne.addStretch(1)
        ligne.addWidget(self._navigation())
        ligne.addStretch(1)

        # A droite : ce qui parle de l'application.
        self._btn_maj = QPushButton("⬆ " + _("Mettre à jour"))
        self._btn_maj.setObjectName("principal")
        self._btn_maj.setVisible(False)
        self._btn_maj.clicked.connect(self._on_maj_clic)
        ligne.addWidget(self._btn_maj)

        # Le zoom des icones de l'inventaire, a portee de main. La molette
        # avec Ctrl le fait aussi, mais elle n'atteint pas tous les pointeurs
        # -- et deux boutons se voient, ce qu'un raccourci ne fait jamais.
        for signe, pas, mot in (("−", -8, _("Réduire les icônes")),
                                ("+", 8, _("Agrandir les icônes"))):
            bouton = QToolButton()
            bouton.setText(signe)
            bouton.setToolTip(mot)
            bouton.setAutoRaise(True)
            # Le meme corps que les symboles voisins : un plus et un moins a
            # la taille du texte se perdaient a cote de la fleche de synchro.
            police = bouton.font()
            police.setPointSizeF(police.pointSizeF() * 1.6)
            police.setBold(True)
            bouton.setFont(police)
            bouton.clicked.connect(
                lambda _c=False, p=pas: self._zoomer_icones(p))
            ligne.addWidget(bouton)

        self._btn_relever = _bouton_icone("view-refresh-symbolic", "🔄",
                                          _("Resynchroniser depuis l'API"))
        self._btn_relever.clicked.connect(self._on_relever)
        self._btn_relever.setEnabled(False)
        ligne.addWidget(self._btn_relever)

        btn_pack = _bouton_icone(
            "document-open-symbolic", "📂",
            _("Charger string_client.pack (noms d'items lisibles)"))
        btn_pack.clicked.connect(self._on_pack)
        ligne.addWidget(btn_pack)

        menu_btn = QToolButton()
        menu_btn.setText("☰")
        menu_btn.setToolTip(_("Menu"))
        menu_btn.setAutoRaise(True)
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(menu_btn)
        menu.addAction(_("Options…"), self._on_options)
        menu.addAction(_("Analyser un chatlog…"), self._on_chatlog)
        menu.addAction(_("Sauvegarder maintenant"), self._on_sauvegarde)
        menu.addAction(_("À propos…"), self._on_apropos)
        menu_btn.setMenu(menu)
        ligne.addWidget(menu_btn)
        return barre

    def _navigation(self) -> QWidget:
        """Les deux onglets et le menu « Bonus », comme dans la barre GTK.

        Deux boutons bascule liés et un menu déroulant : l'inventaire et le
        journal — ce qu'on consulte tous les jours — restent à un clic, et les
        cinq écrans de consultation vivent sous « Bonus ».
        """
        boite = QWidget()
        ligne = QHBoxLayout(boite)
        ligne.setContentsMargins(0, 0, 0, 0)
        # Zero espacement : les trois boutons se touchent, comme la classe
        # "linked" de GTK qui en fait un seul bloc.
        ligne.setSpacing(0)

        self._nav_boutons = {}
        for nom, etiquette in (("inventory", _("Inventaire")),
                               ("log", _("Journal"))):
            bouton = QPushButton(etiquette)
            bouton.setCheckable(True)
            bouton.setObjectName("nav")
            bouton.clicked.connect(lambda _c, n=nom: self._montrer_page(n))
            self._nav_boutons[nom] = bouton
            ligne.addWidget(bouton)

        self._btn_plus = QToolButton()
        self._btn_plus.setText(_("Bonus"))
        self._btn_plus.setObjectName("nav")
        self._btn_plus.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._btn_plus.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        menu = QMenu(self._btn_plus)
        for nom, etiquette in PLUS_PAGES:
            action = QAction(_(etiquette), menu)
            action.triggered.connect(
                lambda _c=False, n=nom: self._montrer_bonus(n))
            menu.addAction(action)
        self._btn_plus.setMenu(menu)
        ligne.addWidget(self._btn_plus)
        return boite

    def _montrer_page(self, nom: str) -> None:
        """Change de page et aligne les boutons dessus.

        C'est la pile qui fait foi, jamais l'état d'un bouton : le clavier, le
        code et la souris peuvent tous changer de page.
        """
        self._pile.setCurrentIndex(self._pages[nom])
        for autre, bouton in self._nav_boutons.items():
            bouton.setChecked(autre == nom)
        if nom == "log":
            self._charger_journal()
        # Le bouton s'appelle "Bonus", toujours : c'est un menu, et un menu
        # ne prend pas le nom de ce qu'on y a choisi. Seul son etat enfonce
        # dit qu'on est dans l'une de ses pages.
        self._btn_plus.setProperty("actif", nom == "plus")
        self._btn_plus.style().unpolish(self._btn_plus)
        self._btn_plus.style().polish(self._btn_plus)

    def _barre_entite(self) -> QWidget:
        """Ligne 1 : sélecteurs d'entité et d'inventaire, puis la saison.

        Le même gris sombre qu'en bas : les deux bandes encadrent la grille.
        """
        barre = QWidget()
        barre.setObjectName("bande")
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(8, 6, 8, 6)
        ligne.setSpacing(8)

        ligne.addWidget(QLabel(_("Entité :")))
        self._dd_entite = QComboBox()
        self._dd_entite.setMinimumWidth(200)
        self._dd_entite.currentIndexChanged.connect(self._on_entite_choisie)
        ligne.addWidget(self._dd_entite)

        ligne.addWidget(QLabel(_("Inventaire :")))
        self._dd_inv = QComboBox()
        self._dd_inv.setMinimumWidth(200)
        self._dd_inv.currentIndexChanged.connect(self._on_contenant_choisi)
        ligne.addWidget(self._dd_inv)

        # Le tourniquet de la synchro. Qt n'a pas de `Gtk.Spinner` : une barre
        # de progression sans bornes tourne en boucle et dit la meme chose.
        self._tourniquet = QProgressBar()
        self._tourniquet.setRange(0, 0)
        self._tourniquet.setTextVisible(False)
        self._tourniquet.setFixedSize(48, 10)
        self._tourniquet.setVisible(False)
        ligne.addWidget(self._tourniquet)

        ligne.addStretch(1)
        self._lbl_saison = QLabel()
        self._lbl_saison.setObjectName("valeur")
        ligne.addWidget(self._lbl_saison)
        return barre

    def _motd(self) -> QWidget:
        """Le message du jour d'une guilde — masqué quand il n'y en a pas.

        Encadré comme sur Android : une ligne grise perdue entre deux rangées
        ne se remarquait pas, et c'est pourtant ce que les officiers écrivent à
        toute la guilde. Le mégaphone reste à part du texte pour que celui-ci
        s'aligne quand il passe à la ligne, au lieu de repartir sous l'icône.
        """
        self._motd_boite = QWidget()
        self._motd_boite.setObjectName("motd")
        ligne = QHBoxLayout(self._motd_boite)
        ligne.setContentsMargins(10, 8, 10, 8)
        ligne.setSpacing(8)
        mega = QLabel("📢")
        mega.setAlignment(Qt.AlignmentFlag.AlignTop)
        ligne.addWidget(mega)
        self._motd_lbl = QLabel()
        self._motd_lbl.setWordWrap(True)
        ligne.addWidget(self._motd_lbl, 1)
        self._motd_boite.setVisible(False)
        return self._motd_boite

    def _page_inventaire(self) -> QWidget:
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        # Ligne volume : jauge de remplissage du contenant courant.
        boite_vol = QWidget()
        ligne_vol = QHBoxLayout(boite_vol)
        ligne_vol.setContentsMargins(8, 6, 8, 0)
        ligne_vol.setSpacing(8)
        ligne_vol.addWidget(QLabel(_("Volume :")))
        self._jauge = QProgressBar()
        self._jauge.setRange(0, 100)
        self._jauge.setTextVisible(False)
        ligne_vol.addWidget(self._jauge, 1)
        self._lbl_volume = QLabel()
        self._lbl_volume.setObjectName("discret")
        ligne_vol.addWidget(self._lbl_volume)
        colonne.addWidget(boite_vol)

        # Ligne 2 : recherche, filtres, tri.
        boite2 = QWidget()
        ligne2 = QHBoxLayout(boite2)
        ligne2.setContentsMargins(8, 0, 8, 0)
        ligne2.setSpacing(8)

        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText(_("Rechercher un item par nom…"))
        self._recherche.setClearButtonEnabled(True)
        self._recherche.textChanged.connect(self._appliquer_filtre)
        ligne2.addWidget(self._recherche, 1)

        self._btn_filtres = QToolButton()
        self._btn_filtres.setText(_("Filtres"))
        self._btn_filtres.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self._btn_filtres.setMenu(self._menu_filtres())
        ligne2.addWidget(self._btn_filtres)

        ligne2.addWidget(QLabel(_("Trier :")))
        self._dd_tri = QComboBox()
        self._dd_tri.addItems([_(t) for t in TRI_LIBELLES])
        # Regle avant de brancher le signal : le branchement d'abord ferait
        # reafficher la grille sur une fenetre a moitie construite.
        self._dd_tri.setCurrentIndex(self._tri_index)
        self._dd_tri.currentIndexChanged.connect(self._on_tri_change)
        ligne2.addWidget(self._dd_tri)

        self._btn_ordre = QPushButton("↑" if self._tri_desc else "↓")
        self._btn_ordre.setToolTip(_("Ordre croissant/décroissant"))
        self._btn_ordre.setFixedWidth(theme.largeur(self._btn_ordre, 1.8))
        self._btn_ordre.clicked.connect(self._on_ordre_bascule)
        ligne2.addWidget(self._btn_ordre)

        btn_reinit = QPushButton(_("Réinit."))
        btn_reinit.clicked.connect(self._on_reinit_filtre)
        ligne2.addWidget(btn_reinit)
        colonne.addWidget(boite2)

        # La grille. En mode icone avec repli automatique : l'equivalent du
        # FlowBox de GTK, il recalcule ses colonnes au redimensionnement.
        self._grille = QListWidget()
        self._grille.setViewMode(QListWidget.ViewMode.IconMode)
        taille = self._settings.icon_size
        self._grille.setIconSize(QSize(taille, taille))
        self._grille.setGridSize(QSize(taille + 8, taille + 8))
        self._grille.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._grille.setMovement(QListWidget.Movement.Static)
        self._grille.setUniformItemSizes(True)
        self._grille.setSelectionMode(
            QListWidget.SelectionMode.NoSelection)
        # Le defilement par pixel : par element, une grille de quatre cents
        # objets saute d'une rangee entiere a chaque cran de molette.
        self._grille.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel)
        # Le clic droit ouvre le menu de l'objet, le double-clic sa fiche --
        # comme les deux gestes de la version GTK.
        # La molette avec Ctrl agrandit les icones, comme partout ailleurs.
        # Un reglage dans les Options ne suffit pas : on veut voir grossir
        # pendant qu'on cherche un objet, pas ouvrir une fenetre pour cela.
        self._grille.viewport().installEventFilter(self)
        self._grille.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu)
        self._grille.customContextMenuRequested.connect(self._menu_objet)
        self._grille.itemDoubleClicked.connect(
            lambda case: self._afficher_details(self._objet_de(case)))
        colonne.addWidget(self._grille, 1)
        return page

    def _page_bonus(self) -> QWidget:
        """Les cinq écrans de consultation, dans leur propre pile.

        Aucune rangée de boutons ici : c'est le menu déroulant de la barre du
        haut qui commande cette pile.
        """
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 0, 0, 0)

        self._pile_bonus = QStackedWidget()
        self._pages_bonus = {}
        self._page_competences = PageCompetences(self)
        self._page_effectif = PageEffectif(self)
        self._page_avant_postes = PageAvantPostes(self)
        self._page_betes = PageBetes(self)
        self._page_meteo = PageMeteo(self)

        for nom, contenu in (
                ("skills", self._page_competences),
                ("roster", self._page_effectif),
                ("betes", self._page_betes),
                ("outposts", self._page_avant_postes),
                ("meteo", self._page_meteo)):
            self._pages_bonus[nom] = self._pile_bonus.addWidget(contenu)
        colonne.addWidget(self._pile_bonus, 1)
        return page

    def _montrer_bonus(self, nom: str) -> None:
        """Ouvre l'onglet « Bonus » sur l'un de ses cinq écrans."""
        self._montrer_page("plus")
        self._pile_bonus.setCurrentIndex(self._pages_bonus[nom])
        if nom == "skills":
            self._page_competences.rafraichir()
        elif nom == "roster":
            self._page_effectif.rafraichir()
        elif nom == "betes":
            self._page_betes.rafraichir()
        elif nom == "outposts":
            # Celui-la va chercher sur le reseau : il ne le fait qu'a la
            # premiere ouverture, et sur demande ensuite. L'annuaire des
            # guildes pese un demi-megaoctet, il n'a pas a partir au demarrage.
            self._page_avant_postes.charger()
        elif nom == "meteo":
            self._page_meteo.charger()

    # ------------------------------------------------ Journal des mouvements
    def _page_journal(self) -> QWidget:
        """L'onglet "Journal" : ce qui est entré et sorti, daté.

        **Un tableau, et non une grille de widgets.** La version GTK empile
        six `Gtk.Label` par ligne dans un `Gtk.Grid` ; à trois mille lignes
        cela ferait dix-huit mille widgets Qt, que ni la mémoire ni le temps
        de construction ne pardonneraient. Un `QTableWidget` porte des
        cellules, bien plus légères, et sait déjà défiler sur des milliers de
        lignes. Les colonnes restent les mêmes, dans le même ordre.
        """
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(0, 0, 0, 0)
        colonne.setSpacing(4)

        barre = QWidget()
        ligne = QHBoxLayout(barre)
        ligne.setContentsMargins(8, 8, 8, 0)
        ligne.setSpacing(8)

        self._recherche_journal = QLineEdit()
        self._recherche_journal.setPlaceholderText(
            _("Rechercher dans le journal…"))
        self._recherche_journal.setClearButtonEnabled(True)
        self._recherche_journal.textChanged.connect(self._rafraichir_journal)
        ligne.addWidget(self._recherche_journal, 1)

        self._dd_journal = QComboBox()
        self._dd_journal.addItems([_("Tout"), _("Entrées"), _("Sorties")])
        self._dd_journal.currentIndexChanged.connect(self._rafraichir_journal)
        ligne.addWidget(self._dd_journal)

        btn_copier = QPushButton(_("Copier"))
        btn_copier.setToolTip(_("Copier les lignes affichées"))
        btn_copier.clicked.connect(self._on_journal_copier)
        ligne.addWidget(btn_copier)

        btn_vider = QPushButton(_("Vider"))
        btn_vider.setToolTip(_("Effacer le journal de cette entité"))
        btn_vider.clicked.connect(self._on_journal_vider)
        ligne.addWidget(btn_vider)
        colonne.addWidget(barre)

        self._table = QTableWidget(0, 6)
        self._table.setObjectName("journal")
        # Pas d'en-tetes : la version GTK n'en a pas, et six mots de plus au
        # sommet d'une liste qu'on parcourt du regard ne servent a rien.
        self._table.horizontalHeader().setVisible(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setIconSize(QSize(TAILLE_ICONE_JOURNAL,
                                      TAILLE_ICONE_JOURNAL))
        self._table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel)
        # Chaque colonne a la largeur de son contenu, et la place qui reste
        # s'ajoute a la derniere. C'est la disposition de la version GTK, ou
        # les six colonnes se serrent a gauche : etirer celle du nom -- ce
        # qu'on avait essaye -- envoyait l'icone et la qualite a l'autre bout
        # de la fenetre, a trente centimetres du nom qu'elles decrivent.
        entete = self._table.horizontalHeader()
        for col in range(6):
            entete.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        entete.setStretchLastSection(True)
        colonne.addWidget(self._table, 1)

        self._table.verticalScrollBar().valueChanged.connect(
            self._servir_icones_visibles)

        self._lbl_journal = QLabel()
        self._lbl_journal.setObjectName("discret")
        self._lbl_journal.setContentsMargins(8, 0, 8, 6)
        colonne.addWidget(self._lbl_journal)
        return page

    def _charger_journal(self) -> None:
        """Relit le journal de l'entité courante depuis le disque."""
        entree = self._entree_courante()
        self._journal = []
        if entree:
            self._journal = movements.load(
                movements_path(entree["kind"], entree["id"]))
        self._rafraichir_journal()

    def _journal_filtre(self) -> list:
        motif = _norm(self._recherche_journal.text().strip())
        mode = self._dd_journal.currentIndex()
        sortie = []
        for mv in self._journal:
            if mode == 1 and mv.delta <= 0:
                continue
            if mode == 2 and mv.delta >= 0:
                continue
            if motif:
                foin = _norm(f"{self._names.name(mv.sheet)} {mv.sheet} "
                             f"{mv.inv_label}")
                if motif not in foin:
                    continue
            sortie.append(mv)
        return sortie

    def _rafraichir_journal(self) -> None:
        self._generation_journal += 1
        self._table.setRowCount(0)
        self._icones_a_venir = {}

        montres = self._journal_filtre()
        nombre = movements.lignes_recentes(montres, JOURNAL_JOURS,
                                           JOURNAL_MINIMUM, JOURNAL_MAX)

        mono = QFont("monospace")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        faible = QColor(self.palette().placeholderText().color())

        jour_precedent = None
        rang = 0
        for mv in montres[:nombre]:
            # Un trait entre deux journees. Le journal se lit du plus recent
            # au plus ancien, et trois releves d'affilee y produisent trois
            # paquets de lignes a la meme seconde : sans separation, on ne
            # voyait plus ou finissait une journee.
            jour = mv.when[:10]
            if jour_precedent is not None and jour != jour_precedent:
                self._table.insertRow(rang)
                self._table.setRowHeight(rang, 7)
                self._table.setSpan(rang, 0, 1, 6)
                trait = QTableWidgetItem()
                trait.setFlags(Qt.ItemFlag.NoItemFlags)
                trait.setBackground(QColor(232, 193, 90, 90))
                self._table.setItem(rang, 0, trait)
                rang += 1
            jour_precedent = jour

            self._table.insertRow(rang)

            # Le tresor n'est pas un objet : pas de fiche a nommer, pas
            # d'icone a telecharger, et des montants a sept chiffres qu'on ne
            # lit pas d'un bloc.
            argent = mv.inv_key == movements.MONEY_KEY

            quand = QTableWidgetItem(mv.when)
            quand.setFont(mono)
            quand.setForeground(faible)
            self._table.setItem(rang, 0, quand)

            ou = QTableWidgetItem(movements.sans_parenthese(mv.inv_label))
            ou.setForeground(faible)
            self._table.setItem(rang, 1, ou)

            combien = QTableWidgetItem(
                f"{mv.delta:+,}".replace(",", " ") if argent
                else f"{mv.delta:+d}")
            combien.setFont(mono)
            combien.setForeground(QColor(VERT_ENTREE if mv.delta > 0
                                         else ROUGE_SORTIE))
            combien.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                     | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(rang, 2, combien)

            self._table.setItem(rang, 3, QTableWidgetItem(
                _("Dappers") if argent else self._names.name(mv.sheet)))

            # L'icone de l'objet, juste avant sa qualite : c'est elle qu'on
            # reconnait en parcourant le journal, bien avant de lire un nom.
            icone = QTableWidgetItem("💰" if argent else "")
            self._table.setItem(rang, 4, icone)
            if not argent:
                # L'icone n'est pas demandee ici : deux mille lignes, ce sont
                # deux mille telechargements lances d'un coup, et autant de
                # rappels a livrer au fil principal -- l'application ne
                # repondait plus. On note ce qu'il faudra, et l'on ne va le
                # chercher que pour les lignes qu'on regarde vraiment.
                self._icones_a_venir[rang] = (mv.sheet, mv.quality)

            qualite = QTableWidgetItem(f"Q{mv.quality}" if mv.quality else "")
            qualite.setForeground(faible)
            self._table.setItem(rang, 5, qualite)
            rang += 1

        self._servir_icones_visibles()

        total = len(self._journal)
        if not total:
            self._lbl_journal.setText(
                _("Aucun mouvement enregistré. Le journal se remplit à chaque "
                  "synchronisation où quelque chose a bougé."))
        elif len(montres) > nombre:
            self._lbl_journal.setText(
                _("{} lignes affichées sur {} retenues ({} au journal) — "
                  "affinez la recherche.").format(nombre, len(montres), total))
        else:
            self._lbl_journal.setText(
                _("{} lignes sur {} au journal").format(len(montres), total))

    def _servir_icones_visibles(self) -> None:
        """Va chercher les icônes des seules lignes à l'écran.

        Deux mille cinq cents lignes de journal ne montrent qu'une quinzaine
        de lignes à la fois : demander les autres, c'est autant de
        téléchargements et de rappels pour rien.
        """
        if not self._icones_a_venir:
            return
        vue = self._table
        haut = vue.rowAt(0)
        bas = vue.rowAt(vue.viewport().height() - 1)
        if haut < 0:
            haut = 0
        if bas < 0:
            bas = vue.rowCount() - 1
        # Une marge de part et d'autre : on prepare ce qui arrive au
        # defilement, sans attendre qu'il soit a l'ecran.
        for rang in range(max(0, haut - 10), min(vue.rowCount(), bas + 11)):
            attendu = self._icones_a_venir.pop(rang, None)
            if attendu is None:
                continue
            cellule = vue.item(rang, 4)
            if cellule is None:
                continue
            cle = attendu
            deja = self._cache_icones.get(cle)
            if deja is not None:
                cellule.setIcon(deja)
                continue
            self._icones.demander(
                ItemInfo(sheet=cle[0], quality=cle[1]),
                self._rappel_icone_journal(self._generation_journal, cellule,
                                           cle))

    def _rappel_icone_journal(self, generation: int, cellule: QTableWidgetItem,
                              cle=None):
        """Pose l'icône si le journal n'a pas été redessiné entre-temps.

        Il l'est à chaque frappe dans la recherche : sans ce garde, une icône
        demandée pour l'ancienne liste viendrait se poser sur la ligne qui a
        pris sa place, et le journal afficherait l'icône du voisin.
        """
        def arrivee(chemin):
            if generation != self._generation_journal or not chemin:
                return
            image = QPixmap(chemin)
            if not image.isNull():
                icone = QIcon(image)
                if cle is not None:
                    # Le meme objet revient des dizaines de fois dans un
                    # journal : on le garde plutot que de le relire du disque.
                    self._cache_icones[cle] = icone
                cellule.setIcon(icone)
        return arrivee

    def _on_journal_copier(self) -> None:
        lignes = [movements.describe(mv, self._names.name)
                  for mv in self._journal_filtre()]
        if not lignes:
            return
        QGuiApplication.clipboard().setText("\n".join(lignes))
        self._lbl_journal.setText(
            _("{} lignes copiées.").format(len(lignes)))

    def _on_journal_vider(self) -> None:
        entree = self._entree_courante()
        if not entree:
            return
        boite = QMessageBox(self)
        boite.setIcon(QMessageBox.Icon.Warning)
        boite.setWindowTitle(_("Vider le journal ?"))
        boite.setText(_("Vider le journal ?"))
        boite.setInformativeText(
            _("Les {} mouvements enregistrés pour {} seront perdus. L'API ne "
              "permet pas de les reconstruire.").format(len(self._journal),
                                                        entree["name"]))
        annuler = boite.addButton(_("Annuler"),
                                  QMessageBox.ButtonRole.RejectRole)
        vider = boite.addButton(_("Vider"),
                                QMessageBox.ButtonRole.DestructiveRole)
        boite.setDefaultButton(annuler)
        boite.exec()
        if boite.clickedButton() is not vider:
            return
        movements.clear(movements_path(entree["kind"], entree["id"]))
        self._charger_journal()

    def _journaliser(self, ent, entree: dict) -> None:
        """Compare le relevé au précédent et consigne ce qui a bougé.

        L'API ne rend qu'un état ; l'histoire, c'est nous qui la tenons. Un
        instantané est gardé après chaque relevé, et le suivant s'y compare.

        Sans instantané précédent — première synchro, journal repris à neuf —
        on ne consigne rien : tout un inventaire compté comme "arrivé" ne
        serait pas une histoire, seulement du bruit.
        """
        chemin = snapshot_path(entree["kind"], entree["id"])
        ancien = alerts.load_snapshot(chemin)
        nouveau = alerts.build_snapshot(ent)
        if ancien:
            bouges = movements.diff(ancien, nouveau, ent)
            movements.append(movements_path(entree["kind"], entree["id"]),
                             bouges)
            # Le tresor est le seul mouvement que la cloche ait le droit de
            # reprendre : il y en a au plus un par releve.
            self._mouvements_argent = [m for m in bouges
                                       if m.inv_key == movements.MONEY_KEY]
            if bouges and self._pile.currentIndex() == self._pages["log"]:
                self._charger_journal()
        alerts.save_snapshot(chemin, nouveau)

    # ------------------------------------------------------ Zoom des icones
    def eventFilter(self, objet, evenement):     # noqa: N802 -- nom impose
        """Ctrl + molette sur la grille : les icônes grossissent ou rapetissent.

        Le réglage des Options reste, pour poser une taille une fois pour
        toutes ; celui-ci sert pendant qu'on cherche, sans quitter la grille.
        """
        if (evenement.type() == QEvent.Type.Wheel
                and objet is self._grille.viewport()
                and evenement.modifiers() & Qt.KeyboardModifier.ControlModifier):
            cran = evenement.angleDelta().y()
            if cran:
                self._zoomer_icones(8 if cran > 0 else -8)
            return True
        return super().eventFilter(objet, evenement)

    def _zoomer_icones(self, pas: int) -> None:
        taille = max(24, min(128, self._settings.icon_size + pas))
        if taille == self._settings.icon_size:
            return
        self._settings.icon_size = taille
        self._appliquer_taille_icones()
        self._statut(_("Icônes : {} pixels").format(taille))

    def _appliquer_taille_icones(self) -> None:
        """Pose la taille des icônes et redessine la grille.

        Les images sont recomposées au passage : les gouttes de bonus et le
        sort gravé sont peints *dans* l'icône, à sa taille — les laisser
        telles quelles donnerait des gouttes minuscules sur une grande image.
        """
        taille = self._settings.icon_size
        self._grille.setIconSize(QSize(taille, taille))
        self._grille.setGridSize(QSize(taille + 8, taille + 8))
        self._reafficher()

    def _pied(self) -> QWidget:
        """La bande du bas : portrait et état, nom gravé au centre, dappers.

        **Une grille à trois colonnes, et non une simple ligne.** Le nom de
        l'application doit être centré sur la fenêtre, quoi que pèsent ses
        voisins — c'est ce que fait la `Gtk.CenterBox` de la version GTK. Avec
        une ligne ordinaire, la ligne d'état prendrait toute la place libre et
        pousserait le nom contre les dappers, centré sur rien. Deux colonnes
        latérales de même force encadrent donc la colonne du milieu.
        """
        pied = QWidget()
        pied.setObjectName("bande")
        colonne = QVBoxLayout(pied)
        colonne.setContentsMargins(8, 2, 8, 2)
        colonne.setSpacing(0)

        barre = QGridLayout()
        barre.setContentsMargins(0, 0, 0, 0)
        barre.setColumnStretch(0, 1)
        barre.setColumnStretch(1, 0)
        barre.setColumnStretch(2, 1)

        # A gauche : le portrait, puis la ligne d'etat sur deux lignes.
        gauche = QWidget()
        ligne_g = QHBoxLayout(gauche)
        ligne_g.setContentsMargins(0, 0, 0, 0)
        # Douze pixels et non huit : a huit, le portrait -- ou l'embleme de la
        # guilde -- et les deux lignes de texte formaient un seul bloc, et
        # l'oeil ne savait plus ou finissait l'image et ou commencait le nom.
        ligne_g.setSpacing(12)
        self._portrait = QLabel()
        self._portrait.setFixedHeight(HAUTEUR_PORTRAIT)
        self._portrait.setToolTip(_("Cliquer pour agrandir"))
        self._portrait.setCursor(Qt.CursorShape.PointingHandCursor)
        self._portrait.mouseReleaseEvent = self._on_portrait_clic
        ligne_g.addWidget(self._portrait, 0, Qt.AlignmentFlag.AlignBottom)
        # Calee en bas, et non centree : la seconde ligne se pose alors sur le
        # bas du portrait au lieu de flotter au-dessus.
        self._lbl_statut = QLabel()
        self._lbl_statut.setObjectName("peuple")
        self._lbl_statut.setWordWrap(True)
        ligne_g.addWidget(self._lbl_statut, 1, Qt.AlignmentFlag.AlignBottom)
        barre.addWidget(gauche, 0, 0)

        barre.addWidget(self._nom_appli(), 0, 1, Qt.AlignmentFlag.AlignBottom)

        self._lbl_dappers = QLabel()
        barre.addWidget(self._lbl_dappers, 0, 2,
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignBottom)
        colonne.addLayout(barre)

        # Signature : d'ou vient cette application. Pas de traduction, ce sont
        # des noms propres. L'AGPL veut que l'interface porte le copyright et
        # le moyen d'obtenir le code.
        signature = QPushButton(SIGNATURE)
        signature.setObjectName("signature")
        signature.setFlat(True)
        signature.setCursor(Qt.CursorShape.PointingHandCursor)
        signature.setToolTip(_("À propos de {}").format(APP_NAME))
        signature.clicked.connect(self._on_apropos)
        colonne.addWidget(signature, 0, Qt.AlignmentFlag.AlignCenter)
        return pied

    def _nom_appli(self) -> QWidget:
        """Le nom de l'application, au milieu de la barre du bas.

        En deux polices, comme dans la version GTK : la gothique porte
        « ZyRoom », qui est le nom de l'application d'origine ; « -Qt » dit de
        quelle mouture il s'agit, et c'est un mot d'ingénieur — la gothique le
        rendrait illisible. Une étroite et grasse, d'un corps en dessous, lui
        rend la densité du blackletter sans lui disputer la vedette.

        Les deux morceaux s'alignent sur la ligne d'écriture et non sur le bas
        de leur boîte : deux polices de tailles différentes posées sur le même
        bord flotteraient l'une par rapport à l'autre.
        """
        boite = QWidget()
        boite.setObjectName("nom-appli")
        ligne = QHBoxLayout(boite)
        ligne.setContentsMargins(18, 0, 18, 0)
        ligne.setSpacing(0)

        # La taille reglee, et non celle du widget : la feuille de style la
        # pose apres coup, et `self.font()` rendrait encore celle du bureau.
        base = float(self._settings.font_size or self.font().pointSizeF() or 10)

        grave = QLabel(NOM_GRAVE)
        police = grave.font()
        police.setFamily(polices.FAMILLE)
        police.setPointSizeF(base * 2.4)
        grave.setFont(police)
        grave.setObjectName("nom-grave")
        ligne.addWidget(grave, 0, Qt.AlignmentFlag.AlignBaseline)

        mouture = QLabel(APP_NAME.removeprefix(NOM_GRAVE))
        pm = mouture.font()
        # Les memes replis que la version GTK, dans le meme ordre : la Heros
        # Cn vient du runtime GNOME, la Liberation Narrow la remplace, et
        # Arial Narrow tient ce role sous Windows.
        pm.setFamilies(["TeX Gyre Heros Cn", "Liberation Sans Narrow",
                        "Arial Narrow", "sans-serif"])
        pm.setPointSizeF(base * 2.2)
        pm.setBold(True)
        mouture.setFont(pm)
        mouture.setObjectName("nom-mouture")
        ligne.addWidget(mouture, 0, Qt.AlignmentFlag.AlignBaseline)
        return boite

    # ------------------------------------------------------------- Filtres
    def _menu_filtres(self) -> QMenu:
        """Le panneau des filtres, sous le bouton « Filtres ».

        Un menu qui ne porte qu'un widget : c'est ainsi que Qt fait un
        `Gtk.Popover`. Le contenu et son ordre sont ceux de la version GTK —
        les bonus d'abord, parce que c'est le tri qu'on vient chercher le plus
        souvent dans un coffre d'équipement.
        """
        menu = QMenu(self)
        contenu = QWidget()
        colonne = QVBoxLayout(contenu)
        colonne.setContentsMargins(8, 8, 8, 8)
        colonne.setSpacing(6)

        colonne.addWidget(self._groupe_bonus())

        boite_q = QWidget()
        ligne_q = QHBoxLayout(boite_q)
        ligne_q.setContentsMargins(0, 0, 0, 0)
        ligne_q.addWidget(QLabel(_("Qualité")))
        self._qmin = QSpinBox()
        self._qmin.setRange(0, 500)
        self._qmin.setSingleStep(10)
        self._qmin.valueChanged.connect(self._appliquer_filtre)
        ligne_q.addWidget(self._qmin)
        ligne_q.addWidget(QLabel(_("à")))
        self._qmax = QSpinBox()
        self._qmax.setRange(0, 500)
        self._qmax.setSingleStep(10)
        self._qmax.setValue(500)
        self._qmax.valueChanged.connect(self._appliquer_filtre)
        ligne_q.addWidget(self._qmax)
        ligne_q.addStretch(1)
        colonne.addWidget(boite_q)

        self._cadenas = QCheckBox(_("Cadenas"))
        self._cadenas.toggled.connect(self._appliquer_filtre)
        colonne.addWidget(self._cadenas)
        self._avec_bonus = QCheckBox(_("Avec bonus"))
        self._avec_bonus.toggled.connect(self._appliquer_filtre)
        colonne.addWidget(self._avec_bonus)
        self._en_vente = QCheckBox(_("En vente"))
        self._en_vente.toggled.connect(self._appliquer_filtre)
        colonne.addWidget(self._en_vente)

        for titre, noms, etat in (("Type d'objet", TYPE_NAMES, self._f_types),
                                  ("Classe", CLASS_NAMES, self._f_classes),
                                  ("Écosystème", ECOSYSTEM_NAMES, self._f_ecosys),
                                  ("Équipement", EQUIP_NAMES, self._f_equips)):
            colonne.addWidget(self._groupe_cases(titre, noms, etat))

        # Le panneau tient sur quatre cent quarante pixels, comme cote GTK ;
        # au-dela, on deroule.
        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        defilant.setMaximumHeight(440)
        defilant.setMinimumWidth(contenu.sizeHint().width() + 24)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        porteur = QWidgetAction(menu)
        porteur.setDefaultWidget(defilant)
        menu.addAction(porteur)
        return menu

    def _groupe_bonus(self) -> QWidget:
        """Les quatre bonus, chacun derrière sa goutte.

        Un groupe à part plutôt qu'un `_groupe_cases` : la couleur est ce qui
        fait le lien avec la grille, où c'est elle — et non un nom — qui marque
        les objets. Une case portant « Sève » sans sa goutte verte obligerait à
        traduire de tête à chaque coup d'œil.
        """
        boite = QWidget()
        colonne = QVBoxLayout(boite)
        colonne.setContentsMargins(0, 4, 0, 0)
        colonne.setSpacing(1)
        titre = QLabel(f"<b>{_('Bonus')}</b>")
        colonne.addWidget(titre)

        for rang, (_attribut, libelle, couleur) in enumerate(
                specialites.SPECIALITES):
            ligne = QWidget()
            h = QHBoxLayout(ligne)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)
            case = QCheckBox()
            case.setChecked(rang in self._f_bonus)
            case.toggled.connect(
                lambda coche, e=self._f_bonus, i=rang:
                self._on_case_groupe(coche, e, i))
            h.addWidget(case)
            goutte = QLabel()
            goutte.setPixmap(specialites.pastille(couleur))
            h.addWidget(goutte)
            h.addWidget(QLabel(_(libelle)), 1)
            colonne.addWidget(ligne)
            self._toutes_cases.append(case)
        return boite

    def _groupe_cases(self, titre: str, noms, etat: set) -> QWidget:
        boite = QWidget()
        colonne = QVBoxLayout(boite)
        colonne.setContentsMargins(0, 4, 0, 0)
        colonne.setSpacing(1)
        colonne.addWidget(QLabel(f"<b>{_(titre)}</b>"))
        for i, nom in enumerate(noms):
            case = QCheckBox(_(nom))
            case.setChecked(i in etat)
            case.toggled.connect(
                lambda coche, e=etat, j=i: self._on_case_groupe(coche, e, j))
            colonne.addWidget(case)
            self._toutes_cases.append(case)
        return boite

    def _on_case_groupe(self, coche: bool, etat: set, i: int) -> None:
        if coche:
            etat.add(i)
        else:
            etat.discard(i)
        self._appliquer_filtre()

    def _appliquer_filtre(self) -> None:
        motif = _norm(self._recherche.text().strip())
        qmin, qmax = self._qmin.value(), self._qmax.value()
        cadenas = self._cadenas.isChecked()
        avec_bonus = self._avec_bonus.isChecked()
        en_vente = self._en_vente.isChecked()

        for case, objet, cle in self._cases:
            ok = True
            if motif and motif not in cle:
                ok = False
            elif not (qmin <= objet.quality <= qmax):
                ok = False
            elif int(objet.item_type) not in self._f_types:
                ok = False
            elif int(objet.ecosystem) not in self._f_ecosys:
                ok = False
            elif int(objet.item_class) not in self._f_classes:
                ok = False
            elif (objet.item_type == ItemType.EQUIPMENT
                  and int(objet.equip) not in self._f_equips):
                ok = False
            elif cadenas and not objet.locked:
                ok = False
            elif avec_bonus and not (objet.hp_buff or objet.sap_buff
                                     or objet.sta_buff or objet.focus_buff):
                ok = False
            elif not specialites.passe_le_filtre(objet, self._f_bonus):
                ok = False
            elif en_vente and objet.expires <= 0:
                ok = False
            case.setHidden(not ok)
        self._maj_statut()

    def _on_reinit_filtre(self) -> None:
        self._recherche.clear()
        self._qmin.setValue(0)
        self._qmax.setValue(500)
        for case in (self._cadenas, self._avec_bonus, self._en_vente):
            case.setChecked(False)
        for case in self._toutes_cases:
            case.setChecked(True)
        # "Reinit." rend la fenetre telle qu'elle se presente au lancement,
        # et c'est le tri par type -- pas l'ordre d'origine, qu'on ne verrait
        # sinon jamais autrement qu'en le demandant.
        self._dd_tri.setCurrentIndex(Settings.TRI_DEFAUT[0])
        if self._tri_desc != Settings.TRI_DEFAUT[1]:
            self._on_ordre_bascule()
        self._appliquer_filtre()

    # ----------------------------------------------------------------- Tri
    #: Regroupement par famille : catalyseurs ensemble, feux d'artifice
    #: ensemble, et les matieres reunies par materiau du plus bas niveau au
    #: plus haut. Voir sorting.py -- le type brut du jeu ne s'y prete pas, la
    #: moitie d'un coffre y etant classee "autre".
    _CLES_TRI = {
        1: lambda self, it: sorting.sort_key(it, _norm(self._names.name(it.sheet))),
        2: lambda self, it: int(it.ecosystem),
        3: lambda self, it: int(it.item_class),
        4: lambda self, it: it.quality,
        5: lambda self, it: it.volume,
        6: lambda self, it: it.stack,
        7: lambda self, it: it.price,
        8: lambda self, it: _norm(self._names.name(it.sheet)),
    }

    def _trie(self, objets):
        cle = self._CLES_TRI.get(self._tri_index)
        if cle is None:
            return list(objets)
        return sorted(objets, key=lambda it: cle(self, it),
                      reverse=self._tri_desc)

    def _on_tri_change(self, rang: int) -> None:
        self._tri_index = rang
        self._settings.sort_order = (self._tri_index, self._tri_desc)
        self._reafficher()

    def _on_ordre_bascule(self) -> None:
        self._tri_desc = not self._tri_desc
        self._btn_ordre.setText("↑" if self._tri_desc else "↓")
        self._settings.sort_order = (self._tri_index, self._tri_desc)
        self._reafficher()

    def _reafficher(self) -> None:
        rang = self._dd_inv.currentIndex()
        if rang >= 0:
            self._afficher_contenant(rang)

    # ------------------------------------------------------------- Entites
    def _charger_noms(self, chemin: str) -> None:
        """Noms lisibles : le pack s'il est là, sinon ce qu'on en avait tiré.

        Le chemin enregistré désigne un fichier de l'installation du jeu, qui
        peut avoir été déplacé depuis. On le cherche alors ailleurs, puis on se
        rabat sur le cache : des noms d'hier valent mieux que des identifiants
        de fiches.
        """
        if chemin and self._names.load(chemin):
            if chemin != self._settings.pack_file:
                self._settings.pack_file = chemin
            return

        trouve = detect_pack()
        if trouve and trouve != chemin and self._names.load(trouve):
            self._settings.pack_file = trouve
            return

        self._names.load_cache()

    def _recharger_entites(self, choisir_id: str | None = None) -> None:
        self._entrees = []
        for entree in self._char_store.entries():
            self._entrees.append(dict(entree, kind=KIND_CHARACTER))
        for entree in self._guild_store.entries():
            self._entrees.append(dict(entree, kind=KIND_GUILD))

        self._dd_entite.blockSignals(True)
        self._dd_entite.clear()
        for entree in self._entrees:
            libelle = f"{_PREFIXE_GENRE.get(entree['kind'], '')} {entree['name']}"
            if entree["server"]:
                libelle += f" ({entree['server']})"
            self._dd_entite.addItem(libelle)
        self._dd_entite.blockSignals(False)

        if not self._entrees:
            self._btn_relever.setEnabled(False)
            self._btn_retirer.setEnabled(False)
            self._entite = None
            self._remplir_contenants()
            self._statut(_("Aucune entité — le bouton « + » ajoute un "
                           "personnage ou une guilde à partir de sa clé."))
            return

        self._btn_relever.setEnabled(True)
        self._btn_retirer.setEnabled(True)
        rang = 0
        if choisir_id:
            for i, e in enumerate(self._entrees):
                if e["id"] == choisir_id:
                    rang = i
                    break
        if self._dd_entite.currentIndex() == rang:
            self._on_entite_choisie(rang)
        else:
            self._dd_entite.setCurrentIndex(rang)

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
        entrees = list(self._entrees)
        if not entrees:
            return

        def travail():
            total = 0
            for entree in entrees:
                total += partage.recuperer(
                    entree["kind"], entree["id"],
                    movements_path(entree["kind"], entree["id"]))
            return total

        def apres(total, erreur):
            if erreur or not total:
                return          # rien de neuf, ou pas de reseau : on se tait
            # Le journal affiche peut-etre celui qu'on vient d'enrichir.
            if self._pile.currentIndex() == self._pages["log"]:
                self._charger_journal()
            self._statut(
                _("Journal de la guilde : {} mouvement(s) repris de la page.")
                .format(total))

        self._passerelle.lancer(travail, apres)

    def _entree_courante(self) -> dict | None:
        rang = self._dd_entite.currentIndex()
        if 0 <= rang < len(self._entrees):
            return self._entrees[rang]
        return None

    def _on_entite_choisie(self, _rang: int) -> None:
        entree = self._entree_courante()
        if not entree:
            return
        chemin = entity_xml_path(entree["kind"], entree["id"])
        jeton = (entree["kind"], entree["id"])

        # Sans cache, la synchronisation est de toute facon obligatoire.
        if not os.path.isfile(chemin):
            self._relevees.add(jeton)
            self._synchroniser(entree)
            return

        # Avec cache, on l'affiche aussitot -- c'est instantane et cela marche
        # hors ligne -- puis on interroge l'API la premiere fois qu'on ouvre
        # cette entite dans la session. Sans quoi on montrerait des stocks
        # vieux de plusieurs jours sans que rien ne le signale.
        try:
            with open(chemin, "rb") as fh:
                self._charger_depuis_xml(fh.read(), entree)
        except Exception:                                # noqa: BLE001
            self._relevees.add(jeton)
            self._synchroniser(entree)
            return

        if self._settings.sync_on_start and jeton not in self._relevees:
            self._relevees.add(jeton)
            self._synchroniser(entree)

    def _on_retirer(self) -> None:
        entree = self._entree_courante()
        if not entree:
            return
        magasin = (self._char_store if entree["kind"] == KIND_CHARACTER
                   else self._guild_store)
        magasin.remove(entree["id"])
        self._recharger_entites()

    def _on_relever(self) -> None:
        entree = self._entree_courante()
        if entree and not self._occupe:
            self._synchroniser(entree)

    def _synchroniser(self, entree: dict) -> None:
        """Récupère le flux de l'API, dans un thread."""
        self._occupe = True
        self._btn_relever.setEnabled(False)
        self._tourniquet.setVisible(True)
        self._statut(_("Synchronisation de {}…").format(entree["name"]))
        cle, genre = entree["key"], entree["kind"]
        chercher = (ryzom_api.fetch_character_xml if genre == KIND_CHARACTER
                    else ryzom_api.fetch_guild_xml)

        def travail():
            xml = chercher(cle)
            with open(entity_xml_path(genre, entree["id"]), "wb") as fh:
                fh.write(xml)
            saison = None
            try:      # la saison du serveur, pour la ligne du haut
                saison = ryzom_api.parse_time(ryzom_api.fetch_time_xml())
            except Exception:                            # noqa: BLE001
                pass
            return xml, saison

        def apres(resultat, erreur):
            self._occupe = False
            self._btn_relever.setEnabled(True)
            self._tourniquet.setVisible(False)
            if erreur:
                self._statut(_("Échec de la synchro : {}").format(erreur))
                return
            xml, saison = resultat
            self._charger_depuis_xml(xml, entree)
            if self._entite is not None:
                self._journaliser(self._entite, entree)
                self._verifier_alertes(self._entite, entree, True, saison)
            if saison:
                self._maj_saison(saison)

        self._passerelle.lancer(travail, apres)

    def _charger_depuis_xml(self, xml: bytes, entree: dict) -> None:
        analyser = (ryzom_api.parse_character if entree["kind"] == KIND_CHARACTER
                    else ryzom_api.parse_guild)
        try:
            ent = analyser(xml, self._sheetdb.name)
        except ApiError as exc:
            self._statut(_("Erreur : {}").format(exc))
            return
        self._entite = ent
        # La liste des objets surveilles suit l'entite : les seuils posee sur
        # le sac d'un personnage n'ont rien a voir avec ceux d'un coffre.
        self._watch = WatchStore(guard_path(entree["kind"], entree["id"]))
        self._mouvements_argent = []
        # Le registre suit la guilde affichee : chaque lecture du flux
        # journalise les arrivees, les departs et les changements de grade --
        # l'API ne rend qu'un effectif, jamais son histoire.
        if ent.kind == KIND_GUILD:
            if ent.members:
                roster.RosterStore(data_dir(), ent.entity_id).record(ent.members)
                self.derniere_guilde = ent
        elif ent.skills:
            self.dernier_perso = ent
        self._maj_entete_entite(ent, entree)
        self._remplir_contenants()
        self._verifier_alertes(ent, entree, depuis_synchro=False)

    def _maj_entete_entite(self, ent, entree: dict) -> None:
        if ent.money:
            try:
                montant = f"{int(ent.money):,}".replace(",", " ")
            except ValueError:
                montant = ent.money
            self._lbl_dappers.setText(f"💰 {montant} dappers")
        else:
            self._lbl_dappers.clear()
        if ent.motd:
            self._motd_lbl.setText(ent.motd)
            self._motd_boite.setVisible(True)
        else:
            self._motd_boite.setVisible(False)
        self._charger_portrait(ent, entree)

    def _rafraichir_saison(self) -> None:
        """Redemande la saison d'Atys, sans toucher au reste.

        Elle ne dépend d'aucune clé : c'est le temps du serveur, et il tourne
        que l'on relève ou non.
        """
        def travail():
            return ryzom_api.parse_time(ryzom_api.fetch_time_xml())

        def apres(saison, erreur):
            if erreur or not saison:
                return          # sans reseau, on garde ce qu'on affiche
            self._maj_saison(saison)

        self._passerelle.lancer(travail, apres)

    def _maj_saison(self, saison: dict) -> None:
        heures = saison["minutes_to_next"] // 60
        self._lbl_saison.setText(
            f"{saison['season_name']} · "
            + _("{} dans {} h").format(saison["next_season_name"], heures))

    # --------------------------------------------------------- Contenants
    def _remplir_contenants(self) -> None:
        ent = self._entite
        self._dd_inv.blockSignals(True)
        self._dd_inv.clear()
        if ent:
            for inv in ent.inventories:
                # Le numero du coffre, son nom, son taux -- et rien du reste
                # de phrase que l'API laisse pendre apres une parenthese
                # jamais refermee.
                self._dd_inv.addItem(
                    f"{movements.sans_parenthese(inv.label)}"
                    f"{self._remplissage(inv)}")
        self._dd_inv.blockSignals(False)

        if ent and ent.inventories:
            self._dd_inv.setCurrentIndex(0)
            self._afficher_contenant(0)
        else:
            self._grille.clear()
            self._cases = []
            self._jauge.setVisible(False)
            self._lbl_volume.clear()

    @staticmethod
    def _remplissage(inv) -> str:
        """Le taux de remplissage d'un contenant, prêt à coller en fin de ligne.

        Le menu annonçait un nombre d'objets, qui ne dit pas si l'on peut
        encore ranger quelque chose : cent matières tiennent où dix armures
        débordent.

        Vide quand la capacité est inconnue — l'API ne la donne pas pour tous
        les contenants, et « (0%) » ferait croire à un coffre vide.
        """
        if getattr(inv, "capacity", 0) <= 0:
            return ""
        return f" ({inv.total_volume / inv.capacity * 100.0:.0f}%)"

    def _on_contenant_choisi(self, rang: int) -> None:
        if rang >= 0:
            self._afficher_contenant(rang)

    def _afficher_contenant(self, rang: int) -> None:
        ent = self._entite
        if not ent or not (0 <= rang < len(ent.inventories)):
            return
        inv = ent.inventories[rang]
        self._maj_jauge(inv)

        # Chaque affichage porte un numero : les icones encore en vol pour le
        # contenant precedent arriveront avec un numero perime, et seront
        # ignorees plutot que posees sur la mauvaise case.
        self._generation += 1
        generation = self._generation
        self._grille.clear()
        self._cases = []

        generique = self.style().standardIcon(
            self.style().StandardPixmap.SP_FileIcon)
        for objet in self._trie(inv.items):
            case = QListWidgetItem(generique, "")
            case.setToolTip(self._infobulle(objet))
            case.setData(_ROLE_OBJET, objet)
            self._grille.addItem(case)
            # La cle de recherche est calculee une fois, a la creation : la
            # recalculer a chaque frappe ferait ramer un coffre de deux cents.
            cle = _norm(f"{self._names.name(objet.sheet)} {objet.sheet}")
            self._cases.append((case, objet, cle))
            self._icones.demander(objet,
                                  self._rappel_icone(generation, case, objet))

        self._appliquer_filtre()

    def _rappel_icone(self, generation: int, case: QListWidgetItem, objet):
        def rappel(chemin):
            if generation != self._generation:
                return                    # affichage perime : on laisse tomber
            if not chemin:
                return
            image = QPixmap(chemin)
            if image.isNull():
                return
            # Les gouttes de bonus sont peintes dans l'image, et non posees
            # par-dessus comme le fait l'Overlay de GTK : une case redevient
            # un seul objet la ou une grille en compte quatre cents.
            taille = self._settings.icon_size
            if image.width() != taille:
                image = image.scaled(
                    taille, taille, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            composee = specialites.appliquer(image, objet)
            case.setIcon(QIcon(composee))
            # Le sort grave dans l'objet, s'il y en a un : son icone arrive
            # separement, et se pose a son tour sur celle qu'on vient de
            # composer.
            brique = enchantements.brique_icone(objet)
            if brique:
                self._icones.demander_brique(
                    brique, self._rappel_sort(generation, case, composee))
        return rappel

    def _rappel_sort(self, generation: int, case: QListWidgetItem,
                     dessous: QPixmap):
        """Pose l'icône du sort en haut à droite de celle de l'objet.

        L'API la rend en 24x24 ; on la montre un peu plus petite, pour laisser
        voir l'objet en dessous. Rien en attendant : un objet enchanté n'est
        pas plus rare qu'un autre dans un sac de mêlée, et une image d'attente
        ferait clignoter la grille.
        """
        def arrivee(chemin):
            if generation != self._generation or not chemin:
                return
            sort = QPixmap(chemin)
            if sort.isNull():
                return
            petite = max(8, round(dessous.width() * TAILLE_ICONE_SORT
                                  / TAILLE_ICONE))
            sort = sort.scaled(
                petite, petite,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            composee = QPixmap(dessous)
            peintre = QPainter(composee)
            peintre.drawPixmap(composee.width() - sort.width(), 0, sort)
            peintre.end()
            case.setIcon(QIcon(composee))
        return arrivee

    def _infobulle(self, objet) -> str:
        # `name()` rend l'identifiant de fiche quand le nom est inconnu : une
        # seule ligne suffit donc, et l'identifiant ne s'affiche qu'a defaut.
        lignes = [self._names.name(objet.sheet)]
        if objet.quality:
            lignes.append(_("Qualité") + f" : {objet.quality}")
        if objet.stack:
            lignes.append(_("Quantité") + f" : {objet.stack}")
        if objet.item_type == ItemType.EQUIPMENT and objet.hp:
            lignes.append(_("Durabilité") + f" : {objet.hp} / {objet.hp_max}"
                          if objet.hp_max
                          else _("Durabilité") + f" : {objet.hp}")
        if objet.volume:
            lignes.append(_("Volume") + f" : {objet.volume:.2f}")

        if objet.price:
            lignes.append(_("Prix") + " : "
                          + f"{objet.price:,.0f}".replace(",", " ") + " dappers")
        if objet.continent:
            lignes.append(_("Continent") + f" : {objet.continent}")
        if objet.locked:
            lignes.append("🔒 " + _("Protégé"))

        # En texte enrichi, et non en texte simple : une goutte ne s'ecrit
        # pas. Le jeu fait de meme -- le nom, la goutte et son nombre.
        morceaux = ["<br>".join(html.escape(l) for l in lignes)]
        gouttes = specialites.bloc_infobulle_html(objet)
        if gouttes:
            morceaux.append(gouttes)
        sort = enchantements.resume(objet, self._names.name)
        if sort:
            # Les charges disent combien de fois le sort part encore ; le
            # cout, ce qu'un lancer prend. Les deux viennent du meme noeud.
            ligne = _("Enchantement : ") + html.escape(sort)
            if objet.sap_charges:
                ligne += "<br>" + _("Charges de sève : {}").format(
                    objet.sap_charges)
            if objet.enchant_cost:
                ligne += _(" (coût {})").format(abs(objet.enchant_cost))
            morceaux.append(ligne)
        return "<br><br>".join(morceaux)

    def _maj_jauge(self, inv) -> None:
        total = inv.total_volume
        if inv.capacity > 0:
            pct = total / inv.capacity * 100.0
            self._jauge.setVisible(True)
            self._jauge.setValue(int(min(pct, 100.0)))
            alerte = " ⚠" if pct >= self._settings.volume_threshold else ""
            self._lbl_volume.setText(
                f"{total:.0f} / {inv.capacity}  ({pct:.0f}%){alerte}")
        else:
            self._jauge.setVisible(False)
            self._lbl_volume.setText(f"{total:.0f}  "
                                     + _("(capacité inconnue)"))

    # ------------------------------------------------------------ Alertes
    def _verifier_alertes(self, ent, entree: dict, depuis_synchro: bool,
                          saison: dict | None = None) -> None:
        """Refait la liste de la cloche : rien que ce qui a été demandé.

        Quatre sources, et toutes réglées par le joueur : les seuils qu'il pose
        lui-même sur un objet, et les trois réglages des options — remplissage
        d'un contenant, vente qui expire, saison qui tourne.

        Les déplacements d'objets n'y sont pas : ranger douze matières ferait
        sonner douze fois, et l'alerte qui compte se perdrait dans le tas. Le
        journal, lui, garde tout.
        """
        resultat = alerts.volume_alerts(ent, self._settings.volume_threshold)
        if self._watch is not None:
            resultat += alerts.watch_alerts(ent, self._watch, self._names.name)
        resultat += alerts.sales_alerts(ent, self._settings.sales_count,
                                        self._names.name)
        if self._watch is not None:
            resultat += alerts.money_alerts(self._mouvements_argent,
                                            self._watch.money_watched())
        if depuis_synchro and saison:
            tournante = alerts.season_alert(saison,
                                            self._settings.season_count)
            if tournante:
                resultat.append(tournante)
        self._alertes = resultat
        self._maj_cloche()
        if depuis_synchro and resultat:
            self._prevenir(resultat)

    def _recalculer_alertes(self) -> None:
        """Recalcule les alertes après un changement de surveillance, sans
        appel réseau."""
        entree = self._entree_courante()
        if self._entite is not None and entree:
            self._verifier_alertes(self._entite, entree, depuis_synchro=False)

    def _maj_cloche(self) -> None:
        nombre = len(self._alertes)
        self._cloche.setText(f"🔔 {nombre}" if nombre else "🔔")
        # Toujours cliquable, meme sans alerte : c'est dans son panneau qu'on
        # pose la surveillance du tresor, et c'est la qu'elle dit ce qu'elle
        # guette. Grisee, elle ne pourrait plus rien apprendre a personne.
        self._cloche.setEnabled(True)
        infobulle = (_("{} alerte(s)").format(nombre) if nombre
                     else _("Aucune alerte"))
        if not self._settings.notifications:
            # Sans quoi la coupure ne se voit plus une fois la fenetre fermee,
            # et l'on croit l'application muette alors qu'on l'a fait taire.
            infobulle += "\n" + _("Notifications du bureau coupées")
        self._cloche.setToolTip(infobulle)

    def _prevenir(self, alertes: list) -> None:
        if not self._settings.notifications:
            return
        notifications.envoyer(self, "ZyRoom — alertes",
                              "\n".join(a.title for a in alertes[:6]))

    def _on_cloche(self) -> None:
        FenetreAlertes(self, self._alertes, self._watch, self._settings,
                       self._apres_alertes).exec()

    def _apres_alertes(self) -> None:
        self._recalculer_alertes()
        self._maj_cloche()

    # ------------------------------------------------------ Surveillance
    def _surveiller(self, objet) -> None:
        if self._watch is None:
            return
        nom = self._names.name(objet.sheet)
        dlg = DialogueSurveillance(self, objet, nom)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._watch.add(objet, dlg.seuil)
        self._recalculer_alertes()
        self._reafficher()

    def _ne_plus_surveiller(self, objet) -> None:
        if self._watch is None:
            return
        self._watch.remove(objet)
        self._recalculer_alertes()
        self._reafficher()

    # -------------------------------------------------- Menu d'un objet
    @staticmethod
    def _objet_de(case: QListWidgetItem):
        return case.data(_ROLE_OBJET) if case is not None else None

    def _menu_objet(self, position) -> None:
        """Le menu du clic droit sur un objet de la grille."""
        case = self._grille.itemAt(position)
        objet = self._objet_de(case)
        if objet is None:
            return
        menu = QMenu(self._grille)
        menu.addAction(_("Détails…"),
                       lambda: self._afficher_details(objet))
        if objet.item_id:
            menu.addAction(_("Copier l'identifiant"),
                           lambda: self._copier_id(objet))
        if self._watch is not None:
            if self._watch.is_watched(objet):
                menu.addAction(_("Ne plus surveiller"),
                               lambda: self._ne_plus_surveiller(objet))
            else:
                libelle = (_("Surveiller la durabilité…")
                           if watch_kind(objet) == KIND_DURABILITY
                           else _("Surveiller la quantité…"))
                menu.addAction(libelle, lambda: self._surveiller(objet))
        menu.addAction(_("Réinitialiser l'icône"),
                       lambda: self._reinitialiser_icone(objet))
        menu.exec(self._grille.viewport().mapToGlobal(position))

    def _afficher_details(self, objet) -> None:
        if objet is not None:
            detail.montrer(self, objet, self._names.name, self._categorydb)

    def _copier_id(self, objet) -> None:
        QGuiApplication.clipboard().setText(objet.item_id)
        self._statut(_("Identifiant copié : {}").format(objet.item_id))

    def _reinitialiser_icone(self, objet) -> None:
        """Jette l'icône du cache et la redemande.

        Utile quand l'API a renvoyé une image abîmée, ou qu'un objet a changé
        d'aspect : le nom du fichier de cache ne dépend que de la fiche, de la
        couleur et de la qualité, donc une image fausse y resterait pour
        toujours.
        """
        chemin = self._icones.chemin_cache(objet)
        try:
            if os.path.isfile(chemin):
                os.remove(chemin)
        except OSError:
            pass
        self._reafficher()

    # ---------------------------------------------------------- Ligne d'etat
    def _maj_statut(self) -> None:
        """Ligne du bas : qui, quel contenant, et de quand datent les données.

        Deux lignes plutôt qu'une : qui l'on regarde d'abord, puis dans quoi
        et de quand. Sur une seule, le nom de l'application venant se centrer
        au milieu de la barre, l'heure de synchro se coupait dès qu'on n'avait
        pas mille deux cent quatre-vingts pixels de large.
        """
        ent = self._entite
        if not ent:
            return
        rang = self._dd_inv.currentIndex()
        libelle = ""
        if 0 <= rang < len(ent.inventories):
            libelle = ent.inventories[rang].label

        extra = f" - {ent.guild}" if ent.guild else ""
        presence = self._presence(ent)
        vu = f" · {presence[0]}" if presence else ""
        self._lbl_statut.setToolTip(presence[1] if presence else "")
        ligne = (f"{ent.name}{extra}{vu}\n"
                 f"{movements.sans_parenthese(libelle)}")

        # Dater les stocks affiches : sans cela, rien ne distingue une donnee
        # de l'instant d'une donnee vieille de plusieurs jours.
        entree = self._entree_courante()
        if entree:
            quand = last_sync(entree["kind"], entree["id"])
            ligne += " · " + _("synchro {}").format(format_last_sync(quand))
            self._btn_relever.setToolTip(
                _("Resynchroniser depuis l'API")
                + f"\n{_('Dernière synchro')} : {format_last_sync(quand)}")
        self._statut(ligne)

    @staticmethod
    def _presence(ent) -> tuple[str, str] | None:
        """« en ligne » ou « vu il y a… », et l'infobulle qui dit d'où ça sort.

        Renvoie None quand l'API se tait : une guilde, ou une clé sans le
        module qui porte la connexion.

        Le mot est « vu » et non « déconnecté » à dessein. On lit un instantané
        de la sauvegarde du personnage, écrit à la déconnexion : ce que la
        ligne affirme, c'est la dernière fois qu'on l'a vu, pas l'état du
        serveur à la seconde présente.
        """
        etat = ent.en_ligne
        if etat is None:
            return None

        def date(horodatage: int) -> str:
            return (f"{datetime.fromtimestamp(horodatage):%d/%m à %Hh%M}"
                    if horodatage else "—")

        infobulle = (f"{_('Dernière connexion')} : {date(ent.lastlogin)}\n"
                     f"{_('Dernière déconnexion')} : {date(ent.lastlogout)}\n"
                     + _("L'API ne montre que la dernière sauvegarde du "
                         "personnage, écrite à la déconnexion : une connexion "
                         "toute fraîche peut ne pas s'y voir encore."))
        if etat:
            return "🟢 " + _("en ligne"), infobulle

        minutes = int((datetime.now()
                       - datetime.fromtimestamp(ent.lastlogout))
                      .total_seconds() // 60)
        if minutes < 1:
            vu = _("vu à l'instant")
        elif minutes < 60:
            vu = _("vu il y a {} min").format(minutes)
        elif minutes < 24 * 60:
            vu = _("vu il y a {} h").format(minutes // 60)
        elif minutes < 7 * 24 * 60:
            vu = _("vu il y a {} j").format(minutes // (24 * 60))
        else:
            vu = _("vu le {}").format(
                f"{datetime.fromtimestamp(ent.lastlogout):%d/%m}")
        return vu, infobulle

    # ------------------------------------------------------------ Portrait
    def _charger_portrait(self, ent, entree: dict) -> None:
        self._generation_portrait += 1
        generation = self._generation_portrait
        self._chemin_portrait = ""
        if not ent.portrait_url:
            self._portrait.clear()
            return
        chemin = portrait_path(entree["kind"], entree["id"], ent.portrait_url)
        if os.path.isfile(chemin) and os.path.getsize(chemin) > 0:
            self._poser_portrait(chemin)
            return
        url = ent.portrait_url

        def travail():
            donnees = ryzom_api.fetch_url(url)
            with open(chemin, "wb") as fh:
                fh.write(donnees)
            return chemin

        def apres(resultat, erreur):
            if generation != self._generation_portrait:
                return
            if erreur or not resultat:
                self._portrait.clear()
                return
            self._poser_portrait(resultat)

        self._passerelle.lancer(travail, apres)

    def _poser_portrait(self, chemin: str) -> None:
        """Affiche le portrait, recadré en tête/épaules si c'est un corps entier.

        L'API rend le rendu 3D d'un personnage en pied ; réduit à quarante-quatre
        pixels de haut, il ne montrerait plus rien. La même découpe que dans la
        version GTK : le quart central en largeur, le tiers haut en hauteur.
        """
        self._chemin_portrait = chemin
        image = QPixmap(chemin)
        if image.isNull():
            self._portrait.clear()
            return
        l, h = image.width(), image.height()
        if h > l * 1.4:
            image = image.copy(int(l * 0.25), int(h * 0.02),
                               int(l * 0.5), int(h * 0.36))
        self._portrait.setPixmap(image.scaledToHeight(
            HAUTEUR_PORTRAIT, Qt.TransformationMode.SmoothTransformation))

    def _on_portrait_clic(self, _event) -> None:
        """Le portrait en grand, dans sa propre fenêtre."""
        if not self._chemin_portrait:
            return
        vue = QDialog(self)
        vue.setWindowTitle(_("Portrait"))
        colonne = QVBoxLayout(vue)
        lbl = QLabel()
        image = QPixmap(self._chemin_portrait)
        lbl.setPixmap(image.scaled(
            QSize(200, 400), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        colonne.addWidget(lbl)
        vue.show()

    # ------------------------------------------------------- Ajout de cle
    def _on_ajouter(self) -> None:
        """Ouvre la fenêtre des clés. Elle recharge la liste par elle-même."""
        cles.FenetreCles(self, self._char_store, self._guild_store,
                         self._sheetdb, self._passerelle,
                         self._recharger_entites).exec()

    # -------------------------------------------- Options et compagnie
    def _on_options(self) -> None:
        FenetreOptions(self, self._settings, self._apres_options).exec()

    def _appliquer_proxy(self) -> None:
        s = self._settings
        ryzom_api.configure_proxy(s.proxy_enabled, s.proxy_address,
                                  s.proxy_port, s.proxy_username,
                                  s.proxy_password)

    def _apres_options(self) -> None:
        # La police et les icones prennent effet sur-le-champ. Attendre le
        # prochain lancement laissait croire que le reglage ne marchait pas --
        # on regle, rien ne bouge, on recommence.
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(
            theme.feuille(self._settings.font_size))
        self._appliquer_taille_icones()
        self._appliquer_proxy()
        self._charger_noms(self._settings.pack_file)
        self._programmer_releve()      # nouvel intervalle, sans redemarrer
        if not self._settings.notifications:
            notifications.retirer()
        self._recalculer_alertes()
        self._reafficher()
        self._statut(_("Options enregistrées."))

    def _on_chatlog(self) -> None:
        """Analyse un fichier `/chatLog` du jeu."""
        depart = self._settings.save_folder or detect_save_folder() or ""
        chemin, _filtre = QFileDialog.getOpenFileName(
            self, _("Choisir un fichier de chatlog"), depart,
            _("Journaux (*.log *.txt);;Tous les fichiers (*)"))
        if chemin:
            self._statut(chatlog.ouvrir(self, chemin))

    def _on_sauvegarde(self) -> None:
        """Copie le dossier « save » de Ryzom, tout de suite.

        C'est le dossier où le jeu range les réglages d'interface et les
        macros : le perdre, c'est refaire son interface entière.
        """
        dossier = self._settings.save_folder or detect_save_folder()
        if not dossier:
            self._statut(_("Dossier « save » de Ryzom non configuré "
                           "(voir Options)."))
            return
        ok, message = backup.run_backup(dossier)
        self._statut((_("Sauvegarde : ") if ok else "") + message)

    def _on_apropos(self) -> None:
        apropos.montrer(self, APP_NAME, VERSION)

    def _on_pack(self) -> None:
        """Charge un `string_client.pack` choisi à la main.

        C'est le fichier de l'installation du jeu qui donne aux objets leurs
        noms lisibles ; sans lui on n'a que des identifiants de fiches.
        """
        chemin, _filtre = QFileDialog.getOpenFileName(
            self, _("Choisir string_client.pack"),
            self._settings.pack_file or "")
        if not chemin:
            return
        if self._names.load(chemin):
            self._settings.pack_file = chemin
            self._statut(_("Noms chargés depuis {}.").format(
                os.path.basename(chemin)))
            self._reafficher()
        else:
            self._statut(_("Impossible de lire ce fichier "
                           "string_client.pack."))

    # ------------------------------------------------- Mise a jour
    def _verifier_maj(self) -> None:
        """Demande au manifeste publié s'il annonce mieux que ce qu'on exécute.

        La lecture part dans un fil : le lancement ne doit pas attendre le
        réseau, et une coupure ne doit pas figer la fenêtre.
        """
        if not self._veilleur.possible or self._btn_maj.isVisible():
            # Une fois le bouton affiche, plus rien a demander : il n'y a pas
            # deux facons d'etre en retard.
            return

        def travail():
            return self._veilleur.mise_a_jour_disponible()

        def apres(version, erreur):
            if erreur or not version:
                return
            self._btn_maj.setVisible(True)
            self._btn_maj.setToolTip(
                _("Une nouvelle version est disponible") + f" ({version})")
            self._statut(
                _("Une nouvelle version est disponible ({}).").format(version))

        self._passerelle.lancer(travail, apres)

    def _on_maj_clic(self) -> None:
        """Télécharge la nouvelle version et la met en place."""
        url = self._veilleur.url
        if not url:
            return
        self._btn_maj.setEnabled(False)
        self._tourniquet.setVisible(True)
        self._statut(_("Téléchargement de la mise à jour…"))

        def avancement(recu: int, total: int) -> None:
            if total:
                self._progres.emit(int(recu * 100 / total))

        def travail():
            archive = updater.telecharger(url, avancement)
            return updater.installer(archive)

        def apres(resultat, erreur):
            self._tourniquet.setVisible(False)
            self._btn_maj.setEnabled(True)
            if erreur:
                self._statut(_("Mise à jour impossible : {}").format(erreur))
                return
            ok, message = resultat
            self._statut(message)
            if ok:
                # Reussie, le bouton n'a plus lieu d'etre. Echouee, on le
                # rend pour permettre un second essai.
                self._btn_maj.setVisible(False)
                self._proposer_redemarrage()

        self._passerelle.lancer(travail, apres)

    def _on_progres_maj(self, pourcent: int) -> None:
        self._statut(_("Téléchargement de la mise à jour… {} %")
                     .format(pourcent))

    def _proposer_redemarrage(self) -> None:
        """Une mise à jour installée ne tourne qu'au prochain lancement.

        On le propose plutôt que de le faire : fermer la fenêtre sous les
        doigts de quelqu'un qui consulte un coffre serait une drôle de façon
        de le remercier d'avoir mis à jour.
        """
        boite = QMessageBox(self)
        boite.setIcon(QMessageBox.Icon.Information)
        boite.setWindowTitle(_("Mise à jour installée"))
        boite.setText(_("Mise à jour installée"))
        boite.setInformativeText(
            _("Elle ne prendra effet qu'au prochain lancement. Relancer "
              "maintenant ?"))
        boite.addButton(_("Plus tard"), QMessageBox.ButtonRole.RejectRole)
        relancer = boite.addButton(_("Relancer"),
                                   QMessageBox.ButtonRole.AcceptRole)
        boite.setDefaultButton(relancer)
        boite.exec()
        if boite.clickedButton() is not relancer:
            return
        if updater.relancer():
            self.close()
        else:
            self._statut(
                _("Impossible de relancer automatiquement : fermez et rouvrez "
                  "l'application pour utiliser la nouvelle version."))

    # ------------------------------------ Resynchronisation periodique
    def _programmer_releve(self) -> None:
        """(Re)programme la resynchronisation automatique.

        Appelée au démarrage et après un changement d'options, pour prendre en
        compte le nouvel intervalle sans redémarrer.
        """
        self._minuteur.stop()
        minutes = self._settings.sync_interval
        if minutes > 0:
            self._minuteur.start(minutes * 60 * 1000)

    def _tour_de_releve(self) -> None:
        """Relève toutes les entités suivies, pas seulement celle qu'on regarde.

        Les journaux — mouvements de coffres, effectif d'une guilde — se
        déduisent de deux instantanés rapprochés. Ne rafraîchir que l'entité
        affichée laisserait des trous de plusieurs heures dans les autres :
        rester sur son personnage une soirée, puis ouvrir la guilde, et les
        allées et venues de la soirée se résumeraient à un seul écart constaté.

        L'entité affichée passe par le chemin ordinaire, qui met l'écran à
        jour. Les autres sont relevées en silence.
        """
        if self._occupe:
            return
        courante = self._entree_courante()
        if courante:
            self._synchroniser(courante)
        for entree in list(self._entrees):
            if courante and (entree["kind"], entree["id"]) == (
                    courante["kind"], courante["id"]):
                continue
            self._relever_en_silence(entree)

    def _relever_en_silence(self, entree: dict) -> None:
        """Va chercher le flux d'une entité et journalise, sans toucher à l'écran.

        Rien n'en sort à l'affichage : la barre d'état parle de ce qu'on
        regarde. Le journal, lui, garde tout — c'est là qu'on va voir.
        """
        genre, cle = entree["kind"], entree["key"]
        chercher = (ryzom_api.fetch_character_xml if genre == KIND_CHARACTER
                    else ryzom_api.fetch_guild_xml)

        def travail():
            xml = chercher(cle)
            with open(entity_xml_path(genre, entree["id"]), "wb") as fh:
                fh.write(xml)
            analyser = (ryzom_api.parse_character if genre == KIND_CHARACTER
                        else ryzom_api.parse_guild)
            ent = analyser(xml, self._sheetdb.name)

            # Le journal des mouvements, comme pour l'entite affichee.
            chemin = snapshot_path(genre, entree["id"])
            avant = alerts.load_snapshot(chemin)
            apres_ = alerts.build_snapshot(ent)
            if avant:
                movements.append(movements_path(genre, entree["id"]),
                                 movements.diff(avant, apres_, ent))
            alerts.save_snapshot(chemin, apres_)

            # Et le registre du personnel, pour une guilde.
            if genre == KIND_GUILD and ent.members:
                roster.RosterStore(data_dir(), ent.entity_id).record(ent.members)
            return ent.name

        def fini(_nom, erreur):
            # Un echec est sans consequence : on reessaiera au prochain tour,
            # et le dire volerait la barre d'etat a ce qu'on regarde.
            if erreur:
                return
            if self._pile.currentIndex() == self._pages["log"]:
                self._charger_journal()

        self._passerelle.lancer(travail, fini)

    # ------------------------------------------------------------- Divers
    def _statut(self, texte: str) -> None:
        self._lbl_statut.setText(texte)

    def closeEvent(self, event) -> None:      # noqa: N802 -- nom impose par Qt
        """Retient la taille de la fenêtre, puis coupe les téléchargements."""
        if not self.isMaximized():
            self._settings.window_size = (self.width(), self.height())
        self._settings.window_maximized = self.isMaximized()
        self._minuteur.stop()
        self._minuteur_maj.stop()
        self._minuteur_saison.stop()
        notifications.arreter()
        self._icones.arreter()
        super().closeEvent(event)
