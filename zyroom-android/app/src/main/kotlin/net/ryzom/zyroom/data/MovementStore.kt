package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Entity
import org.json.JSONObject
import java.io.File

/**
 * Le journal des mouvements : ce qui est entré et sorti des contenants.
 *
 * Porté de `zyroom/movements.py`, lui-même repris de la fenêtre d'alerte du
 * Delphi d'origine (atAdded / atRemoved / atModified).
 *
 * L'API de Ryzom ne fournit **aucun historique** : elle ne renvoie qu'un état.
 * Les mouvements se déduisent donc de la comparaison de deux états successifs,
 * et seul ce qui a bougé entre deux relevés est vu — deux mouvements qui
 * s'annulent entre-temps passent inaperçus. C'était déjà la limite de
 * l'original.
 *
 * Deux fichiers par entité : l'instantané du dernier état connu, et le journal
 * en JSON Lines. Le journal vit dans les fichiers privés et non dans le cache,
 * parce que c'est justement ce que l'API ne saura pas reconstruire — vider le
 * cache ne doit pas l'effacer.
 */
class MovementStore(private val dir: File) {

    enum class Kind { ADDED, REMOVED, MODIFIED }

    data class Movement(
        /** Secondes Unix, comme le journal de la version GTK. */
        val at: Long,
        val invKey: String,
        val invLabel: String,
        val sheet: String,
        val quality: Int,
        val kind: Kind,
        /**
         * Quantité entrée (positive) ou sortie (négative).
         *
         * En `Long` et non en `Int` à cause du trésor : une pile d'objets se
         * compte par centaines, un coffre de guilde par dizaines de millions
         * de dappers. La marge d'un `Int` suffirait aujourd'hui, mais un
         * débordement ne se verrait qu'au journal, sous la forme d'un nombre
         * absurde — et il n'y a rien à gagner à le laisser possible.
         */
        val delta: Long,
        val before: Long,
        val after: Long,
    )

    /**
     * Confronte l'entité au dernier état connu, ajoute ce qui a bougé au
     * journal, et retient le nouvel état.
     *
     * Au tout premier relevé il n'y a rien à comparer : on enregistre l'état
     * sans rien journaliser, sinon l'inventaire entier passerait pour un
     * arrivage.
     */
    suspend fun record(entry: EntityStore.Suivie, entity: Entity): List<Movement> =
        withContext(Dispatchers.IO) {
            val avant = readSnapshot(entry)
            val apres = snapshotOf(entity)
            val mouvements = if (avant == null) emptyList()
                             else diff(avant, apres, entity)
            if (mouvements.isNotEmpty()) appendLog(entry, mouvements)
            writeSnapshot(entry, apres)
            mouvements
        }

    /** Le journal, de la relève la plus récente à la plus ancienne. */
    suspend fun history(entry: EntityStore.Suivie): List<Movement> =
        withContext(Dispatchers.IO) {
            val file = logFile(entry)
            if (!file.isFile) return@withContext emptyList()
            val lignes = runCatching { file.readLines() }.getOrDefault(emptyList())
            lignes.mapNotNull { ligne ->
                if (ligne.isBlank()) null
                else runCatching { fromJson(JSONObject(ligne)) }.getOrNull()
            }
                // Tri stable sur le seul horodatage : les relèves ressortent de
                // la plus récente à la plus ancienne, mais à l'intérieur de
                // l'une d'elles l'ordre d'écriture est conservé. Lire le fichier
                // à l'envers retournerait aussi cet ordre-là.
                .sortedByDescending { it.at }
        }

    suspend fun clear(entry: EntityStore.Suivie) = withContext(Dispatchers.IO) {
        logFile(entry).delete()
        Unit
    }

    // ------------------------------------------------------------- interne

    private fun base(entry: EntityStore.Suivie) =
        "${entry.kind.name.lowercase()}-${entry.id}"

    private fun logFile(entry: EntityStore.Suivie) = File(dir, "${base(entry)}.jsonl")

    private fun snapFile(entry: EntityStore.Suivie) = File(dir, "${base(entry)}-etat.json")

    /**
     * `{clé du contenant: {fiche|qualité: quantité}}`
     *
     * Les contenants masqués en sont **exclus**, et pas seulement vidés : un
     * instantané antérieur où le coffre était garni ferait sinon apparaître, au
     * relevé suivant, un retrait par objet — soit exactement la liste qu'on
     * masque, recopiée dans le journal. `diff` ne parcourant que les clés du
     * nouvel instantané, l'absence suffit à les en tenir dehors.
     */
    private fun snapshotOf(entity: Entity): Map<String, Map<String, Long>> {
        val snap = entity.inventories.filterNot { it.masked }
            .associate { inventaire ->
                val comptes = mutableMapOf<String, Long>()
                inventaire.items.forEach { item ->
                    val signature = WatchStore.signatureOf(item)
                    comptes[signature] =
                        (comptes[signature] ?: 0L) + maxOf(item.stack, 1).toLong()
                }
                inventaire.key to comptes
            }.toMutableMap()

        // Le trésor, sous une clé réservée : ni contenant ni objet, mais il
        // entre et il sort comme le reste, et le journal n'en demande pas plus.
        // Absent tant que l'API n'en dit rien — une clé manquante vaut mieux
        // qu'un zéro, qui ferait croire au relevé suivant que la guilde vient
        // de tout dépenser.
        if (entity.dappers > 0) {
            snap[MONEY_KEY] = mutableMapOf(MONEY_SIG to entity.dappers)
        }
        return snap
    }

