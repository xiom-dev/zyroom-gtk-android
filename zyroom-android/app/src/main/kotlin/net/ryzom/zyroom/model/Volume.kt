package net.ryzom.zyroom.model

import kotlin.math.abs

/**
 * Volume des objets, porté de `zyroom/volume.py` — lui-même portage fidèle de
 * `TRyzom.GetItemInfoFromName` (UnitRyzom.pas).
 *
 * Le volume ne vient pas du flux : l'API donne la pile et la fiche, jamais
 * l'encombrement. Il se déduit du **nom de fiche**, dont le motif dit ce que
 * l'objet est — volume = coefficient × |taille de pile|.
 *
 * Faute de ce calcul, `Inventory.totalVolume` valait zéro pour tout le monde :
 * le taux de remplissage annonçait « 0 % » sur des coffres pleins, et l'alerte
 * de volume ne pouvait pas se déclencher, son seuil n'étant jamais atteint.
 *
 * La même analyse rend aussi l'écosystème, la classe et l'emplacement
 * d'équipement : ce sont trois choses que le nom de fiche dit au passage, et
 * que le panneau des filtres demande. Les déduire ailleurs voudrait dire
 * refaire ce parcours de motifs une seconde fois, sur les mêmes chaînes.
 */
object Volume {

    /** Matières de métier, coefficient 1. */
    private val MAT_JOBS = setOf(
        "lucky_flower.sitem", "protect_amber.sitem",
        "water_barrel.sitem", "tools_ticket.sitem",
    )

    /**
     * Matières de construction des coffres de guilde, coefficient 0.
     *
     * Écart assumé avec l'original, repris tel quel du bureau : UnitRyzom.pas
     * leur donne 0,1, mais le jeu affiche un volume de 0,00 — elles ne comptent
     * pas dans l'encombrement. Le 0,1 faisait déborder tout coffre qui en
     * stockait beaucoup.
     */
    private val MAT_GUILD_CHEST = setOf(
        "mp_hard.sitem", "mp_soft.sitem", "mp_colonne.sitem",
        "mp_ornement.sitem", "mp_revetement.sitem", "mp_socle.sitem",
    )

    /** Objets nommément désignés, avec leur coefficient. */
    private val SPECIAUX = mapOf(
        "teddyubo.sitem" to 5.0, "xmas_gingeryubo.sitem" to 5.0,
        "louche.sitem" to 5.0, "if1.sitem" to 15.0, "if2.sitem" to 5.0,
        "if3.sitem" to 9.0, "winch.sitem" to 5.0,
        "s2e1_salins.sitem" to 0.5, "s2e1_seve_suc.sitem" to 0.5,
        "ulo_4.sitem" to 1.0, "event_magnetized_amber.sitem" to 0.5,
        "rite_ranger_map_book.sitem" to 0.5,
        "anniversary_dance_scroll.sitem" to 0.5,
    )

    private val NATURAL_MAT = Regex("^m\\d{4}dxa([pcdfljg])([a-f])01\\.sitem")
    private val ANIMAL_MAT = Regex("^m\\d{4}.{3}([pcdfljg])([a-f])01\\.sitem")
    private val SYSTEM_MAT = Regex("(system_mp_?|mp_kami_ep2_|mp_karavan_ep2_)(\\w*)\\.sitem")
    private val TOOL = Regex("^(ico(kar|kam|mar|gen)t|sfxitforage|it).*\\.sitem")
    private val EQUIPMENT = Regex("^ic(.).*(..)\\.sitem")
    private val EQUIPMENT_ARMOR = Regex("^ic.a([lmhcbgpsv]).*")
    private val EQUIPMENT_SHIELD = Regex("^ic(?:.|ka[rm])s([bs]).*")
    private val EQUIPMENT_AMPLIFIER = Regex("^ic.+m2ms.*")
    private val EQUIPMENT_WEAPON = Regex("^ic.+([rm])([12])(..).*")
    private val EQUIPMENT_AMMO = Regex("^ic.p([12][ablpr]).*\\.sitem")
    private val EQUIPMENT_JEWEL = Regex("^ic.j.*")
    private val BANDIT_CHEST = Regex("compo_.*mark\\d\\.sitem")

    /** La lettre d'armure, en emplacement : botte, gant, casque… */
    private val ARMURES = mapOf(
        'l' to ItemEquip.LIGHT_ARMOR, 'c' to ItemEquip.LIGHT_ARMOR,
        'b' to ItemEquip.LIGHT_ARMOR, 'g' to ItemEquip.LIGHT_ARMOR,
        'p' to ItemEquip.LIGHT_ARMOR, 's' to ItemEquip.LIGHT_ARMOR,
        'v' to ItemEquip.LIGHT_ARMOR, 'm' to ItemEquip.MEDIUM_ARMOR,
        'h' to ItemEquip.HEAVY_ARMOR,
    )

