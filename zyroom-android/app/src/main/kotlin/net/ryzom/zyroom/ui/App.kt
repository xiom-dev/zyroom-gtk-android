package net.ryzom.zyroom.ui

import androidx.activity.compose.BackHandler
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.OutpostStore
import net.ryzom.zyroom.data.Preferences
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.data.WatchStore

/**
 * L'enchaînement des écrans : la liste des entités, puis l'inventaire de celle
 * qu'on ouvre. Deux écrans ne justifient pas une bibliothèque de navigation.
 */
@Composable
fun App(
    store: EntityStore,
    repository: Repository,
    watches: WatchStore,
    movements: MovementStore,
    outposts: OutpostStore,
    preferences: Preferences,
) {
    // On retient l'identifiant plutôt que l'entité : tourner le téléphone
    // reconstruit l'écran, et un simple `remember` renvoyait à l'accueil au
    // milieu d'une consultation. L'identifiant, lui, se range dans l'état
    // sauvegardé et retrouve l'entité au retour.
    var ouverteId by rememberSaveable { mutableStateOf<String?>(null) }
    val ouverte = store.all().firstOrNull { it.id == ouverteId }
    // La météo ne dépend d'aucune entité : c'est un écran à part, et non une
    // page de plus dans la rangée des coffres.
    var meteo by rememberSaveable { mutableStateOf(false) }

    // Le bouton « retour » du téléphone doit remonter d'un écran, comme la
    // flèche de la barre de titre. Sans cela il fermait l'application depuis
    // n'importe où, ce qui n'est ni ce qu'on attend ni ce qu'on veut au milieu
    // d'un inventaire.
    BackHandler(enabled = meteo) { meteo = false }
    BackHandler(enabled = !meteo && ouverte != null) { ouverteId = null }

    ZyRoomTheme {
        val choisie = ouverte
        if (meteo) {
            // Le pincement ne vaut que pour la météo : c'est le seul écran dont
            // le contenu ne s'adapte pas — une courbe et un tableau de matières
            // qu'on veut tantôt lire de près, tantôt embrasser d'un coup. Les
            // inventaires, eux, ont déjà leurs boutons « − » et « + » pour la
            // taille des cases, et l'arbre des compétences se replie.
            ZoomPincee {
                MeteoScreen(repository = repository, onBack = { meteo = false })
            }
        } else if (choisie == null) {
            EntitiesScreen(
                store = store,
                repository = repository,
                onOpen = { ouverteId = it.id },
                onMeteo = { meteo = true },
            )
        } else {
            InventoryScreen(
                entry = choisie,
                repository = repository,
                watches = watches,
                movements = movements,
                outposts = outposts,
                preferences = preferences,
                onBack = { ouverteId = null },
            )
        }
    }
}
