"""Le journal : les libellés de coffres, et la coupure entre deux journées.

Les coffres de guilde portent, après leur nom, ce que la guilde y range — et
l'API tronque le tout à une quarantaine de signes, si bien que la parenthèse ne
se referme presque jamais. « Coffre 15 — La Lune Des Maraudeurs(Gh Armure » est
le libellé réel, pas un exemple inventé : il vient du journal de Ludo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import movements                                      # noqa: E402
from zyroom.window import MainWindow                              # noqa: E402


class LibelleDeCoffre(unittest.TestCase):

    #: Relevés tels quels dans le journal de la guilde.
    RELEVES = (
        ("Coffre 15 — La Lune Des Maraudeurs(Gh Armure",
         "Coffre 15 — La Lune Des Maraudeurs"),
        ("Coffre 2 — La Resserre Lunaire 1/2 (Equipem",
         "Coffre 2 — La Resserre Lunaire 1/2"),
        ("Coffre 7 — La Forge Lunaire (Craft Armes 3/",
         "Coffre 7 — La Forge Lunaire"),
        ("Coffre 9 — La Lune d'Ambre(Craft Bijoux/Amp",
         "Coffre 9 — La Lune d'Ambre"),
    )

    def test_le_parenthetique_disparait(self):
        for brut, attendu in self.RELEVES:
            self.assertEqual(attendu, MainWindow._sans_parenthese(brut))

    def test_ce_qui_n_en_a_pas_ne_bouge_pas(self):
        for intact in ("Sac", "Coffre 1", "Appartement", "Zig 3",
                       "Coffre 4 — Gh Mps Utile pour les Coffres"):
            self.assertEqual(intact, MainWindow._sans_parenthese(intact))

    def test_l_alerte_de_volume_coupe_comme_le_journal(self):
        """La cloche nommait le coffre en entier, phrase pendante comprise.

        Le journal coupait depuis toujours, l'alerte non : elle est calculée
        dans `alerts.py`, qui ne connaît pas d'interface et ne pouvait donc
        pas appeler la recette rangée dans la fenêtre. Celle-ci vit désormais
        dans `movements`, et les deux s'en servent.
        """
        from zyroom import alerts

        class Contenant:
            label = "Coffre 15 — La Lune Des Maraudeurs(Gh Armure"
            capacity = 5000
            total_volume = 4800.0

        class Entite:
            inventories = [Contenant()]

        sorties = alerts.volume_alerts(Entite(), 90)
        self.assertEqual(1, len(sorties))
        self.assertEqual("Coffre 15 — La Lune Des Maraudeurs : 96% plein",
                         sorties[0].title)

    def test_le_menu_des_coffres_coupe_aussi(self):
        """Le sélecteur nommait le coffre en entier, phrase pendante comprise.

        Le journal coupait, les alertes coupaient, le menu non — et c'est
        pourtant lui qu'on regarde le plus souvent.
        """
        from zyroom.window import MainWindow
        from zyroom import movements

        class Contenant:
            label = "Coffre 15 — La Lune Des Maraudeurs(Gh Armure"
            capacity = 5000
            total_volume = 4800.0

        ligne = (movements.sans_parenthese(Contenant.label)
                 + MainWindow._remplissage(Contenant))
        self.assertEqual("Coffre 15 — La Lune Des Maraudeurs (96%)", ligne)

    def test_un_libelle_entierement_parenthese_est_gardé(self):
        """Mieux vaut un libellé étrange que pas de libellé du tout.

        Si la troncature laissait une parenthèse en tête, couper rendrait une
        chaîne vide et la colonne serait muette : on garde alors l'original."""
        self.assertEqual("(Gh Armure", MainWindow._sans_parenthese("(Gh Armure"))
        self.assertEqual("", MainWindow._sans_parenthese(""))




class MemoireDuJournal(unittest.TestCase):
    """Combien de lignes le journal montre, et sur quelle profondeur.

    Le cas réel : la guilde de Ludo produit huit cents mouvements en deux
    jours. La grille s'arrêtait à quatre cents lignes, soit moins d'une
    journée — l'avant-veille était invisible alors qu'elle était sur le disque.
    """

    MAINTENANT = 1_800_000_000.0
    JOUR = 86400

    def _journal(self, nombre, ecart):
        """`nombre` mouvements espacés de `ecart` secondes, du plus récent."""
        return [movements.Movement(ts=self.MAINTENANT - rang * ecart)
                for rang in range(nombre)]

    def test_une_guilde_active_montre_bien_sept_jours(self):
        """Deux cents mouvements par jour : la semaine en fait quatorze cents.

        Quatorze cent **un** : celui qui tombe pile sur la frontière est gardé.
        La borne est inclusive, et mieux vaut une ligne de trop qu'un mouvement
        qui disparaît en franchissant la seconde."""
        journal = self._journal(3000, self.JOUR // 200)
        montrees = movements.lignes_recentes(journal, 7, 400, 3000,
                                             maintenant=self.MAINTENANT)
        self.assertEqual(7 * 200 + 1, montrees)

    def test_un_coffre_calme_garde_le_minimum(self):
        """Une semaine sans rien ne doit pas donner une page vide."""
        journal = self._journal(600, 3 * self.JOUR)     # un mouvement tous les 3 jours
        montrees = movements.lignes_recentes(journal, 7, 400, 3000,
                                             maintenant=self.MAINTENANT)
        self.assertEqual(400, montrees)

    def test_le_plafond_protege_un_journal_laisse_courir(self):
        journal = self._journal(9000, 60)               # un mouvement par minute
        montrees = movements.lignes_recentes(journal, 7, 400, 3000,
                                             maintenant=self.MAINTENANT)
        self.assertEqual(3000, montrees)

    def test_on_ne_montre_jamais_plus_que_ce_qu_il_y_a(self):
        journal = self._journal(12, self.JOUR)
        montrees = movements.lignes_recentes(journal, 7, 400, 3000,
                                             maintenant=self.MAINTENANT)
        self.assertEqual(12, montrees)

    def test_un_journal_vide(self):
        self.assertEqual(0, movements.lignes_recentes([], 7, 400, 3000,
                                                      maintenant=self.MAINTENANT))


if __name__ == "__main__":
    unittest.main()
