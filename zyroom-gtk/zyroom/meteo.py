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
from dataclasses import dataclass, field

from . import armory

#: Heures d'Atys dans un cycle météo.
HEURES_PAR_CYCLE = 3

#: Minutes réelles pour une heure d'Atys. Mesuré sur l'API, et confirmé par le
#: code du jeu (`ATYS_HOUR = 3`).
MINUTES_PAR_HEURE_ATYS = 3

#: Durée réelle d'un cycle, en minutes.
MINUTES_PAR_CYCLE = 9

#: Les quatre saisons, dans l'ordre où l'API les numérote.
SAISONS = ("PRINTEMPS", "ETE", "AUTOMNE", "HIVER")

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


def texte_condition(condition: str) -> str:
    """La condition de gisement, en français."""
    return {"best": "Excellente", "good": "Bonne",
            "bad": "Mauvaise", "worst": "Exécrable"}.get(condition.lower(), condition)


def duree(minutes: int) -> str:
    """« 27 min », « 1 h 12 » — un compte à rebours se lit, pas se calcule."""
    if minutes <= 0:
        # À cheval sur la bascule, l'arrondi rendait « dans 0 min », qui se lit
        # comme une panne plutôt que comme une imminence.
        return "moins d'une minute"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60} h {minutes % 60:02d}"


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
