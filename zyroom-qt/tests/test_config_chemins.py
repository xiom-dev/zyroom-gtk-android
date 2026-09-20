#!/usr/bin/env python3
"""Ou ce portage range ses fichiers, et ce qu'il reprend de ZyRoom-GTK.

`config.py` est le module le plus propre au portage, avec `updater.py` : il
sait deux systemes, et personne ne peut regarder les deux a la fois. Sous
Linux il suit XDG ; sous Windows, la configuration va dans l'itinerant --
%APPDATA%, qui suit l'utilisateur d'une machine a l'autre -- et le cache dans
le local, qu'on ne recopie pas sur le reseau.

Windows se simule ici : le drapeau `WINDOWS` et les deux variables
d'environnement suffisent a emprunter ce chemin-la, et c'est justement la
partie qu'aucune machine du mainteneur n'execute jamais.

La reprise de ZyRoom-GTK est l'autre morceau : les cles d'API se saisissent a
la main, une par entite, et ressaisir la meme chose pour retrouver les memes
inventaires serait une brimade. Ces essais tiennent la promesse -- une copie,
une seule fois, et jamais par-dessus ce qu'on a deja.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import config  # noqa: E402


class Chemins(unittest.TestCase):
    """Les trois dossiers, d'un systeme a l'autre."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="essai-config-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # Un foyer a nous : sans quoi les essais liraient -- et creeraient --
        # les dossiers reels de celui qui les lance.
        self.foyer = os.path.join(self.tmp, "foyer")
        os.makedirs(self.foyer)
        self.env = mock.patch.dict(os.environ, {"HOME": self.foyer}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        for variable in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
                         "APPDATA", "LOCALAPPDATA"):
            os.environ.pop(variable, None)
        # La reprise ne regarde le disque qu'une fois par execution : chaque
        # essai doit donc repartir d'une ardoise propre.
        config._reprise_faite = False
        config._dossiers_repris.clear()
        self.addCleanup(setattr, config, "_reprise_faite", False)
        self.addCleanup(config._dossiers_repris.clear)

    # ------------------------------------------------------------ Linux

    def test_linux_suit_xdg_quand_il_est_pose(self):
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp, "ailleurs")
        with mock.patch.object(config, "WINDOWS", False):
            self.assertEqual(os.path.join(self.tmp, "ailleurs", "zyroom-qt"),
                             config.config_dir())

    def test_linux_sans_xdg_prend_le_chemin_conventionnel(self):
        with mock.patch.object(config, "WINDOWS", False):
            self.assertEqual(os.path.join(self.foyer, ".config", "zyroom-qt"),
                             config.config_dir())
            self.assertEqual(os.path.join(self.foyer, ".cache", "zyroom-qt"),
                             config.cache_dir())
            self.assertEqual(
                os.path.join(self.foyer, ".local", "share", "zyroom-qt"),
                config.data_dir())

    def test_le_dossier_est_cree(self):
        with mock.patch.object(config, "WINDOWS", False):
            self.assertTrue(os.path.isdir(config.config_dir()))

    # ---------------------------------------------------------- Windows

    def test_windows_range_la_configuration_dans_l_itinerant(self):
        roaming = os.path.join(self.tmp, "Roaming")
        local = os.path.join(self.tmp, "Local")
        os.environ.update({"APPDATA": roaming, "LOCALAPPDATA": local})
        with mock.patch.object(config, "WINDOWS", True):
            self.assertEqual(os.path.join(roaming, "zyroom-qt"),
                             config.config_dir())

    def test_windows_range_le_cache_dans_le_local(self):
        """Un cache d'icones n'a rien a faire sur le reseau d'un domaine."""
        roaming = os.path.join(self.tmp, "Roaming")
        local = os.path.join(self.tmp, "Local")
        os.environ.update({"APPDATA": roaming, "LOCALAPPDATA": local})
        with mock.patch.object(config, "WINDOWS", True):
            self.assertEqual(os.path.join(local, "zyroom-qt", "cache"),
                             config.cache_dir())
            self.assertEqual(os.path.join(local, "zyroom-qt"),
                             config.data_dir())

    def test_windows_sans_ses_variables_retombe_sous_le_profil(self):
        """Un environnement depouille ne doit pas faire echouer le demarrage."""
        with mock.patch.object(config, "WINDOWS", True):
            self.assertEqual(
                os.path.join(self.foyer, "AppData", "Roaming", "zyroom-qt"),
                config.config_dir())
            self.assertEqual(
                os.path.join(self.foyer, "AppData", "Local", "zyroom-qt",
                             "cache"),
                config.cache_dir())

    def test_xdg_ne_deborde_pas_sur_windows(self):
        """Une variable XDG trainant dans l'environnement ne doit rien changer."""
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp, "xdg")
        os.environ["APPDATA"] = os.path.join(self.tmp, "Roaming")
        with mock.patch.object(config, "WINDOWS", True):
            self.assertEqual(os.path.join(self.tmp, "Roaming", "zyroom-qt"),
                             config.config_dir())


