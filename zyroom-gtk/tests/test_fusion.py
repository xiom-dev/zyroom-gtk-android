"""Deux journaux qui se racontent ce que l'autre a vu.

L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
déduit de deux relevés successifs, et chaque application ne connaît donc que
ce qu'elle a regardé elle-même. Deux applications qui ne relèvent pas aux
mêmes moments décrivent le même trajet avec un découpage différent.

Le cas qui a motivé ce fichier est réel, relevé le 29 août 2026 sur le trésor
de La Lune Éternelle : le bureau avait vu deux mouvements, le téléphone un
seul, et c'était le même argent.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import movements                                     # noqa: E402


def mv(ts, old, new, inv="money", sheet="dappers", q=0):
    return movements.Movement(ts=ts, inv_key=inv, sheet=sheet, quality=q,
                              kind=movements.MODIFIED, delta=new - old,
                              old=old, new=new)


class LeTresorDeLaLuneEternelle(unittest.TestCase):
    """Le cas réel, chiffres compris."""

    def test_le_gros_ecart_du_telephone_cede_au_detail_du_bureau(self):
        bureau = [mv(1787000000, 75000000, 75440000),      # 24/08 +440 000
                  bureau_second := mv(1787345000, 75440000, 73640000)]  # 28/08
        telephone = [mv(1788007080, 75000000, 73640000)]   # 29/08 -1 360 000

        fusionne, ajoutes = movements.fusionner(bureau, telephone)

        self.assertEqual(2, len(fusionne),
                         "le mouvement grossier du téléphone fait double emploi")
        self.assertEqual(0, ajoutes, "il n'apprenait rien de neuf")
        self.assertIn(bureau_second, fusionne)
        self.assertEqual({(75000000, 75440000), (75440000, 73640000)},
                         {(m.old, m.new) for m in fusionne})

    def test_et_dans_l_autre_sens_le_telephone_gagne_le_detail(self):
        """Le même calcul, vu du téléphone : c'est lui qui reçoit les deux."""
        bureau = [mv(1787000000, 75000000, 75440000),
                  mv(1787345000, 75440000, 73640000)]
        telephone = [mv(1788007080, 75000000, 73640000)]

        fusionne, ajoutes = movements.fusionner(telephone, bureau)

        self.assertEqual(2, len(fusionne))
        self.assertEqual(2, ajoutes, "les deux pas du bureau sont neufs ici")
        self.assertNotIn((75000000, 73640000),
                         {(m.old, m.new) for m in fusionne})


class CeQueLaFusionGarde(unittest.TestCase):

    def test_un_ecart_que_personne_ne_detaille_est_garde(self):
        """Sans le pas intermédiaire, l'écart global est la seule vérité connue."""
        bureau = [mv(1787345000, 75440000, 73640000)]
        telephone = [mv(1788007080, 75000000, 73640000)]

        fusionne, ajoutes = movements.fusionner(bureau, telephone)

        self.assertEqual(2, len(fusionne))
        self.assertEqual(1, ajoutes)

    def test_le_meme_pas_vu_des_deux_cotes_ne_compte_qu_une_fois(self):
        pas = (1787345000, 75440000, 73640000)
        fusionne, ajoutes = movements.fusionner([mv(*pas)], [mv(1788000000, *pas[1:])])
        self.assertEqual(1, len(fusionne))
        self.assertEqual(0, ajoutes)

    def test_le_plus_ancien_horodatage_l_emporte(self):
        """Il dit quand on a regardé ; le premier à avoir vu date le mieux."""
        tot, tard = 1787345000, 1788007080
        fusionne, _ = movements.fusionner([mv(tard, 100, 90)], [mv(tot, 100, 90)])
        self.assertEqual(1, len(fusionne))
        self.assertEqual(tot, fusionne[0].ts)

    def test_deux_objets_differents_ne_se_melangent_pas(self):
        """Les mêmes quantités sur deux fiches restent deux trajets distincts."""
        a = mv(1787000000, 10, 20, inv="chest1", sheet="ambre.sitem")
        b = mv(1787000000, 10, 20, inv="chest1", sheet="resine.sitem")
        fusionne, ajoutes = movements.fusionner([a], [b])
        self.assertEqual(2, len(fusionne))
        self.assertEqual(1, ajoutes)

    def test_un_meme_objet_dans_deux_coffres_reste_deux_trajets(self):
        a = mv(1787000000, 10, 20, inv="chest1", sheet="ambre.sitem")
        b = mv(1787000000, 10, 20, inv="chest2", sheet="ambre.sitem")
        fusionne, _ = movements.fusionner([a], [b])
        self.assertEqual(2, len(fusionne))

    def test_un_aller_retour_ne_fait_pas_disparaitre_les_deux_pas(self):
        """On vend puis on rachète : le compteur repasse par une valeur connue.

        Le trajet 100 → 90 → 100 ne doit pas être pris pour un chemin qui
        justifierait d'écarter quoi que ce soit — il n'y a rien à écarter.
        """
        journal = [mv(1787000000, 100, 90), mv(1787001000, 90, 100)]
        fusionne, ajoutes = movements.fusionner(journal, [])
        self.assertEqual(2, len(fusionne))
        self.assertEqual(0, ajoutes)


