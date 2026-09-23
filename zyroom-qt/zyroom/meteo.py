"""La météo d'Atys, et ce qu'elle fait sortir.

Porté de `model/Meteo.kt` et de `EntityParser.parseWeather` du portage Android.

La météo est **calculée** par le jeu à partir du jour et de l'heure, non
mesurée : d'où la possibilité de la demander quarante cycles à l'avance, et de
tracer une prévision qui ne devine rien. `weather.php` ne demande aucune clé.

Deux constantes gouvernent tout le reste : une heure d'Atys dure trois minutes
réelles — mesuré sur l'API, et confirmé par le code du jeu (`ATYS_HOUR = 3`) —
et un cycle météo couvre trois heures d'Atys. Se tromper là-dessus rend tout
compte à rebours faux d'un facteur trois, ce qui est pire que de ne rien
afficher.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from . import armory, forage as _forage, gisements as _gisements

#: Heures d'Atys dans un cycle météo.
HEURES_PAR_CYCLE = 3

#: Minutes réelles pour une heure d'Atys. Mesuré sur l'API, et confirmé par le
#: code du jeu (`ATYS_HOUR = 3`).
MINUTES_PAR_HEURE_ATYS = 3

#: Durée réelle d'un cycle, en minutes.
MINUTES_PAR_CYCLE = 9

#: Les quatre saisons, dans l'ordre où l'API les numérote.
SAISONS = ("PRINTEMPS", "ETE", "AUTOMNE", "HIVER")

#: Les trois qualités qu'un gisement des Primes rend, de la meilleure à la
#: moindre. L'ordre compte : une zone annonce la première qu'elle a à offrir.
SUPREME, EXCELLENTE, CHOIX = "supreme", "excellente", "choix"
QUALITES = (SUPREME, EXCELLENTE, CHOIX)

#: Ces mêmes qualités telles que `gisements.py` les nomme. Le choix n'a pas de
#: carte : ses gisements ne sont relevés nulle part.
#:
#: Le relevé des positions ne connaît que deux qualités, et il place ses
#: excellentes sur les **continents** — voir `positions_des_primes`, qui fait
#: le tri.
QUALITE_GISEMENT = {SUPREME: "supreme", EXCELLENTE: "excellent", CHOIX: ""}

#: Les seuils du jeu, qui découpent les quatre conditions de gisement.
SEUILS = (0.1666, 0.5, 0.8333)

#: Zone du relevé → continent interrogé pour la météo. Les quatre zones des
#: Primes partagent deux continents seulement, et rendent la même série : c'est
#: vérifié sur quarante cycles.
CONTINENT_DE_ZONE = {
    "Sources Interdites": "sources",
    "Terre de la Continuité": "terre",
    "Cité Engloutie": "terre",
    "Profondeurs Interdites": "terre",
}


@dataclass(frozen=True)
class Meteo:
    """La météo d'un continent, pour un cycle donné."""

    cycle: int
    condition: str          #: worst, bad, good, best — la condition de gisement
    value: float            #: humidité, de 0 à 1
    text: str               #: clé de traduction du jeu : uiFair, uiRainy…


