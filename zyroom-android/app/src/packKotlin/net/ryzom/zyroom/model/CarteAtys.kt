package net.ryzom.zyroom.model

// Fichier produit par outils/carte_atys.py — ne pas modifier à la main.

/**
 * Où tombe un point d'Atys sur la carte embarquée.
 *
 * Les positions du flux — `<position x="10328" y="-2316"/>` — sont **locales à
 * la région** où se trouve le personnage : la carte du monde est un assemblage,
 * et chaque région y est posée à sa place. Un repère unique plaçait donc
 * correctement ce qui était dans une région, et n'importe où ailleurs le reste.
 *
 * La plus petite région qui contient le point l'emporte : le Nexus est inclus
 * dans les bornes matis, et il est plus précis.
 */
object CarteAtys {
    const val LARGEUR = 4000
    const val HAUTEUR = 3000
    const val UNITES_PAR_PIXEL = 5.0f

    /** Une région, ses bornes en coordonnées de jeu, et son origine. */
    data class Region(
        val nom: String,
        val x1: Int, val x2: Int, val y1: Int, val y2: Int,
        val ox: Int, val oy: Int,
    ) {
        fun contient(x: Int, y: Int) = x in x1..x2 && y in y1..y2
    }

    /** De la plus petite à la plus grande : la première qui contient gagne. */
    val REGIONS = listOf(
        Region("bagne", 467, 1611, -11320, -9742, -8473, -6027),
        Region("sources", 2445, 3901, -11437, -9626, 1287, -2764),
        Region("nexus", 7789, 9786, -8346, -6054, -804, -424),
        Region("terre", 122, 3062, -15856, -13100, -2792, -8166),
        Region("route_gouffre", 5274, 7371, -16983, -9423, -933, -5459),
        Region("fyros", 15753, 26084, -27145, -23672, 12337, -23208),
        Region("zorai", 6633, 19068, -5767, -496, 6113, 7877),
        Region("tryker", 13428, 27513, -35219, -29117, 5462, -20384),
        Region("matis", 30, 18736, -7995, 211, 6111, 7876),
    )

    /** La région d'un point, ou rien si aucune ne le couvre. */
    fun regionDe(x: Int, y: Int): Region? = REGIONS.firstOrNull { it.contient(x, y) }

    /** Le point du jeu, en pixels de la carte, ou rien s'il n'est sur aucune. */
    fun pixel(x: Int, y: Int): Pair<Float, Float>? {
        val region = regionDe(x, y) ?: return null
        val px = (x - region.ox) / UNITES_PAR_PIXEL
        val py = (region.oy - y) / UNITES_PAR_PIXEL
        if (px !in 0f..LARGEUR.toFloat() || py !in 0f..HAUTEUR.toFloat()) return null
        return px to py
    }

    /** Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien. */
    fun contient(x: Int, y: Int): Boolean = pixel(x, y) != null
}
