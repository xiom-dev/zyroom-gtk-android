"""La météo d'Atys : lecture du flux, et ce qu'on en déduit du temps qui passe.

Un cycle vaut trois heures d'Atys, neuf minutes réelles ; l'API donne l'heure
d'Atys avec ses décimales, et c'est d'elles que dépendent les comptes à rebours.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, meteo                                   # noqa: E402

FLUX = """{"version":"1.0","hour":"104011.496","cycle":34670,
 "continents":{"terre":{
   "34670":{"cycle":34670,"condition":"good","value":"0.483","text":"uiFair"},
   "34671":{"cycle":34671,"condition":"best","value":"0.042","text":"uiFair"}}}}"""


class Lecture(unittest.TestCase):

    def test_le_flux_rend_cycle_heure_et_continents(self):
        r = meteo.parse_weather(FLUX)
        self.assertEqual(34670, r.cycle_courant)
        self.assertAlmostEqual(104011.496, r.heure_atys, places=3)
        self.assertEqual([34670, 34671], [m.cycle for m in r.continents["terre"]])
        self.assertAlmostEqual(0.483, r.continents["terre"][0].value, places=3)

    def test_sans_heure_le_cycle_fait_foi(self):
        r = meteo.parse_weather('{"cycle":100,"continents":{}}')
        self.assertEqual(300.0, r.heure_atys)
        self.assertEqual(0.0, r.avancement_du_cycle)

    def test_une_erreur_de_l_api_est_signalee(self):
        with self.assertRaises(ValueError):
            meteo.parse_weather('{"errors":"nope"}')


class TempsDAtys(unittest.TestCase):

    def releve(self):
        r = meteo.parse_weather(FLUX)
        return meteo.MeteoAtys(r.cycle_courant, r.heure_atys, 0, r.continents)

    def test_l_avancement_se_lit_dans_les_decimales(self):
        """104011,496 au cycle 34670 : le cycle commence à 104010, on est donc
        à la moitié. Compter en cycles pleins surestimait l'attente."""
        self.assertAlmostEqual(0.499, self.releve().avancement_du_cycle, places=2)

    def test_le_compte_a_rebours_tient_compte_du_cycle_entame(self):
        r = self.releve()
        # Le cycle suivant commence dans une demi-période, soit ~4 min.
        self.assertEqual(4, r.minutes_avant(34671))

    def test_l_heure_du_jour_et_la_nuit(self):
        self.assertEqual(19, self.releve().heure_du_jour)
        self.assertFalse(self.releve().nuit)

    def test_la_nuit_va_de_vingt_deux_heures_a_trois_heures(self):
        for h in (22, 23, 0, 2):
            self.assertTrue(meteo.est_la_nuit(h), h)
        for h in (3, 12, 21):
            self.assertFalse(meteo.est_la_nuit(h), h)


class Textes(unittest.TestCase):

    def test_les_quatre_temps_que_l_api_emploie(self):
        self.assertEqual("Beau", meteo.texte_meteo("uiFair"))
        self.assertEqual("Pluie", meteo.texte_meteo("uiRainy"))
        self.assertEqual("Orage", meteo.texte_meteo("uiThundery"))
        self.assertEqual("Orage de sève", meteo.texte_meteo("uiSapThundery"))

    def test_une_cle_inconnue_reste_lisible(self):
        """Mieux vaut l'afficher qu'un blanc : elle dit qu'il se passe
        quelque chose, et se traduira le jour où on la rencontre."""
        self.assertEqual("Bidule", meteo.texte_meteo("uiBidule"))

    def test_les_conditions_de_gisement(self):
        self.assertEqual("Excellente", meteo.texte_condition("best"))
        self.assertEqual("Exécrable", meteo.texte_condition("worst"))

    def test_un_compte_a_rebours_se_lit(self):
        self.assertEqual("27 min", meteo.duree(27))
        self.assertEqual("1 h 12", meteo.duree(72))
        # À cheval sur la bascule, « dans 0 min » se lisait comme une panne.
        self.assertEqual("moins d'une minute", meteo.duree(0))


