package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Entity
import java.net.HttpURLConnection
import java.net.URL

/**
 * Le journal de guilde que le dépôt publie, et que chacun relit.
 *
 * L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
 * déduit de deux relevés successifs, et chaque installation ne connaît donc
 * que ce qu'elle a regardé elle-même. Un officier qui relève une fois par
 * semaine voit d'un bloc ce qu'un autre a vu en trois fois — et ce qui se
 * passe pendant que tout le monde dort n'est vu par personne.
 *
 * Un relevé programmé tourne donc sur GitHub, à l'heure, sans qu'aucune
 * machine soit allumée. Les applications le relisent au lancement et le
 * fusionnent au leur ; elles ne font que lire une adresse publique, sans
 * jeton ni compte, et ne peuvent rien écrire.
 *
 * **Ce qui circule** : des mouvements de coffres, en fiches et en quantités.
 * Pas un seul nom de joueur — l'API n'associe pas les mouvements à qui les a
 * faits, et le journal ne l'invente pas.
 */
object Partage {

    /**
     * La branche `journaux`, servie telle quelle par GitHub.
     *
     * Une branche **orpheline**, reconstruite et poussée en force à chaque
     * relevé — le motif de `gh-pages`, pour la même raison : un journal
     * réécrit toutes les heures laisserait sinon, dans l'historique, chacune
     * de ses versions pour toujours. Ici il n'y a jamais qu'un état, celui du
     * dernier relevé.
     *
     * Ni `main`, qui garderait tout, ni `gh-pages`, que la livraison réécrit —
     * ce qui effacerait le journal au premier envoi d'APK.
     */
    private const val BASE =
        "https://raw.githubusercontent.com/xiom-dev/zyroom-gtk-android/journaux/"

    /** Au-delà, on renonce : c'est un confort, pas une raison d'attendre. */
    private const val DELAI = 10_000

    fun urlDuJournal(entry: EntityStore.Suivie): String =
        "$BASE${entry.kind.name.lowercase()}-${entry.id}.jsonl"

    /** L'adresse du registre du personnel publié pour cette guilde. */
    fun urlDuRegistre(guildId: String): String = "${BASE}roster-$guildId.jsonl"

    /**
     * Relit le journal publié et le verse dans celui d'ici.
     *
     * Renvoie le nombre de mouvements ajoutés, zéro si le dépôt n'en publie
     * pas pour cette entité — le cas de tous les personnages, dont le journal
     * ne regarde personne d'autre.
     *
     * Ne lève jamais : ni l'absence de réseau, ni une page absente, ni un
     * fichier bancal ne doivent gêner le lancement.
     */
    suspend fun recuperer(
        movements: MovementStore,
        entry: EntityStore.Suivie,
    ): Int = withContext(Dispatchers.IO) {
        // Un journal de personnage n'est publie par personne : il ne
        // concerne que celui qui le tient, et le demander ne ferait qu'un
        // 404 par lancement.
        if (entry.kind != Entity.Kind.GUILD) return@withContext 0

        val lignes = runCatching {
            val lien = URL(urlDuJournal(entry)).openConnection() as HttpURLConnection
            lien.connectTimeout = DELAI
            lien.readTimeout = DELAI
            try {
                if (lien.responseCode != HttpURLConnection.HTTP_OK) emptyList()
                else lien.inputStream.bufferedReader().readLines()
            } finally {
                lien.disconnect()
            }
        }.getOrDefault(emptyList())

        if (lignes.isEmpty()) 0
        else runCatching { movements.importer(entry, lignes) }.getOrDefault(0)
    }

    /**
     * Relit le registre du personnel publié et le verse dans celui d'ici.
     *
     * Le pendant de `recuperer` pour les arrivées, les départs et les
     * changements de grade. Les deux applications de bureau le font déjà ;
     * ici, le registre ne connaissait que ce que le téléphone avait vu
     * lui-même, et un téléphone ne reste pas ouvert la nuit.
     *
     * Ne lève jamais, et ne concerne que les guildes : un personnage n'a pas
     * de personnel, et le demander ne ferait qu'un 404 par lancement.
     */
    suspend fun recupererRegistre(
        roster: RosterStore,
        entry: EntityStore.Suivie,
    ): Int = withContext(Dispatchers.IO) {
        if (entry.kind != Entity.Kind.GUILD) return@withContext 0

        val lignes = runCatching {
            val lien = URL(urlDuRegistre(entry.id)).openConnection() as HttpURLConnection
            lien.connectTimeout = DELAI
            lien.readTimeout = DELAI
            try {
                if (lien.responseCode != HttpURLConnection.HTTP_OK) emptyList()
                else lien.inputStream.bufferedReader().readLines()
            } finally {
                lien.disconnect()
            }
        }.getOrDefault(emptyList())

        val ajoutes =
            if (lignes.isEmpty()) 0
            else runCatching { roster.importer(entry.id, lignes) }.getOrDefault(0)
        noterReleve(roster, entry.id)
        ajoutes
    }

    /** L'adresse du témoin de date du relevé publié pour cette guilde. */
    fun urlDuReleve(guildId: String): String = "${BASE}roster-$guildId.releve"

    /**
     * Note la date du dernier relevé publié, pour que le registre local sache
     * se taire quand le relevé horaire a déjà tout vu.
     *
     * Ne lève jamais, et ne se plaint pas : sans ce témoin, le registre se
     * conduit comme avant, c'est-à-dire comme s'il était seul au monde.
     */
    private suspend fun noterReleve(roster: RosterStore, guildId: String) {
        val quand = runCatching {
            val lien = URL(urlDuReleve(guildId)).openConnection() as HttpURLConnection
            lien.connectTimeout = DELAI
            lien.readTimeout = DELAI
            try {
                if (lien.responseCode != HttpURLConnection.HTTP_OK) 0L
                else lien.inputStream.bufferedReader().readText().trim().toLong()
            } finally {
                lien.disconnect()
            }
        }.getOrDefault(0L)
        if (quand > 0L) roster.noterRelevePublie(guildId, quand)
    }
}