@dataclass(frozen=True)
class MeteoAtys:
    """Un relevé complet : la saison, le cycle en cours, et chaque continent.

    Le relevé porte l'instant où il a été pris. Le temps d'Atys avançant à
    cadence fixe — une heure pour trois minutes réelles —, on sait donc le
    faire avancer soi-même : `a_present()` rend le même relevé, recalé sur
    maintenant, **sans rien redemander à l'API**. Les quarante cycles reçus
    couvrent six heures ; il n'y a aucune raison de les redemander toutes les
    minutes pour voir un trait bouger.
    """

    cycle_courant: int
    #: L'heure d'Atys en cours, décimales comprises. Un cycle couvre trois
    #: heures : la partie fractionnaire dit donc où l'on en est **dans** le
    #: cycle, et c'est d'elle que dépendent les comptes à rebours comme la place
    #: du trait « maintenant » sur la courbe.
    heure_atys: float
    saison: int             #: 0 printemps … 3 hiver ; -1 si le temps n'a pas répondu
    continents: dict = field(default_factory=dict)
    #: Horloge monotone au moment du relevé. Monotone et non horloge murale :
    #: un changement d'heure ou une mise à l'heure réseau ferait sauter la
    #: seconde, et le graphique avec.
    pris_a: float = field(default_factory=time.monotonic)

    def a_present(self) -> "MeteoAtys":
        """Le même relevé, recalé sur l'instant présent.

        Une heure d'Atys dure trois minutes réelles : les secondes écoulées
        depuis le relevé se convertissent donc directement en heures d'Atys.
        Rien n'est redemandé — la série des cycles ne change pas, seul le
        curseur qui la parcourt avance.
        """
        ecoulees = max(0.0, time.monotonic() - self.pris_a)
        heure = self.heure_atys + ecoulees / (60.0 * MINUTES_PAR_HEURE_ATYS)
        return MeteoAtys(cycle_courant=int(heure // HEURES_PAR_CYCLE),
                         heure_atys=heure, saison=self.saison,
                         continents=self.continents, pris_a=self.pris_a)

    @property
    def avancement_du_cycle(self) -> float:
        """Avancement dans le cycle en cours, de 0 à 1."""
        return min(1.0, max(0.0, self.heure_atys / HEURES_PAR_CYCLE - self.cycle_courant))

    @property
    def heure_du_jour(self) -> int:
        """L'heure d'Atys du jour, de 0 à 23 — elle fait le jour et la nuit."""
        return int(self.heure_atys) % 24

    @property
    def nuit(self) -> bool:
        return est_la_nuit(self.heure_du_jour)

    @property
    def saison_cle(self) -> str:
        return SAISONS[self.saison] if 0 <= self.saison < 4 else ""

    def cycles_des_primes(self) -> list[Meteo]:
        """La série que partagent les quatre zones des Primes."""
        return self.continents.get(next(iter(CONTINENT_DE_ZONE.values())), [])

    def maintenant(self) -> Meteo | None:
        cycles = self.cycles_des_primes()
        for m in cycles:
            if m.cycle == self.cycle_courant:
                return m
        return cycles[0] if cycles else None

    def minutes_avant(self, cycle: int) -> int:
        """Minutes réelles avant le début d'un cycle à venir.

        Compter les cycles pleins surestimait l'attente de neuf minutes au
        pire : quand on regarde, on est déjà quelque part **dans** le cycle en
        cours."""
        ecart = cycle - self.cycle_courant - self.avancement_du_cycle
        return max(0, int(ecart * MINUTES_PAR_CYCLE))


def est_la_nuit(heure_du_jour: int) -> bool:
    """Il fait nuit sur Atys de 22 h à 3 h.

    Bornes relevées sur le calendrier d'Atys de Ballistic Mystix, qui ombre
    cette plage sur son graphique : c'est la même que celle qui décide des
    matières excellentes de nuit."""
    return heure_du_jour >= 22 or heure_du_jour < 3


def parse_weather(brut: bytes | str) -> MeteoAtys:
    """Le flux JSON de `weather.php` → un relevé.

    Le document est en JSON là où tout le reste de l'API est en XML."""
    if isinstance(brut, bytes):
        brut = brut.decode("utf-8", "replace")
    racine = json.loads(brut)
    if racine.get("errors"):
        raise ValueError(f"météo : {racine['errors']}")
    cycle = int(racine.get("cycle", 0))
    # `hour` est l'heure d'Atys en cours, avec ses décimales : 104011.496 au
    # cycle 34670 veut dire qu'on est à la moitié du cycle.
    try:
        heure = float(racine.get("hour", cycle * HEURES_PAR_CYCLE))
    except (TypeError, ValueError):
        heure = cycle * float(HEURES_PAR_CYCLE)
    continents = {}
    for nom, par_cycle in (racine.get("continents") or {}).items():
        serie = []
        for entree in (par_cycle or {}).values():
            try:
                serie.append(Meteo(
                    cycle=int(entree.get("cycle", 0)),
                    condition=str(entree.get("condition", "")),
                    value=float(entree.get("value", 0.0)),
                    text=str(entree.get("text", "")),
                ))
            except (TypeError, ValueError):
                continue
        continents[nom] = sorted(serie, key=lambda m: m.cycle)
    return MeteoAtys(cycle_courant=cycle, heure_atys=heure, saison=-1,
                     continents=continents)


#: Le temps qu'il fait, en français. Le jeu ne rend que sa clé.
#:
#: Les quatre premières sont les seules que l'API emploie réellement : relevé
#: sur les dix continents et quatre-vingts cycles, elle ne rend que `uiFair`,
#: `uiRainy`, `uiSapThundery` et `uiThundery`. Les autres sont gardées parce que
#: le client du jeu les connaît, et qu'une saison ou une région pourrait les
#: sortir un jour.
_TEMPS = {
    "uiFair": "Beau",
    "uiRainy": "Pluie",
    "uiThundery": "Orage",
    # L'orage de sève : la pluie de sève d'Atys, qui n'a pas d'équivalent
    # terrestre. « Orage » seul se confondrait avec le précédent.
    "uiSapThundery": "Orage de sève",
    "uiStormy": "Tempête",
    "uiSnowy": "Neige",
    "uiWindy": "Vent",
    "uiFoggy": "Brouillard",
    "uiCloudy": "Nuageux",
}


def texte_meteo(cle: str) -> str:
    """Le temps qu'il fait, en français. Le jeu ne rend que sa clé."""
    # Une clé inconnue vaut mieux affichée que remplacée par un blanc : elle dit
    # au moins qu'il se passe quelque chose, et se traduira le jour où on la
    # rencontre.
    return _TEMPS.get(cle, cle.removeprefix("ui"))


#: Le nom de chaque qualité de gisement, celui des foreuses.
#:
#: **« XL » et non « excellente ».** « Excellente » nomme aussi une bande
#: d'humidité — le temps le plus sec, sous 16,6 % — et l'écran écrivait le mot
#: deux fois de suite pour deux choses sans rapport : « sort suprême et
#: excellente », puis « excellente dans 1 h 08 », qui parlait de la météo.
#: « XL » est le mot du relevé, celui des onglets de xiom.be/forage, et il ne
#: désigne jamais que la matière.
MOT_QUALITE = {SUPREME: "suprême", EXCELLENTE: "XL", CHOIX: "choix"}


def mot_qualite(qualite: str | None) -> str:
    """La qualité d'un gisement, telle qu'on l'écrit en tête d'une colonne.

    `None` n'est pas une qualité : c'est l'aveu que la guilde n'a pas encore
    testé ce créneau dans cette zone. Le dire vaut mieux que laisser croire
    qu'il ne sort rien."""
    if qualite is None:
        return "Pas encore relevé"
    mot = MOT_QUALITE.get(qualite, qualite or "")
    # Et non `.capitalize()`, qui rendrait « Xl ».
    return mot[:1].upper() + mot[1:]


def enumere_qualites(qualites) -> str:
    """« suprême », « suprême et XL », « suprême, XL et choix ».

    La ligne du haut n'annonçait que la meilleure qualité en vue. Par temps
    mauvais, elle écrivait « sort suprême » pour une matière, en taisant les
    quinze excellentes de la même zone — celles qu'on irait justement forer
    faute de mieux.
    """
    mots = [MOT_QUALITE.get(q, q) for q in qualites]
    if len(mots) <= 1:
        return mots[0] if mots else ""
    return ", ".join(mots[:-1]) + " et " + mots[-1]


def texte_condition(condition: str) -> str:
    """La condition de gisement, en français."""
    return {"best": "Excellente", "good": "Bonne",
            "bad": "Mauvaise", "worst": "Exécrable"}.get(condition.lower(), condition)


def duree(minutes: int, unite: bool = False) -> str:
    """« 27 min », « 1 h 12 », « 4 j 4 h 43 » — un compte à rebours se lit.

    **Les jours se comptent à part passé vingt-quatre heures.** « Hiver dans
    100 h 43 min » oblige à poser une division pour savoir s'il faut s'y
    préparer ce soir ou la semaine prochaine ; « 4 j 4 h 43 min » se lit. Une
    saison d'Atys dure quatre jours et demi réels, c'est donc le cas courant
    de la barre du haut, pas une extrémité.

    `unite` écrit « 1 h 12 min » plutôt que « 1 h 12 ». La forme courte va bien
    aux petites attentes de l'écran météo, où l'heure est rare et le contexte
    proche ; passé la journée, « 83 h 23 » se lit comme une heure de la
    journée, et il faut le mot pour lever le doute.
    """
    if minutes <= 0:
        # À cheval sur la bascule, l'arrondi rendait « dans 0 min », qui se lit
        # comme une panne plutôt que comme une imminence.
        return "moins d'une minute"
    if minutes < 60:
        return f"{minutes} min"
    fin = " min" if unite else ""
    heures, reste = divmod(minutes, 60)
    if heures < 24:
        return f"{heures} h {reste:02d}{fin}"
    jours, heures = divmod(heures, 24)
    return f"{jours} j {heures} h {reste:02d}{fin}"


def moment_du_changement(minutes: float, maintenant=None) -> str:
    """Quand tombe une échéance : « demain à 09:12 », « le 15/09 à 09:12 ».

    **Un compte à rebours ne se planifie pas.** « dans 21 h 47 » dit bien
    l'attente, mais pour savoir si l'on sera devant son écran il faut poser
    l'addition — et une saison peut changer jusqu'à quatre jours et demi plus
    tard. L'heure du calendrier répond sans calcul ; le compte à rebours reste
    à côté, pour l'imminence.

    Le jour se dit en mots tant qu'il en existe un : « aujourd'hui » et
    « demain » se lisent plus vite qu'une date, et ce sont les deux cas qui
    intéressent vraiment.
    """
    maintenant = maintenant or datetime.now()
    quand = maintenant + timedelta(minutes=max(0.0, minutes))
    heure = quand.strftime("%H:%M")
    # Des dates civiles, et non un nombre d'heures divise par vingt-quatre :
    # a 23 h 50, « dans 20 min » tombe demain, ce qu'un quotient ne voit pas.
    jours = (quand.date() - maintenant.date()).days
    if jours <= 0:
        return f"aujourd'hui à {heure}"
    if jours == 1:
        return f"demain à {heure}"
    return quand.strftime("le %d/%m à ") + heure


def nom_saison(index: int) -> str:
    return ("Printemps", "Été", "Automne", "Hiver")[index] if 0 <= index < 4 else "?"

#: Le dossier des symboles de familles, à côté du paquet.
#:
#: Les images sont dans `zyroom/symboles/`, que le Makefile recopie avec le
#: reste du paquet : rien à déclarer pour qu'elles suivent l'installation.
_SYMBOLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "symboles")


