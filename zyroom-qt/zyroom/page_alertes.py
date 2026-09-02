"""La cloche : ce que l'application a été chargée de guetter.

Quatre sources, et toutes réglées par le joueur : les seuils qu'il pose
lui-même sur un objet (quantité minimale, durabilité), et les trois réglages
des options — remplissage d'un contenant, vente qui expire, saison qui tourne.
Un objet surveillé qui a disparu s'y ajoute, puisque c'est bien lui qu'on avait
demandé à suivre.

**Les déplacements d'objets n'y sont pas.** Ranger douze matières faisait
sonner douze fois, et l'alerte qui comptait se perdait dans le tas. Le journal,
lui, garde tout — daté et consultable.
"""
from __future__ import annotations

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from .i18n import _
from .watch import KIND_DURABILITY, watch_kind

#: Une figure par sorte d'alerte : la liste se lit d'un coup d'oeil, et l'on
#: voit tout de suite laquelle des surveillances a parle.
FIGURES = {"quantity": "📉", "durability": "🛡", "unfound": "❓",
           "volume": "📦", "sales": "💰", "season": "🍂", "money": "🪙"}


class FenetreAlertes(QDialog):
    def __init__(self, parent, alertes: list, watch, settings,
                 apres_changement) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Alertes"))
        # Rouverte a la taille ou on l'a laissee : la bonne largeur depend des
        # noms d'objets surveilles, que nous ne connaissons pas d'avance.
        self.resize(*settings.alerts_window_size)
        self._settings = settings
        self._watch = watch
        self._apres = apres_changement

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(8, 8, 8, 8)
        colonne.setSpacing(8)

        contenu = QWidget()
        liste = QVBoxLayout(contenu)
        liste.setContentsMargins(0, 0, 0, 0)
        liste.setSpacing(10)

        if not alertes:
            liste.addWidget(QLabel(_("Aucune alerte.")))
        for alerte in alertes:
            figure = FIGURES.get(alerte.kind, "🔔")
            titre = QLabel(f"{figure} <b>{html.escape(alerte.title)}</b>")
            titre.setWordWrap(True)
            liste.addWidget(titre)
            detail = QLabel(alerte.detail)
            detail.setObjectName("discret")
            detail.setWordWrap(True)
            detail.setContentsMargins(18, 0, 0, 0)
            liste.addWidget(detail)
        liste.addStretch(1)

        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        defilant.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        colonne.addWidget(defilant, 1)

        # La surveillance du tresor se pose ici, et nulle part ailleurs :
        # l'argent n'a pas d'icone dans un inventaire ou l'on ferait un clic
        # droit, comme pour les objets. La cloche etant l'endroit ou l'on vient
        # voir ce qui est guette, c'est aussi celui ou on le lui demande.
        self._tresor = QCheckBox(_("Prévenir mouvement dappers"))
        self._tresor.setEnabled(watch is not None)
        self._tresor.setChecked(watch is not None and watch.money_watched())
        self._tresor.setToolTip(_(
            "Une alerte à chaque relevé où les dappers ont bougé, dans un sens "
            "ou dans l'autre. Sans seuil à régler : un relevé rapporte au plus "
            "un mouvement d'argent, il ne peut donc pas noyer les autres."))
        self._tresor.toggled.connect(self._on_tresor)
        colonne.addWidget(self._tresor)

        # Le pied : la coupure a gauche, la sortie a droite. La coupure ne
        # touche qu'au bureau -- la liste au-dessus reste pleine.
        pied = QHBoxLayout()
        self._bulles = QCheckBox(_("Notifications du bureau"))
        self._bulles.setChecked(settings.notifications)
        self._bulles.setToolTip(_(
            "Coupe les bulles qui s'affichent près de l'horloge à chaque "
            "synchronisation. Les alertes restent listées ici."))
        self._bulles.toggled.connect(self._on_bulles)
        pied.addWidget(self._bulles)
        pied.addStretch(1)
        fermer = QPushButton(_("Fermer"))
        fermer.clicked.connect(self.accept)
        pied.addWidget(fermer)
        colonne.addLayout(pied)

    def _on_tresor(self, actif: bool) -> None:
        """Pose ou lève la surveillance du trésor de l'entité affichée.

        Elle vit dans la liste des objets surveillés, sous la signature
        réservée du journal : une surveillance de plus, rangée avec les autres,
        et qui suit l'entité comme elles.
        """
        if self._watch is not None:
            self._watch.set_money_watched(actif)
            self._apres()

    def _on_bulles(self, actif: bool) -> None:
        """Coupe ou rétablit les bulles du bureau, sans toucher aux alertes."""
        self._settings.notifications = actif
        if not actif:
            from . import notifications
            notifications.retirer()
        self._apres()

    def closeEvent(self, event) -> None:      # noqa: N802 -- nom impose par Qt
        """Retient la taille de la fenêtre avant qu'elle parte."""
        self._settings.alerts_window_size = (self.width(), self.height())
        super().closeEvent(event)


class DialogueSurveillance(QDialog):
    """Le seuil sous lequel un objet doit faire sonner la cloche."""

    def __init__(self, parent, item, nom: str) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Surveiller un objet"))
        self.setMinimumWidth(420)
        self._durabilite = watch_kind(item) == KIND_DURABILITY

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(10)

        entete = QLabel(f"<b>{html.escape(nom)}</b> (Q{item.quality})")
        entete.setWordWrap(True)
        colonne.addWidget(entete)

        explication = QLabel(
            _("Alerte si la durabilité descend sous ce seuil :")
            if self._durabilite
            else _("Alerte si la quantité descend sous ce seuil :"))
        explication.setWordWrap(True)
        colonne.addWidget(explication)

        self._seuil = QSpinBox()
        self._seuil.setRange(0, 100000)
        self._seuil.setValue(item.hp if self._durabilite else item.stack)
        colonne.addWidget(self._seuil)

        pied = QHBoxLayout()
        pied.addStretch(1)
        annuler = QPushButton(_("Annuler"))
        annuler.clicked.connect(self.reject)
        pied.addWidget(annuler)
        valider = QPushButton(_("Surveiller"))
        valider.setObjectName("principal")
        valider.clicked.connect(self.accept)
        pied.addWidget(valider)
        colonne.addLayout(pied)

    @property
    def seuil(self) -> int:
        return self._seuil.value()
