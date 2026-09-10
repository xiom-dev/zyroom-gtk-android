#!/usr/bin/env python3
"""Les noms de dossier de la mise a jour ne s'empilent pas.

Un joueur s'est retrouve avec `ZyRoom-Qt`, `ZyRoom-Qt.nouveau` et
`ZyRoom-Qt.nouveau.nouveau` : la mise en place n'avait pas eu lieu, il avait
lance l'application depuis le dossier depose a cote, et la mise a jour
suivante avait colle un second suffixe au premier.

Ces controles tournent sur n'importe quel systeme : ils ne portent que sur le
calcul des noms, qui est justement ce qui avait lache.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import updater  # noqa: E402


class Suffixes(unittest.TestCase):
    """Le dossier de base se retrouve quel que soit l'empilement."""

    def test_sans_suffixe(self):
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt"),
                         "/o/ZyRoom-Qt")

    def test_un_suffixe(self):
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt.nouveau"),
                         "/o/ZyRoom-Qt")

    def test_suffixes_empiles(self):
        self.assertEqual(
            updater.dossier_canonique("/o/ZyRoom-Qt.nouveau.nouveau"),
            "/o/ZyRoom-Qt")

    def test_melange(self):
        self.assertEqual(
            updater.dossier_canonique("/o/ZyRoom-Qt.ancien.nouveau"),
            "/o/ZyRoom-Qt")

    def test_un_point_qui_n_est_pas_a_nous(self):
        """Un dossier nomme autrement garde son nom."""
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt.1.11"),
                         "/o/ZyRoom-Qt.1.11")


class ChezSoi(unittest.TestCase):
    """On sait dire qu'on tourne depuis un dossier depose a cote."""

    def _poser(self, dossier):
        updater.dossier_installe = lambda: dossier

    def setUp(self):
        self._vrai = updater.dossier_installe
        self.addCleanup(lambda: setattr(updater, "dossier_installe",
                                        self._vrai))

    def test_chez_soi(self):
        self._poser("/o/ZyRoom-Qt")
        self.assertFalse(updater.hors_de_chez_soi())

    def test_ailleurs(self):
        self._poser("/o/ZyRoom-Qt.nouveau")
        self.assertTrue(updater.hors_de_chez_soi())

    def test_hors_paquet(self):
        """Depuis les sources, il n'y a pas d'installation : rien a dire."""
        self._poser("")
        self.assertFalse(updater.hors_de_chez_soi())


if __name__ == "__main__":
    unittest.main()


class InstallationUnix(unittest.TestCase):
    """Une vraie installation, mise a jour cinq fois de suite.

    Le defaut de Windows -- un dossier de plus a chaque mise a jour -- n'existe
    pas ici : Unix laisse renommer le dossier d'ou l'on tourne, la permutation
    se fait tout de suite, et rien ne s'accumule. Ce controle le verifie plutot
    que de le supposer.
    """

    NOM = "ZyRoom-Qt"

    def setUp(self):
        import shutil
        import tempfile
        self.bac = tempfile.mkdtemp(prefix="essai-maj-")
        self.addCleanup(shutil.rmtree, self.bac, ignore_errors=True)
        self.maison = os.path.join(self.bac, self.NOM)
        self._vrai_frozen = getattr(sys, "frozen", None)
        self._vrai_exe = sys.executable
        self.addCleanup(self._rendre_sys)

    def _rendre_sys(self):
        sys.executable = self._vrai_exe
        if self._vrai_frozen is None:
            if hasattr(sys, "frozen"):
                del sys.frozen
        else:
            sys.frozen = self._vrai_frozen

    def _poser(self, dossier, version):
        os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, self.NOM)
        with open(chemin, "w") as f:
            f.write(f"version {version}\n")
        os.chmod(chemin, 0o755)

    def _archive(self, version):
        import shutil
        import tempfile
        import zipfile
        lieu = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, lieu, ignore_errors=True)
        dedans = os.path.join(lieu, self.NOM)
        self._poser(dedans, version)
        archive = os.path.join(self.bac, f"maj-{version}.zip")
        with zipfile.ZipFile(archive, "w") as z:
            z.write(os.path.join(dedans, self.NOM), f"{self.NOM}/{self.NOM}")
        return archive

    def _dossiers(self):
        return sorted(d for d in os.listdir(self.bac)
                      if os.path.isdir(os.path.join(self.bac, d)))

    def test_rien_ne_s_accumule(self):
        self._poser(self.maison, "1.0")
        sys.frozen = True
        sys.executable = os.path.join(self.maison, self.NOM)
        for n in range(1, 6):
            reussi, message = updater.installer(self._archive(f"1.{n}"))
            self.assertTrue(reussi, message)
            updater.nettoyer_ancienne()
            self.assertEqual(self._dossiers(), [self.NOM],
                             f"un dossier de trop apres la maj {n}")
        with open(os.path.join(self.maison, self.NOM)) as f:
            self.assertEqual(f.read().strip(), "version 1.5")

    def test_on_ne_s_efface_pas_sous_les_pieds(self):
        """Lancee depuis la mise de cote, l'application survit au menage."""
        self._poser(self.maison, "1.0")
        ancienne = self.maison + updater.SUFFIXE_ANCIEN
        self._poser(ancienne, "0.9")
        sys.frozen = True
        sys.executable = os.path.join(ancienne, self.NOM)
        updater.nettoyer_ancienne()
        self.assertTrue(os.path.isdir(ancienne),
                        "le menage a efface le dossier d'ou l'on tourne")