def symbole(groupe: str) -> str | None:
    """Le chemin du symbole d'une famille de matières, ou None.

    Ce sont les images du jeu — une coquille pour la carapace, une goutte pour
    la sève —, relevées une fois par `table_armory.py` et embarquées : rien ne
    se télécharge à l'affichage du tableau.

    La correspondance vit dans `armory.py`, qui est produit par cet outil ;
    cette fonction, non — un fichier généré perd à chaque régénération ce qu'on
    y ajoute à la main. Une famille que Ryzom ajouterait n'aurait pas encore de
    symbole : le tableau l'affichera sans, plutôt que de tomber.
    """
    icone = armory.SYMBOLES.get(groupe)
    if not icone:
        return None
    chemin = os.path.join(_SYMBOLES_DIR, icone + ".png")
    return chemin if os.path.isfile(chemin) else None


#: Les zones des Primes, dans l'ordre où l'écran les montre.
#:
#: Tirées de la table écrite plus haut, et non de celle que `pop.py` porte
#: aussi : deux copies de la même correspondance finiraient par diverger, et
#: c'est celle-ci que le reste du module emploie déjà.
ZONES = list(CONTINENT_DE_ZONE)


def _creneau(saison: int, condition: str) -> tuple[str, str]:
    """Le couple (saison, condition) sous lequel les tables du tutoriel rangent.

    La saison arrive numérotée par l'API, la condition en minuscules : les deux
    tables, elles, sont écrites en clair et en capitales.
    """
    cle = SAISONS[saison] if 0 <= saison < len(SAISONS) else ""
    return cle, condition.upper()