    private fun diff(
        avant: Map<String, Map<String, Long>>,
        apres: Map<String, Map<String, Long>>,
        entity: Entity,
    ): List<Movement> {
        val quand = dateReleve(entity)
        val libelles = entity.inventories.associate { it.key to it.label }
        val out = mutableListOf<Movement>()

        // Seuls les contenants du nouvel état sont examinés : un contenant
        // disparu — une bête vendue — ne doit pas faire croire que tout son
        // contenu vient d'être retiré.
        apres.forEach { (cle, comptesApres) ->
            if (cle == MONEY_KEY) return@forEach   // le trésor a sa comparaison
            val comptesAvant = avant[cle].orEmpty()
            (comptesApres.keys + comptesAvant.keys).forEach { signature ->
                val depuis = comptesAvant[signature] ?: 0L
                val vers = comptesApres[signature] ?: 0L
                if (depuis == vers) return@forEach
                val fiche = signature.substringBeforeLast('|', signature)
                val qualite = signature.substringAfterLast('|', "").toIntOrNull() ?: 0
                out += Movement(
                    at = quand,
                    invKey = cle,
                    invLabel = libelles[cle] ?: cle,
                    sheet = fiche,
                    quality = qualite,
                    kind = when {
                        depuis == 0L -> Kind.ADDED
                        vers == 0L -> Kind.REMOVED
                        else -> Kind.MODIFIED
                    },
                    delta = vers - depuis,
                    before = depuis,
                    after = vers,
                )
            }
        }
        // Entrées d'abord, puis sorties, groupées par contenant : l'ordre le
        // plus lisible quand une relève en rapporte beaucoup d'un coup. Le
        // trésor passe devant : une relève qui rapporte trente rangements de
        // matières rapporte au plus un mouvement d'argent, et c'est celui-là
        // qu'on cherche des yeux.
        return diffMoney(avant, apres, quand) +
            out.sortedWith(compareBy({ it.invKey }, { -it.delta }))
    }

    /**
     * Le mouvement du trésor entre deux instantanés, s'il y en a un.
     *
     * Rien tant que l'instantané **précédent** n'en portait pas : sans cette
     * garde, la première relève qui suit la mise à jour journaliserait le
     * trésor entier comme une entrée de soixante-dix-neuf millions.
     */
    private fun diffMoney(
        avant: Map<String, Map<String, Long>>,
        apres: Map<String, Map<String, Long>>,
        quand: Long,
    ): List<Movement> {
        val depuis = avant[MONEY_KEY]?.get(MONEY_SIG) ?: return emptyList()
        val vers = apres[MONEY_KEY]?.get(MONEY_SIG) ?: return emptyList()
        if (depuis == vers) return emptyList()
        return listOf(Movement(
            at = quand,
            invKey = MONEY_KEY,
            invLabel = MONEY_LABEL,
            sheet = MONEY_SHEET,
            quality = 0,
            kind = Kind.MODIFIED,
            delta = vers - depuis,
            before = depuis,
            after = vers,
        ))
    }

    private fun appendLog(entry: EntityStore.Suivie, mouvements: List<Movement>) {
        runCatching {
            dir.mkdirs()
            val file = logFile(entry)
            file.appendText(mouvements.joinToString("") { toJson(it).toString() + "\n" })
            trim(file)
        }
    }

    /** Au-delà de [MAX_LINES] lignes, on ne garde que les [KEEP_LINES] dernières. */
    private fun trim(file: File) {
        runCatching {
            val lignes = file.readLines()
            if (lignes.size <= MAX_LINES) return
            file.writeText(lignes.takeLast(KEEP_LINES).joinToString("\n", postfix = "\n"))
        }
    }

    private fun readSnapshot(entry: EntityStore.Suivie): Map<String, Map<String, Long>>? {
        val file = snapFile(entry)
        if (!file.isFile) return null
        return runCatching {
            val racine = JSONObject(file.readText())
            racine.keys().asSequence().associateWith { cle ->
                val contenant = racine.getJSONObject(cle)
                contenant.keys().asSequence()
                    .associateWith { contenant.getLong(it) }
            }
        }.getOrNull()
    }