class RepriseDuPortageGTK(unittest.TestCase):
    """Ce qu'on reprend de ZyRoom-GTK au tout premier lancement."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="essai-reprise-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.foyer = os.path.join(self.tmp, "foyer")
        self.gtk_config = os.path.join(self.foyer, ".config", "zyroom-gtk")
        self.gtk_data = os.path.join(self.foyer, ".local", "share", "zyroom-gtk")
        os.makedirs(self.gtk_config)
        os.makedirs(os.path.join(self.gtk_data, "movements"))
        self.ecrire(os.path.join(self.gtk_config, "characters.ini"),
                    "[123]\nKey = abcdef\n")
        self.ecrire(os.path.join(self.gtk_config, "guilds.ini"),
                    "[105906237]\nKey = 123456\n")
        self.ecrire(os.path.join(self.gtk_data, "movements", "guild-1.json"),
                    "[]")
        self.ecrire(os.path.join(self.gtk_data, "roster-105906237.json"), "{}")

        self.env = mock.patch.dict(os.environ, {"HOME": self.foyer}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        for variable in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"):
            os.environ.pop(variable, None)
        config._reprise_faite = False
        config._dossiers_repris.clear()
        self.addCleanup(setattr, config, "_reprise_faite", False)
        self.addCleanup(config._dossiers_repris.clear)
        self.linux = mock.patch.object(config, "WINDOWS", False)
        self.linux.start()
        self.addCleanup(self.linux.stop)

    @staticmethod
    def ecrire(chemin: str, contenu: str) -> None:
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as fichier:
            fichier.write(contenu)

    def test_les_cles_ne_se_ressaisissent_pas(self):
        dossier = config.config_dir()
        for nom in ("characters.ini", "guilds.ini"):
            self.assertTrue(os.path.isfile(os.path.join(dossier, nom)),
                            f"{nom} aurait du etre repris de ZyRoom-GTK")

    def test_c_est_une_copie_pas_un_partage(self):
        """Regler l'une ne doit pas deregler l'autre."""
        dossier = config.config_dir()
        repris = os.path.join(dossier, "guilds.ini")
        self.ecrire(repris, "[999]\nKey = autre\n")
        with open(os.path.join(self.gtk_config, "guilds.ini"),
                  encoding="utf-8") as fichier:
            self.assertIn("105906237", fichier.read())

    def test_un_dossier_deja_garni_fait_foi(self):
        """Des qu'on a quelque chose a soi, on ne reprend plus rien."""
        dossier = config._dossier("XDG_CONFIG_HOME", ".config", "roaming")
        self.ecrire(os.path.join(dossier, "settings.ini"), "[GENERAL]\n")
        config._reprise_faite = False
        config.config_dir()
        self.assertFalse(os.path.isfile(os.path.join(dossier, "guilds.ini")))

    def test_la_reprise_ne_se_fait_qu_une_fois(self):
        dossier = config.config_dir()
        os.unlink(os.path.join(dossier, "guilds.ini"))
        config.config_dir()          # deuxieme appel, dans la meme execution
        self.assertFalse(os.path.isfile(os.path.join(dossier, "guilds.ini")),
                         "la reprise ne doit pas revenir sur ce qu'on a retire")

    def test_l_historique_des_mouvements_est_repris(self):
        """La seule donnee que l'API ne sait pas reconstruire."""
        dossier = config.data_dir()
        self.assertTrue(os.path.isfile(
            os.path.join(dossier, "movements", "guild-1.json")))

    def test_le_registre_du_personnel_aussi(self):
        """Pose a plat, et non dans un sous-dossier : l'effectif repartait de zero."""
        dossier = config.data_dir()
        self.assertTrue(os.path.isfile(
            os.path.join(dossier, "roster-105906237.json")))

    def test_le_bac_a_sable_flatpak_est_regarde_aussi(self):
        """La variante du mainteneur ecrit dans ~/.var/app, pas sous ~/.local."""
        shutil.rmtree(self.gtk_data)
        bac = os.path.join(self.foyer, ".var", "app", "net.ryzom.zyroomgtk.dev",
                           "data", "zyroom-gtk")
        self.ecrire(os.path.join(bac, "movements", "guild-2.json"), "[]")
        config._dossiers_repris.clear()
        dossier = config.data_dir()
        self.assertTrue(os.path.isfile(
            os.path.join(dossier, "movements", "guild-2.json")),
            "un registre de sept mouvements repris quand celui qui compte en a"
            " cinquante, c'est deja arrive")

    def test_sous_windows_on_ne_reprend_rien(self):
        """Le portage GTK n'y tourne pas : il n'y a rien a reprendre."""
        config._reprise_faite = False
        with mock.patch.object(config, "WINDOWS", True):
            os.environ["APPDATA"] = os.path.join(self.tmp, "Roaming")
            dossier = config.config_dir()
        self.assertFalse(os.path.isfile(os.path.join(dossier, "guilds.ini")))


if __name__ == "__main__":
    unittest.main()