class TableDesMatieres(unittest.TestCase):
    """Le relevé figé doit couvrir les quatre saisons et les quatre zones."""

    def test_les_quatre_saisons_ont_leurs_suprêmes(self):
        for saison in meteo.SAISONS:
            zones = armory.SUPREMES.get(saison, {})
            self.assertEqual(4, len(zones), saison)
            self.assertTrue(all(groupes for groupes in zones.values()), saison)

    def test_les_excellentes_se_donnent_de_jour_et_de_nuit(self):
        for saison in meteo.SAISONS:
            self.assertEqual({"JOUR", "NUIT"}, set(armory.EXCELLENTES[saison]))

    def test_chaque_zone_du_releve_a_son_continent(self):
        for zone in armory.SUPREMES["PRINTEMPS"]:
            self.assertIn(zone, meteo.CONTINENT_DE_ZONE, zone)


class AvanceToutSeul(unittest.TestCase):
    """Le temps d'Atys avance à cadence fixe : on le suit sans rien redemander."""

    def releve(self, il_y_a: float = 0.0):
        import time
        r = meteo.parse_weather(FLUX)
        return meteo.MeteoAtys(r.cycle_courant, r.heure_atys, 0, r.continents,
                               pris_a=time.monotonic() - il_y_a)

    def test_neuf_minutes_font_un_cycle(self):
        """Un cycle vaut trois heures d'Atys, soit neuf minutes réelles."""
        depart = self.releve()
        plus_tard = self.releve(il_y_a=9 * 60).a_present()
        self.assertEqual(depart.cycle_courant + 1, plus_tard.cycle_courant)

    def test_trois_minutes_font_une_heure_d_atys(self):
        plus_tard = self.releve(il_y_a=3 * 60).a_present()
        self.assertAlmostEqual(self.releve().heure_atys + 1,
                               plus_tard.heure_atys, places=1)

    def test_la_serie_des_cycles_ne_bouge_pas(self):
        """Seul le curseur avance : les prévisions reçues restent les mêmes."""
        depart = self.releve()
        self.assertEqual(depart.continents, depart.a_present().continents)

    def test_sans_temps_ecoule_rien_ne_change(self):
        depart = self.releve()
        self.assertEqual(depart.cycle_courant, depart.a_present().cycle_courant)


class Symboles(unittest.TestCase):
    """Les symboles des familles, embarqués avec le paquet.

    Ils viennent du jeu, relevés une fois par `table_armory.py` : rien ne se
    télécharge à l'affichage du tableau. Le fichier doit donc être là — un
    chemin rendu pour une image absente ferait un cadre vide dans la grille.
    """

    def test_chaque_famille_du_releve_a_son_symbole(self):
        for saison, zones in armory.SUPREMES.items():
            for zone, groupes in zones.items():
                for groupe in groupes:
                    chemin = meteo.symbole(groupe)
                    self.assertIsNotNone(chemin, f"{groupe} ({saison}, {zone})")
                    self.assertTrue(os.path.isfile(chemin), chemin)

    def test_une_famille_inconnue_ne_rend_rien(self):
        """Plutôt que de tomber : Ryzom peut en ajouter une."""
        self.assertIsNone(meteo.symbole("Bidule"))

    def test_le_symbole_est_une_image(self):
        with open(meteo.symbole("Sève"), "rb") as fh:
            self.assertEqual(b"\x89PNG", fh.read(4))


def _gtk_disponible() -> bool:
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Gdk", "4.0")
        from gi.repository import Gtk                              # noqa: F401
        return True
    except Exception:
        return False


