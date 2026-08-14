package net.ryzom.zyroom.model

/**
 * La météo d'un continent d'Atys, pour un cycle donné.
 *
 * Elle est **calculée** et non mesurée : le jeu la déduit du jour et de l'heure
 * d'Atys, si bien que l'API peut la donner quarante cycles à l'avance. C'est ce
 * qui rend un compte à rebours possible.
 */
data class Meteo(
    val cycle: Int,
    /** `worst`, `bad`, `good`, `best` — la condition de gisement. */
    val condition: String,
    /** Humidité, de 0 à 1. */
    val value: Double,
    /** Clé de traduction du jeu : `uiFair`, `uiRainy`… */
    val text: String,
) {
    val conditionMajuscule: String get() = condition.uppercase()
}

/**
 * Un relevé complet : la saison, le cycle en cours, et chaque continent.
 *
 * Le relevé porte l'instant où il a été pris. Le temps d'Atys avançant à
 * cadence fixe — une heure pour trois minutes réelles —, on sait donc le faire
 * avancer soi-même : `aPresent()` rend le même relevé recalé sur maintenant,
 * **sans rien redemander à l'API**. Les cycles reçus couvrent plusieurs heures ;
 * il n'y a aucune raison de les redemander toutes les minutes pour voir un
 * trait bouger.
 */
data class MeteoAtys(
    val cycleCourant: Int,
    /**
     * L'heure d'Atys en cours, décimales comprises.
     *
     * Un cycle couvre trois heures d'Atys : la partie fractionnaire dit donc où
     * l'on en est **dans** le cycle, et c'est d'elle que dépendent les comptes à
     * rebours comme la place du trait « maintenant » sur la courbe.
     */
    val heureAtys: Double,
    /** 0 printemps … 3 hiver ; -1 si le flux de temps n'a pas répondu. */
    val saison: Int,
    val continents: Map<String, List<Meteo>>,
    /**
     * Horloge monotone au moment du relevé, en millisecondes.
     *
     * Monotone et non horloge murale : une mise à l'heure réseau ou un
     * changement d'heure ferait sinon sauter le graphique.
     */
    val prisA: Long = System.nanoTime() / 1_000_000,
) {

    /**
     * Le même relevé, recalé sur l'instant présent.
     *
     * Une heure d'Atys dure trois minutes réelles : le temps écoulé depuis le
     * relevé se convertit donc directement en heures d'Atys. Rien n'est
     * redemandé — la série des cycles ne change pas, seul le curseur qui la
     * parcourt avance.
     */
    fun aPresent(maintenant: Long = System.nanoTime() / 1_000_000): MeteoAtys {
        val ecoulees = (maintenant - prisA).coerceAtLeast(0L) / 1000.0
        val heure = heureAtys + ecoulees / (60.0 * MINUTES_PAR_HEURE_ATYS)
        return copy(cycleCourant = (heure / HEURES_PAR_CYCLE).toInt(),
                    heureAtys = heure)
    }
    /** Avancement dans le cycle en cours, de 0 à 1. */
    val avancementDuCycle: Double
        get() = (heureAtys / HEURES_PAR_CYCLE - cycleCourant).coerceIn(0.0, 1.0)

    /** L'heure d'Atys du jour, de 0 à 23 — c'est elle qui fait le jour et la nuit. */
    val heureDuJour: Int get() = (heureAtys.toLong() % 24).toInt()

    /** Vrai s'il fait nuit sur Atys : les matières excellentes n'y sont pas les mêmes. */
    val nuit: Boolean get() = estLaNuit(heureDuJour)
}

/**
 * Il fait nuit sur Atys de 22 h à 3 h.
 *
 * Bornes relevées sur le calendrier d'Atys de Ballistic Mystix, qui ombre cette
 * plage sur son graphique : c'est la même que celle qui décide des matières
 * excellentes de nuit.
 */
fun estLaNuit(heureDuJour: Int): Boolean = heureDuJour >= 22 || heureDuJour < 3

