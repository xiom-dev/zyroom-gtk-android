package net.ryzom.zyroom.model

/**
 * Un avant-poste et la guilde qui le tient.
 *
 * L'API ne dit d'un avant-poste que son identifiant — `fyros_outpost_04` — et
 * la guilde à qui il appartient. Ni le niveau, ni la production, ni les
 * horaires d'attaque : rien de tout cela n'est exposé. Le nom lisible, « Ferme
 * de Malmontagne », vient du pack du client, sous la clé `<code>.outpost`.
 *
 * Le peuple se lit dans le code lui-même, avant le premier tiret bas.
 */
data class Outpost(
    val code: String,
    val guild: String,
    /** Identifiant d'emblème, pour `guild_icon.php`. */
    val icon: String = "",
) {
    /** « fyros », « matis », « tryker », « zorai »… */
    val people: String get() = code.substringBefore('_', code)

    /** La clé sous laquelle le pack range son nom. */
    val nameKey: String get() = "$code.outpost"
}