def qualite_de(zone: str, famille: str, matiere: str,
               saison: int, condition: str) -> str | None:
    """La qualité que rend une matière dans une zone, à cet instant.

    **La zone compte.** C'était l'erreur d'avant : une seule table pour les
    quatre, alors qu'au printemps par temps mauvais la Cité Engloutie sort une
    suprême que la Terre de la Continuité n'a pas.

    Rend `None` quand aucune des trois tables ne dit rien de ce créneau : la
    cartographie de la guilde est un chantier en cours, et un silence n'est pas
    un « rien ne sort ». Le suprême, lui, est complet — un `None` veut donc
    toujours dire « pas de suprême, et le reste n'a pas été relevé ».
    """
    creneau = _creneau(saison, condition)
    couple = (famille, matiere)
    for qualite, table in ((SUPREME, _forage.SUPREMES),
                           (EXCELLENTE, _forage.EXCELLENTES),
                           (CHOIX, _forage.CHOIX)):
        if creneau in table.get(zone, {}).get(couple, ()):
            return qualite
    return None


def positions_des_primes(qualite: str, famille: str, matiere: str) -> list:
    """Où sort cette matière **dans les Primes**, et nulle part ailleurs.

    Le relevé des positions couvre tout Atys, et il ne distingue que deux
    qualités : « supreme » et « excellent ». Ses suprêmes sont bien celles des
    Primes — cent quatre-vingts points, tous dans les quatre zones. Ses
    excellentes, non : cent cinquante-sept de ses cent cinquante-huit points
    sont au Gouffre d'Ichor, à la Porte des Vents ou à la Forêt Insaisissable,
    sur les continents.

    D'où le filtre. Cliquer « Motega » sous l'XL des Sources Interdites
    ouvrait une carte montrant trois gisements de la Porte des Vents, de la
    Forêt Insaisissable et de la Porte de l'Obscurité : ni la bonne zone, ni
    même de la q250. Une matière dont on ne connaît aucune position dans les
    Primes rend une liste vide, et son nom reste du texte — rien n'invite
    alors à cliquer sur ce qui ne répondrait pas.
    """
    nom = QUALITE_GISEMENT.get(qualite, "")
    if not nom:
        return []
    return [point for point in _gisements.points(nom, famille, matiere)
            if point[2] in ZONES]


