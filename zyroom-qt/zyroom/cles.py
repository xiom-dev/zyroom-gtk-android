"""La fenêtre des clés d'API : en poser dans un onglet, les relire dans l'autre.

Les deux gestes vont ensemble — remplacer une clé expirée, c'est en saisir une
nouvelle là où l'on vient de lire l'ancienne — et une clé qu'on ne peut pas
relire est une clé qu'il faut aller rechercher sur le site de Ryzom chaque fois
qu'on veut la vérifier.

Une clé est toujours **vérifiée auprès de l'API avant d'être enregistrée** :
une clé qu'on pose sans la vérifier est une entité qui ne se synchronisera
jamais, et l'on ne le découvre qu'au relevé suivant.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QRadioButton,
                               QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from . import ryzom_api
from .config import entity_xml_path
from .i18n import _
from .ryzom_api import KIND_CHARACTER, KIND_GUILD

#: Le message d'une cle mal formee. Ce qui se voit a l'oeil ne vaut pas un
#: aller-retour reseau : une cle tronquee au copier-coller partait quand meme,
#: et l'on attendait la reponse de Ryzom pour l'apprendre.
_MAL_FORMEE = ("Cette clé n'a pas la forme d'une clé d'API : 41 signes, "
               "commençant par « c » ou « g ».")


def _mono(texte: str) -> QLabel:
    """La clé en entier, en chasse fixe et sélectionnable.

    La lire est tout l'objet de l'onglet « Modifier », et une clé tronquée ne
    se recopie pas à la main. En chasse fixe, où l'œil distingue le 0 du O et
    le 1 du l.
    """
    lbl = QLabel(texte)
    police = QFont("monospace")
    police.setStyleHint(QFont.StyleHint.Monospace)
    lbl.setFont(police)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse)
    return lbl


class FenetreCles(QDialog):
    def __init__(self, parent, char_store, guild_store, sheetdb, passerelle,
                 apres_changement) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Clés API"))
        self.resize(620, 540)
        self._char_store = char_store
        self._guild_store = guild_store
        self._sheetdb = sheetdb
        self._passerelle = passerelle
        self._apres = apres_changement

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(10)

        self._onglets = QTabWidget()
        self._onglets.addTab(self._page_ajout(), _("Ajouter"))
        self._page_liste = QWidget()
        QVBoxLayout(self._page_liste).setContentsMargins(0, 0, 0, 0)
        self._onglets.addTab(self._page_liste, _("Modifier"))
        self._remplir_liste()
        colonne.addWidget(self._onglets, 1)

        pied = QHBoxLayout()
        pied.addStretch(1)
        fermer = QPushButton(_("Fermer"))
        fermer.clicked.connect(self.accept)
        pied.addWidget(fermer)
        colonne.addLayout(pied)

    # ------------------------------------------------- Onglet "Ajouter"
    def _page_ajout(self) -> QWidget:
        page = QWidget()
        colonne = QVBoxLayout(page)
        colonne.setContentsMargins(10, 10, 10, 10)
        colonne.setSpacing(10)

        genre = QWidget()
        ligne_genre = QHBoxLayout(genre)
        ligne_genre.setContentsMargins(0, 0, 0, 0)
        ligne_genre.setSpacing(12)
        self._rb_perso = QRadioButton(_("Personnage"))
        self._rb_perso.setChecked(True)
        self._rb_guilde = QRadioButton(_("Guilde"))
        ligne_genre.addWidget(self._rb_perso)
        ligne_genre.addWidget(self._rb_guilde)
        ligne_genre.addStretch(1)
        colonne.addWidget(genre)

        self._indice = QLabel()
        self._indice.setObjectName("discret")
        self._indice.setWordWrap(True)
        colonne.addWidget(self._indice)
        self._rb_perso.toggled.connect(self._maj_indice)
        self._maj_indice()

        self._saisie = QLineEdit()
        self._saisie.setPlaceholderText(_("Clé API"))
        self._saisie.returnPressed.connect(self._ajouter)
        colonne.addWidget(self._saisie)

        # Aller chercher sa cle et la coller : les deux gestes que le
        # telephone offrait deja, et qu'il fallait faire a la main ici.
        gestes = QWidget()
        ligne_gestes = QHBoxLayout(gestes)
        ligne_gestes.setContentsMargins(0, 0, 0, 0)
        ligne_gestes.setSpacing(8)
        obtenir = QPushButton(_("Obtenir ma clé"))
        obtenir.setToolTip(ryzom_api.KEY_PAGE)
        obtenir.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(ryzom_api.KEY_PAGE)))
        ligne_gestes.addWidget(obtenir)
        coller = QPushButton(_("Coller"))
        coller.setToolTip(_("Coller la clé depuis le presse-papiers"))
        coller.clicked.connect(
            lambda: self._saisie.setText(
                (QGuiApplication.clipboard().text() or "").strip()))
        ligne_gestes.addWidget(coller)
        ligne_gestes.addStretch(1)
        colonne.addWidget(gestes)

        self._nom = QLineEdit()
        self._nom.setPlaceholderText(_("Nom affiché (optionnel)"))
        colonne.addWidget(self._nom)

        self._etat = QLabel()
        self._etat.setWordWrap(True)
        colonne.addWidget(self._etat)

        pied = QHBoxLayout()
        pied.addStretch(1)
        self._btn_ajouter = QPushButton(_("Ajouter"))
        self._btn_ajouter.setObjectName("principal")
        self._btn_ajouter.clicked.connect(self._ajouter)
        pied.addWidget(self._btn_ajouter)
        colonne.addLayout(pied)
        colonne.addStretch(1)
        return page

    def _maj_indice(self) -> None:
        requis = (ryzom_api.REQUIRED_MODULES_CHAR if self._rb_perso.isChecked()
                  else ryzom_api.REQUIRED_MODULES_GUILD)
        self._indice.setText(
            _("Une clé fait 41 signes. Celles de personnage commencent par "
              "« c », celles de guilde par « g ». Modules requis : ")
            + ", ".join(requis))

    def _ajouter(self) -> None:
        cle = self._saisie.text().strip()
        if not cle:
            self._etat.setText(_("Veuillez saisir une clé API."))
            return
        if not ryzom_api.is_api_key(cle):
            self._etat.setText(_(_MAL_FORMEE))
            return
        perso = self._rb_perso.isChecked()
        genre = KIND_CHARACTER if perso else KIND_GUILD
        magasin = self._char_store if perso else self._guild_store
        self._btn_ajouter.setEnabled(False)
        self._etat.setText(_("Vérification de la clé…"))

        def apres(ent, xml, souci):
            if souci:
                self._etat.setText(souci)
                self._btn_ajouter.setEnabled(True)
                return
            nom = self._nom.text().strip() or ent.name
            magasin.save(ent.entity_id, cle, nom, ent.shard, ent.guild)
            with open(entity_xml_path(genre, ent.entity_id), "wb") as fh:
                fh.write(xml)
            self._apres(ent.entity_id)
            self.accept()

        self._verifier(cle, genre, apres)

    # ------------------------------------------------ Onglet "Modifier"
    def _remplir_liste(self) -> None:
        """Refait la liste des clés enregistrées, à l'ouverture et après coup."""
        ancien = self._page_liste.layout()
        while ancien.count():
            element = ancien.takeAt(0)
            if element.widget():
                element.widget().deleteLater()

        contenu = QWidget()
        colonne = QVBoxLayout(contenu)
        colonne.setContentsMargins(10, 10, 10, 10)
        colonne.setSpacing(4)

        vide = True
        for genre, magasin, mot in ((KIND_CHARACTER, self._char_store,
                                     _("personnage")),
                                    (KIND_GUILD, self._guild_store,
                                     _("guilde"))):
            for entree in magasin.entries():
                vide = False
                colonne.addWidget(self._ligne_cle(entree, genre, magasin, mot))
        if vide:
            lbl = QLabel(_("Aucune clé enregistrée — l'onglet « Ajouter » est "
                           "à côté."))
            lbl.setObjectName("discret")
            lbl.setWordWrap(True)
            colonne.addWidget(lbl)
        colonne.addStretch(1)

        defilant = QScrollArea()
        defilant.setWidget(contenu)
        defilant.setWidgetResizable(True)
        ancien.addWidget(defilant)

    def _ligne_cle(self, entree: dict, genre: str, magasin, mot: str) -> QWidget:
        """Une entité : son nom, sa clé en entier, et ce qu'on peut en faire."""
        ligne = QWidget()
        colonne = QVBoxLayout(ligne)
        colonne.setContentsMargins(0, 0, 0, 10)
        colonne.setSpacing(2)

        titre = QLabel(f"<b>{entree['name']}</b>&nbsp;&nbsp;"
                       f"<span style='opacity:0.6'>{mot}</span>")
        colonne.addWidget(titre)
        colonne.addWidget(_mono(entree["key"]))

        actions = QHBoxLayout()
        actions.addStretch(1)
        copier = QPushButton(_("Copier"))
        copier.setToolTip(_("Copier la clé dans le presse-papiers"))
        copier.clicked.connect(
            lambda: QGuiApplication.clipboard().setText(entree["key"]))
        actions.addWidget(copier)

        changer = QPushButton("✎")
        changer.setToolTip(_("Remplacer la clé"))
        changer.setFixedWidth(34)
        changer.clicked.connect(
            lambda: self._changer_cle(entree, genre, magasin))
        actions.addWidget(changer)

        retirer = QPushButton("🗑")
        retirer.setToolTip(_("Retirer cette entité"))
        retirer.setFixedWidth(34)
        retirer.clicked.connect(lambda: self._confirmer_retrait(entree, magasin))
        actions.addWidget(retirer)
        colonne.addLayout(actions)

        trait = QFrame()
        trait.setFrameShape(QFrame.Shape.HLine)
        trait.setFrameShadow(QFrame.Shadow.Plain)
        colonne.addWidget(trait)
        return ligne

    def _changer_cle(self, entree: dict, genre: str, magasin) -> None:
        """Remplace la clé d'une entité déjà connue, après l'avoir vérifiée.

        La nouvelle clé peut désigner une autre entité — on s'est trompé de
        ligne, ou l'on a repris la clé d'un autre personnage. L'ancienne entrée
        est alors retirée : sans quoi la liste porterait deux fois la même
        entité, l'une avec une clé qui n'est plus la sienne.
        """
        petit = QDialog(self)
        petit.setWindowTitle(_("Remplacer la clé"))
        petit.setMinimumWidth(460)
        colonne = QVBoxLayout(petit)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(10)

        explication = QLabel(
            _("Nouvelle clé pour « {} ». Elle est vérifiée auprès de Ryzom "
              "avant d'être enregistrée.").format(entree["name"]))
        explication.setWordWrap(True)
        colonne.addWidget(explication)

        saisie = QLineEdit(entree["key"])
        saisie.setPlaceholderText(_("Clé API"))
        colonne.addWidget(saisie)

        etat = QLabel()
        etat.setWordWrap(True)
        colonne.addWidget(etat)

        pied = QHBoxLayout()
        pied.addStretch(1)
        annuler = QPushButton(_("Annuler"))
        annuler.clicked.connect(petit.reject)
        pied.addWidget(annuler)
        valider = QPushButton(_("Remplacer"))
        valider.setObjectName("principal")
        pied.addWidget(valider)
        colonne.addLayout(pied)

        def poser():
            cle = saisie.text().strip()
            if not cle:
                etat.setText(_("Veuillez saisir une clé API."))
                return
            if not ryzom_api.is_api_key(cle):
                etat.setText(_(_MAL_FORMEE))
                return
            valider.setEnabled(False)
            etat.setText(_("Vérification de la clé…"))

            def apres(ent, xml, souci):
                if souci:
                    etat.setText(souci)
                    valider.setEnabled(True)
                    return
                if ent.entity_id != entree["id"]:
                    magasin.remove(entree["id"])
                magasin.save(ent.entity_id, cle, entree["name"] or ent.name,
                             ent.shard, ent.guild)
                with open(entity_xml_path(genre, ent.entity_id), "wb") as fh:
                    fh.write(xml)
                petit.accept()
                self._remplir_liste()
                self._apres(ent.entity_id)

            self._verifier(cle, genre, apres)

        valider.clicked.connect(poser)
        saisie.returnPressed.connect(poser)
        petit.exec()

    def _confirmer_retrait(self, entree: dict, magasin) -> None:
        """Le retrait se demande deux fois : les trois boutons sont voisins.

        Celui de la barre principale ne demande rien, mais il porte sur
        l'entité qu'on est en train de regarder. Ici on vise une ligne dans une
        liste, et la corbeille est à un centimètre de « Copier ».
        """
        boite = QMessageBox(self)
        boite.setIcon(QMessageBox.Icon.Warning)
        boite.setWindowTitle(_("Retirer « {} » ?").format(entree["name"]))
        boite.setText(_("Retirer « {} » ?").format(entree["name"]))
        boite.setInformativeText(
            _("Sa clé sera oubliée. Rien n'est supprimé chez Ryzom, et la "
              "remettre suffit à la retrouver."))
        annuler = boite.addButton(_("Annuler"),
                                  QMessageBox.ButtonRole.RejectRole)
        retirer = boite.addButton(_("Retirer"),
                                  QMessageBox.ButtonRole.DestructiveRole)
        boite.setDefaultButton(annuler)
        boite.exec()
        if boite.clickedButton() is not retirer:
            return
        magasin.remove(entree["id"])
        self._remplir_liste()
        self._apres(None)

    # ---------------------------------------------------- Verification
    def _verifier(self, cle: str, genre: str, apres) -> None:
        """Demande à l'API ce que vaut cette clé, puis `apres(ent, xml, souci)`.

        `souci` est le message à afficher, ou une chaîne vide si tout va bien.
        Le même chemin sert à l'ajout et au remplacement.
        """
        perso = genre == KIND_CHARACTER
        chercher = (ryzom_api.fetch_character_xml if perso
                    else ryzom_api.fetch_guild_xml)
        analyser = (ryzom_api.parse_character if perso
                    else ryzom_api.parse_guild)
        requis = (ryzom_api.REQUIRED_MODULES_CHAR if perso
                  else ryzom_api.REQUIRED_MODULES_GUILD)

        def travail():
            xml = chercher(cle)
            return analyser(xml, self._sheetdb.name), xml

        def fini(resultat, erreur):
            if erreur:
                apres(None, None, _("Échec : {}").format(erreur))
                return
            ent, xml = resultat
            manquants = ryzom_api.check_modules(ent.modules, requis)
            if manquants:
                apres(None, None,
                      _("Modules manquants : ") + ", ".join(manquants))
                return
            apres(ent, xml, "")

        self._passerelle.lancer(travail, fini)
