"""La veille des mises à jour, sans passer par le portail.

Rien ici ne touche au réseau : ce qui est vérifié, c'est la décision — quand
proposer une mise à jour, et surtout quand se taire.
"""

import unittest

from zyroom import updater


COMMIT_A = "095a4e25428bb5fd06187cc0585f0cbc0069dbb239165a153524ce82e06d355d"
COMMIT_B = "40af7ba6ec31312448682b523a17f3689d0c8db548dee21e93263a42f222cd8f"


class Veille(unittest.TestCase):

    def veilleur(self, publie, installe=COMMIT_A):
        v = updater.Veilleur()
        v.application = "net.ryzom.zyroomgtk.dev"
        v.commit_installe = installe
        v.commit_publie = lambda timeout=15: publie
        return v

    def test_rien_a_proposer_quand_on_execute_ce_qui_est_publie(self):
        self.assertEqual("", self.veilleur(COMMIT_A).mise_a_jour_disponible())

    def test_une_empreinte_differente_est_une_mise_a_jour(self):
        self.assertEqual(COMMIT_B, self.veilleur(COMMIT_B).mise_a_jour_disponible())

    def test_un_depot_muet_ne_propose_rien(self):
        """Coupure réseau, page absente : on s'en tient à ce qu'on a."""
        self.assertEqual("", self.veilleur("").mise_a_jour_disponible())

    def test_hors_bac_a_sable_la_veille_ne_s_arme_pas(self):
        v = updater.Veilleur()
        v.application, v.commit_installe = "", ""
        self.assertFalse(v.possible)
        self.assertEqual("", v.mise_a_jour_disponible())

    def test_l_adresse_vise_la_reference_de_l_application(self):
        self.assertEqual(
            "https://xiom-dev.github.io/zyroom-gtk-android/repo/"
            "refs/heads/app/net.ryzom.zyroomgtk.dev/x86_64/master",
            self.veilleur(COMMIT_A).url)


class LectureDeLaReference(unittest.TestCase):
    """Le dépôt doit rendre une empreinte, pas une page d'erreur.

    GitHub Pages répond volontiers du HTML à une adresse absente : le prendre
    pour un commit ferait clignoter un bouton de mise à jour perpétuel.
    """

    def lecture(self, charge: bytes) -> str:
        import contextlib, io
        v = updater.Veilleur()

        @contextlib.contextmanager
        def faux_urlopen(url, timeout=15):
            yield io.BytesIO(charge)

        origine = updater.urllib.request.urlopen
        updater.urllib.request.urlopen = faux_urlopen
        try:
            return v.commit_publie()
        finally:
            updater.urllib.request.urlopen = origine

    def test_une_empreinte_est_retenue(self):
        self.assertEqual(COMMIT_A, self.lecture((COMMIT_A + "\n").encode()))

    def test_une_page_html_est_rejetee(self):
        self.assertEqual("", self.lecture(b"<!DOCTYPE html><h1>404</h1>"))

    def test_une_empreinte_tronquee_est_rejetee(self):
        self.assertEqual("", self.lecture(b"095a4e25\n"))


class IdentiteFlatpak(unittest.TestCase):
    """Ce que le bac à sable dit de l'application qui tourne.

    Extrait d'un vrai `/.flatpak-info`, celui de la variante dev installée : les
    noms de groupes et de clés viennent de Flatpak, pas de nous.
    """

    INFO = """[Application]
name=net.ryzom.zyroomgtk.dev
runtime=runtime/org.gnome.Platform/x86_64/50

[Instance]
instance-id=3675886960
app-commit=095a4e25428bb5fd06187cc0585f0cbc0069dbb239165a153524ce82e06d355d
branch=master
"""

    def lecture(self, contenu):
        import tempfile, os
        fd, chemin = tempfile.mkstemp()
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        origine = updater._INFO_FLATPAK
        updater._INFO_FLATPAK = chemin
        try:
            return updater._identite_flatpak()
        finally:
            updater._INFO_FLATPAK = origine
            os.unlink(chemin)

    def test_l_application_et_son_empreinte_sont_lues(self):
        self.assertEqual(("net.ryzom.zyroomgtk.dev", COMMIT_A),
                         self.lecture(self.INFO))

    def test_un_fichier_absent_ne_fait_rien_tomber(self):
        origine = updater._INFO_FLATPAK
        updater._INFO_FLATPAK = "/nulle/part/.flatpak-info"
        try:
            self.assertEqual(("", ""), updater._identite_flatpak())
        finally:
            updater._INFO_FLATPAK = origine

    def test_un_fichier_incomplet_ne_fait_rien_tomber(self):
        self.assertEqual(("", ""), self.lecture("[Application]\nname=x\n"))


if __name__ == "__main__":
    unittest.main()