    /** La lettre de style d'une piece d'equipement, en region. */
    private val ECOSYS_EQUIPEMENT = mapOf(
        't' to ItemEcosystem.LAKES, 'f' to ItemEcosystem.DESERT,
        'm' to ItemEcosystem.FOREST, 'z' to ItemEcosystem.JUNGLE,
    )

    /** La lettre de region d'une matiere. */
    private val ECOSYS_MATIERE = mapOf(
        'c' to ItemEcosystem.COMMON, 'g' to ItemEcosystem.COMMON,
        'p' to ItemEcosystem.PRIME, 'd' to ItemEcosystem.DESERT,
        'f' to ItemEcosystem.FOREST, 'l' to ItemEcosystem.LAKES,
        'j' to ItemEcosystem.JUNGLE,
    )

    /** La lettre de qualite d'une matiere. Les deux baremes different. */
    private val CLASSE_NATURELLE = mapOf(
        'a' to ItemClass.BASIC, 'b' to ItemClass.BASIC, 'c' to ItemClass.FINE,
        'd' to ItemClass.CHOICE, 'e' to ItemClass.EXCELLENT, 'f' to ItemClass.SUPREME,
    )
    private val CLASSE_ANIMALE = mapOf(
        'a' to ItemClass.BASIC, 'b' to ItemClass.FINE, 'c' to ItemClass.CHOICE,
        'd' to ItemClass.EXCELLENT, 'e' to ItemClass.SUPREME, 'f' to ItemClass.SUPREME,
    )

    /**
     * Ce que le nom de fiche apprend d'un objet.
     *
     * La classe reste inconnue pour l'équipement : elle s'y lit dans l'énergie
     * du flux, que le nom ne porte pas. Le parseur la pose par-dessus.
     */
    data class Analyse(
        val type: ItemType,
        val coefficient: Double,
        val equip: ItemEquip = ItemEquip.OTHER,
        val ecosystem: ItemEcosystem = ItemEcosystem.UNKNOWN,
        val itemClass: ItemClass = ItemClass.UNKNOWN,
    )

    /** Le volume d'un objet : son coefficient par la taille de sa pile. */
    fun volume(sheet: String, stack: Int): Double =
        coefficient(sheet) * abs(stack)

    /** Tout ce que la fiche apprend, le volume déjà multiplié par la pile. */
    fun classer(sheet: String, stack: Int): Analyse {
        val lu = analyser(sheet)
        return lu.copy(coefficient = lu.coefficient * abs(stack))
    }

    fun coefficient(sheet: String): Double = analyser(sheet).coefficient

    fun type(sheet: String): ItemType = analyser(sheet).type

