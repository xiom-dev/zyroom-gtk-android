#!/usr/bin/env python3
"""Le remplacement d'une installation par la suivante, et ses echecs.

C'est le seul endroit du projet qui efface et remplace un dossier
d'application. Le README affirmait depuis des mois : « Verifie -- archive
illisible, archive etrangere, absence d'installation : les trois laissent le
dossier intact. » Verifie une fois, a la main. Ce sont ces trois phrases,
devenues des essais, plus ce que le tour de main doit preserver au passage :
les liens symboliques de Qt, le bit d'execution, et le lanceur du chef.

**Rien n'est simule a moitie** : chaque essai construit une vraie installation
dans un dossier jetable, une vraie archive ZIP, et regarde le disque apres
coup. Ce qui ne peut pas l'etre ici, c'est Windows -- la ou l'on depose a cote
au lieu de renommer ; `test_updater_suffixes.py` couvre le relais qui s'en
charge.
"""
import os
import shutil
import stat
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import updater  # noqa: E402

#: Le nom du dossier distribue, et celui de l'executable qu'il porte.
NOM = "ZyRoom-Qt"


class Installation(unittest.TestCase):
    """Une installation en place, et une archive qui vient la remplacer."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="essai-maj-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cible = os.path.join(self.tmp, NOM)
        os.makedirs(self.cible)
        self.binaire = os.path.join(self.cible, NOM)
        self.ecrire(self.binaire, "#!/bin/sh\necho ancienne\n", 0o755)
        self.ecrire(os.path.join(self.cible, "marque-ancienne.txt"), "1.0")

        # L'application se croit empaquetee et installee la : `installer`
        # lit le dossier par `dossier_installe`, et le nom de l'executable
        # attendu par `sys.executable`.
        self.enter(mock.patch.object(updater, "dossier_installe",
                                     lambda: self.cible))
        self.enter(mock.patch.object(updater.sys, "executable", self.binaire))

    def enter(self, patcheur):
        patcheur.start()
        self.addCleanup(patcheur.stop)

    @staticmethod
    def ecrire(chemin: str, contenu: str, mode: int = 0o644) -> None:
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write(contenu)
        os.chmod(chemin, mode)

    def archive(self, nom="neuve.zip", avec_binaire=True, liens=False,
                mode_binaire=0o755) -> str:
        """Une archive comme celles que la CI produit : un dossier unique."""
        chemin = os.path.join(self.tmp, nom)
        with zipfile.ZipFile(chemin, "w") as zip_:
            if avec_binaire:
                info = zipfile.ZipInfo(f"{NOM}/{NOM}")
                info.external_attr = (mode_binaire | stat.S_IFREG) << 16
                zip_.writestr(info, "#!/bin/sh\necho neuve\n")
            zip_.writestr(f"{NOM}/marque-neuve.txt", "2.0")
            if liens:
                # Qt en pose des dizaines : libQt6Core.so.6 pointe sur
                # libQt6Core.so.6.11.2. Extraits comme des fichiers, ce sont
                # trente octets a la place d'une bibliotheque.
                zip_.writestr(f"{NOM}/libQt6Core.so.6.11.2", "x" * 40)
                lien = zipfile.ZipInfo(f"{NOM}/libQt6Core.so.6")
                lien.external_attr = (0o777 | stat.S_IFLNK) << 16
                zip_.writestr(lien, "libQt6Core.so.6.11.2")
        return chemin

    # ------------------------------------------------------ Le cas nominal

    def test_la_neuve_prend_la_place_et_l_ancienne_est_mise_de_cote(self):
        reussi, message = updater.installer(self.archive())
        self.assertTrue(reussi, message)
        self.assertTrue(os.path.isfile(os.path.join(self.cible,
                                                    "marque-neuve.txt")))
        self.assertFalse(os.path.isfile(os.path.join(self.cible,
                                                     "marque-ancienne.txt")))
        ancienne = self.cible + updater.SUFFIXE_ANCIEN
        self.assertTrue(os.path.isfile(os.path.join(ancienne,
                                                    "marque-ancienne.txt")),
                        "l'ancienne installation doit etre renommee, pas effacee")

    def test_l_executable_reste_executable(self):
        """`extractall` rend tout en lecture seule -- l'application ne demarrerait plus."""
        updater.installer(self.archive())
        self.assertTrue(os.access(os.path.join(self.cible, NOM), os.X_OK))

    def test_un_binaire_sans_droits_dans_l_archive_en_recoit(self):
        """Ceinture et bretelles : archive faite sous Windows, modes absents."""
        updater.installer(self.archive(mode_binaire=0o644))
        self.assertTrue(os.access(os.path.join(self.cible, NOM), os.X_OK))

    def test_les_liens_symboliques_restent_des_liens(self):
        reussi, message = updater.installer(self.archive(liens=True))
        self.assertTrue(reussi, message)
        lien = os.path.join(self.cible, "libQt6Core.so.6")
        self.assertTrue(os.path.islink(lien),
                        "un lien extrait comme fichier, c'est « file too short »")
        self.assertEqual("libQt6Core.so.6.11.2", os.readlink(lien))

    def test_le_lanceur_du_chef_passe_dans_la_neuve(self):
        """L'archive publique ne le contient pas : sans report, il disparait."""
        lanceur = os.path.join(self.cible, "ZyRoom-Qt-dev.sh")
        self.ecrire(lanceur, "#!/bin/sh\n", 0o755)
        updater.installer(self.archive())
        passe = os.path.join(self.cible, "ZyRoom-Qt-dev.sh")
        self.assertTrue(os.path.isfile(passe))
        self.assertTrue(os.access(passe, os.X_OK))

    def test_une_mise_de_cote_qui_trainait_n_empeche_pas_le_renommage(self):
        os.makedirs(self.cible + updater.SUFFIXE_ANCIEN)
        reussi, message = updater.installer(self.archive())
        self.assertTrue(reussi, message)

    # ---------------------------------------------------- Les trois echecs

    def test_archive_illisible(self):
        chemin = os.path.join(self.tmp, "pas-un-zip.zip")
        self.ecrire(chemin, "ceci n'est pas une archive")
        reussi, message = updater.installer(chemin)
        self.assertFalse(reussi)
        self.assertIn("Archive illisible", message)
        self.installation_intacte()

    def test_archive_etrangere(self):
        """Un ZIP valide, mais qui ne porte pas notre application."""
        reussi, message = updater.installer(
            self.archive(nom="etrangere.zip", avec_binaire=False))
        self.assertFalse(reussi)
        self.assertIn("ne contient pas l'application attendue", message)
        self.installation_intacte()

    def test_aucune_installation_a_remplacer(self):
        with mock.patch.object(updater, "dossier_installe", lambda: ""):
            reussi, message = updater.installer(self.archive())
        self.assertFalse(reussi)
        self.assertIn("Aucune installation", message)
        self.installation_intacte()

    def test_l_echec_du_deplacement_remet_l_ancienne_en_place(self):
        """A aucun moment l'application ne doit manquer."""
        def refuse(*_a, **_k):
            raise OSError("disque plein")
        with mock.patch.object(updater.shutil, "move", refuse):
            reussi, message = updater.installer(self.archive())
        self.assertFalse(reussi)
        self.assertIn("Installation impossible", message)
        self.installation_intacte()
        self.assertFalse(os.path.isdir(self.cible + updater.SUFFIXE_ANCIEN))

    def installation_intacte(self):
        self.assertTrue(os.path.isfile(os.path.join(self.cible,
                                                    "marque-ancienne.txt")),
                        "l'installation d'origine doit rester entiere")
        self.assertTrue(os.access(self.binaire, os.X_OK))


