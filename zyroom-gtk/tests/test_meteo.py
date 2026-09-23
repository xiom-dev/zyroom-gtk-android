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
        from test_axe_meteo import constantes_de_fenetre

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
            # La courbe ecrit ses heures au corps du zoom courant. Un seul
            # reglage l'interesse, et ce qu'on mesure ici -- la pente des
            # segments -- n'en depend pas : la taille normale suffit.
            _settings=types.SimpleNamespace(zoom=1.0),
            # **Toutes les constantes de la fenetre, et non une liste tenue
            # a la main.** Elle se perimait a chaque reglage ajoute au trace :
            # l'essai tombait alors sur un AttributeError qui ne disait rien
            # du defaut qu'il est cense garder.
            **constantes_de_fenetre())
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


class FenetreSupreme(unittest.TestCase):
    """Le compte à rebours que le tracker d'atys.us affiche, refait ici.

    Sa règle a été trouvée en le mesurant : le 22 septembre 2026 à 14 h 22, il
    annonçait « Supremes Available in 2h 48m », et la prévision du jeu plaçait
    le prochain cycle exécrable à 17 h 09 — la même minute. « Bonnes conditions
    pour le suprême » veut donc dire humidité au-dessus de 83,4 %, et rien
    d'autre.
    """

    @staticmethod
    def _releve(conditions, cycle=100):
        cycles = [meteo.Meteo(cycle=cycle + i, condition=c, value=0.5,
                              text="uiRainy")
                  for i, c in enumerate(conditions)]
        return meteo.MeteoAtys(cycle_courant=cycle, heure_atys=cycle * 3.0,
                               saison=1,
                               continents={"sources": cycles, "terre": cycles})

    def test_le_premier_cycle_exécrable_à_venir(self):
        r = self._releve(["good", "bad", "good", "worst", "worst", "best"])
        self.assertEqual(103, meteo.prochaine_fenetre_supreme(r).cycle)

    def test_le_cycle_en_cours_ne_compte_pas(self):
        """On cherche la prochaine fenêtre, pas celle qu'on vit déjà.

        L'écran dit « Fenêtre suprême ouverte » dans ce cas-là, et le compte à
        rebours n'aurait aucun sens."""
        r = self._releve(["worst", "good", "worst"])
        self.assertEqual(102, meteo.prochaine_fenetre_supreme(r).cycle)

    def test_rien_en_vue_ne_s_invente_pas(self):
        """La prévision du jeu ne porte que six heures."""
        self.assertIsNone(
            meteo.prochaine_fenetre_supreme(self._releve(["good"] * 40)))

    def test_sans_relevé_du_tout(self):
        self.assertIsNone(meteo.prochaine_fenetre_supreme(self._releve([])))

    def test_la_fenêtre_d_un_seul_cycle_dure_neuf_minutes(self):
        """Un cycle vaut neuf minutes réelles : trois heures d'Atys."""
        r = self._releve(["worst", "good", "good"])
        self.assertEqual(9, int(meteo.fin_fenetre_supreme(r)))

    def test_deux_cycles_exécrables_ne_font_qu_une_fenêtre(self):
        """« Le cycle suivant » serait faux : on cherche la fin, pas le pas."""
        r = self._releve(["worst", "worst", "bad"])
        self.assertEqual(18, int(meteo.fin_fenetre_supreme(r)))

    def test_la_ligne_et_le_titre_ne_peuvent_plus_se_contredire(self):
        """« sort suprême » n'apparaît qu'en même temps que « Suprême maintenant ».

        La ligne a écrit « sort suprême pendant 1 min » pendant que le titre
        annonçait le suprême pour dans une heure vingt. Les deux se déduisaient
        de règles différentes : la ligne des fourchettes d'humidité, le titre du
        temps exécrable. C'est le titre qui dit vrai."""
        from zyroom.page_meteo import PageMeteo
        for saison in range(4):
            for condition in ("best", "good", "bad", "worst"):
                actuelle = meteo.Meteo(cycle=1, condition=condition,
                                       value=0.5, text="uiRainy")
                releve = self._releve([condition])
                releve = meteo.MeteoAtys(
                    cycle_courant=releve.cycle_courant,
                    heure_atys=releve.heure_atys, saison=saison,
                    continents=releve.continents)
                qualite = PageMeteo._qualite_du_moment(releve, actuelle)
                self.assertEqual(condition == "worst",
                                 qualite == meteo.SUPREME,
                                 f"{meteo.SAISONS[saison]} / {condition}")

    def test_exécrable_jusqu_au_bout_de_la_prévision(self):
        """On ne sait pas jusqu'à quand : l'écran le dit sans compter."""
        self.assertIsNone(meteo.fin_fenetre_supreme(
            self._releve(["worst"] * 40)))