@unittest.skipUnless(_gtk_disponible(), "GTK4 absent de cette machine")
class Courbe(unittest.TestCase):
    """Ce que la courbe météo trace réellement.

    Le palier est exact — l'API donne une valeur par cycle — mais la bascule
    d'un palier au suivant ne l'est pas : le taux monte et descend
    graduellement. Un trait vertical laisserait croire à un saut instantané.

    On relève ici les segments posés sur le contexte Cairo, plutôt que de
    relire le code : c'est la seule façon de voir qu'une oblique est bien
    dessinée, et non qu'elle est bien écrite.
    """

    def _segments(self, valeurs):
        import types
        from zyroom.window import MainWindow

        class FauxCr:
            """Un contexte Cairo qui ne dessine rien mais retient la courbe.

            Elle est le seul chemin tracé au trait de deux points ; on
            s'arrête à son `stroke()`, sinon le trait du présent — vertical,
            et lui aussi épais de deux points — viendrait s'y ajouter et
            passerait pour une bascule.
            """

            def __init__(self):
                self.segments, self.dernier = [], None
                self.trait = self.fini = False

            def set_line_width(self, w):
                self.trait = (w == 2.0) and not self.fini

            def stroke(self):
                if self.trait:
                    self.fini = True
                self.trait = False

            def move_to(self, x, y):
                self.dernier = (x, y)

            def line_to(self, x, y):
                if self.trait and self.dernier:
                    self.segments.append((self.dernier, (x, y)))
                self.dernier = (x, y)

            def __getattr__(self, nom):
                return lambda *a, **k: None

        cycles = [meteo.Meteo(cycle=1000 + i, condition="good", value=v,
                              text="uiFair")
                  for i, v in enumerate(valeurs)]
        releve = types.SimpleNamespace(
            heure_atys=1000 * meteo.HEURES_PAR_CYCLE + 1.0,
            cycles_des_primes=lambda: cycles)
        faux = types.SimpleNamespace(
            _meteo_affiche=releve, _meteo_releve=None,
            ANCRE=MainWindow.ANCRE, FENETRE_HEURES=MainWindow.FENETRE_HEURES,
            TRANSITION_HEURES=MainWindow.TRANSITION_HEURES)
        cr = FauxCr()
        MainWindow._dessiner_courbe(faux, None, cr, 800.0, 300.0)
        # Le premier segment relève du chemin précédent — l'aire — que ce faux
        # contexte ne sait pas clore ; Cairo, lui, repart d'un point neuf.
        return cr.segments[1:]

    def test_un_changement_de_palier_se_trace_en_oblique(self):
        segments = self._segments([0.20, 0.80])
        montees = [s for s in segments
                   if abs(s[0][1] - s[1][1]) > 0.5 and abs(s[0][0] - s[1][0]) > 0.5]
        verticales = [s for s in segments
                      if abs(s[0][1] - s[1][1]) > 0.5 and abs(s[0][0] - s[1][0]) < 0.5]
        self.assertEqual(1, len(montees), "la bascule doit être une oblique")
        self.assertEqual([], verticales, "aucune bascule ne doit être verticale")

    def test_deux_cycles_de_même_valeur_ne_font_pas_de_bascule(self):
        segments = self._segments([0.50, 0.50])
        self.assertTrue(all(abs(s[0][1] - s[1][1]) < 0.5 for s in segments),
                        "rien ne change : la ligne doit rester plate")

    def test_le_palier_occupe_le_milieu_du_cycle(self):
        """Le palier est exact ; c'est la bascule qui mord de part et d'autre."""
        from zyroom.window import MainWindow
        segments = self._segments([0.20, 0.80])
        plat = next(s for s in segments if abs(s[0][1] - s[1][1]) < 0.5)
        largeur = (800.0 - 34.0) / MainWindow.FENETRE_HEURES
        attendu = (meteo.HEURES_PAR_CYCLE - MainWindow.TRANSITION_HEURES) * largeur
        self.assertAlmostEqual(attendu, plat[1][0] - plat[0][0], places=6)


if __name__ == "__main__":
    unittest.main()