    private fun writeSnapshot(
        entry: EntityStore.Suivie,
        etat: Map<String, Map<String, Long>>,
    ) {
        runCatching {
            dir.mkdirs()
            val racine = JSONObject()
            etat.forEach { (cle, comptes) ->
                racine.put(cle, JSONObject().apply {
                    comptes.forEach { (signature, quantite) -> put(signature, quantite) }
                })
            }
            snapFile(entry).writeText(racine.toString())
        }
    }

    private fun toJson(m: Movement) = JSONObject().apply {
        put("at", m.at)
        put("inv", m.invKey)
        put("label", m.invLabel)
        put("sheet", m.sheet)
        put("q", m.quality)
        put("kind", m.kind.name)
        put("delta", m.delta)
        put("before", m.before)
        put("after", m.after)
    }

    private fun fromJson(o: JSONObject) = Movement(
        at = o.optLong("at"),
        invKey = o.optString("inv"),
        invLabel = o.optString("label"),
        sheet = o.optString("sheet"),
        quality = o.optInt("q"),
        kind = runCatching { Kind.valueOf(o.optString("kind")) }.getOrDefault(Kind.MODIFIED),
        delta = o.optLong("delta"),
        before = o.optLong("before"),
        after = o.optLong("after"),
    )

    companion object {
        private const val MAX_LINES = 20_000
        private const val KEEP_LINES = 10_000

        /**
         * Le trésor, rangé dans l'instantané comme s'il était un contenant.
         *
         * L'argent n'est pas un objet : il ne vit dans aucun coffre, l'API le
         * rend à part (`<money>`), et il n'a ni fiche, ni qualité, ni icône.
         * Mais il entre et il sort, et c'est tout ce que le journal demande —
         * lui donner une clé de contenant réservée le fait suivre le même
         * chemin que le reste, de l'instantané au disque, sans une seule
         * structure de plus.
         */
        const val MONEY_KEY = "money"
        const val MONEY_SHEET = "dappers"
        const val MONEY_SIG = "$MONEY_SHEET|0"
        const val MONEY_LABEL = "Trésor"

        /** Avant l'ouverture de Ryzom, aucune date n'est croyable. */
        private const val OUVERTURE_DU_JEU = 1_095_638_400L   // 20 septembre 2004

        /**
         * Quand le serveur a calculé le flux d'où sortent ces mouvements.
         *
         * **Ce n'est pas l'heure du mouvement, et rien ne peut l'être** : l'API
         * rend un état, jamais un historique — pas un `<item>`, pas le
         * `<money>`, ne porte de date. Tout ce qu'on sait d'un mouvement, c'est
         * qu'il a eu lieu entre deux relevés. La date du relevé est la meilleure
         * des deux bornes, et la seule que le flux fournisse.
         *
         * Ce qu'elle corrige, en revanche, est réel. L'API ne recalcule pas un
         * flux à la demande : elle sert le dernier mis en cache — c'est tout le
         * propos de `cachedUntil` — et l'écart se compte en heures. Un flux de
         * personnage relevé le 22 août 2026 à 01h32 portait `created` au 21 à
         * 14h48. Dater les mouvements de l'horloge du téléphone revenait donc à
         * les dater du moment où l'on ouvre l'application : relever tous les
         * soirs vers la même heure donnait un journal où chaque jour portait la
         * même heure, et trois jours d'absence s'écrasaient sur l'instant du
         * retour.
         *
         * Une date absente, ou hors du temps du jeu, vaut l'horloge locale :
         * moins juste, mais jamais absurde.
         */
        fun dateReleve(entity: Entity): Long {
            val maintenant = System.currentTimeMillis() / 1000
            // Une date dans l'avenir trahit une horloge locale en retard, pas
            // un flux venu de demain : on ne la laisse pas passer devant le
            // reste du journal.
            if (entity.created < OUVERTURE_DU_JEU ||
                entity.created > maintenant + 3600) return maintenant
            return entity.created
        }

        /** Un nombre de dappers, groupé par milliers — 79000000 → 79 000 000. */
        fun montant(nombre: Long): String {
            val chiffres = kotlin.math.abs(nombre).toString().reversed()
                .chunked(3).joinToString(" ").reversed()
            return if (nombre < 0) "-$chiffres" else chiffres
        }

        /** Ligne rédigée, sur le modèle de l'original. */
        fun describe(m: Movement, nameOf: (String) -> String): String {
            if (m.invKey == MONEY_KEY) {
                val sens = if (m.delta > 0) "entrés" else "sortis"
                return "${montant(kotlin.math.abs(m.delta))} dappers $sens " +
                    "(${montant(m.before)} > ${montant(m.after)})"
            }
            val nom = nameOf(m.sheet)
            val qualite = if (m.quality > 0) " Q${m.quality}" else ""
            return when (m.kind) {
                Kind.ADDED -> "l'objet $nom$qualite a été ajouté (${m.after})"
                Kind.REMOVED -> "l'objet $nom$qualite a été retiré (${m.before})"
                Kind.MODIFIED ->
                    "la quantité de l'objet $nom$qualite a changé (${m.before} > ${m.after})"
            }
        }
    }
}