class CeQuiSort(unittest.TestCase):
    """Ce que la météo du moment fait sortir, zone par zone.

    L'humidité décide de la condition, la condition décide de la qualité, et la
    qualité décide de ce qu'on trouve — mais **pas de la même façon dans les
    quatre zones**. C'est ce que les deux relevés de la guilde disent, et
    qu'aucun site public ne donne.
    """

    def test_les_deux_tables_nomment_les_mêmes_zones(self):
        """Une zone de la table de forage absente d'ici ne s'afficherait jamais."""
        from zyroom import forage
        self.assertEqual(set(forage.SUPREMES), set(meteo.ZONES))

    def test_chaque_saison_et_chaque_condition_rend_quelque_chose(self):
        """Une case vide se lirait « rien ne sort », ce qui n'arrive jamais.

        Chaque gisement occupe deux des quatre bandes d'humidité : quelle que
        soit l'heure, il y a toujours une moitié des matières qui sort."""
        for saison in range(4):
            for condition in ("worst", "bad", "good", "best"):
                for zone in meteo.ZONES:
                    qualite, groupes = meteo.sortie_de(saison, zone, condition)
                    self.assertIsNotNone(qualite, f"{saison}/{condition}/{zone}")
                    self.assertTrue(groupes, f"{saison}/{condition}/{zone}")

    def test_la_casse_de_la_condition_est_sans_importance(self):
        """L'API rend « best », les tables rangent sous « BEST »."""
        self.assertEqual(meteo.sortie_de(0, "Sources Interdites", "best"),
                         meteo.sortie_de(0, "Sources Interdites", "BEST"))

    def test_une_saison_hors_bornes_ne_rend_rien(self):
        """Le flux du temps peut ne pas avoir répondu : la saison vaut -1."""
        self.assertEqual((None, {}),
                         meteo.sortie_de(-1, "Sources Interdites", "best"))

    def test_une_zone_inconnue_ne_rend_rien(self):
        self.assertEqual((None, {}), meteo.sortie_de(0, "Fyros", "best"))

    def test_une_zone_ne_rend_que_sa_meilleure_qualité(self):
        """Suprême et excellente ne se mélangent pas dans une même colonne.

        Le forage se choisit par la qualité : mêler les deux ferait lire comme
        suprême une matière qui ne l'est pas."""
        for saison in range(4):
            for condition in ("worst", "bad", "good", "best"):
                for zone in meteo.ZONES:
                    qualite, groupes = meteo.sortie_de(saison, zone, condition)
                    for famille, matieres in groupes.items():
                        for matiere in matieres:
                            self.assertEqual(
                                qualite,
                                meteo.qualite_de(zone, famille, matiere,
                                                 saison, condition),
                                f"{zone} / {famille} / {matiere}")

    def test_les_quatre_zones_ne_disent_pas_la_même_chose(self):
        """Le cœur de la correction : la zone change ce qui sort.

        Avant, une table unique servait les quatre colonnes — c'était les
        Sources Interdites affichées partout."""
        differents = 0
        for saison in range(4):
            for condition in ("worst", "bad", "good", "best"):
                rendus = [tuple(sorted(
                    (f, tuple(m)) for f, m in
                    meteo.sortie_de(saison, z, condition)[1].items()))
                    for z in meteo.ZONES]
                differents += len(set(rendus)) > 1
        self.assertEqual(16, differents)

    def test_la_table_dit_ce_que_les_foreuses_ont_relevé(self):
        """Le suprême vient du terrain, et rien ne doit s'y ajouter en chemin.

        `donnees/forage-releve-guilde.json` porte les quatre cent vingt-six
        croix telles qu'elles ont été saisies sur xiom.be/forage. Ce contrôle
        refait la traduction — noms de saisons, de conditions, de matières — et
        compare case pour case à ce que l'écran affichera.
        """
        import json
        from zyroom import armory, forage
        releve = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))),
            "donnees", "forage-releve-guilde.json")
        with open(releve, encoding="utf-8") as fh:
            cases = json.load(fh)["cases"]
        saisons = {"Printemps": "PRINTEMPS", "Été": "ETE",
                   "Automne": "AUTOMNE", "Hiver": "HIVER"}
        conditions = {"Worst": "WORST", "Bad": "BAD",
                      "Good": "GOOD", "Best": "BEST"}
        # Les noms canoniques sont ceux d'Armory : `gisements.LIBELLES` en
        # porte jusqu'à trois par matière, et l'un d'eux ne serait pas celui
        # que la table emploie.
        noms = {m: (f, m)
                for zones in armory.SUPREMES.values()
                for familles in zones.values()
                for f, ms in familles.items() for m in ms}
        # Le classeur de la guilde, d'où la page tient ses noms, écrit
        # « Scratch » là où Armory écrit « Scrath ». La faute vient de Ryzom et
        # les deux la portent ; le générateur fait le même rapprochement.
        noms["Scratch"] = noms["Scrath"]
        attendu = {}
        for case, valeur in cases.items():
            zone, saison, matiere, qualite, condition = case.split("|")
            if qualite != "Supp" or valeur != "x":
                continue
            attendu.setdefault(zone, {}).setdefault(
                noms[matiere], set()).add(
                    (saisons[saison], conditions[condition]))
        self.assertEqual(attendu, {z: dict(m)
                                   for z, m in forage.SUPREMES.items()})


