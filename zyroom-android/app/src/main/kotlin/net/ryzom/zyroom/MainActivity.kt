package net.ryzom.zyroom

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.OutpostStore
import net.ryzom.zyroom.data.Preferences
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.data.WatchStore
import net.ryzom.zyroom.ui.App
import java.io.File

/**
 * Point d'entrée de l'application.
 *
 * Le magasin d'entités et le cache des flux vivent dans les dossiers privés de
 * l'application ; le `string_client.pack`, lui, est importé par l'utilisateur —
 * il n'y a pas d'installation de Ryzom sur un téléphone.
 */
/** Nom du pack, le même dans les ressources livrées et dans le dossier privé. */
private const val PACK_NAME = "string_client.pack"

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val store = EntityStore(File(filesDir, "entities.json"))
        val repository = Repository(File(cacheDir, "flux"), store)
        val watches = WatchStore(File(filesDir, "watch.json"))
        // Le journal des mouvements va dans les fichiers privés, pas dans le
        // cache : c'est le seul historique qui existe, l'API n'en tient aucun.
        val movements = MovementStore(File(filesDir, "movements"))
        // Le journal des avant-postes vit à côté, et pour la même raison : il
        // est le seul témoin des prises et des pertes, l'API n'en garde rien.
        val outposts = OutpostStore(File(filesDir, "outposts"))
        val preferences = Preferences(this)

        // Les noms d'items sont livrés avec l'application, sauf dans la variante
        // F-Droid : là, le pack du jeu n'est pas embarqué et le joueur l'importe
        // lui-même — le menu ⋮ est fait pour ça. Un pack importé prend de toute
        // façon le pas sur celui qui serait livré.
        lifecycleScope.launch {
            repository.loadNames(File(filesDir, PACK_NAME)) {
                runCatching { assets.open(PACK_NAME) }.getOrNull()
            }
        }

        setContent { App(store, repository, watches, movements, outposts, preferences) }
    }
}
