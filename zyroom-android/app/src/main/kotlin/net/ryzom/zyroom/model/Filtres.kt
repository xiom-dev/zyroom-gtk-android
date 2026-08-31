package net.ryzom.zyroom.model

/**
 * Les filtres de la grille d'inventaire, portés du panneau GTK
 * (`window.py`, `_build_filter_popover` et `_apply_filter`).
 *
 * Un coffre de guilde tient des centaines d'objets, et la recherche par nom ne
 * répond qu'à une question : « où est *cet* objet ». Les autres questions —
 * qu'est-ce qui est monté en sève, que reste-t-il en armure lourde au-dessus de
 * la qualité 200, qu'ai-je mis en vente — se posent par élimination, et c'est
 * ce que ce filtre fait.
 *
 * Tout ici est du calcul sur des données, sans un mot de Compose : c'est la
 * seule part où l'on se trompe, et elle se teste alors sans téléphone ni
 * émulateur.
 *
 * **L'état de repos laisse tout passer.** Chaque ensemble part complet, la
 * qualité couvre toute la plage, et les trois interrupteurs sont éteints :
 * `Filtres()` ne retire rien. C'est ce qui permet de le traverser sans y
 * penser tant qu'on ne l'a pas ouvert.
 */
data class Filtres(
    val qualiteMin: Int = QUALITE_MIN,
    val qualiteMax: Int = QUALITE_MAX,
    val cadenas: Boolean = false,
    val avecBonus: Boolean = false,
    val enVente: Boolean = false,
    val jauges: Set<Jauge> = Jauge.entries.toSet(),
    val types: Set<ItemType> = ItemType.entries.toSet(),
    val classes: Set<ItemClass> = ItemClass.entries.toSet(),
    val ecosystemes: Set<ItemEcosystem> = ItemEcosystem.entries.toSet(),
    val equipements: Set<ItemEquip> = ItemEquip.entries.toSet(),
) {

    /**
     * Vrai si l'objet survit à tous les critères.
     *
     * L'ordre des tests ne change rien au résultat — il faut les passer tous —
     * mais les moins chers viennent d'abord, la grille en appelant un par
     * objet et par frappe au clavier.
     */
    fun passe(item: Item): Boolean {
        if (item.quality < qualiteMin || item.quality > qualiteMax) return false
        if (cadenas && !item.locked) return false
        if (avecBonus && !item.aDesBonus) return false
        if (enVente && item.expires <= 0L) return false
        if (item.type !in types) return false
        if (item.itemClass !in classes) return false
        if (item.ecosystem !in ecosystemes) return false
        // L'emplacement ne qualifie que l'équipement : l'appliquer à une
        // matière, qui n'en a pas, la ferait disparaître dès qu'on décoche
        // « Autre » en cherchant une pièce d'armure.
        if (item.type == ItemType.EQUIPMENT && item.equip !in equipements) return false
        return passeLesJauges(item)
    }

    /**
     * Le filtre des quatre bonus, à part parce qu'il ne se lit pas comme les
     * autres.
     *
     * Toutes cochées, il ne trie rien — **objets sans bonus compris**, car
     * c'est l'état de repos et non une demande. Dès qu'une case tombe, ne
     * restent que les objets portant l'une des jauges encore cochées :
     * décocher trois cases sur quatre, c'est demander « montre-moi ce qui est
     * monté en sève », pas « montre-moi tout sauf ».
     */
    private fun passeLesJauges(item: Item): Boolean {
        if (jauges.size >= Jauge.entries.size) return true
        return jauges.any { it.valeur(item) > 0 }
    }

    /** Vrai dès qu'un critère retire quelque chose : le bouton le signale. */
    val actif: Boolean
        get() = qualiteMin > QUALITE_MIN || qualiteMax < QUALITE_MAX ||
            cadenas || avecBonus || enVente ||
            jauges.size < Jauge.entries.size ||
            types.size < ItemType.entries.size ||
            classes.size < ItemClass.entries.size ||
            ecosystemes.size < ItemEcosystem.entries.size ||
            equipements.size < ItemEquip.entries.size

    companion object {
        /**
         * Les bornes de qualité.
         *
         * Le jeu s'arrête à 250, la borne haute monte à 500 : c'est celle du
         * bureau, et une borne trop basse couperait en silence un objet
         * d'événement hors barème.
         */
        const val QUALITE_MIN = 0
        const val QUALITE_MAX = 500
    }
}

/**
 * Les quatre jauges du jeu, dans leur ordre, et le bonus que chacune porte.
 *
 * Elles vivent ici plutôt qu'avec le dessin des gouttes : le filtre les
 * manipule sans rien savoir de leurs couleurs, et l'ordre — vie, sève,
 * endurance, concentration — doit être le même dans la pile posée sur l'icône
 * et dans la liste des cases à cocher, sans quoi la couleur cesse de faire le
 * lien entre les deux.
 */
enum class Jauge(val label: String, val valeur: (Item) -> Int) {
    VIE("Vie", { it.hpBuff }),
    SEVE("Sève", { it.sapBuff }),
    ENDURANCE("Endurance", { it.staBuff }),
    CONCENTRATION("Concentration", { it.focusBuff }),
}