class Minuteur(unittest.TestCase):
    """Le battement qui fait avancer l'heure d'Atys.

    Il ne doit jamais cesser d'avancer : la prévision qui manque ne concerne
    que la droite du graphique, jamais le trait du présent.
    """

    def _fenetre(self, releve, en_cours=False):
        import types
        from zyroom.window import MainWindow
        faux = types.SimpleNamespace(
            _meteo_releve=releve, _meteo_affiche=None, _meteo_timer=1,
            _meteo_en_cours=en_cours, charges=0, refraichi=0)
        faux._load_meteo = lambda force=False: setattr(
            faux, "charges", faux.charges + 1)
        faux._refresh_meteo = lambda: setattr(faux, "refraichi",
                                              faux.refraichi + 1)
        # Le battement entraîne aussi les cartes de gisements laissées
        # ouvertes : on compte qu'il les appelle, sans monter de fenêtre.
        faux.cartes = 0
        faux._rafraichir_cartes_gisements = lambda: setattr(
            faux, "cartes", faux.cartes + 1)
        MainWindow._meteo_tick(faux)
        return faux

    def _releve(self, cycles_restants):
        """Un relevé dont le présent est à `cycles_restants` du bout."""
        courant = 1000
        cycles = [meteo.Meteo(cycle=courant + i, condition="good", value=0.5,
                              text="uiFair")
                  for i in range(cycles_restants + 1)]
        return meteo.MeteoAtys(
            cycle_courant=courant,
            heure_atys=courant * meteo.HEURES_PAR_CYCLE,
            saison=0, continents={"sources": cycles})

    def test_au_milieu_de_la_prévision_il_avance_sans_rien_demander(self):
        faux = self._fenetre(self._releve(20))
        self.assertIsNotNone(faux._meteo_affiche)
        self.assertEqual(1, faux.refraichi)
        self.assertEqual(0, faux.charges)

    def test_il_entraîne_les_cartes_ouvertes(self):
        """Sans quoi une carte laissée ouverte mentirait dès la bascule.

        Neuf minutes réelles par cycle, et rien ne distingue un point vert
        juste d'un point vert périmé."""
        self.assertEqual(1, self._fenetre(self._releve(20)).cartes)

    def test_près_du_bout_il_avance_ET_redemande(self):
        """Les deux tenaient dans le même « si » : il redemandait sans avancer."""
        faux = self._fenetre(self._releve(2))
        self.assertIsNotNone(faux._meteo_affiche)
        self.assertEqual(1, faux.refraichi, "la courbe doit avancer quand même")
        self.assertEqual(1, faux.charges)

    def test_il_ne_redemande_pas_tant_qu_une_requête_est_en_vol(self):
        """Sinon une requête partait toutes les dix secondes, pour rien."""
        faux = self._fenetre(self._releve(2), en_cours=True)
        self.assertEqual(0, faux.charges)
        self.assertEqual(1, faux.refraichi, "et il avance toujours")

    def test_sans_relevé_le_battement_s_arrête(self):
        import types
        from zyroom.window import MainWindow
        faux = types.SimpleNamespace(_meteo_releve=None, _meteo_timer=1)
        self.assertFalse(MainWindow._meteo_tick(faux))
        self.assertIsNone(faux._meteo_timer)





