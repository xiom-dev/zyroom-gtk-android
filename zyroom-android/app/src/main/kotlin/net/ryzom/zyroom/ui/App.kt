package net.ryzom.zyroom.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
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
    preferences: Preferences,
) {
    var ouverte by remember { mutableStateOf<EntityStore.Suivie?>(null) }

    ZyRoomTheme {
        val choisie = ouverte
        if (choisie == null) {
            EntitiesScreen(
                store = store,
                repository = repository,
                onOpen = { ouverte = it },
            )
        } else {
            InventoryScreen(
                entry = choisie,
                repository = repository,
                watches = watches,
                movements = movements,
                preferences = preferences,
                onBack = { ouverte = null },
            )
        }
    }
}