class Menage(unittest.TestCase):
    """Ce que le demarrage efface, et ce qu'il ne doit jamais effacer."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="essai-menage-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cible = os.path.join(self.tmp, NOM)
        self.ancienne = self.cible + updater.SUFFIXE_ANCIEN
        os.makedirs(self.cible)
        os.makedirs(self.ancienne)

    def test_l_ancienne_installation_est_effacee(self):
        with mock.patch.object(updater, "dossier_installe", lambda: self.cible):
            updater.nettoyer_ancienne()
        self.assertFalse(os.path.isdir(self.ancienne))

    def test_jamais_le_dossier_d_ou_l_on_tourne(self):
        """Sinon l'application s'efface sous ses propres pieds."""
        with mock.patch.object(updater, "dossier_installe",
                               lambda: self.ancienne):
            updater.nettoyer_ancienne()
        self.assertTrue(os.path.isdir(self.ancienne))

    def test_maj_en_attente_voit_le_depot_windows(self):
        attente = self.cible + updater.SUFFIXE_NOUVEAU
        with mock.patch.object(updater, "dossier_installe", lambda: self.cible):
            self.assertFalse(updater.maj_en_attente())
            os.makedirs(attente)
            self.assertTrue(updater.maj_en_attente())

    def test_hors_de_chez_soi_reconnait_le_dossier_depose_a_cote(self):
        attente = self.cible + updater.SUFFIXE_NOUVEAU
        with mock.patch.object(updater, "dossier_installe", lambda: self.cible):
            self.assertFalse(updater.hors_de_chez_soi())
        with mock.patch.object(updater, "dossier_installe", lambda: attente):
            self.assertTrue(updater.hors_de_chez_soi())


if __name__ == "__main__":
    unittest.main()