class CarteDesRegions(unittest.TestCase):
    """Chaque région a son origine sur la carte du monde, et c'est tout le sujet.

    La carte est un assemblage : les Lacs, la jungle et le désert y sont posés
    côte à côte, et les positions que rend l'API sont locales à la région où
    l'on se trouve. Un repère unique plaçait correctement ce qui était dans une
    région, et n'importe où ailleurs le reste.

    Le repère vient des tables que Ballistic Mystix publie, et non plus d'un
    calage fait à la main dans l'image.
    """

    def test_deux_regions_ont_deux_reperes(self):
        from zyroom import carte
        self.assertEqual("tryker", carte.region_de(17410, -32849)[0])
        self.assertEqual("zorai", carte.region_de(10328, -2316)[0])
        fx, fy = carte.pixel(17410, -32849)      # Fairhaven, dans les Lacs
        self.assertAlmostEqual(2390.0, fx, delta=0.5)
        self.assertAlmostEqual(2493.8, fy, delta=0.5)
        mx, my = carte.pixel(10328, -2316)       # Mounty, dans la jungle
        self.assertAlmostEqual(844.0, mx, delta=0.5)
        self.assertAlmostEqual(2039.2, my, delta=0.5)

    def test_la_region_la_plus_precise_l_emporte(self):
        """Le Nexus est inclus dans les bornes matis, et il est plus précis."""
        from zyroom import carte
        self.assertEqual("nexus", carte.region_de(8700, -7000)[0])

    def test_les_terres_matis_se_placent(self):
        """Elles ne se plaçaient pas, et rien ne le disait.

        L'origine matis calée à la main était celle de la jungle, à quatorze
        mille unités de la vraie : tout point de la forêt tombait hors de
        l'image et `pixel()` rendait `None`. **Aucune bête laissée chez les
        Matis n'apparaissait sur la carte.** C'est la table publiée qui l'a
        révélé, en désaccord d'un seul chiffre sur neuf.
        """
        from zyroom import carte
        for x, y in ((320, -7840), (3280, -4080), (6240, -320)):
            self.assertEqual("matis", carte.region_de(x, y)[0])
            self.assertTrue(carte.contient(x, y), f"({x}, {y}) devrait se placer")

    def test_les_regions_venues_de_la_table_publiee(self):
        """Silan et les sous-terrains du Nexus, que le calage n'avait pas eus."""
        from zyroom import carte
        self.assertEqual("newbieland", carte.region_de(9500, -11000)[0])
        self.assertTrue(carte.contient(9500, -11000))
        self.assertEqual(13, len(carte.REGIONS))

    def test_hors_de_toute_region_on_ne_montre_rien(self):
        from zyroom import carte
        self.assertIsNone(carte.pixel(0, 0))
        self.assertFalse(carte.contient(30000, -2000))




class PositionDuJoueur(unittest.TestCase):
    """La position du personnage, à la racine du flux.

    Elle y est depuis toujours et personne ne la lisait. C'est le repère qui
    manquait sur la carte, et il dit du même coup à quelle distance de ses
    bêtes on se trouve.
    """

    def _ent(self, xml: str):
        from zyroom import ryzom_api
        return ryzom_api.parse_character(xml.encode("utf-8"))

    def test_le_personnage_porte_sa_position(self):
        ent = self._ent(
            '<?xml version="1.0"?><ryzomapi><character><id>1</id>'
            '<name>Xiom</name><position x="17410" y="-32849" z="-7"/>'
            '</character></ryzomapi>')
        self.assertEqual((17410, -32849), (ent.x, ent.y))

    def test_sans_position_on_ne_pretend_rien(self):
        ent = self._ent('<?xml version="1.0"?><ryzomapi><character><id>1</id>'
                        '<name>X</name></character></ryzomapi>')
        self.assertEqual((0, 0), (ent.x, ent.y))
        from zyroom import carte
        self.assertFalse(carte.contient(ent.x, ent.y))




class ColonnesDesBetes(unittest.TestCase):
    """Porteurs à gauche, zigs à droite.

    L'espèce est relevée à la lecture du flux, pas devinée de l'étiquette :
    celle-ci porte un numéro et se traduit.
    """

    def _betes(self):
        from zyroom import ryzom_api
        xml = (
            '<?xml version="1.0"?><ryzomapi><character><id>1</id><name>X</name>'
            '<pets>'
            '<animal index="0"><sheet>gubani_mount_03.creature</sheet>'
            '<status>landscape</status><inventory/></animal>'
            '<animal index="1"><sheet>chjjf3.creature</sheet>'
            '<status>stable</status><inventory/></animal>'
            '<animal index="2"><sheet>chxjf_zig.creature</sheet>'
            '<status>landscape</status><inventory/></animal>'
            '</pets></character></ryzomapi>')
        return ryzom_api.parse_character(xml.encode("utf-8")).betes

    def test_l_espece_est_relevee(self):
        self.assertEqual(["mount", "mektoub", "zig"],
                         [b.espece for b in self._betes()])

    def test_seul_le_zig_va_dans_sa_colonne(self):
        betes = self._betes()
        self.assertEqual(["Zig 1"], [b.etiquette for b in betes if b.zig])
        # La monture et les mektoubs de bat partagent les quatre
        # emplacements du jeu : la numerotation court sur les deux.
        self.assertEqual(["Monture 1", "Mektoub 2"],
                         [b.etiquette for b in betes if not b.zig])

if __name__ == "__main__":
    unittest.main()
