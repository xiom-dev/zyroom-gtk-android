package net.ryzom.zyroom.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.data.Alert
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.Preferences
import net.ryzom.zyroom.data.WatchStore
import net.ryzom.zyroom.data.volumeAlerts
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.SortOrder
import net.ryzom.zyroom.model.sortItems
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * L'inventaire d'une entité : un choix de contenant, puis la grille d'items.
 *
 * On montre d'abord ce qu'on a en cache — c'est ce qui rend l'application
 * utilisable en jeu, sans attendre le réseau —, puis on rafraîchit si l'API a
 * de quoi rendre autre chose.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun InventoryScreen(
    entry: EntityStore.Suivie,
    repository: Repository,
    watches: WatchStore,
    movements: MovementStore,
    preferences: Preferences,
    onBack: () -> Unit,
) {
    var entity by remember { mutableStateOf<Entity?>(null) }
    var contenant by remember { mutableStateOf(0) }
    var occupe by remember { mutableStateOf(true) }
    var erreur by remember { mutableStateOf<String?>(null) }
    var detail by remember { mutableStateOf<Item?>(null) }
    var recherche by remember { mutableStateOf("") }
    var tri by remember { mutableStateOf(SortOrder.FAMILY) }
    var alertes by remember { mutableStateOf(emptyList<Alert>()) }
    var voirAlertes by remember { mutableStateOf(false) }
    var surveiller by remember { mutableStateOf<Item?>(null) }
    // Journal : un contenant de plus dans la rangée, mais qui montre l'histoire
    // au lieu du contenu.
    var journal by remember { mutableStateOf(false) }
    var lignes by remember { mutableStateOf(emptyList<MovementStore.Movement>()) }
    var filtreJournal by remember { mutableStateOf(0) }   // 0 tout, 1 entrées, 2 sorties
    var viderJournal by remember { mutableStateOf(false) }
    val portee = rememberCoroutineScope()

    suspend fun charger(force: Boolean) {
        occupe = true
        erreur = null
        repository.cached(entry)?.let { entity = it }
        try {
            entity = repository.refresh(entry, force)
        } catch (echec: ApiException) {
            erreur = echec.message
        }
        entity?.let {
            alertes = watches.alerts(it) { fiche -> repository.nameOf(fiche) } +
                volumeAlerts(it)
            // Comparer au dernier état connu et journaliser ce qui a bougé. Un
            // état identique ne produit rien, l'appel est donc sans effet quand
            // l'API a resservi le même document.
            movements.record(entry, it)
            lignes = movements.history(entry)
        }
        occupe = false
    }

    LaunchedEffect(entry.id) { charger(force = false) }

    val courant = entity
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(courant?.name ?: entry.label.ifEmpty { entry.id }) },
                navigationIcon = {
                    IconButton(onClick = onBack) { Symbole("←") }
                },
                actions = {
                    // Zoom : le pas est de 16 points, de 48 à 160.
                    IconButton(
                        onClick = { preferences.zoom(-Preferences.STEP) },
                        enabled = preferences.canZoomOut,
                    ) { Symbole("−") }
                    IconButton(
                        onClick = { preferences.zoom(Preferences.STEP) },
                        enabled = preferences.canZoomIn,
                    ) { Symbole("+") }
                    if (alertes.isNotEmpty()) {
                        TextButton(onClick = { voirAlertes = true }) {
                            Text("🔔 ${alertes.size}")
                        }
                    }
                    IconButton(onClick = { portee.launch { charger(force = true) } }) {
                        Symbole("⟳")
                    }
                },
            )
        },
    ) { marges ->
        Column(Modifier.fillMaxSize().padding(marges)) {
            erreur?.let {
                Text(
                    it,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                )
            }

            val inventaires = courant?.inventories.orEmpty()
            if (inventaires.isNotEmpty()) {
                // Un bouton par groupe — Personnage, Mektoub, Zig, Coffres —
                // et un menu déroulant dès qu'un groupe compte plusieurs
                // contenants : sept bêtes ne tiennent pas sur une ligne.
                val groupes = inventaires.withIndex().groupBy { it.value.group }
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(groupes.entries.toList()) { (nom, membres) ->
                        GroupPicker(
                            titre = nom.ifEmpty { "Inventaires" },
                            membres = membres,
                            choisi = if (journal) -1 else contenant,
                            onChoisir = { contenant = it; journal = false },
                        )
                    }
                    // Le journal prend sa place au bout de la rangée, à côté du
                    // menu des coffres : c'est une vue de plus sur la même
                    // entité, pas un autre écran.
                    item {
                        FilterChip(
                            selected = journal,
                            onClick = { journal = true },
                            label = { Text("🕘 Journal") },
                        )
                    }
                }
            }

            when {
                occupe && courant == null ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        CircularProgressIndicator()
                    }

                journal -> JournalView(
                    lignes = lignes,
                    filtre = filtreJournal,
                    onFiltre = { filtreJournal = it },
                    recherche = recherche,
                    onRecherche = { recherche = it },
                    nameOf = { repository.nameOf(it) },
                    onVider = { viderJournal = true },
                )

                inventaires.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        Text("Aucun inventaire", textAlign = TextAlign.Center)
                    }

                else -> {
                    val tous = inventaires[contenant.coerceIn(inventaires.indices)].items
                    // La recherche porte sur le nom lisible et sur la fiche :
                    // sans pack chargé, il ne reste que la fiche.
                    val cherche = normalise(recherche.trim())
                    val filtres = if (cherche.isEmpty()) tous else tous.filter {
                        cherche in normalise(repository.nameOf(it.sheet)) ||
                            cherche in normalise(it.sheet)
                    }
                    val items = sortItems(filtres, tri) { repository.nameOf(it.sheet) }
                    OutlinedTextField(
                        value = recherche,
                        onValueChange = { recherche = it },
                        label = { Text("Rechercher") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                            .padding(horizontal = 12.dp, vertical = 4.dp),
                    )
                    // Le tri par famille réunit les matières premières par
                    // matière, du plus bas niveau au plus haut.
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(SortOrder.entries) { ordre ->
                            FilterChip(
                                selected = ordre == tri,
                                onClick = { tri = ordre },
                                label = { Text(ordre.label) },
                            )
                        }
                    }
                    if (items.isEmpty()) {
                        Box(Modifier.fillMaxSize(), Alignment.Center) {
                            Text("Rien ne correspond", textAlign = TextAlign.Center)
                        }
                        return@Column
                    }
                    LazyVerticalGrid(
                        columns = GridCells.Adaptive(minSize = preferences.cellSize.dp),
                        modifier = Modifier.fillMaxSize().padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(items, key = { it.id.ifEmpty { it.sheet + it.slot } }) { item ->
                            ItemCell(
                                item = item,
                                surveille = watches.isWatched(item),
                                onClick = { detail = item },
                                onLongClick = { surveiller = item },
                            )
                        }
                    }
                }
            }
        }
    }

    detail?.let { item ->
        ItemDialog(item, repository.nameOf(item.sheet)) { detail = null }
    }

    if (voirAlertes) {
        AlertDialog(
            onDismissRequest = { voirAlertes = false },
            title = { Text("Alertes") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    alertes.forEach { alerte ->
                        Column {
                            Text(alerte.title,
                                 style = MaterialTheme.typography.titleSmall)
                            Text(alerte.detail,
                                 style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { voirAlertes = false }) { Text("Fermer") }
            },
        )
    }

    if (viderJournal) {
        AlertDialog(
            onDismissRequest = { viderJournal = false },
            title = { Text("Vider le journal ?") },
            text = {
                Text("Les ${lignes.size} mouvements enregistrés seront perdus. " +
                     "L'API ne permet pas de les reconstruire.")
            },
            confirmButton = {
                TextButton(onClick = {
                    viderJournal = false
                    portee.launch {
                        movements.clear(entry)
                        lignes = movements.history(entry)
                    }
                }) { Text("Vider") }
            },
            dismissButton = {
                TextButton(onClick = { viderJournal = false }) { Text("Annuler") }
            },
        )
    }

    surveiller?.let { item ->
        WatchDialog(
            nom = repository.nameOf(item.sheet),
            actuel = watches.watchOf(item),
            surQuantite = WatchStore.kindOf(item) == WatchStore.Kind.QUANTITY,
            onRemove = {
                watches.remove(item)
                surveiller = null
                entity?.let { alertes = watches.alerts(it) { f -> repository.nameOf(f) } +
                    volumeAlerts(it) }
            },
            onWatch = { seuil ->
                watches.add(item, seuil)
                surveiller = null
                entity?.let { alertes = watches.alerts(it) { f -> repository.nameOf(f) } +
                    volumeAlerts(it) }
            },
            onDismiss = { surveiller = null },
        )
    }
}

/** Sur un écran de téléphone, la date tient sur la ligne du dessous. */
private val HORODATAGE: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm").withZone(ZoneId.systemDefault())

private val ENTREE = Color(0xFF4CAF50)
private val SORTIE = Color(0xFFE05252)

/**
 * Le journal : ce qui est entré et sorti, du plus récent au plus ancien.
 *
 * Une ligne par mouvement, en deux étages — la quantité et l'objet d'abord,
 * parce que c'est ce qu'on cherche ; la date et le contenant en dessous, en
 * petit. Sur un téléphone, tout mettre sur une ligne rendait les noms d'items
 * illisibles.
 */
@Composable
private fun JournalView(
    lignes: List<MovementStore.Movement>,
    filtre: Int,
    onFiltre: (Int) -> Unit,
    recherche: String,
    onRecherche: (String) -> Unit,
    nameOf: (String) -> String,
    onVider: () -> Unit,
) {
    val cherche = normalise(recherche.trim())
    val retenues = lignes.filter { mouvement ->
        when (filtre) {
            1 -> mouvement.delta > 0
            2 -> mouvement.delta < 0
            else -> true
        } && (cherche.isEmpty() ||
            cherche in normalise(nameOf(mouvement.sheet)) ||
            cherche in normalise(mouvement.invLabel))
    }

    Column(Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = recherche,
            onValueChange = onRecherche,
            label = { Text("Rechercher") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
        )
        LazyRow(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(listOf("Tout", "Entrées", "Sorties").withIndex().toList()) { (rang, nom) ->
                FilterChip(
                    selected = rang == filtre,
                    onClick = { onFiltre(rang) },
                    label = { Text(nom) },
                )
            }
            if (lignes.isNotEmpty()) {
                item {
                    FilterChip(
                        selected = false,
                        onClick = onVider,
                        label = { Text("Vider") },
                    )
                }
            }
        }

        if (retenues.isEmpty()) {
            Box(Modifier.fillMaxSize(), Alignment.Center) {
                Text(
                    if (lignes.isEmpty())
                        "Aucun mouvement enregistré.\nLe journal se remplit à chaque " +
                            "relève où quelque chose a bougé."
                    else "Rien ne correspond",
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(24.dp),
                )
            }
            return@Column
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            items(retenues) { mouvement ->
                Row(Modifier.fillMaxWidth()) {
                    Text(
                        text = (if (mouvement.delta > 0) "+" else "") + mouvement.delta,
                        color = if (mouvement.delta > 0) ENTREE else SORTIE,
                        style = MaterialTheme.typography.titleSmall,
                        textAlign = TextAlign.End,
                        modifier = Modifier.width(64.dp).padding(end = 10.dp),
                    )
                    Column {
                        Text(
                            nameOf(mouvement.sheet) +
                                if (mouvement.quality > 0) " Q${mouvement.quality}" else "",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(
                            "${HORODATAGE.format(Instant.ofEpochSecond(mouvement.at))} · " +
                                mouvement.invLabel,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

/** Mise sous surveillance : un seuil, et de quoi la lever. */
@Composable
private fun WatchDialog(
    nom: String,
    actuel: WatchStore.Watch?,
    surQuantite: Boolean,
    onRemove: () -> Unit,
    onWatch: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    var seuil by remember {
        mutableStateOf((actuel?.threshold ?: if (surQuantite) 10 else 50).toString())
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Surveiller $nom") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    if (surQuantite)
                        "Alerte quand la quantité en réserve descend sous le seuil."
                    else "Alerte quand la durabilité descend sous le seuil.",
                    style = MaterialTheme.typography.bodySmall,
                )
                OutlinedTextField(
                    value = seuil,
                    onValueChange = { seuil = it.filter(Char::isDigit).take(5) },
                    label = { Text("Seuil") },
                    singleLine = true,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onWatch(seuil.toIntOrNull() ?: 0) }) {
                Text(if (actuel == null) "Surveiller" else "Modifier")
            }
        },
        dismissButton = {
            if (actuel == null) TextButton(onClick = onDismiss) { Text("Annuler") }
            else TextButton(onClick = onRemove) { Text("Ne plus surveiller") }
        },
    )
}

/** Une case d'item : son icône, sa qualité, sa pile, et l'œil du guet. */
@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ItemCell(
    item: Item,
    surveille: Boolean,
    onClick: () -> Unit,
    onLongClick: () -> Unit,
) {
    Card(
        modifier = Modifier.aspectRatio(1f)
            .combinedClickable(onClick = onClick, onLongClick = onLongClick),
    ) {
        Box(Modifier.fillMaxSize()) {
            AsyncImage(
                model = RyzomApi.itemIconUrl(item),
                contentDescription = item.sheet,
                modifier = Modifier.fillMaxSize().padding(4.dp),
            )
            // Ni qualité ni quantité par-dessus : l'API les dessine déjà dans
            // l'icône, par `&q=` et `&s=`. Les répéter masquait le dessin.
            if (surveille) {
                Text(
                    "👁",
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.align(Alignment.TopEnd).padding(2.dp),
                )
            }
        }
    }
}

/**
 * Les symboles de la barre du haut — retour, zoom, rafraîchir.
 *
 * Ce sont des caractères, pas des dessins : à la taille du texte courant ils
 * étaient minuscules au bout du doigt.
 */
@Composable
private fun Symbole(caractere: String) {
    Text(caractere, fontSize = 24.sp, fontWeight = FontWeight.Medium)
}

/**
 * Un groupe de contenants : bouton simple s'il n'y en a qu'un, menu déroulant
 * sinon. Le nombre d'items est rappelé à côté de chaque nom.
 */
@Composable
private fun GroupPicker(
    titre: String,
    membres: List<IndexedValue<net.ryzom.zyroom.model.Inventory>>,
    choisi: Int,
    onChoisir: (Int) -> Unit,
) {
    val actif = membres.any { it.index == choisi }
    if (membres.size == 1) {
        val seul = membres.first()
        FilterChip(
            selected = actif,
            onClick = { onChoisir(seul.index) },
            label = { Text("${seul.value.label} · ${seul.value.items.size}") },
        )
        return
    }

    var ouvert by remember { mutableStateOf(false) }
    Box {
        FilterChip(
            selected = actif,
            onClick = { ouvert = true },
            label = {
                val courant = membres.firstOrNull { it.index == choisi }
                Text(if (courant != null) "${courant.value.label} ▾"
                     else "$titre (${membres.size}) ▾")
            },
        )
        // Une guilde peut aligner des dizaines de coffres : le menu se borne
        // en hauteur et défile.
        DropdownMenu(
            expanded = ouvert,
            onDismissRequest = { ouvert = false },
            modifier = Modifier.heightIn(max = 360.dp),
        ) {
            membres.forEach { membre ->
                DropdownMenuItem(
                    text = { Text("${membre.value.label} · ${membre.value.items.size}") },
                    onClick = {
                        onChoisir(membre.index)
                        ouvert = false
                    },
                )
            }
        }
    }
}

/** Le détail d'un item : son nom lisible quand le pack est chargé. */
@Composable
private fun ItemDialog(item: Item, nom: String, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(nom) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                if (item.quality > 0) Text("Qualité ${item.quality}")
                if (item.stack > 0) Text("Quantité ${item.stack}")
                if (item.hp > 0) Text("Durabilité ${item.hp}")
                if (item.price > 0) Text("Prix ${item.price.toLong()} dappers")
                if (item.continent.isNotEmpty()) Text("Continent ${item.continent}")
                if (item.locked) Text("🔒 Protégé")
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Fermer") } },
    )
}
