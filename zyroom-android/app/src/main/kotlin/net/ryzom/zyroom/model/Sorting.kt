package net.ryzom.zyroom.model

/**
 * Classement des objets pour l'affichage, porté de `zyroom/sorting.py`.
 *
 * Les sept catégories de l'original conviennent au calcul des volumes, pas au
 * rangement : dans un coffre de guilde, la moitié des objets tombent dans
 * « autre » et s'y perdent. Ce classement-ci est plus fin, et ne sert qu'à
 * l'affichage.
 *
 * Les matières premières viennent en tête et sont **réunies par matière**, du
 * plus bas niveau au plus haut : c'est ce qui montre d'un coup d'œil ce qu'on
 * possède d'une même matière.
 */
enum class Family(val label: String) {
    RAW_HARVESTED("Matières forées"),
    RAW_LOOTED("Matières de créature"),
    RAW_SYSTEM("Matières spéciales"),
    EQUIPMENT("Équipement"),
    TOOL("Outils"),
    CATALYST("Catalyseurs"),
    SAP_RECHARGE("Recharges de sève"),
    POTION("Potions"),
    FIREWORK("Feux d'artifice"),
    TELEPORT("Téléportation"),
    JOB_ITEM("Objets de métier"),
    COMPONENT("Composants"),
    EVENT("Événements"),
    OTHER("Divers");

    val raw: Boolean
        get() = this == RAW_HARVESTED || this == RAW_LOOTED || this == RAW_SYSTEM
}

// L'ordre compte : le premier motif qui correspond l'emporte.
private val PATTERNS: List<Pair<Regex, Family>> = listOf(
    Regex("^m0?\\d{3,4}") to Family.RAW_HARVESTED,
    Regex("^item_sap_recharge") to Family.SAP_RECHARGE,
    Regex("^conso_fireworks") to Family.FIREWORK,
    Regex("^(pvp_boost|ipoc|ipk)_?") to Family.POTION,
    Regex("^rpjobitem") to Family.JOB_ITEM,
    Regex("^compo_") to Family.COMPONENT,
    Regex("^event_") to Family.EVENT,
    Regex("^tp_ka") to Family.TELEPORT,
    Regex("^ic") to Family.EQUIPMENT,
)

/** Matière première : « m0497dxape01.sitem » — les chiffres nomment la matière. */
private val RAW_MATERIAL = Regex("^m0?(\\d{3,4})")

/** Famille d'un objet, d'après son type puis sa fiche. */
fun familyOf(item: Item): Family {
    when (item.type) {
        ItemType.ANIMAL_MAT -> return Family.RAW_LOOTED
        ItemType.NATURAL_MAT -> return Family.RAW_HARVESTED
        ItemType.SYSTEM_MAT -> return Family.RAW_SYSTEM
        ItemType.CATA -> return Family.CATALYST
        ItemType.TELEPORTER -> return Family.TELEPORT
        ItemType.EQUIPMENT -> return Family.EQUIPMENT
        ItemType.OTHER -> Unit
    }
    val sheet = item.sheet.lowercase()
    return PATTERNS.firstOrNull { (motif, _) -> motif.containsMatchIn(sheet) }
        ?.second ?: Family.OTHER
}

/** Identifiant de matière, pour réunir les qualités d'une même matière. */
fun materialKey(item: Item): String =
    RAW_MATERIAL.find(item.sheet.lowercase())?.groupValues?.get(1) ?: item.sheet

/** Les tris proposés à l'écran. */
enum class SortOrder(val label: String) {
    FAMILY("Famille"),
    NAME("Nom"),
    QUALITY("Qualité"),
    QUANTITY("Quantité"),
}

/**
 * Range une liste d'items.
 *
 * En tri par famille, les matières sont réunies par matière puis classées du
 * plus bas niveau au plus haut ; le reste est groupé par famille, puis par nom
 * et par qualité, si bien que deux objets identiques de qualités différentes
 * restent côte à côte.
 */
fun sortItems(items: List<Item>, order: SortOrder, nameOf: (Item) -> String): List<Item> =
    when (order) {
        SortOrder.FAMILY -> items.sortedWith(
            compareBy({ familyOf(it).ordinal },
                      { if (familyOf(it).raw) materialKey(it) else nameOf(it) },
                      { it.quality },
                      { nameOf(it) }))
        SortOrder.NAME -> items.sortedWith(compareBy({ nameOf(it) }, { -it.quality }))
        SortOrder.QUALITY -> items.sortedWith(compareByDescending<Item> { it.quality }
            .thenBy { nameOf(it) })
        SortOrder.QUANTITY -> items.sortedWith(compareByDescending<Item> { it.stack }
            .thenBy { nameOf(it) })
    }
