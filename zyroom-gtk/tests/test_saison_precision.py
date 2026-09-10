"""Le compte à rebours de saison, à la minute et à la date.

Ce que ces essais gardent, et pourquoi. Le compte se faisait en heures d'Atys
entières : il ignorait l'heure en cours, et annonçait donc le changement
jusqu'à trois minutes trop tôt — toujours dans le même sens. Affiché, il ne
disait que « dans 83 h », sans la minute ni le jour, alors qu'une saison peut
changer quatre jours et demi plus tard. Les joueurs de la guilde ont demandé
les deux.

Le battement du serveur donne la précision manquante : mille huit cents
battements par heure d'Atys, vérifiés sur le flux — `server_tick // 1800 % 24`
redonne le `time_of_day` du même document.
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import meteo, ryzom_api                              # noqa: E402


def flux(tick=None, jour=20, heure=11, saison=3) -> bytes:
    """Un time.php réduit à ce que `parse_time` y lit."""
    battement = f"<server_tick>{tick}</server_tick>" if tick is not None else ""
    return (f'<?xml version="1.0"?><shard_time>{battement}'
            f"<season>{saison}</season>"
            f"<day_of_season>{jour}</day_of_season>"
            f"<time_of_day>{heure}</time_of_day></shard_time>").encode()


class CompteARebours(unittest.TestCase):

    def test_le_battement_ajoute_la_fin_de_l_heure_en_cours(self):
        # Un battement au tout debut de l'heure : il reste presque l'heure
        # entiere, soit trois minutes reelles de plus que l'ancien compte.
        debut = ryzom_api.parse_time(flux(tick=1800 * 4))["minutes_to_next"]
        # Et un a la toute fin : il ne reste presque rien a ajouter.
        fin = ryzom_api.parse_time(
            flux(tick=1800 * 4 + 1799))["minutes_to_next"]
        self.assertAlmostEqual(3.0, debut - fin, places=1)
        self.assertGreater(debut, fin)

    def test_sans_battement_on_retombe_sur_l_ancien_compte(self):
        # Un flux tronque ne doit pas inventer une demi-heure : l'affichage
        # oscillerait a chaque relecture.
        sans = ryzom_api.parse_time(flux(tick=None))["minutes_to_next"]
        self.assertEqual(((89 - 20) * 24 + (23 - 11)) * 3, sans)

    def test_le_battement_redonne_l_heure_du_meme_flux(self):
        # La relation qui fonde la constante. Si elle cesse d'etre vraie,
        # c'est que l'API a change de cadence, et tout le reste est faux.
        for heure in (0, 7, 11, 23):
            tick = ryzom_api.TICKS_PAR_HEURE_ATYS * (24 * 400 + heure) + 900
            with self.subTest(heure=heure):
                self.assertEqual(
                    heure, tick // ryzom_api.TICKS_PAR_HEURE_ATYS % 24)


class QuandCelaTombe(unittest.TestCase):

    def test_dans_la_journee_le_jour_ne_se_dit_pas(self):
        midi = datetime(2026, 9, 10, 12, 0)
        self.assertEqual("aujourd'hui à 14:30",
                         meteo.moment_du_changement(150, midi))

    def test_le_lendemain_se_dit_demain(self):
        soir = datetime(2026, 9, 10, 23, 50)
        self.assertEqual("demain à 00:10",
                         meteo.moment_du_changement(20, soir))

    def test_au_dela_c_est_une_date(self):
        midi = datetime(2026, 9, 10, 12, 0)
        # Une saison entiere : quatre jours et demi reels.
        self.assertEqual("le 13/09 à 23:22",
                         meteo.moment_du_changement(5002, midi))


class Duree(unittest.TestCase):

    def test_l_unite_leve_le_doute_des_grandes_attentes(self):
        # « 83 h 23 » se lit comme une heure de la journee ; « 83 h 23 min »
        # non. La forme courte reste celle de l'ecran meteo.
        self.assertEqual("83 h 23", meteo.duree(5003))
        self.assertEqual("83 h 23 min", meteo.duree(5003, unite=True))

    def test_sous_l_heure_rien_ne_change(self):
        self.assertEqual("27 min", meteo.duree(27))
        self.assertEqual("27 min", meteo.duree(27, unite=True))


if __name__ == "__main__":
    unittest.main()