def sorties_de(saison: int, zone: str,
               condition: str) -> list[tuple[str, dict]]:
    """Tout ce qui sort dans une zone à ce créneau, qualité par qualité.

    Rend `[(qualité, {famille: [matières]}), …]`, la meilleure qualité
    d'abord, et une liste vide quand la guilde n'a rien relevé là.

    **Pourquoi plusieurs et non la seule meilleure.** La fonction n'en rendait
    qu'une, du temps où l'excellente était déduite des fourchettes d'humidité
    et ne valait rien : la masquer derrière le suprême ne coûtait pas cher.
    Maintenant qu'elle est relevée sur le terrain comme lui, s'en tenir à la
    meilleure jette l'essentiel — aux Sources Interdites, en automne par temps
    mauvais, une seule suprême cacherait quinze excellentes. Chaque bloc porte
    le nom de sa qualité, ce qui répond à la crainte d'origine : rien ne se
    lit comme suprême sans l'être.
    """
    creneau = _creneau(saison, condition)
    trouve = []
    for qualite, table in ((SUPREME, _forage.SUPREMES),
                           (EXCELLENTE, _forage.EXCELLENTES),
                           (CHOIX, _forage.CHOIX)):
        groupes: dict[str, list[str]] = {}
        for (famille, matiere), creneaux in table.get(zone, {}).items():
            if creneau in creneaux:
                groupes.setdefault(famille, []).append(matiere)
        if groupes:
            trouve.append((qualite, {f: sorted(m)
                                     for f, m in groupes.items()}))
    return trouve