class LesDeuxDialectes(unittest.TestCase):
    """Le téléphone nomme trois champs autrement, et crie ses `kind`."""

    def test_une_ligne_du_telephone_se_lit_ici(self):
        venu = movements.lire_etranger({
            "at": 1788007080, "inv": "money", "label": "Trésor",
            "sheet": "dappers", "q": 0, "kind": "MODIFIED",
            "delta": -1360000, "before": 75000000, "after": 73640000})
        self.assertEqual(1788007080, venu.ts)
        self.assertEqual(75000000, venu.old)
        self.assertEqual(73640000, venu.new)
        self.assertEqual(movements.MODIFIED, venu.kind)

    def test_une_ligne_d_ici_se_relit_aussi(self):
        """Importer le journal d'un autre poste de bureau doit marcher."""
        venu = movements.lire_etranger({
            "ts": 1787345000.5, "inv": "chest1", "label": "Coffre 1",
            "sheet": "ambre.sitem", "q": 150, "kind": "modified",
            "delta": 7992, "old": 8524, "new": 16516})
        self.assertEqual(8524, venu.old)
        self.assertEqual(16516, venu.new)


class LeFichierImporte(unittest.TestCase):

    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self.chemin = os.path.join(self._dossier.name, "guild-1.jsonl")

    def tearDown(self):
        self._dossier.cleanup()

    def test_l_import_ecrit_le_journal_fusionne(self):
        movements.append(self.chemin, [mv(1787345000, 75440000, 73640000)])
        ajoutes = movements.importer(self.chemin, [
            '{"at": 1788007080, "inv": "money", "sheet": "dappers", "q": 0,'
            ' "kind": "MODIFIED", "delta": -1360000,'
            ' "before": 75000000, "after": 73640000}',
        ])
        self.assertEqual(1, ajoutes)
        relu = movements.load(self.chemin)
        self.assertEqual(2, len(relu))

    def test_une_ligne_illisible_ne_perd_pas_les_autres(self):
        ajoutes = movements.importer(self.chemin, [
            "ceci n'est pas du JSON",
            '{"at": 1, "inv": "money", "sheet": "dappers", "q": 0,'
            ' "kind": "MODIFIED", "delta": 5, "before": 0, "after": 5}',
            "",
        ])
        self.assertEqual(1, ajoutes)

    def test_importer_deux_fois_n_ajoute_rien_la_seconde(self):
        ligne = ('{"at": 1788007080, "inv": "money", "sheet": "dappers", "q": 0,'
                 ' "kind": "MODIFIED", "delta": -1360000,'
                 ' "before": 75000000, "after": 73640000}')
        self.assertEqual(1, movements.importer(self.chemin, [ligne]))
        self.assertEqual(0, movements.importer(self.chemin, [ligne]))
        self.assertEqual(1, len(movements.load(self.chemin)))

    def test_un_fichier_vide_ne_touche_a_rien(self):
        movements.append(self.chemin, [mv(1787345000, 100, 90)])
        self.assertEqual(0, movements.importer(self.chemin, []))
        self.assertEqual(1, len(movements.load(self.chemin)))


if __name__ == "__main__":
    unittest.main()
