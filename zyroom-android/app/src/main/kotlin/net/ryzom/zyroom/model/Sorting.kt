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

/**
 * Comparaison des noms à la française.
 *
 * L'ordre naturel des chaînes est celui des codes de caractères : les
 * majuscules avant toutes les minuscules, et les lettres accentuées après le
 * Z. Le jeu, lui, nomme sans constance — « Bracelet matis » avec une capitale,
 * « bracelet zoraï » sans — si bien qu'un tri brut séparait deux bijoux d'une
 * même parure de toute la longueur de la liste, et renvoyait « Épée Zo'Kovan »
 * tout à la fin.
 *
 * Le classeur du français range comme un dictionnaire : la casse et les
 * accents ne départagent que des mots par ailleurs identiques.
 */
private val CLASSEUR: Comparator<String> =
    java.text.Collator.getInstance(java.util.Locale.FRENCH).apply {
        strength = java.text.Collator.SECONDARY
    }.let { collator -> Comparator { a, b -> collator.compare(a, b) } }

/**
 * Pièces d'une tenue et bijoux d'une parure, dans l'ordre où on les porte.
 *
 * Une fiche d'armure se lit `ic` + peuple + `a` + poids + pièce + qualité de
 * fabrication : `icmahb_3` est la botte (`b`) d'une tenue lourde (`h`) matis.
 * Un bijou suit la même règle avec `j` : `iczja` est l'anneau de cheville
 * zoraï. Retirer la lettre de pièce donne donc la tenue elle-même.
 */
private val ARMURE = Regex("^(ic[a-z]a[a-z])([a-z])(_\\d+)?\\.sitem$")
private val BIJOU = Regex("^(ic[a-z]j)([a-z])(_\\d+)?\\.sitem$")

/** De la tête aux pieds pour une tenue, du haut du corps aux chevilles pour une parure. */
private const val ORDRE_ARMURE = "hvsgpb"
private const val ORDRE_BIJOU = "derbpa"

/**
 * Ce qui réunit deux pièces d'une même tenue, ou rien.
 *
 * Six pièces d'une même armure portent six noms différents — « Bottes Kara
 * Paroks », « Casque Kara Parok » — et un tri par nom les éparpillait parmi
 * les autres tenues. Le classer par fiche les remet ensemble.
 */
fun outfitKey(item: Item): String? {
    val sheet = item.sheet.lowercase()
    val trouve = ARMURE.find(sheet) ?: BIJOU.find(sheet) ?: return null
    val (tenue, _, qualite) = trouve.destructured
    return tenue + qualite
}

/** Rang de la pièce dans sa tenue ; les inconnues passent après. */
private fun pieceRank(item: Item): Int {
    val sheet = item.sheet.lowercase()
    val (ordre, lettre) = when {
        ARMURE.matches(sheet) -> ORDRE_ARMURE to ARMURE.find(sheet)!!.groupValues[2]
        BIJOU.matches(sheet) -> ORDRE_BIJOU to BIJOU.find(sheet)!!.groupValues[2]
        else -> return 0
    }
    val rang = ordre.indexOf(lettre.first())
    return if (rang < 0) ordre.length else rang
}

/** Les tris proposés à l'écran. */
enum class SortOrder(val label: String) {
    FAMILY("Famille"),
    NAME("Nom"),
    QUALITY("Qualité"),
    QUANTITY("Quantité"),
}

/**
 * Ce que la grille montre : un contenant, ou le résultat d'une recherche.
 *
 * Tant qu'on ne cherche rien, on montre le contenant choisi, et lui seul.
 * **Dès qu'on tape, tous les contenants sont fouillés** — « où est cette
 * écorce ? » ne se répond pas en ouvrant dix-sept coffres l'un après l'autre.
 * Il n'y a pas de réglage pour ça : c'est le seul comportement qu'on veuille
 * jamais, et une case à cocher de plus ne ferait qu'une chose à oublier.
 *
 * Le résultat garde le nom du contenant avec chaque groupe : trouver l'objet
 * sans dire où il est ne répondrait pas à la question posée. Les contenants
 * sans réponse disparaissent, et l'ordre des autres est celui de la rangée du
 * haut.
 *
 * Vit ici, hors de l'écran, pour être couvert par des tests.
 */
fun chercheDansTout(
    inventaires: List<Inventory>,
    contenantChoisi: Int,
    recherche: String,
    order: SortOrder,
    nameOf: (Item) -> String,
    normalise: (String) -> String,
): List<Pair<String, List<Item>>> {
    if (inventaires.isEmpty()) return emptyList()
    val cherche = normalise(recherche.trim())
    if (cherche.isEmpty()) {
        val choisi = inventaires[contenantChoisi.coerceIn(inventaires.indices)]
        return listOf(choisi.label to sortItems(choisi.items, order, nameOf))
    }
    // Le nom lisible et la fiche : sans pack chargé, il ne reste que la fiche,
    // et chercher « m0117 » doit continuer de répondre.
    return inventaires.mapNotNull { inventaire ->
        val trouves = inventaire.items.filter {
            cherche in normalise(nameOf(it)) || cherche in normalise(it.sheet)
        }
        if (trouves.isEmpty()) null
        else inventaire.label to sortItems(trouves, order, nameOf)
    }
}

/**
 * Range une liste d'items.
 *
 * En tri par famille, les matières sont réunies par matière puis classées du
 * plus bas niveau au plus haut ; les tenues et les parures sont réunies par
 * fiche, chacune à sa qualité et à sa couleur, et se lisent de la tête aux
 * pieds ; le reste est groupé par famille, puis par nom et par qualité, si
 * bien que deux objets identiques de qualités différentes restent côte à côte.
 *
 * Partout où un nom départage, c'est le classeur français qui compare : sinon
 * la casse et les accents du jeu décident du rangement à la place du joueur.
 */
fun sortItems(items: List<Item>, order: SortOrder, nameOf: (Item) -> String): List<Item> =
    when (order) {
        SortOrder.FAMILY -> items.sortedWith(
            compareBy<Item> { familyOf(it).ordinal }
                // Les ensembles d'abord, le reste ensuite : une clé de fiche et
                // un nom d'arme ne se classent pas sur la même chose, et les
                // mêler intercalait la Pique entre deux parures.
                .thenBy { if (familyOf(it).raw || outfitKey(it) != null) 0 else 1 }
                .thenBy(CLASSEUR) {
                    when {
                        familyOf(it).raw -> materialKey(it)
                        else -> outfitKey(it) ?: nameOf(it)
                    }
                }
                .thenBy { it.displayColor.ordinal }
                .thenBy { it.quality }
                .thenBy { pieceRank(it) }
                .thenBy(CLASSEUR) { nameOf(it) })
        SortOrder.NAME -> items.sortedWith(
            compareBy<Item, String>(CLASSEUR) { nameOf(it) }
                .thenByDescending { it.quality })
        SortOrder.QUALITY -> items.sortedWith(
            compareByDescending<Item> { it.quality }.thenBy(CLASSEUR) { nameOf(it) })
        SortOrder.QUANTITY -> items.sortedWith(
            compareByDescending<Item> { it.stack }.thenBy(CLASSEUR) { nameOf(it) })
    }