    /**
     * (type, coefficient) d'après le nom de fiche.
     *
     * L'enchaînement des tests est celui de `GetItemInfoFromName`, drapeau
     * `autre` compris : un objet reconnu plus haut n'est plus examiné ensuite,
     * et l'ordre des familles n'est donc pas indifférent.
     */
    private fun analyser(nom: String): Analyse {
        var coef = 0.0
        var type = ItemType.OTHER
        var autre = true
        var equip = ItemEquip.OTHER
        var ecosysteme = ItemEcosystem.UNKNOWN
        var classe = ItemClass.UNKNOWN

        if (nom.startsWith("ixpca0")) {
            autre = false
            type = ItemType.CATA
            coef = 0.01
        }

        if (nom.startsWith("tp_ka")) {
            autre = false
            type = ItemType.TELEPORTER
        }

        if (autre && TOOL.find(nom) != null && !nom.contains("_sap_recharge")) {
            autre = false
            type = ItemType.EQUIPMENT
            equip = ItemEquip.TOOL
            coef = 10.0
        }

        val equipement = EQUIPMENT.find(nom)
        if (autre && equipement != null) {
            autre = false
            type = ItemType.EQUIPMENT
            ecosysteme = ECOSYS_EQUIPEMENT[equipement.groupValues[1].firstOrNull()]
                ?: ItemEcosystem.COMMON
            var trouve = false

            EQUIPMENT_SHIELD.find(nom)?.let { m ->
                when (m.groupValues[1]) {
                    "b" -> { equip = ItemEquip.BUCKLER; coef = 5.0; trouve = true }
                    "s" -> {
                        equip = ItemEquip.SHIELD
                        coef = if (nom == "icbss_pvp.sitem") 20.0 else 10.0
                        trouve = true
                    }
                }
            }

            EQUIPMENT_ARMOR.find(nom)?.let { m ->
                if (!trouve) {
                    equip = ARMURES[m.groupValues[1].firstOrNull()] ?: ItemEquip.LIGHT_ARMOR
                    coef = if (nom.startsWith("iccah")) 20.0 else 7.0
                    trouve = true
                }
            }

            if (!trouve && EQUIPMENT_AMPLIFIER.find(nom) != null) {
                equip = ItemEquip.AMPLIFIER
                coef = 10.0
                trouve = true
            }

            if (!trouve) {
                EQUIPMENT_WEAPON.find(nom)?.let { m ->
                    val genre = m.groupValues[1]
                    val mains = m.groupValues[2]
                    val queue = m.groupValues[3]
                    if (genre == "m") {
                        equip = ItemEquip.WEAPON_MELEE
                        coef = when (mains) {
                            "1" -> if (queue == "pd") 5.0 else 10.0
                            "2" -> 15.0
                            else -> coef
                        }
                    } else if (genre == "r") {
                        equip = ItemEquip.WEAPON_RANGE
                        coef = when (mains) {
                            "1" -> 10.0
                            "2" -> when (queue.firstOrNull()) {
                                'a' -> 30.0; 'b' -> 15.0
                                'r' -> 15.0; 'l' -> 30.0
                                else -> 0.0
                            }
                            else -> coef
                        }
                    }
                    trouve = true
                }
            }

            if (!trouve) {
                EQUIPMENT_AMMO.find(nom)?.let { m ->
                    equip = ItemEquip.AMMO
                    val g = m.groupValues[1]
                    coef = when (g[0]) {
                        '1' -> 0.04
                        '2' -> when (g[1]) {
                            'a' -> 5.0; 'b' -> 0.1
                            'r' -> 0.1; 'l' -> 15.0
                            else -> 0.0
                        }
                        else -> 0.0
                    }
                    trouve = true
                }
            }

            if (!trouve && EQUIPMENT_JEWEL.find(nom) != null) {
                equip = ItemEquip.JEWEL
                coef = 2.0
                trouve = true
            }

            if (!trouve) {
                if (nom.startsWith("ic_candy_stick")) coef = 30.0
                else if (nom.startsWith("ic_halloween_stick")) coef = 30.0
                else if (nom.startsWith("ic_anlor_helmet01")) coef = 7.0
            }
        }

        NATURAL_MAT.find(nom)?.let { m ->
            if (autre) {
                autre = false
                type = ItemType.NATURAL_MAT
                coef = 0.5
                ecosysteme = ECOSYS_MATIERE[m.groupValues[1].firstOrNull()]
                    ?: ItemEcosystem.COMMON
                classe = CLASSE_NATURELLE[m.groupValues[2].firstOrNull()] ?: ItemClass.UNKNOWN
            }
        }
        ANIMAL_MAT.find(nom)?.let { m ->
            if (autre) {
                autre = false
                type = ItemType.ANIMAL_MAT
                coef = 0.5
                ecosysteme = ECOSYS_MATIERE[m.groupValues[1].firstOrNull()]
                    ?: ItemEcosystem.COMMON
                classe = CLASSE_ANIMALE[m.groupValues[2].firstOrNull()] ?: ItemClass.UNKNOWN
            }
        }

        if (autre) {
            if (nom.contains("pre_order.sitem")) coef = 5.0
            SPECIAUX[nom]?.let { coef = it }
            if (nom.startsWith("ipoc_")) coef = 1.0
            if (nom.startsWith("ipm")) coef = 1.0
            if (nom.startsWith("ipk_")) coef = 1.0
            if (nom in MAT_JOBS) coef = 1.0
            if (BANDIT_CHEST.containsMatchIn(nom)) coef = 0.5
            if (nom in MAT_GUILD_CHEST) coef = 0.0
            if (nom == "icbm1sa_2.sitem" || nom == "icbm1bs.sitem") {
                type = ItemType.EQUIPMENT
                coef = 20.0
            }
            if (nom.startsWith("ikaracp_ep") || nom.startsWith("ikamacp_ep")) {
                type = ItemType.EQUIPMENT
                coef = 7.0
            }
            if (SYSTEM_MAT.containsMatchIn(nom)) {
                type = ItemType.SYSTEM_MAT
                if (nom == "system_mp_loot.sitem") coef = 0.5
            }
        }

        return Analyse(type, coef, equip, ecosysteme, classe)
    }
}
