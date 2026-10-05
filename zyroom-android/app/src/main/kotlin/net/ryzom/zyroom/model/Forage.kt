package net.ryzom.zyroom.model

/**
 * Ce qui sort dans les Primes, d'après le relevé de terrain de la guilde.
 *
 * Le même calcul que `meteo.sorties_de` dans ZyRoom-GTK, sur la même table :
 * `ForageTable.kt` est produit avec `forage.py`, par `outils/table_forage.py`.
 *
 * **Pourquoi plus la table d'Armory.** Elle donnait les suprêmes d'une saison
 * entière, sans le temps qu'il fait, et la fourchette d'humidité d'un gisement
 * — qui disait « ce qui sort » — tombe juste une fois sur deux face au relevé.
 * Le relevé, lui, a été coché en jeu, créneau par créneau.
 */
object Forage {

    const val SUPREME = "supreme"
    const val EXCELLENTE = "excellent"
    const val A_CONFIRMER = "a_confirmer"

    /** {zone: {(famille, matière): {(saison, condition)}}}, rangé au premier usage. */
    private fun ranger(cases: List<String>):
        Map<String, Map<Pair<String, String>, Set<Pair<String, String>>>> {
        val table = mutableMapOf<String,
            MutableMap<Pair<String, String>, MutableSet<Pair<String, String>>>>()
        for (case in cases) {
            val (zone, famille, matiere, saison, condition) = case.split("|")
            table.getOrPut(zone) { mutableMapOf() }
                .getOrPut(famille to matiere) { mutableSetOf() }
                .add(saison to condition)
        }
        return table
    }

    private class Tables(
        val supremes: Map<String, Map<Pair<String, String>, Set<Pair<String, String>>>>,
        val excellentes: Map<String, Map<Pair<String, String>, Set<Pair<String, String>>>>,
        val aConfirmer: Map<String, Map<Pair<String, String>, Set<Pair<String, String>>>>,
    ) {
        constructor(supreme: List<String>, excellente: List<String>, aConfirmer: List<String>) :
            this(ranger(supreme), ranger(excellente), ranger(aConfirmer))
    }

    /** L'instantané figé à la livraison : `ForageTable.kt`. */
    private val embarque by lazy {
        Tables(RELEVE_SUPREME, RELEVE_EXCELLENTE, RELEVE_A_CONFIRMER)
    }

    /** Le relevé publié sur GitHub, une fois lu ; sinon l'instantané sert. */
    @Volatile
    private var publie: Tables? = null

    /**
     * Combien de créneaux suprêmes au minimum pour croire un relevé publié.
     * Une réponse tronquée ne doit pas vider l'écran : le relevé en porte
     * plus de quatre cents. Le même plancher que `meteo.PLANCHER_SUPREMES`.
     */
    const val PLANCHER_SUPREMES = 300

    /**
     * Remplace l'instantané par le relevé que la machine de Ludo recopie de
     * xiom.be/forage (`Partage.recupererForage`). Sans lui, chaque nouveau
     * spot attendait une livraison.
     *
     * Rend `false`, et ne change rien, si le relevé paraît tronqué ou bancal.
     */
    fun poserPublie(
        supreme: List<String>,
        excellente: List<String>,
        aConfirmer: List<String>,
    ): Boolean {
        if (supreme.size < PLANCHER_SUPREMES) return false
        publie = runCatching { Tables(supreme, excellente, aConfirmer) }
            .getOrNull() ?: return false
        return true
    }

    /** Revient à l'instantané embarqué. */
    internal fun oublierPublie() {
        publie = null
    }

    /**
     * Tout ce qui sort dans une zone à ce créneau, qualité par qualité.
     *
     * Rend `[(qualité, {famille: [matières]})…]`, la meilleure d'abord, et une
     * liste vide quand la guilde n'a rien relevé là.
     *
     * **Les croix oranges ne se montrent que dans la variante dev**
     * (`voirAVerifier`), comme dans gtk-dev : ce sont des pistes pour les
     * foreuses, pas des certitudes. Ailleurs elles sont retirées de l'XL, sans
     * quoi elles y reviendraient sous le nom d'une XL vue en jeu.
     */
    fun sortiesDe(
        saison: Int,
        zone: String,
        condition: String,
        voirAVerifier: Boolean = false,
    ): List<Pair<String, Map<String, List<String>>>> {
        val creneau = (SAISONS.getOrNull(saison) ?: return emptyList()) to
            condition.uppercase()

        fun groupesDe(table: Map<String, Map<Pair<String, String>,
                                       Set<Pair<String, String>>>>):
            Map<String, List<String>> =
            table[zone].orEmpty()
                .filterValues { creneau in it }.keys
                .groupBy({ it.first }, { it.second })
                .mapValues { (_, matieres) -> matieres.sorted() }

        val tables = publie ?: embarque
        val douteuses = groupesDe(tables.aConfirmer)
        val vues = groupesDe(tables.excellentes)
            .mapValues { (famille, matieres) ->
                matieres.filter { it !in douteuses[famille].orEmpty() }
            }
            .filterValues { it.isNotEmpty() }

        return buildList {
            groupesDe(tables.supremes).takeIf { it.isNotEmpty() }?.let { add(SUPREME to it) }
            if (vues.isNotEmpty()) add(EXCELLENTE to vues)
            if (voirAVerifier && douteuses.isNotEmpty()) add(A_CONFIRMER to douteuses)
        }
    }

    /** Le nom d'une qualité, tel que l'écran l'écrit au-dessus de son bloc. */
    fun nomQualite(qualite: String): String = when (qualite) {
        SUPREME -> "Suprême"
        EXCELLENTE -> "Excellente"
        A_CONFIRMER -> "Excellente à vérifier"
        else -> qualite
    }
}
