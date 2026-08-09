package net.ryzom.zyroom.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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
    var ouverte by remember { mutableStateOf<EntityStore.Suivie?>(null) }
    // La météo ne dépend d'aucune entité : c'est un écran à part, et non une
    // page de plus dans la rangée des coffres.
    var meteo by remember { mutableStateOf(false) }

    ZyRoomTheme {
        val choisie = ouverte
        if (meteo) {
            MeteoScreen(repository = repository, onBack = { meteo = false })
        } else if (choisie == null) {
            EntitiesScreen(
                store = store,
                repository = repository,
                onOpen = { ouverte = it },
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
                onBack = { ouverte = null },
            )
        }
    }
}
