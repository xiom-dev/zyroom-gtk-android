package net.ryzom.zyroom.api

import net.ryzom.zyroom.model.Entity.Kind
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.ItemColor
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * Client de l'API web de Ryzom, porté de `zyroom/ryzom_api.py`.
 *
 * Rien d'autre que la bibliothèque standard : une requête GET, un flux
 * d'octets. Les appels sont bloquants ; c'est à l'appelant de les tenir hors du
 * fil principal — sur Android, une coroutine sur `Dispatchers.IO`.
 */
object RyzomApi {

    const val BASE_URL = "https://api.ryzom.com"

    private const val USER_AGENT = "zyroom-android/0.1"
    private const val TIMEOUT_MS = 30_000

    /** Modules que la clé d'API doit porter, pour un personnage. */
    val REQUIRED_MODULES_CHARACTER = listOf("C01", "C04", "C05", "C06", "A01", "A03")

    /** Modules que la clé d'API doit porter, pour une guilde. */
    val REQUIRED_MODULES_GUILD = listOf("G01", "G02", "G03")

    /**
     * Page où le joueur crée ses clés, telle que la documentation la donne :
     * « API keys must be created using "RyzomAPI app" ».
     */
    const val KEY_PAGE = "https://app.ryzom.com/app_ryzomapi"

    fun characterUrl(apiKey: String): String = "$BASE_URL/character.php?apikey=$apiKey"

    fun guildUrl(apiKey: String): String = "$BASE_URL/guild.php?apikey=$apiKey"

    /**
     * Plusieurs clés en un seul appel : l'API accepte `apikey[]=…&apikey[]=…`.
     *
     * Un joueur qui a quatre personnages les voit ainsi arriver ensemble, et
     * l'API n'est dérangée qu'une fois.
     */
    fun charactersUrl(keys: List<String>): String =
        BASE_URL + "/character.php?" + keys.joinToString("&") { "apikey%5B%5D=$it" }

    /**
     * L'annuaire des guildes du serveur — **sans clé d'API**.
     *
     * Deux mille quatre cents guildes avec leur nom, leur emblème et, ce qui
     * nous intéresse, la liste des avant-postes qu'elles tiennent. C'est la
     * seule source publique sur les avant-postes : le flux de guilde n'en dit
     * rien de plus que la liste de la sienne, et il faut sa clé pour l'obtenir.
     *
     * Le document pèse un demi-méga-octet et n'est pas compressé par le
     * serveur — moitié moins tout de même que le flux de La Lune Eternelle, que
     * l'application télécharge déjà à chaque relevé. C'est la fréquence qui
     * compte, pas le poids : on ne l'interroge qu'à l'ouverture de l'écran.
     */
    fun guildDirectoryUrl(): String = "$BASE_URL/guilds.php"

    fun guildsUrl(keys: List<String>): String =
        BASE_URL + "/guild.php?" + keys.joinToString("&") { "apikey%5B%5D=$it" }

    /**
     * Reconnaît une clé d'API à sa forme.
     *
     * La documentation est explicite : « API keys are 41 alphanumeric
     * characters. Character keys start with 'c' and guild keys with 'g'. »
     */
    fun isApiKey(value: String): Boolean =
        value.length == 41 && value.all { it.isLetterOrDigit() } &&
            (value.startsWith("c") || value.startsWith("g"))

    /** L'espèce que désigne une clé, d'après sa première lettre. */
    fun kindOf(key: String): Kind? = when {
        key.startsWith("c") -> Kind.CHARACTER
        key.startsWith("g") -> Kind.GUILD
        else -> null
    }

    /**
     * URL de l'icône d'un item, fidèle au `ApiItemIcon` d'origine.
     *
     * La couleur « aucune » vaut beige côté API ; qualité et pile ne sont
     * transmises que si elles sont positives.
     */
    fun itemIconUrl(item: Item): String {
        val colour = if (item.displayColor == ItemColor.NONE) ItemColor.BEIGE
                     else item.displayColor
        val options = StringBuilder("?sheetid=${item.sheet}&c=${colour.value}")
        if (item.quality > 0) options.append("&q=${item.quality}")
        if (item.stack > 0) options.append("&s=${item.stack}")
        if (item.sap) options.append("&sap=0")
        if (item.destroyed) options.append("&destroyed=1")
        if (item.locked) options.append("&locked=1")
        return "$BASE_URL/item_icon.php$options"
    }

    /** Lit une URL entièrement. Lève [ApiException] sur erreur réseau. */
    @Throws(ApiException::class)
    fun get(url: String): ByteArray {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.setRequestProperty("User-Agent", USER_AGENT)
        connection.connectTimeout = TIMEOUT_MS
        connection.readTimeout = TIMEOUT_MS
        try {
            if (connection.responseCode !in 200..299) {
                throw ApiException("HTTP ${connection.responseCode} sur $url")
            }
            return connection.inputStream.use { it.readBytes() }
        } catch (error: IOException) {
            throw ApiException("appel impossible : ${error.message}", error)
        } finally {
            connection.disconnect()
        }
    }
}

/** Erreur rendue par l'API, dans son XML ou à l'appel. */
class ApiException(message: String, cause: Throwable? = null) : Exception(message, cause)