def sortie_de(saison: int, zone: str, condition: str) -> tuple[str | None, dict]:
    """La meilleure qualité qu'une zone ait à offrir à ce créneau.

    Rend `(qualité, {famille: [matières]})`, ou `(None, {})` quand la guilde
    n'a encore rien relevé pour ce créneau dans cette zone. C'est la réponse
    courte — « vaut-il mieux aller là ou ailleurs ? » ; `sorties_de` donne le
    détail que l'écran affiche.
    """
    sorties = sorties_de(saison, zone, condition)
    return sorties[0] if sorties else (None, {})


def prochaine_fenetre_supreme(releve: "MeteoAtys") -> "Meteo | None":
    """Le prochain cycle par temps exécrable — la fenêtre de forage du suprême.

    **Mesuré contre le tracker d'atys.us**, qui affiche le même compte à
    rebours : le 22 septembre 2026 à 14 h 22, il annonçait « Supremes Available
    in 2h 48m », et la prévision du jeu plaçait le prochain cycle exécrable à
    17 h 09 — la même minute. Son « bonnes conditions pour le suprême », c'est
    donc l'humidité au-dessus de 83,4 %, et rien d'autre.

    Ce n'est pas la même chose que la fourchette d'un gisement, qui dit où on
    le trouve : à tout instant la moitié des matières d'une zone est dans sa
    fourchette, et un compte à rebours bâti là-dessus ne s'allumerait jamais.
    La grande fenêtre, celle qu'on attend, c'est l'exécrable.

    Rend `None` si aucun cycle exécrable n'est en vue : la prévision du jeu ne
    porte que six heures, et on ne devine pas au-delà.
    """
    for cycle in releve.cycles_des_primes():
        if cycle.cycle > releve.cycle_courant and cycle.condition.lower() == "worst":
            return cycle
    return None


def fin_fenetre_supreme(releve: "MeteoAtys") -> float | None:
    """Minutes réelles avant que la fenêtre en cours ne se referme.

    Une fenêtre dure rarement plus d'un cycle — neuf minutes réelles —, mais
    elle peut en enchaîner deux : on cherche donc le premier cycle à venir qui
    ne soit pas exécrable, et non « le cycle suivant ».

    Le compte part de l'instant présent, pas du début du cycle : à la sixième
    minute d'une fenêtre de neuf, il reste trois minutes, et c'est cela qu'une
    foreuse veut lire.

    Rend `None` si la prévision s'arrête sans jamais quitter l'exécrable — on
    ne sait alors pas dire jusqu'à quand.
    """
    for cycle in sorted(releve.cycles_des_primes(), key=lambda c: c.cycle):
        if cycle.cycle > releve.cycle_courant \
                and cycle.condition.lower() != "worst":
            return releve.minutes_avant(cycle.cycle)
    return None
