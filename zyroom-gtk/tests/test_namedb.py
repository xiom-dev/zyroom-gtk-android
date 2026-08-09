"""Le lecteur de `string_client.pack`.

Premiers tests du portage GTK : le côté Android en a soixante-trois, celui-ci
n'en avait aucun, et c'est justement ici qu'un défaut est resté invisible des
mois — le lecteur perdait des noms sans rien signaler.

    python3 -m unittest discover -s tests
"""
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom.namedb import NameDb, _parse_pack   # noqa: E402

PACK_DU_JEU = os.path.expanduser("~/.local/share/Ryzom/0/save/string_client.pack")


def enregistrement(cle: bytes, valeur: str, separateur: int = 0x02) -> bytes:
    """Un enregistrement du pack, dans l'un ou l'autre de ses deux formats."""
    if separateur == 0x01:
        octets, compte = valeur.encode("utf-16-le"), len(valeur)
    else:
        octets = valeur.encode("utf-8")
        compte = len(octets)
    return (struct.pack("<I", len(cle)) + cle + bytes([separateur])
            + struct.pack("<I", compte) + octets)


class LecteurDePack(unittest.TestCase):

    def test_les_deux_formats(self):
        """Le 0x01 est l'ancien (UTF-16), le 0x02 celui des clients récents."""
        data = b"STR_PACK" + enregistrement(b"a.sitem", "Ambre", 0x01) \
                           + enregistrement(b"b.sitem", "Bois", 0x02)
        noms = _parse_pack(data)
        self.assertEqual("Ambre", noms["a.sitem"])
        self.assertEqual("Bois", noms["b.sitem"])

    def test_un_faux_enregistrement_ne_fait_pas_perdre_le_suivant(self):
        """Le défaut corrigé : le parcours cherche octet par octet quand un
        enregistrement ne se présente pas, et rien ne l'empêchait de prendre
        une suite d'octets quelconque pour un enregistrement — celui qui
        commençait à l'intérieur était alors perdu. Ici la fausse clé porte un
        octet accentué, ce qu'aucune clé du pack n'a."""
        leurre = struct.pack("<I", 4) + bytes([0xE9, 0x21, 0x21, 0x21]) \
            + bytes([0x02]) + struct.pack("<I", 200)
        data = b"STR_PACK" + leurre + enregistrement(b"m0117dxajd01.sitem", "Ambre de choix")
        self.assertEqual("Ambre de choix", _parse_pack(data)["m0117dxajd01.sitem"])

    def test_une_fiche_inconnue_rend_son_identifiant(self):
        self.assertEqual("inconnu.sitem", NameDb().name("inconnu.sitem"))


class CacheDesNoms(unittest.TestCase):
    """Le cache porte un numéro de format en plus de l'empreinte du pack.

    Sans lui, corriger le lecteur ne servirait à personne : le pack n'ayant pas
    changé, chacun garderait la table incomplète qu'il en avait tirée."""

    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.pack = os.path.join(self.dossier.name, "string_client.pack")
        with open(self.pack, "wb") as fh:
            fh.write(b"STR_PACK" + enregistrement(b"a.sitem", "Ambre"))
        self.cache = os.path.join(self.dossier.name, "names.json")

    def tearDown(self):
        self.dossier.cleanup()

    def test_le_cache_se_relit(self):
        premier = NameDb(self.cache)
        self.assertTrue(premier.load(self.pack))
        with open(self.cache, encoding="utf-8") as fh:
            garde = json.load(fh)
        self.assertTrue(garde["signature"].startswith("v"))

        # Second chargement : il vient du cache, et rend les mêmes noms.
        second = NameDb(self.cache)
        self.assertTrue(second.load(self.pack))
        self.assertEqual("Ambre", second.name("a.sitem"))

    def test_un_cache_d_un_autre_format_est_ignore(self):
        NameDb(self.cache).load(self.pack)
        with open(self.cache, encoding="utf-8") as fh:
            garde = json.load(fh)
        garde["signature"] = "v1:" + garde["signature"].split(":", 1)[1]
        garde["names"] = {"a.sitem": "PÉRIMÉ"}
        with open(self.cache, "w", encoding="utf-8") as fh:
            json.dump(garde, fh)

        db = NameDb(self.cache)
        db.load(self.pack)
        self.assertEqual("Ambre", db.name("a.sitem"))


@unittest.skipUnless(os.path.isfile(PACK_DU_JEU), "pack du client absent")
class SurLeVraiPack(unittest.TestCase):
    """Trois mégaoctets réels : le seul endroit où le défaut se voyait."""

    def test_items_competences_et_avant_postes(self):
        with open(PACK_DU_JEU, "rb") as fh:
            noms = _parse_pack(fh.read())
        items = [k for k in noms if k.endswith(".sitem")]
        avant_postes = [k for k in noms if k.endswith(".outpost")]
        self.assertGreater(len(items), 7000, "trop peu d'items")
        self.assertGreater(len(avant_postes), 25, "avant-postes perdus")
        self.assertEqual("Ambre de choix / Sha de la Jungle",
                         noms["m0117dxajd01.sitem"])
        # Six codes de compétences et une fiche d'item disparaissaient avant la
        # correction : ceux-ci servent de témoins.
        self.assertEqual("Expert en création de manches lourdes", noms["scahse"])
        self.assertEqual("Ferme de Malmontagne", noms["fyros_outpost_04.outpost"])


if __name__ == "__main__":
    unittest.main()
