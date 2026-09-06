"""La barre d'attente : son curseur doit courir dans un seul sens.

`Gtk.ProgressBar.pulse()` fait **rebondir** son curseur : arrivé au bord, il
repart vers la gauche. Un défilement à sens unique demande donc de le renvoyer
au départ avant qu'il ne se retourne, et le seuil de ce retour se déduit du
pas — il ne s'écrit pas à la main. Posé à huit alors que le bord s'atteint en
5,7 pulsations, il laissait le curseur rebondir puis revenir sur deux
pulsations : un demi-tour de deux dixièmes de seconde, qui se voyait comme un
arrêt.
"""
import unittest


def pas_avant_le_bord(pulse_step: float) -> int:
    """La règle du module, éprouvée à d'autres pas que celui du programme.

    `zyroom.attente.pas_avant_le_bord` ne prend pas d'argument — elle lit la
    constante `PAS` —, alors qu'on veut la vérifier sur toute une plage. On
    rejoue donc le calcul, et un dernier test confronte les deux pour que la
    copie ne puisse pas dériver de l'original.
    """
    return max(1, int((1.0 - pulse_step) / pulse_step))


class BarreAttente(unittest.TestCase):

    def test_le_retour_precede_le_rebond(self):
        """À chaque pas, le curseur doit repartir avant d'avoir touché le bord."""
        for pas in (0.05, 0.1, 0.15, 0.2, 0.25, 0.5):
            seuil = pas_avant_le_bord(pas)
            # Là où en est le curseur au moment du retour : il occupe `pas` de
            # la barre, il lui reste donc `1 - pas` à parcourir.
            position = seuil * pas
            self.assertLessEqual(
                position, 1.0 - pas + 1e-9,
                f"à {pas}, le curseur a déjà rebondi quand on le renvoie")

    def test_le_seuil_ne_gaspille_pas_la_course(self):
        """Il repart d'aussi près du bord que possible, sans le toucher."""
        for pas in (0.1, 0.15, 0.2, 0.25):
            seuil = pas_avant_le_bord(pas)
            # Une pulsation de plus dépasserait : le seuil est donc le bon.
            self.assertGreater((seuil + 1) * pas, 1.0 - pas + 1e-9,
                               f"à {pas}, le curseur repart trop tôt")

    def test_un_pas_grossier_garde_au_moins_une_pulsation(self):
        """Même à 0,9, la barre doit bouger d'un cran avant de revenir."""
        self.assertGreaterEqual(pas_avant_le_bord(0.9), 1)

    def test_la_valeur_du_programme(self):
        """Le pas retenu, 0,15, donne cinq battements — et non huit."""
        self.assertEqual(pas_avant_le_bord(0.15), 5)

    def test_le_module_dit_la_meme_chose(self):
        """La règle recopiée ici et celle du programme ne doivent pas diverger."""
        import os
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from zyroom import attente

        self.assertEqual(attente.pas_avant_le_bord(),
                         pas_avant_le_bord(attente.PAS))

    def test_les_deux_portages_ont_les_memes_nombres(self):
        """La barre de Qt est le jumeau de celle-ci : mêmes pas, même cadence.

        Les deux fichiers sont écrits à la main, chacun dans son toolkit ; rien
        n'empêcherait l'un de dériver, sinon ce test.
        """
        import os
        import re

        ici = os.path.dirname(os.path.abspath(__file__))
        jumeau = os.path.join(os.path.dirname(os.path.dirname(ici)),
                              "zyroom-qt", "zyroom", "attente.py")
        if not os.path.isfile(jumeau):
            self.skipTest("le portage Qt n'est pas à côté")
        source = open(jumeau, encoding="utf-8").read()
        from zyroom import attente

        for nom, valeur in (("PAS", attente.PAS), ("CADENCE", attente.CADENCE),
                            ("RAYON", attente.RAYON)):
            trouve = re.search(rf"^{nom} = ([\d.]+)", source, re.M)
            self.assertIsNotNone(trouve, f"{nom} absent du portage Qt")
            self.assertEqual(float(trouve.group(1)), float(valeur),
                             f"{nom} diffère entre les deux portages")


if __name__ == "__main__":
    unittest.main()
