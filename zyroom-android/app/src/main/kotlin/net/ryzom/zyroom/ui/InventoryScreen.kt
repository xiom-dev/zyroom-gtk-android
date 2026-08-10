package net.ryzom.zyroom.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import kotlinx.coroutines.launch
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.data.Alert
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.OutpostStore
import net.ryzom.zyroom.data.Preferences
import net.ryzom.zyroom.data.WatchStore
import net.ryzom.zyroom.data.volumeAlerts
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.Outpost
import net.ryzom.zyroom.model.Skill
import net.ryzom.zyroom.model.SkillPoints
import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.SortOrder
import net.ryzom.zyroom.model.chercheDansTout
import net.ryzom.zyroom.model.finishedSkills
import net.ryzom.zyroom.model.skillTree
import net.ryzom.zyroom.model.sortItems
import net.ryzom.zyroom.model.visibleSkills
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Ce que la rangée du haut donne à voir : un contenant, le journal, l'arbre. */
private enum class Vue { INVENTAIRE, JOURNAL, COMPETENCES, AVANTPOSTES }

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
    outposts: OutpostStore,
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
    // Journal et compétences prennent leur place dans la rangée des contenants,
    // mais montrent autre chose que le contenu d'un coffre. Une seule vue à la
    // fois : un état à trois valeurs, plutôt que deux booléens dont l'un pourrait
    // contredire l'autre.
    var vue by remember { mutableStateOf(Vue.INVENTAIRE) }
    var lignes by remember { mutableStateOf(emptyList<MovementStore.Movement>()) }
    var filtreJournal by remember { mutableStateOf(0) }   // 0 tout, 1 entrées, 2 sorties
    var viderJournal by remember { mutableStateOf(false) }
    // La carte des avant-postes ne dépend d'aucune clé : elle vient de
    // l'annuaire public des guildes, et n'est demandée qu'à l'ouverture de
    // l'onglet — un demi-méga-octet n'a pas à partir au démarrage.
    var carte by remember { mutableStateOf<List<Outpost>?>(null) }
    var changements by remember { mutableStateOf(emptyList<OutpostStore.Change>()) }
    var premierReleve by remember { mutableStateOf(false) }
    var erreurCarte by remember { mutableStateOf<String?>(null) }
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

    suspend fun chargerCarte(force: Boolean) {
        erreurCarte = null
        premierReleve = outposts.jamaisReleve()
        try {
            val relevee = repository.outposts(force)
            changements = outposts.record(relevee).let { outposts.history() }
            carte = relevee
        } catch (echec: ApiException) {
            erreurCarte = echec.message
        }
    }

    LaunchedEffect(entry.id) { charger(force = false) }

    LaunchedEffect(vue) {
        if (vue == Vue.AVANTPOSTES && carte == null) chargerCarte(force = false)
    }

    val courant = entity
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(courant?.name ?: entry.label.ifEmpty { entry.id }) },
                navigationIcon = {
                    // Un vrai dessin plutôt qu'un caractère « ← » : le trait de
                    // la police est fin, et la flèche se voyait à peine. Celle-ci
                    // se retourne d'elle-même sur un téléphone en écriture de
                    // droite à gauche, et porte enfin un nom pour la synthèse
                    // vocale.
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Retour",
                            modifier = Modifier.size(34.dp),
                        )
                    }
                },
                actions = {
                    // Zoom : le pas est de 16 points, de 48 à 160.
                    // Des dessins et non des caractères : « − », « + » et « ⟳ »
                    // n'ont pas la même encre dans leur case, et se retrouvaient
                    // à des hauteurs différentes sur la même ligne. Un icône
                    // Material est centré dans son cadre, par construction.
                    IconButton(
                        onClick = { preferences.zoom(-Preferences.STEP) },
                        enabled = preferences.canZoomOut,
                    ) { Moins() }
                    IconButton(
                        onClick = { preferences.zoom(Preferences.STEP) },
                        enabled = preferences.canZoomIn,
                    ) { Icon(Icons.Filled.Add, "Agrandir", Modifier.size(30.dp)) }
                    if (alertes.isNotEmpty()) {
                        TextButton(onClick = { voirAlertes = true }) {
                            Text("🔔 ${alertes.size}")
                        }
                    }
                    IconButton(onClick = {
                        portee.launch {
                            if (vue == Vue.AVANTPOSTES) chargerCarte(force = true)
                            else charger(force = true)
                        }
                    }) {
                        Icon(Icons.Filled.Refresh, "Rafraîchir", Modifier.size(30.dp))
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
            // La rangée reste là pour un personnage sans le moindre contenant :
            // ses compétences, elles, sont consultables.
            if (inventaires.isNotEmpty() || courant?.skills?.isNotEmpty() == true) {
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
                            choisi = if (vue == Vue.INVENTAIRE) contenant else -1,
                            onChoisir = { contenant = it; vue = Vue.INVENTAIRE },
                        )
                    }
                    // Le journal prend sa place au bout de la rangée, à côté du
                    // menu des coffres : c'est une vue de plus sur la même
                    // entité, pas un autre écran.
                    item {
                        FilterChip(
                            selected = vue == Vue.JOURNAL,
                            onClick = { vue = Vue.JOURNAL },
                            label = { Text("📗 Journal") },
                        )
                    }
                    // Les compétences ne concernent qu'un personnage, et encore
                    // faut-il que la clé accorde le module de l'API : la puce ne
                    // s'affiche que si le flux en a rendu.
                    if (courant?.skills?.isNotEmpty() == true) {
                        item {
                            FilterChip(
                                selected = vue == Vue.COMPETENCES,
                                onClick = { vue = Vue.COMPETENCES },
                                label = { Text("🎓 Compétences") },
                            )
                        }
                    }
                    // Les avant-postes appartiennent aux guildes : la puce n'a
                    // rien à faire sur un personnage.
                    if (entry.kind == Entity.Kind.GUILD) {
                        item {
                            FilterChip(
                                selected = vue == Vue.AVANTPOSTES,
                                onClick = { vue = Vue.AVANTPOSTES },
                                label = { Text("⚔️ Avant-postes") },
                            )
                        }
                    }
                }
            }

            // Le message du jour de la guilde, entre la rangée des contenants et
            // la recherche : sous ce qui sert à naviguer, au-dessus de ce qui
            // sert à chercher. Un personnage n'en a pas — l'API ne le rend que
            // pour une guilde.
            courant?.motd?.takeIf { it.isNotBlank() }?.let { Motd(it) }

            when {
                occupe && courant == null ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        CircularProgressIndicator()
                    }

                vue == Vue.JOURNAL -> JournalView(
                    lignes = lignes,
                    filtre = filtreJournal,
                    onFiltre = { filtreJournal = it },
                    recherche = recherche,
                    onRecherche = { recherche = it },
                    nameOf = { repository.nameOf(it) },
                    onVider = { viderJournal = true },
                )

                vue == Vue.COMPETENCES -> SkillsView(
                    skills = courant?.skills.orEmpty(),
                    points = courant?.skillPoints.orEmpty(),
                    recherche = recherche,
                    onRecherche = { recherche = it },
                    nameOf = { repository.nameOf(it) },
                )

                vue == Vue.AVANTPOSTES -> OutpostsView(
                    carte = carte,
                    changements = changements,
                    premierReleve = premierReleve,
                    erreur = erreurCarte,
                    guilde = courant?.name ?: entry.label,
                    nameOf = { repository.nameOf(it) },
                )

                inventaires.isEmpty() ->
                    Box(Modifier.fillMaxSize(), Alignment.Center) {
                        Text("Aucun inventaire", textAlign = TextAlign.Center)
                    }

                else -> {
                    // Chercher, c'est chercher partout : voir chercheDansTout.
                    val parContenant = chercheDansTout(
                        inventaires = inventaires,
                        contenantChoisi = contenant,
                        recherche = recherche,
                        order = tri,
                        nameOf = { repository.nameOf(it.sheet) },
                        normalise = ::normalise,
                    )
                    val items = parContenant.flatMap { it.second }
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
                        parContenant.forEach { (contenantNom, trouves) ->
                            // Le nom du contenant, sur toute la largeur, entre
                            // deux groupes. Il ne paraît qu'en cherchant : sans
                            // lui, trouver l'objet ne dirait pas où il est, ce
                            // qui est justement la question posée.
                            if (parContenant.size > 1) {
                                item(span = { GridItemSpan(maxLineSpan) }) {
                                    // Le nom et le compte sur deux textes, non
                                    // sur un seul : les coffres de guilde ont
                                    // des noms à rallonge — « Coffre 6 — La
                                    // Forge Lunaire (Craft Armes 2/3) » — et
                                    // une seule chaîne se faisait couper en
                                    // plein milieu, emportant le compte avec
                                    // elle. Ici le nom s'abrège, le compte
                                    // reste.
                                    Row(
                                        Modifier.fillMaxWidth()
                                            .padding(top = 6.dp, bottom = 2.dp),
                                        verticalAlignment = Alignment.CenterVertically,
                                    ) {
                                        Text(
                                            contenantNom,
                                            style = MaterialTheme.typography.titleSmall,
                                            color = MaterialTheme.colorScheme.secondary,
                                            maxLines = 1,
                                            overflow = TextOverflow.Ellipsis,
                                            modifier = Modifier.weight(1f, fill = false),
                                        )
                                        Text(
                                            "  ${trouves.size}",
                                            style = MaterialTheme.typography.titleSmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                }
                            }
                            items(trouves,
                                  key = { "$contenantNom-${it.id.ifEmpty { it.sheet + it.slot }}" }
                            ) { item ->
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
            contentPadding = PaddingValues(vertical = 8.dp),
        ) {
            // Le retrait latéral passe dans la ligne : la bande de couleur doit
            // aller d'un bord à l'autre, sinon elle flotte au milieu.
            itemsIndexed(retenues) { rang, mouvement ->
                Row(
                    Modifier.fillMaxWidth()
                        .background(fondZebre(rang % 2 == 0))
                        .padding(horizontal = 12.dp, vertical = 7.dp),
                ) {
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

/**
 * L'arbre des compétences : quatre branches dépliables, niveau et avancement.
 *
 * Le code d'une compétence contient celui de son parent — `sf` « Combat », `sfm`
 * « Mêlée », `sfms` « Manier épée ». La hiérarchie n'a donc pas à être décrite :
 * elle se déduit des préfixes, et l'ordre alphabétique des codes est déjà celui
 * de l'arbre. La profondeur compte les codes qui préfixent le nôtre, ce qui reste
 * juste même si l'API saute un échelon.
 *
 * Cent soixante-quatorze lignes sur un écran de téléphone : **toute compétence
 * qui a des descendants se plie**, pas seulement les quatre racines. Ouvrir
 * Artisanat d'un coup déversait cent sept lignes ; échelon par échelon, on
 * descend où l'on veut. Tout est replié au départ, et une compétence n'apparaît
 * que si tous ses parents sont ouverts.
 *
 * Une recherche, elle, traverse tout — chercher « épée » et ne rien voir parce
 * que la branche est fermée serait absurde.
 */
@Composable
private fun SkillsView(
    skills: List<Skill>,
    points: Map<String, SkillPoints>,
    recherche: String,
    onRecherche: (String) -> Unit,
    nameOf: (String) -> String,
) {
    // L'arbre ne change pas d'une frappe à l'autre : il se calcule une fois.
    val arbre = remember(skills) { skillTree(skills) }
    val finies = remember(arbre) { finishedSkills(arbre) }
    // Une teinte par sous-branche, dans l'ordre de l'arbre : « Magie
    // salvatrice » et « Magie destructrice » ne se confondent plus, et la
    // couleur ne bouge pas quand on plie et déplie.
    val teintes = remember(arbre) {
        arbre.filter { it.depth == 1 }
            .groupBy { it.root }
            .flatMap { (_, freres) ->
                freres.mapIndexed { rang, noeud ->
                    noeud.skill.code to OrangesDuCoffre[rang % OrangesDuCoffre.size]
                }
            }.toMap()
    }
    var depliees by remember(skills) { mutableStateOf(emptySet<String>()) }
    var enCoursSeulement by remember { mutableStateOf(false) }

    val cherche = normalise(recherche.trim())
    // Chercher ou ne garder que ce qui monte, c'est demander une réponse, pas un
    // arbre : on passe alors en liste plate, sans branche ni retrait. L'arbre
    // repliable ne sert que la consultation, filtres au repos.
    val filtrant = cherche.isNotEmpty() || enCoursSeulement
    val visibles = if (filtrant) {
        arbre.filter { noeud ->
            (!enCoursSeulement || noeud.skill.progress > 0) &&
                (cherche.isEmpty() || cherche in normalise(nameOf(noeud.skill.code)))
        }
    } else {
        visibleSkills(arbre, depliees)
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
            item {
                FilterChip(
                    selected = !enCoursSeulement,
                    onClick = { enCoursSeulement = false },
                    label = { Text("Tout") },
                )
            }
            item {
                FilterChip(
                    selected = enCoursSeulement,
                    onClick = { enCoursSeulement = true },
                    label = { Text("En cours") },
                )
            }
            // Un seul bouton plutôt que deux : son nom dit ce qu'il va faire,
            // et il n'y a jamais qu'une action sensée à proposer. Il disparaît
            // quand une recherche ou un filtre est actif, la liste étant alors
            // plate et le repli sans objet.
            if (!filtrant) {
                item {
                    val quelqueChoseOuvert = depliees.isNotEmpty()
                    FilterChip(
                        selected = false,
                        onClick = {
                            depliees = if (quelqueChoseOuvert) emptySet()
                                       else arbre.filter { it.hasChildren }
                                           .map { it.skill.code }.toSet()
                        },
                        label = {
                            Text(if (quelqueChoseOuvert) "Tout replier"
                                 else "Tout déplier")
                        },
                    )
                }
            }
        }

        if (visibles.isEmpty()) {
            Box(Modifier.fillMaxSize(), Alignment.Center) {
                Text(
                    if (enCoursSeulement && cherche.isEmpty())
                        "Aucune compétence en train de monter.\nL'API ne donne " +
                            "l'avancement que des niveaux entamés."
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
            contentPadding = PaddingValues(vertical = 8.dp),
        ) {
            // Le retrait latéral passe dans la ligne : la bande de couleur doit
            // aller d'un bord à l'autre. Le zébrage suit ce qui est affiché,
            // plié ou déplié — c'est le rang à l'écran qui compte, pas la place
            // dans l'arbre.
            itemsIndexed(visibles, key = { _, r -> r.skill.code }) { rangee, rang ->
              Box(
                  Modifier.fillMaxWidth()
                      .background(fondZebre(rangee % 2 == 0))
                      .padding(horizontal = 12.dp),
              ) {
                if (!filtrant && rang.depth == 0) {
                    Branche(
                        nom = nomDeBranche(rang.skill.code, nameOf),
                        // Le niveau d'une racine plafonne bas — Combat vaut 20 :
                        // c'est le plus haut de ses descendants qui dit où en est
                        // la branche.
                        niveau = arbre.filter { it.root == rang.root }
                            .maxOf { it.skill.level },
                        finie = rang.skill.code in finies,
                        points = points[rang.skill.code],
                        depliee = rang.skill.code in depliees,
                        onBascule = {
                            depliees = if (rang.skill.code in depliees)
                                depliees - rang.skill.code else depliees + rang.skill.code
                        },
                    )
                } else {
                    Competence(
                        nom = nameOf(rang.skill.code),
                        skill = rang.skill,
                        finie = rang.skill.code in finies,
                        teinte = teintes[rang.skill.code],
                        // En liste plate, tout est au même bord et rien ne se
                        // plie : la liste est déjà le résultat d'un filtre.
                        profondeur = if (filtrant) 1 else rang.depth,
                        pliable = !filtrant && rang.hasChildren,
                        depliee = rang.skill.code in depliees,
                        onBascule = {
                            depliees = if (rang.skill.code in depliees)
                                depliees - rang.skill.code else depliees + rang.skill.code
                        },
                    )
                }
              }
            }
        }
    }
}

/**
 * Le nom d'une branche, raccourci quand celui du jeu est trop long.
 *
 * Le pack appelle la branche de forage « Extraire les matières premières » :
 * une phrase là où les trois autres tiennent en un mot, et qui déborde sur un
 * téléphone. Les autres gardent le nom du jeu.
 */
private fun nomDeBranche(code: String, nameOf: (String) -> String): String =
    if (code == "sh") "Extraction" else nameOf(code)

@Composable
private fun Branche(
    nom: String,
    niveau: Int,
    finie: Boolean,
    points: SkillPoints?,
    depliee: Boolean,
    onBascule: () -> Unit,
) {
    Column(
        Modifier.fillMaxWidth()
            .clickable(onClick = onBascule)
            .padding(top = 10.dp, bottom = 4.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(if (depliee) "▾" else "▸", modifier = Modifier.width(20.dp))
            // Les quatre branches dans l'or des titres, comme les peuples du
            // tableau des avant-postes : ce sont les repères qu'on cherche en
            // faisant défiler. Une branche entièrement montée passe au vert,
            // titre compris : c'est ce qui se voit de plus loin.
            val couleur = if (finie) MaterialTheme.colorScheme.primary
                          else MaterialTheme.colorScheme.secondary
            Text(
                nom,
                style = MaterialTheme.typography.titleSmall,
                color = couleur,
                modifier = Modifier.weight(1f),
            )
            Text(
                niveau.toString(),
                style = MaterialTheme.typography.titleSmall,
                color = couleur,
            )
        }
        points?.let {
            Text(
                "%,d points · %,d dépensés".format(Locale.FRANCE, it.available, it.spent),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 20.dp),
            )
        }
    }
}

@Composable
private fun Competence(
    nom: String,
    skill: Skill,
    finie: Boolean,
    /** Nuance d'orange d'une sous-branche ; nulle pour une compétence ordinaire. */
    teinte: Color?,
    profondeur: Int,
    pliable: Boolean = false,
    depliee: Boolean = false,
    onBascule: () -> Unit = {},
) {
    Column(
        Modifier.fillMaxWidth()
            .clickable(enabled = pliable, onClick = onBascule)
            // Un cran de douze points par échelon, à partir du retrait de la
            // flèche des racines. Douze et non vingt : l'arbre descend à cinq
            // échelons, et les noms de l'artisanat sont longs.
            .padding(start = 20.dp + 12.dp * (profondeur - 1), top = 5.dp, bottom = 5.dp),
    ) {
        // Une compétence finie passe au vert, nom compris — et « finie » vaut
        // pour toute la descendance, pas seulement pour la feuille à 250 : le
        // père plafonne à 100 alors que tout ce qu'il porte est monté.
        //
        // Une sous-branche non finie garde sa nuance d'orange : c'est ce qui la
        // distingue de ses voisines quand la liste défile.
        val couleurNom = when {
            finie -> MaterialTheme.colorScheme.primary
            teinte != null -> teinte
            else -> MaterialTheme.colorScheme.onSurface
        }
        val couleurNiveau = when {
            finie || skill.progress > 0 -> MaterialTheme.colorScheme.primary
            teinte != null -> teinte
            else -> MaterialTheme.colorScheme.onSurface
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            // La place de la flèche est tenue même pour une feuille : sans elle,
            // les noms d'un même échelon ne s'aligneraient pas.
            Text(
                if (!pliable) "" else if (depliee) "▾" else "▸",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.width(14.dp),
            )
            Text(
                nom,
                style = MaterialTheme.typography.bodyMedium,
                color = couleurNom,
                fontWeight = if (teinte != null) FontWeight.Medium else null,
                modifier = Modifier.weight(1f),
            )
            Text(
                if (skill.progress > 0) "${skill.level} · ${skill.progress} %"
                else skill.level.toString(),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurNiveau,
            )
        }
        // La barre ne s'affiche que pour un niveau entamé : sur cent soixante-dix
        // lignes, une barre vide partout n'apprendrait rien et alourdirait tout.
        if (skill.progress > 0) {
            LinearProgressIndicator(
                progress = { skill.progress / 100f },
                modifier = Modifier.fillMaxWidth().padding(top = 3.dp, end = 40.dp),
            )
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
 * Le message du jour de la guilde.
 *
 * Replié sur deux lignes, et déplié d'une tape : les officiers y écrivent
 * parfois un paragraphe, qui mangerait la grille d'items sur un écran de
 * téléphone. Le repli ne se signale que quand il coupe quelque chose — un
 * message court n'a pas à porter de « ▾ » qui ne fait rien.
 */
@Composable
private fun Motd(message: String) {
    var deplie by remember(message) { mutableStateOf(false) }
    var coupe by remember(message) { mutableStateOf(false) }
    Surface(
        color = MaterialTheme.colorScheme.surfaceVariant,
        shape = MaterialTheme.shapes.small,
        modifier = Modifier.fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
            .clickable(enabled = coupe || deplie) { deplie = !deplie },
    ) {
        Row(Modifier.padding(horizontal = 10.dp, vertical = 8.dp)) {
            Text("📢", modifier = Modifier.padding(end = 8.dp))
            Text(
                message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = if (deplie) Int.MAX_VALUE else 2,
                overflow = TextOverflow.Ellipsis,
                onTextLayout = { coupe = it.hasVisualOverflow || coupe },
                modifier = Modifier.weight(1f),
            )
            if (coupe || deplie) {
                Text(
                    if (deplie) "▴" else "▾",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }
        }
    }
}

/**
 * Le moins du zoom, dessiné.
 *
 * Material fournit un plus et une flèche de rafraîchissement, mais aucun moins :
 * un trait de deux points sur dix-sept, à l'encre du bouton, reprend exactement
 * la barre horizontale de son plus. Il suit l'état désactivé, `LocalContentColor`
 * portant déjà l'atténuation que le bouton applique à son contenu.
 */
@Composable
private fun Moins() {
    Box(Modifier.size(30.dp), contentAlignment = Alignment.Center) {
        Box(
            Modifier.width(17.dp).height(2.dp)
                .background(LocalContentColor.current, RoundedCornerShape(1.dp)),
        )
    }
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