/** Heures d'Atys dans un cycle météo. */
const val HEURES_PAR_CYCLE = 3

/**
 * Minutes réelles pour une heure d'Atys.
 *
 * Mesuré sur l'API, et confirmé par le code du jeu (`ATYS_HOUR = 3`).
 */
const val MINUTES_PAR_HEURE_ATYS = 3

/**
 * Le temps qu'il fait, en français. Le jeu ne rend que sa clé.
 *
 * Les quatre premières sont les seules que l'API emploie réellement : relevé
 * sur les dix continents et quatre-vingts cycles, elle ne rend que `uiFair`,
 * `uiRainy`, `uiSapThundery` et `uiThundery`. Les autres sont gardées parce que
 * le client du jeu les connaît, et qu'une saison ou une région pourrait les
 * sortir un jour.
 */
fun texteMeteo(cle: String): String = when (cle) {
    "uiFair" -> "Beau"
    "uiRainy" -> "Pluie"
    "uiThundery" -> "Orage"
    // L'orage de sève : la pluie de sève d'Atys, qui n'a pas d'équivalent
    // terrestre. « Orage » seul se confondrait avec le précédent.
    "uiSapThundery" -> "Orage de sève"
    "uiStormy" -> "Tempête"
    "uiSnowy" -> "Neige"
    "uiWindy" -> "Vent"
    "uiFoggy" -> "Brouillard"
    "uiCloudy" -> "Nuageux"
    // Une clé inconnue vaut mieux affichée que remplacée par un blanc : elle
    // dit au moins qu'il se passe quelque chose, et se traduira le jour où on
    // la rencontre.
    else -> cle.removePrefix("ui")
}

/** La condition de gisement, en français. */
fun texteCondition(condition: String): String = when (condition.lowercase()) {
    "best" -> "Excellente"
    "good" -> "Bonne"
    "bad" -> "Mauvaise"
    "worst" -> "Exécrable"
    else -> condition
}

/**
 * Les quatre saisons, dans l'ordre où l'API les numérote.
 *
 * `time.php` rend `season` de 0 à 3 ; le classeur de la guilde nomme ses
 * onglets dans le même ordre.
 */
val SAISONS = listOf("PRINTEMPS", "ETE", "AUTOMNE", "HIVER")

fun nomSaison(index: Int): String = when (index) {
    0 -> "Printemps"
    1 -> "Été"
    2 -> "Automne"
    3 -> "Hiver"
    else -> "?"
}

/**
 * Durée réelle d'un cycle météo, en minutes.
 *
 * Une heure d'Atys dure trois minutes réelles — mesuré sur l'API, et confirmé
 * par le code du jeu (`ATYS_HOUR = 3`) — et un cycle météo vaut trois heures
 * d'Atys. Se tromper là-dessus rend tout compte à rebours faux d'un facteur
 * trois, ce qui est pire que de ne rien afficher.
 */
const val MINUTES_PAR_CYCLE = 9

/**
 * Ce qui peut sortir ici et maintenant.
 *
 * La table ne vient plus du classeur de la guilde : elle se déduit du relevé de
 * Ryzom Armory pour le couple saison × zone, et des fourchettes d'humidité du
 * tracker d'atys.us pour la condition. Elle est complète — les quatre
 * conditions sont remplies partout — donc un vide ne veut pas dire « pas encore
 * relevé », il signalerait une table mal fabriquée.
 *
 * Ce qui sort est **la moitié** de ce que la saison peut donner : chaque
 * gisement occupe deux des quatre bandes d'humidité. Comparé au relevé
 * d'Armory, qui donne la saison entière sans notion de météo, il manquera
 * toujours l'autre moitié — ce n'est pas un trou.
 */
fun popDe(saison: Int, zone: String, condition: String): Map<String, List<String>> =
    POP[SAISONS.getOrNull(saison)]?.get(zone)?.get(condition.uppercase()).orEmpty()

/** Les zones des Primes, dans l'ordre où l'écran les montre. */
val ZONES: List<String> get() = CONTINENT_DE_ZONE.keys.toList()
