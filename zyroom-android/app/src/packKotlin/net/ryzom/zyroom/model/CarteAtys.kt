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
        Region("matis_island_1", 14080, 15360, -1600, -320, -552, 1740),
        Region("kitiniere", 1760, 3040, -17440, -16160, -13512, -10228),
        Region("bagne", 480, 1600, -11360, -9760, -8480, -6020),
        Region("sources", 2560, 3840, -11360, -9760, 1284, -2760),
        Region("undernexus", 7680, 11040, -9600, -8480, -808, -424),
        Region("newbieland", 8160, 11360, -12320, -10240, -7660, -10040),
        Region("terre", 160, 3040, -15840, -13120, -2796, -8160),
        Region("nexus", 7680, 11040, -9440, -5920, -808, -424),
        Region("route_gouffre", 5440, 7360, -16960, -9600, -936, -5456),
        Region("fyros", 15840, 20320, -27040, -23840, 12336, -23204),
        Region("zorai", 6880, 12480, -5920, -960, 6108, 7880),
        Region("tryker", 13760, 20000, -34880, -29440, 5460, -20380),
        Region("matis", 320, 6240, -7840, -320, -8480, 396),
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
