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

/** Un relevé complet : la saison, le cycle en cours, et chaque continent. */
data class MeteoAtys(
    val cycleCourant: Int,
    /** 0 printemps … 3 hiver ; -1 si le flux de temps n'a pas répondu. */
    val saison: Int,
    val continents: Map<String, List<Meteo>>,
)

/** Le temps qu'il fait, en français. Le jeu ne rend que sa clé. */
fun texteMeteo(cle: String): String = when (cle) {
    "uiFair" -> "Beau"
    "uiRainy" -> "Pluie"
    "uiStormy" -> "Orage"
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

/** Ce qui peut sortir ici et maintenant, d'après le relevé de la guilde. */
fun popDe(saison: Int, zone: String, condition: String): Map<String, List<String>> =
    POP[SAISONS.getOrNull(saison)]?.get(zone)?.get(condition.uppercase()).orEmpty()

/** Les zones du relevé, dans l'ordre du classeur. */
val ZONES: List<String> get() = CONTINENT_DE_ZONE.keys.toList()
