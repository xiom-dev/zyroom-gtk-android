"""Fenêtre d'options (réglages généraux).

Les mêmes réglages que la version GTK, dans le même ordre : langue, chemins du
jeu, seuils d'alerte, notifications, resynchronisation, sauvegarde, proxy.
Rien n'est écrit tant qu'on n'a pas cliqué « Enregistrer » — annuler laisse le
fichier `settings.ini` exactement comme il était.

**Le seul écart avec GTK** tient au sélecteur de fichier : `Gtk.FileDialog`
rend la main par un rappel, `QFileDialog` par une valeur de retour. Le code y
gagne, et le comportement est identique.
"""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QGridLayout, QLabel, QLineEdit,
                               QPushButton, QSpinBox, QVBoxLayout, QWidget)

from .i18n import LANGUAGES, _


class FenetreOptions(QDialog):
    def __init__(self, parent, settings, apres_enregistrement=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("Options"))
        self.setMinimumWidth(560)
        self._settings = settings
        self._apres = apres_enregistrement

        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(14, 14, 14, 14)
        colonne.setSpacing(10)

        porteur = QWidget()
        grille = QGridLayout(porteur)
        grille.setContentsMargins(0, 0, 0, 0)
        grille.setHorizontalSpacing(10)
        grille.setVerticalSpacing(10)
        grille.setColumnStretch(1, 1)
        colonne.addWidget(porteur)
        rang = 0

        # Langue de l'interface
        grille.addWidget(QLabel(_("Langue")), rang, 0)
        self._codes_langue = list(LANGUAGES.keys())
        self._dd_langue = QComboBox()
        self._dd_langue.addItems(list(LANGUAGES.values()))
        try:
            self._dd_langue.setCurrentIndex(
                self._codes_langue.index(settings.language))
        except ValueError:
            self._dd_langue.setCurrentIndex(0)
        grille.addWidget(self._dd_langue, rang, 1, 1, 2)
        rang += 1

        # string_client.pack
        grille.addWidget(QLabel(_("Fichier string_client.pack")), rang, 0)
        self._pack = QLineEdit(settings.pack_file)
        grille.addWidget(self._pack, rang, 1)
        btn_pack = QPushButton(_("Parcourir…"))
        btn_pack.clicked.connect(lambda: self._parcourir(self._pack, False))
        grille.addWidget(btn_pack, rang, 2)
        rang += 1

        # Dossier save de Ryzom
        grille.addWidget(QLabel(_("Dossier « save » de Ryzom")), rang, 0)
        self._save = QLineEdit(settings.save_folder)
        grille.addWidget(self._save, rang, 1)
        btn_save = QPushButton(_("Parcourir…"))
        btn_save.clicked.connect(lambda: self._parcourir(self._save, True))
        grille.addWidget(btn_save, rang, 2)
        rang += 1

        # Le corps du texte, avant les seuils : c'est un reglage de confort,
        # pas d'alerte, et il se cherche a cote de la langue.
        grille.addWidget(QLabel(_("Taille du texte (points)")), rang, 0)
        self._police = QSpinBox()
        self._police.setRange(0, 30)
        self._police.setSpecialValueText(_("taille du bureau"))
        self._police.setValue(settings.font_size)
        self._police.setToolTip(_(
            "Le corps du texte, comme dans un traitement de texte. Le bureau "
            "tourne autour de 10 ; 12 ou 14 se lisent mieux dans les tableaux. "
            "Zéro laisse la police du système. Le changement prend effet au "
            "prochain lancement."))
        grille.addWidget(self._police, rang, 1)
        rang += 1

        grille.addWidget(QLabel(_("Taille des icônes (pixels)")), rang, 0)
        self._icones = QSpinBox()
        self._icones.setRange(24, 128)
        self._icones.setSingleStep(8)
        self._icones.setValue(settings.icon_size)
        self._icones.setToolTip(_(
            "Le côté des icônes de l'inventaire. L'API les rend en 48 ; "
            "au-delà elles sont agrandies et se ramollissent un peu, mais une "
            "grille chargée se parcourt mieux. Prend effet au prochain "
            "lancement."))
        grille.addWidget(self._icones, rang, 1)
        rang += 1

        rang = self._ligne_nombre(grille, rang, "Seuil d'alerte de volume (%)",
                                  "_volume", 0, 100, 5,
                                  settings.volume_threshold)
        rang = self._ligne_nombre(grille, rang,
                                  "Alerte ventes (heures avant expiration)",
                                  "_ventes", 0, 168, 1, settings.sales_count)
        rang = self._ligne_nombre(grille, rang,
                                  "Alerte saison (heures avant changement)",
                                  "_saison", 0, 168, 1, settings.season_count)

        # Notifications du bureau.
        self._notifications = QCheckBox(
            _("Afficher les alertes sur le bureau (bulles près de l'horloge)"))
        self._notifications.setChecked(settings.notifications)
        self._notifications.setToolTip(_(
            "Décochée, l'application n'envoie plus rien au bureau. Les alertes "
            "restent visibles dans la fenêtre de la cloche."))
        grille.addWidget(self._notifications, rang, 0, 1, 3)
        rang += 1

        rang = self._ligne_nombre(
            grille, rang, "Resynchroniser toutes les (minutes, 0 = jamais)",
            "_intervalle", 0, 240, 5, settings.sync_interval)

        self._sync_ouverture = QCheckBox(
            _("Synchroniser à l'ouverture d'un personnage ou d'une guilde"))
        self._sync_ouverture.setChecked(settings.sync_on_start)
        grille.addWidget(self._sync_ouverture, rang, 0, 1, 3)
        rang += 1

        self._sauvegarde_auto = QCheckBox(
            _("Sauvegarder le dossier « save » à la fermeture"))
        self._sauvegarde_auto.setChecked(settings.backup_auto)
        grille.addWidget(self._sauvegarde_auto, rang, 0, 1, 3)
        rang += 1

        # Proxy HTTP
        self._proxy_actif = QCheckBox(_("Utiliser un proxy HTTP"))
        self._proxy_actif.setChecked(settings.proxy_enabled)
        grille.addWidget(self._proxy_actif, rang, 0, 1, 3)
        rang += 1

        grille.addWidget(QLabel(_("Adresse du proxy")), rang, 0)
        self._proxy_adresse = QLineEdit(settings.proxy_address)
        grille.addWidget(self._proxy_adresse, rang, 1, 1, 2)
        rang += 1

        rang = self._ligne_nombre(grille, rang, "Port du proxy", "_proxy_port",
                                  0, 65535, 1, settings.proxy_port)

        grille.addWidget(QLabel(_("Identifiant proxy")), rang, 0)
        self._proxy_utilisateur = QLineEdit(settings.proxy_username)
        grille.addWidget(self._proxy_utilisateur, rang, 1, 1, 2)
        rang += 1

        grille.addWidget(QLabel(_("Mot de passe proxy")), rang, 0)
        self._proxy_motdepasse = QLineEdit(settings.proxy_password)
        self._proxy_motdepasse.setEchoMode(QLineEdit.EchoMode.Password)
        grille.addWidget(self._proxy_motdepasse, rang, 1, 1, 2)
        rang += 1

        boutons = QDialogButtonBox()
        boutons.addButton(_("Annuler"),
                          QDialogButtonBox.ButtonRole.RejectRole)
        valider = boutons.addButton(_("Enregistrer"),
                                    QDialogButtonBox.ButtonRole.AcceptRole)
        valider.setObjectName("principal")
        boutons.accepted.connect(self._enregistrer)
        boutons.rejected.connect(self.reject)
        colonne.addWidget(boutons)

    def _ligne_nombre(self, grille: QGridLayout, rang: int, libelle: str,
                      attribut: str, mini: int, maxi: int, pas: int,
                      valeur: int) -> int:
        """Une ligne « libellé + compteur ». Rend le rang suivant."""
        grille.addWidget(QLabel(_(libelle)), rang, 0)
        compteur = QSpinBox()
        compteur.setRange(mini, maxi)
        compteur.setSingleStep(pas)
        compteur.setValue(valeur)
        grille.addWidget(compteur, rang, 1)
        setattr(self, attribut, compteur)
        return rang + 1

    def _parcourir(self, champ: QLineEdit, dossier: bool) -> None:
        if dossier:
            chemin = QFileDialog.getExistingDirectory(
                self, _("Dossier « save » de Ryzom"), champ.text())
        else:
            chemin, _filtre = QFileDialog.getOpenFileName(
                self, _("Choisir string_client.pack"), champ.text())
        if chemin:
            champ.setText(chemin)

    def _enregistrer(self) -> None:
        s = self._settings
        s.pack_file = self._pack.text().strip()
        s.save_folder = self._save.text().strip()
        s.volume_threshold = self._volume.value()
        s.sales_count = self._ventes.value()
        s.season_count = self._saison.value()
        s.sync_interval = self._intervalle.value()
        s.sync_on_start = self._sync_ouverture.isChecked()
        s.notifications = self._notifications.isChecked()
        s.backup_auto = self._sauvegarde_auto.isChecked()
        s.proxy_enabled = self._proxy_actif.isChecked()
        s.proxy_address = self._proxy_adresse.text().strip()
        s.proxy_port = self._proxy_port.value()
        s.proxy_username = self._proxy_utilisateur.text().strip()
        s.proxy_password = self._proxy_motdepasse.text()
        s.language = self._codes_langue[self._dd_langue.currentIndex()]
        s.font_size = self._police.value()
        s.icon_size = self._icones.value()
        self.accept()
        if self._apres:
            self._apres()
