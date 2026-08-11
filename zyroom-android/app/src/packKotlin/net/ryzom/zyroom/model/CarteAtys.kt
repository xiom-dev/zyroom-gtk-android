package net.ryzom.zyroom.model

// Fichier produit par outils/carte_atys.py — ne pas modifier à la main.

/**
 * Où tombe un point d'Atys sur la carte embarquée.
 *
 * Les positions du flux — `<position x="10328" y="-2316"/>` — sont en
 * coordonnées du monde. La carte les couvre de (6112, 7876) au coin haut-gauche
 * jusqu'à (26112, -7124) au coin
 * bas-droit, à raison de 5 unités de jeu par pixel.
 */
object CarteAtys {
    const val LARGEUR = 4000
    const val HAUTEUR = 3000
    const val UNITES_PAR_PIXEL = 5.0f
    const val X0 = 6112
    const val Y0 = 7876

    /** L'abscisse d'un point du jeu, en pixels de la carte. */
    fun x(x: Int): Float = (x - X0) / UNITES_PAR_PIXEL

    /** L'ordonnée d'un point du jeu. L'axe descend dans l'image, monte dans le jeu. */
    fun y(y: Int): Float = (Y0 - y) / UNITES_PAR_PIXEL

    /** Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien. */
    fun contient(x: Int, y: Int): Boolean =
        x(x) in 0f..LARGEUR.toFloat() && y(y) in 0f..HAUTEUR.toFloat()
}
