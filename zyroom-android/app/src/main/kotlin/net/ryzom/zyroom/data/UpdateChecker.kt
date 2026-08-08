package net.ryzom.zyroom.data

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Vérifie qu'une version plus récente existe, et sait aller la chercher.
 *
 * Android n'a pas d'équivalent au portail de Flatpak : une application hors
 * Play Store ne peut pas se mettre à jour d'elle-même. Le plus qu'on puisse
 * faire tient en trois temps — interroger une adresse, prévenir, puis proposer
 * l'APK au système, qui demandera confirmation.
 *
 * Le fichier interrogé décrit chaque variante par son identifiant de paquet :
 *
 * ```json
 * { "net.ryzom.zyroom": { "versionCode": 2, "versionName": "0.3",
 *                         "url": "https://…/ZyRoom-Android_0.3.apk" } }
 * ```
 *
 * La comparaison porte sur `versionCode`, pas sur le nom : c'est le seul
 * numéro qu'Android ordonne. **Il doit donc être incrémenté à chaque
 * livraison**, sans quoi rien ne sera jamais proposé.
 */
class UpdateChecker(private val context: Context) {

    data class Disponible(val versionName: String, val url: String)

    /** Rend la version en ligne si elle est plus récente, `null` sinon. */
    suspend fun check(): Disponible? = withContext(Dispatchers.IO) {
        runCatching {
            val texte = lire(MANIFESTE_URL) ?: return@runCatching null
            val entree = JSONObject(texte).optJSONObject(context.packageName)
                ?: return@runCatching null
            val enLigne = entree.optInt("versionCode")
            if (enLigne <= versionInstallee()) null
            else Disponible(entree.optString("versionName"), entree.optString("url"))
        }.getOrNull()
    }

    /**
     * Télécharge l'APK et le présente au système, qui demandera confirmation.
     *
     * Le fichier passe par un `FileProvider` : depuis Android 7, livrer un
     * `file://` à une autre application lève une exception.
     */
    suspend fun telechargerEtInstaller(url: String): String? = withContext(Dispatchers.IO) {
        runCatching {
            val dossier = File(context.cacheDir, "updates").apply { mkdirs() }
            dossier.listFiles()?.forEach { it.delete() }   // pas d'APK qui s'accumulent
            val fichier = File(dossier, "zyroom-update.apk")

            (URL(url).openConnection() as HttpURLConnection).apply {
                instanceFollowRedirects = true
                connectTimeout = 30_000
                readTimeout = 60_000
            }.inputStream.use { entree ->
                fichier.outputStream().use { entree.copyTo(it) }
            }

            val uri = FileProvider.getUriForFile(
                context, "${context.packageName}.updates", fichier)
            context.startActivity(
                Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, "application/vnd.android.package-archive")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                })
            null
        }.exceptionOrNull()?.let { "Échec du téléchargement : ${it.message}" }
    }

    private fun versionInstallee(): Int = runCatching {
        val info = context.packageManager.getPackageInfo(context.packageName, 0)
        @Suppress("DEPRECATION")
        info.versionCode
    }.getOrDefault(Int.MAX_VALUE)   // en cas de doute, ne rien proposer

    private fun lire(url: String): String? = runCatching {
        (URL(url).openConnection() as HttpURLConnection).apply {
            instanceFollowRedirects = true
            connectTimeout = 15_000
            readTimeout = 15_000
        }.inputStream.bufferedReader().use { it.readText() }
    }.getOrNull()

    companion object {
        const val MANIFESTE_URL =
            "https://xiom-dev.github.io/zyroom-gtk-android/version.json"
    }
}
