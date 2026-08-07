package net.ryzom.zyroom.model

/**
 * Modèle de domaine Ryzom, porté de `zyroom/models.py` (lui-même porté du
 * Delphi `UnitRyzom.pas`).
 *
 * Les valeurs entières des énumérations doivent rester dans cet ordre : elles
 * partent telles quelles dans les appels à `item_icon.php` et servent à nommer
 * les fichiers de cache.
 */

enum class ItemColor(val value: Int) {
    RED(0), BEIGE(1), GREEN(2), TURQUOISE(3),
    BLUE(4), PURPLE(5), WHITE(6), BLACK(7), NONE(8);

    companion object {
        /** Équivalent de `to_item_color` : entier du XML, NONE à défaut. */
        fun from(raw: String?): ItemColor =
            entries.firstOrNull { it.value == raw?.trim()?.toIntOrNull() } ?: NONE
    }
}

/** Type d'item, dans l'ordre du `TItemType` d'origine. */
enum class ItemType {
    ANIMAL_MAT, NATURAL_MAT, SYSTEM_MAT, CATA, EQUIPMENT, TELEPORTER, OTHER
}

/** Couleur de l'armure de réfugié, donnée par la sixième lettre de la fiche. */
private val REFUGEE_COLOUR = mapOf(
    'a' to ItemColor.BLACK, 'e' to ItemColor.BEIGE, 'g' to ItemColor.GREEN,
    'r' to ItemColor.RED, 't' to ItemColor.TURQUOISE, 'u' to ItemColor.BLUE,
    'v' to ItemColor.PURPLE, 'w' to ItemColor.WHITE,
)

/**
 * Un item d'inventaire, réduit à ce que l'écran montre.
 *
 * Les caractéristiques de craft — protections, résistances, amplis — viendront
 * avec l'écran de détail ; elles ne servent pas à la grille.
 */
data class Item(
    val sheet: String = "",
    val id: String = "",
    val slot: Int = 0,
    val color: ItemColor = ItemColor.NONE,
    val quality: Int = 0,
    val stack: Int = 0,
    val locked: Boolean = false,
    val sap: Boolean = false,
    val destroyed: Boolean = false,
    val hp: Int = 0,
    val volume: Double = 0.0,
    val type: ItemType = ItemType.OTHER,
    val price: Double = 0.0,
    val continent: String = "",
) {
    /** Couleur retenue pour l'affichage, cas de l'armure de réfugié compris. */
    val displayColor: ItemColor
        get() = when {
            color != ItemColor.NONE -> color
            sheet.startsWith("icra") && sheet.length >= 6 ->
                REFUGEE_COLOUR[sheet[5]] ?: ItemColor.NONE
            else -> ItemColor.NONE
        }
}

/** Un contenant : sac, appartement, coffre de guilde, monture… */
data class Inventory(
    val key: String,
    val label: String,
    val items: List<Item> = emptyList(),
    val capacity: Int = 0,
    /** Ce qui les réunit sous un même bouton : « Mektoub », « Zig », « Coffres »… */
    val group: String = "",
    /**
     * Contenant montré vide (cf. HIDDEN_CHESTS). Il est exclu des instantanés,
     * sans quoi le journal des mouvements trahirait ce qu'on masque : passer
     * d'un état où le coffre était garni à un état vide produirait un retrait
     * par objet, nommément.
     */
    val masked: Boolean = false,
) {
    val totalVolume: Double get() = items.sumOf { it.volume }
}

/** Un personnage ou une guilde, avec ses inventaires. */
data class Entity(
    val kind: Kind,
    val id: String,
    val name: String,
    val shard: String = "",
    val guild: String = "",
    val dappers: Long = 0,
    /** Date de création du document par l'API, en secondes Unix. */
    val created: Long = 0,
    /** Date jusqu'à laquelle l'API servira ce même document. */
    val cachedUntil: Long = 0,
    val inventories: List<Inventory> = emptyList(),
) {
    enum class Kind { CHARACTER, GUILD }

    /**
     * Vrai quand l'API a de quoi rendre autre chose que ce document.
     *
     * C'est elle qui décide de la fraîcheur : tant que `cachedUntil` n'est pas
     * dépassé, la rappeler rend le même XML. La version GTK l'ignore et
     * redemande toutes les quinze minutes ; ici on s'en sert.
     */
    fun isStale(nowSeconds: Long): Boolean = nowSeconds >= cachedUntil
}
