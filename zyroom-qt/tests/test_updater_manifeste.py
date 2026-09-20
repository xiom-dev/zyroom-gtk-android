#!/usr/bin/env python3
"""Ce que l'application lit dans le manifeste, et ce qu'elle en conclut.

**Deux joueurs ont tourne en rond sous Windows.** Le manifeste ne portait
qu'un numero, celui du dernier paquet livre quel que soit le systeme ; les
archives Linux et Windows, elles, ne paraissent pas ensemble -- celle de
Windows sort d'une machine que le mainteneur n'a pas. L'application Windows se
croyait donc en retard, telechargeait une archive plus ancienne que le numero
annonce, s'installait, se retrouvait en retard, recommencait.

Le manifeste porte desormais une case par systeme, et la racine reste ecrite
pour les versions deja installees qui ne connaissent pas ce bloc. Ces essais
tiennent les deux lectures, celle d'hier et celle d'aujourd'hui.

Rien n'ici ne touche au reseau : le manifeste est une chaine, et `urlopen` est
remplace le temps d'un essai.
"""
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import updater  # noqa: E402


class CleSysteme(unittest.TestCase):
    """Le nom du systeme, tel que le manifeste le nomme."""

    def test_le_nom_suit_os_name(self):
        with mock.patch.object(updater.os, "name", "nt"):
            self.assertEqual("windows", updater.cle_systeme())
        with mock.patch.object(updater.os, "name", "posix"):
            self.assertEqual("linux", updater.cle_systeme())


class AnnoncePourIci(unittest.TestCase):
    """La case du systeme l'emporte sur la racine, quand elle existe."""

    ENTREE = {
        "versionCode": 105,
        "versionName": "1.11.76",
        "systemes": {
            "linux": {"versionCode": 105, "versionName": "1.11.76"},
            "windows": {"versionCode": 103, "versionName": "1.11.74"},
        },
    }

    def test_la_case_du_systeme_prime(self):
        with mock.patch.object(updater, "cle_systeme", lambda: "windows"):
            annonce = updater._annonce_pour_ici(self.ENTREE)
        self.assertEqual(103, annonce["versionCode"])
        self.assertEqual("1.11.74", annonce["versionName"])

    def test_sans_bloc_systemes_on_lit_la_racine(self):
        """C'est le manifeste d'hier, et les versions deja installees."""
        entree = {"versionCode": 105, "versionName": "1.11.76"}
        with mock.patch.object(updater, "cle_systeme", lambda: "windows"):
            self.assertEqual(105, updater._annonce_pour_ici(entree)["versionCode"])

    def test_un_systeme_absent_de_la_case_retombe_sur_la_racine(self):
        entree = dict(self.ENTREE, systemes={"linux": {"versionCode": 99}})
        with mock.patch.object(updater, "cle_systeme", lambda: "windows"):
            self.assertEqual(105, updater._annonce_pour_ici(entree)["versionCode"])

    def test_l_adresse_reste_celle_de_la_racine(self):
        """La case dit un numero, jamais ou trouver l'archive."""
        entree = dict(self.ENTREE, urls={"windows": "https://exemple/w.zip"})
        with mock.patch.object(updater, "cle_systeme", lambda: "windows"):
            annonce = updater._annonce_pour_ici(entree)
        self.assertEqual({"windows": "https://exemple/w.zip"}, annonce["urls"])


class UrlPourIci(unittest.TestCase):
    """Une archive par systeme -- un bundle Linux ne se lance pas ailleurs."""

    def test_l_adresse_du_systeme(self):
        entree = {"urls": {"linux": "https://exemple/l.zip",
                           "windows": "https://exemple/w.zip"}}
        with mock.patch.object(updater.os, "name", "nt"):
            self.assertEqual("https://exemple/w.zip", updater._url_pour_ici(entree))
        with mock.patch.object(updater.os, "name", "posix"):
            self.assertEqual("https://exemple/l.zip", updater._url_pour_ici(entree))

    def test_une_seule_url_a_l_ancienne(self):
        self.assertEqual("https://exemple/tout.zip",
                         updater._url_pour_ici({"url": "https://exemple/tout.zip"}))

    def test_sans_archive_pour_ce_systeme_on_ne_rend_rien(self):
        """Mieux vaut se taire qu'annoncer une version qu'on n'ira pas chercher."""
        entree = {"urls": {"linux": "https://exemple/l.zip"}}
        with mock.patch.object(updater.os, "name", "nt"):
            self.assertEqual("", updater._url_pour_ici(entree))


