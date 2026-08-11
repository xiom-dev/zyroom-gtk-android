package net.ryzom.zyroom.model

/**
 * Une bête du joueur : sa monture, ses mektoubs de bât, ses zigs.
 *
 * Le flux du personnage donne leur position — `<position x="10328" y="-2316"/>`
 * — et c'est la seule chose que l'API sache dire d'un animal qu'on ne retrouve
 * plus. Un mektoub laissé en pleine terre y reste, et son propriétaire finit
 * par oublier où.
 */
data class Bete(
    /** Le nom donné en jeu, déjà décodé. Vide si la bête n'en a pas. */
    val nom: String,
    /** L'étiquette de son inventaire : « Mektoub 2 », « Zig 1 ». */
    val etiquette: String,
    /**
     * `landscape` — dehors, sur la carte —, `stable` en écurie, `dead`…
     *
     * Seules celles qui sont dehors ont une position qui veuille dire quelque
     * chose ; une bête en écurie est là où on l'a rangée.
     */
    val statut: String,
    val x: Int,
    val y: Int,
    /**
     * Sa satiété. Une bête laissée dehors a faim, et finit par mourir de faim.
     *
     * L'échelle n'est pas documentée : les valeurs relevées vont de 54 à 933.
     * On la montre telle quelle plutôt que d'inventer un pourcentage.
     */
    val satiete: Double = 0.0,
) {
    /** Vrai si la bête est dehors, donc si sa position a un sens. */
    val dehors: Boolean get() = statut == "landscape"
}