class RelaisWindows(unittest.TestCase):
    """Le script de permutation, tel qu'il est ecrit sur le disque.

    Il ne peut pas s'executer ici -- `cmd` n'existe pas sous Linux --, mais
    son texte, lui, se relit. Ce sont ses gardes qu'on verifie : elles ont ete
    ajoutees apres coup, et rien n'empechait qu'une reecriture les emporte.
    """

    NOM = "ZyRoom-Qt"
    RELANCER = True

    def setUp(self):
        import shutil
        import tempfile
        self.bac = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.bac, ignore_errors=True)
        self.maison = os.path.join(self.bac, self.NOM)
        os.makedirs(self.maison + updater.SUFFIXE_NOUVEAU, exist_ok=True)
        self._vrai_exe = sys.executable
        self._vrai_frozen = getattr(sys, "frozen", None)
        sys.frozen = True
        # On tourne depuis le dossier depose a cote : le cas du joueur.
        sys.executable = os.path.join(self.maison + updater.SUFFIXE_NOUVEAU,
                                      self.NOM)
        self.addCleanup(self._rendre)
        # `cmd` n'existe pas ici : l'appel echoue, mais le script est ecrit
        # avant, et c'est lui qu'on vient lire.
        updater._relais_windows(relancer_apres=self.RELANCER)
        import tempfile as _t
        self.script = os.path.join(_t.gettempdir(), "zyroom-qt-maj.bat")
        self.addCleanup(lambda: os.path.exists(self.script)
                        and os.unlink(self.script))

    def _rendre(self):
        sys.executable = self._vrai_exe
        if self._vrai_frozen is None:
            if hasattr(sys, "frozen"):
                del sys.frozen
        else:
            sys.frozen = self._vrai_frozen

    def _texte(self):
        with open(self.script, encoding="ascii") as f:
            return f.read()

    def test_le_script_est_en_ascii_pur(self):
        # Un prenom accentue dans le chemin faisait lever UnicodeEncodeError,
        # et le bouton ne relancait rien : les chemins passent par
        # l'environnement, jamais par le texte du script.
        self._texte()          # leve si un octet n'est pas de l'ASCII
        self.assertNotIn(self.bac, self._texte())

    def test_la_cible_absente_ne_bloque_pas_la_permutation(self):
        # Un joueur qui decouvre trois dossiers presque identiques en
        # supprime, et parfois le bon. Sans cette garde, le `move` echouait
        # et l'on partait a l'echec alors qu'il n'y avait qu'a poser.
        self.assertIn('if not exist "%ZY_CIBLE%" goto :poser', self._texte())

    def test_l_echec_relance_ce_qui_existe(self):
        # L'executable de destination n'existe que si la cible existe. Sans
        # recours, le relais lancait un chemin vide : plus d'application du
        # tout.
        texte = self._texte()
        self.assertIn("%ZY_SECOURS%", texte)
        self.assertIn('if exist "%ZY_EXE%"', texte)

    def test_les_dossiers_suffixes_sont_balayes(self):
        # Sans ce menage, un `.nouveau` oublie serait repris pour une mise a
        # jour en attente au lancement suivant, et remettrait en place une
        # version plus ancienne.
        self.assertIn('for /d %%d in ("%ZY_CIBLE%.nouveau*")', self._texte())


class RelaisSilencieux(RelaisWindows):
    """Le meme relais, quand l'application se ferme pour de bon.

    Il permute et s'arrete la : rouvrir une fenetre sous les doigts de
    quelqu'un qui vient de cliquer sur la croix serait pris pour une panne.
    """

    RELANCER = False

    def test_rien_ne_se_relance(self):
        texte = self._texte()
        self.assertIn('if not "%ZY_RELANCER%"=="1" goto :fin', texte)

    def test_la_permutation_a_quand_meme_lieu(self):
        # C'est tout l'interet : le remplacement se fait, seul le demarrage
        # est omis.
        texte = self._texte()
        self.assertIn('move "%ZY_ATTENTE%" "%ZY_CIBLE%"', texte)


class PoserEnPartant(unittest.TestCase):
    """`poser_a_la_fermeture` ne se declenche que la ou elle a un sens."""

    def test_hors_paquet_il_n_y_a_rien_a_poser(self):
        vrai = getattr(sys, "frozen", None)
        if hasattr(sys, "frozen"):
            del sys.frozen
        try:
            self.assertFalse(updater.poser_a_la_fermeture())
        finally:
            if vrai is not None:
                sys.frozen = vrai

    def test_sous_unix_la_permutation_s_est_deja_faite(self):
        # Pas de relais ici : `installer` a permute sur-le-champ. Appeler
        # ceci en partant ne doit rien tenter.
        if os.name == "nt":
            self.skipTest("essai propre aux systemes sans relais")
        self.assertFalse(updater.poser_a_la_fermeture())