def faux_reseau(charge: dict):
    """Remplace `urlopen` par une reponse toute prete."""
    class Reponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            self.close()
            return False

    def ouvrir(_requete, timeout=None):
        return Reponse(json.dumps(charge).encode("utf-8"))

    return mock.patch.object(updater.urllib.request, "urlopen", ouvrir)


class MiseAJourDisponible(unittest.TestCase):
    """Ce que le veilleur annonce, et ce sur quoi il se tait."""

    def setUp(self):
        self.veilleur = updater.Veilleur()
        # Une installation imaginaire : sans elle le veilleur ne regarde
        # meme pas le manifeste, et tous les essais rendraient la meme chose.
        self.installe = mock.patch.object(updater, "dossier_installe",
                                          lambda: "/o/ZyRoom-Qt")
        self.installe.start()
        self.addCleanup(self.installe.stop)

    def manifeste(self, code: int, nom: str = "9.9.9") -> dict:
        return {updater.APPLICATION: {
            "versionCode": code, "versionName": nom,
            "urls": {"linux": "https://exemple/l.zip",
                     "windows": "https://exemple/w.zip"}}}

    def test_une_version_plus_recente_est_annoncee(self):
        with faux_reseau(self.manifeste(updater.__version_code__ + 1)):
            self.assertEqual("9.9.9", self.veilleur.mise_a_jour_disponible())

    def test_la_meme_version_ne_l_est_pas(self):
        with faux_reseau(self.manifeste(updater.__version_code__)):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_une_version_plus_ancienne_non_plus(self):
        with faux_reseau(self.manifeste(updater.__version_code__ - 1)):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_c_est_un_entier_qu_on_compare_jamais_un_nom(self):
        """« 0.10 » vient apres « 0.9 » pour nous, avant pour un tri de chaines."""
        charge = self.manifeste(updater.__version_code__ + 1, nom="0.10")
        charge[updater.APPLICATION]["versionName"] = "0.10"
        with faux_reseau(charge):
            self.assertEqual("0.10", self.veilleur.mise_a_jour_disponible())

    def test_un_manifeste_qui_ne_nous_connait_pas(self):
        with faux_reseau({"net.ryzom.autre": {"versionCode": 9999}}):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_un_versioncode_illisible_ne_casse_rien(self):
        charge = self.manifeste(updater.__version_code__ + 1)
        charge[updater.APPLICATION]["versionCode"] = "dernière"
        with faux_reseau(charge):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_une_panne_de_reseau_ne_casse_rien(self):
        """Sans reponse, on s'en tient a ce qu'on a, et on redemandera."""
        def tombe(*_a, **_k):
            raise OSError("réseau injoignable")
        with mock.patch.object(updater.urllib.request, "urlopen", tombe):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_sans_archive_pour_ce_systeme_on_se_tait(self):
        charge = self.manifeste(updater.__version_code__ + 1)
        charge[updater.APPLICATION]["urls"] = {"linux": "https://exemple/l.zip"}
        with mock.patch.object(updater.os, "name", "nt"), \
                faux_reseau(charge):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())

    def test_hors_paquet_on_ne_regarde_meme_pas(self):
        self.installe.stop()
        with mock.patch.object(updater, "dossier_installe", lambda: ""), \
                faux_reseau(self.manifeste(updater.__version_code__ + 1)):
            self.assertEqual("", self.veilleur.mise_a_jour_disponible())
        self.installe.start()


if __name__ == "__main__":
    unittest.main()
