package net.ryzom.zyroom.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Button
import android.content.res.Configuration
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.Icon
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import coil.compose.AsyncImage
import net.ryzom.zyroom.R
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.data.UpdateChecker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import net.ryzom.zyroom.model.Entity

/**
 * Les personnages et guildes suivis.
 *
 * On ajoute une entité par sa clé d'API : c'est elle qui porte l'identité, le
 * nom vient de l'API au premier rafraîchissement.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EntitiesScreen(
    store: EntityStore,
    repository: Repository,
    onOpen: (EntityStore.Suivie) -> Unit,
    onMeteo: () -> Unit = {},
) {
    var entrees by remember { mutableStateOf(store.all()) }
    var ajout by remember { mutableStateOf(false) }
    var occupe by remember { mutableStateOf(false) }
    var erreur by remember { mutableStateOf<String?>(null) }
    var maj by remember { mutableStateOf<UpdateChecker.Disponible?>(null) }
    var majEnCours by remember { mutableStateOf(false) }
    var apropos by remember { mutableStateOf(false) }
    var menu by remember { mutableStateOf(false) }
    val contexte = LocalContext.current

    // À chaque retour au premier plan, et non une seule fois par lancement.
    // Un téléphone garde les applications en mémoire des jours durant : une
    // version publiée pendant ce temps restait invisible, et il fallait balayer
    // l'application hors des récentes pour la voir arriver. Personne n'y pense.
    // UpdateChecker garde sa réponse une minute, une bascule d'application ne
    // redemande donc pas le manifeste.
    val cycle = LocalLifecycleOwner.current
    LaunchedEffect(cycle) {
        cycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            maj = UpdateChecker(contexte).check()
        }
    }

    // Les vignettes des entités déjà en cache, pour celles qui n'en ont pas
    // encore. L'adresse se déduit du flux, et le flux n'était relu qu'à
    // l'ouverture d'une entité : après une mise à jour, les cartes restaient
    // nues jusqu'à ce qu'on les ouvre une à une. Ici on lit le cache, sans
    // réseau ; une entité jamais consultée n'a rien à lire et prendra sa
    // vignette à sa première ouverture.
    LaunchedEffect(entrees.size) {
        val manquantes = entrees.filter { it.vignette.isEmpty() }
        if (manquantes.isEmpty()) return@LaunchedEffect
        manquantes.forEach { entree ->
            val connue = repository.cached(entree) ?: return@forEach
            store.rename(entree, connue.name, connue.portraitUrl)
        }
        entrees = store.all()
    }

    // Import du `string_client.pack` : sur un téléphone, il n'y a pas
    // d'installation de Ryzom où aller le chercher.
    val portee = rememberCoroutineScope()
    val importer = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) portee.launch {
            val cible = File(contexte.filesDir, "string_client.pack")
            withContext(Dispatchers.IO) {
                runCatching {
                    contexte.contentResolver.openInputStream(uri)!!.use { entree ->
                        cible.outputStream().use { entree.copyTo(it) }
                    }
                }
            }
            repository.loadNames(cible) { null }
        }
    }

    Scaffold(
        topBar = {
            // Couché, l'écran n'a plus que la moitié de sa hauteur : le titre
            // en prenait le tiers et ne laissait voir qu'une carte et demie.
            // Il se réduit donc, au lieu de tout repousser hors de l'écran.
            val paysage = LocalConfiguration.current.orientation ==
                Configuration.ORIENTATION_LANDSCAPE
            CenterAlignedTopAppBar(
                // La hauteur d'une barre de titre comprend l'encoche et la
                // barre d'état du téléphone : quatre-vingt-quatre points n'en
                // laissaient qu'une cinquantaine à la lettre, et la gothique y
                // perdait ses hampes. Cent vingt lui vont.
                modifier = Modifier.height(if (paysage) 76.dp else 120.dp),
                title = {
                    // Le V de la gothique se lit comme un U : il est composé à
                    // part, dans une capitale romaine gravée, qui le dessine
                    // sans ambiguïté. Le reste garde le lettrage gothique, et
                    // l'or est le même pour les deux.
                    val corps = if (paysage) 34.sp else 58.sp
                    Text(
                        buildAnnotatedString {
                            withStyle(SpanStyle(
                                fontFamily = Capitale,
                                fontSize = corps * 0.86f,
                            )) { append("V") }
                            withStyle(SpanStyle(fontFamily = Titrage)) { append("-RyLune") }
                        },
                        fontSize = corps,
                        lineHeight = corps * 1.07f,
                        color = MaterialTheme.colorScheme.secondary,
                    )
                },
                actions = {
                    // Le nombre de noms chargés n'apprenait rien à personne : on
                    // ne charge un pack qu'une fois, et savoir qu'il y en a huit
                    // mille quatre cent trente ne se traduit par aucune décision.
                    // L'import reste joignable, dans le menu, pour le jour où une
                    // mise à jour du jeu ajoute des items.
                    Box {
                        IconButton(onClick = { menu = true }) {
                            Icon(Icons.Filled.MoreVert, "Menu",
                                 modifier = Modifier.size(30.dp))
                        }
                        DropdownMenu(
                            expanded = menu,
                            onDismissRequest = { menu = false },
                        ) {
                            DropdownMenuItem(
                                text = { Text("Charger les noms d'items…") },
                                onClick = {
                                    menu = false
                                    importer.launch(arrayOf("*/*"))
                                },
                            )
                            DropdownMenuItem(
                                text = { Text("Météo et sources…") },
                                onClick = { menu = false; onMeteo() },
                            )
                            DropdownMenuItem(
                                text = { Text("À propos") },
                                onClick = { menu = false; apropos = true },
                            )
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { ajout = true }) { Text("+") }
        },
    ) { marges ->
      Column(Modifier.fillMaxSize().padding(marges)) {
        maj?.let { disponible ->
            BandeauMiseAJour(disponible, majEnCours) {
                majEnCours = true
                portee.launch {
                    val echec = UpdateChecker(contexte)
                        .telechargerEtInstaller(disponible.url)
                    majEnCours = false
                    if (echec != null) erreur = echec
                }
            }
        }
        if (entrees.isEmpty()) {

            Box(Modifier.weight(1f).fillMaxWidth(), Alignment.Center) {
                Text(
                    "Aucune entité.\nAjoutez un personnage ou une guilde par sa clé d'API.",
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
        } else {
          // Le coffre en filigrane occupe le vide sous les cartes. Derrière la
          // liste et non après elle : ainsi il reste au même endroit qu'on suive
          // deux entités ou dix, et les cartes, opaques, passent devant.
          Box(Modifier.weight(1f).fillMaxWidth()) {
            Image(
                painter = painterResource(R.mipmap.ic_launcher_foreground),
                contentDescription = null,
                alpha = 0.18f,
                modifier = Modifier.align(Alignment.Center).size(340.dp),
            )
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(entrees, key = { "${it.kind}-${it.id}" }) { entree ->
                    Card(
                        modifier = Modifier.fillMaxWidth().clickable { onOpen(entree) },
                        // Le vert de l'application, celui du bouton « + ».
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                        ),
                    ) {
                        Row(
                            Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            // Le rendu 3D du personnage, ou l'emblème de la
                            // guilde. Rien tant que l'API n'a pas répondu une
                            // première fois : l'adresse se déduit du flux.
                            if (entree.vignette.isNotEmpty()) {
                                // Une vignette carrée, à la hauteur qu'occupent
                                // déjà les deux lignes de texte : la carte garde
                                // ainsi exactement la taille qu'elle avait avant
                                // qu'on l'illustre.
                                AsyncImage(
                                    model = entree.vignette,
                                    contentDescription = null,
                                    modifier = Modifier.size(44.dp)
                                        .padding(end = 12.dp),
                                )
                            }
                            Column {
                                Text(
                                    entree.label.ifEmpty { entree.id },
                                    style = MaterialTheme.typography.titleMedium,
                                )
                                Text(
                                    if (entree.kind == Entity.Kind.CHARACTER) "Personnage"
                                    else "Guilde",
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                        }
                    }
                }
            }
          }
        }
        // Le crédit reste sous les yeux, en dehors de la liste qui défile : la
        // licence veut que l'interface le porte, pas seulement le dépôt.
        LigneSignature { apropos = true }
      }
    }

    if (apropos) AboutDialog { apropos = false }

    if (ajout) {
        AddEntityDialog(
            onDismiss = { ajout = false },
            occupe = occupe,
            erreur = erreur,
            onAdd = { cles ->
                portee.launch {
                    occupe = true
                    erreur = null
                    try {
                        // L'API rend le nom et l'identifiant : inutile de les
                        // demander à l'utilisateur.
                        val trouvees = repository.discover(cles)
                        trouvees.forEach { (cle, entite) ->
                            store.add(EntityStore.Suivie(
                                id = entite.id, kind = entite.kind,
                                apiKey = cle, label = entite.name))
                        }
                        entrees = store.all()
                        if (trouvees.isEmpty()) {
                            erreur = "Aucune clé n'a été acceptée."
                        } else {
                            ajout = false
                        }
                    } catch (echec: ApiException) {
                        erreur = echec.message
                    }
                    occupe = false
                }
            },
        )
    }
}

@Composable
private fun AddEntityDialog(
    onDismiss: () -> Unit,
    onAdd: (List<String>) -> Unit,
    occupe: Boolean,
    erreur: String?,
) {
    val contexte = LocalContext.current
    val presse = LocalClipboardManager.current
    var saisie by remember { mutableStateOf("") }

    // Une clé fait 41 caractères ; on en accepte plusieurs, séparées par ce
    // qu'on veut — retour à la ligne, espace, virgule.
    val cles = remember(saisie) {
        saisie.split(Regex("[\\s,;]+")).map(String::trim).filter(String::isNotEmpty)
    }
    val bonnes = cles.filter(RyzomApi::isApiKey)
    val mauvaises = cles - bonnes.toSet()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Ajouter une clé d'API") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    "Une clé fait 41 caractères. Celles de personnage commencent " +
                        "par « c », celles de guilde par « g ». On peut en coller " +
                        "plusieurs d'un coup.",
                    style = MaterialTheme.typography.bodySmall,
                )
                OutlinedTextField(
                    value = saisie,
                    onValueChange = { saisie = it },
                    label = { Text("Clé(s) d'API") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth(),
                )
                Row2 {
                    TextButton(onClick = {
                        presse.getText()?.text?.let { saisie = it.toString() }
                    }) { Text("Coller") }
                    TextButton(onClick = {
                        contexte.startActivity(
                            Intent(Intent.ACTION_VIEW, Uri.parse(RyzomApi.KEY_PAGE)))
                    }) { Text("Obtenir ma clé") }
                }
                if (mauvaises.isNotEmpty()) {
                    Text(
                        "Ignorée${if (mauvaises.size > 1) "s" else ""} : " +
                            mauvaises.joinToString(", ") { it.take(8) + "…" },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
                erreur?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall,
                         color = MaterialTheme.colorScheme.error)
                }
                if (occupe) {
                    Text("Interrogation de l'API…",
                         style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onAdd(bonnes) },
                enabled = bonnes.isNotEmpty() && !occupe,
            ) { Text(if (bonnes.size > 1) "Ajouter ${bonnes.size} clés" else "Ajouter") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Annuler") } },
    )
}

/** Deux boutons côte à côte — une ligne, sans plus de cérémonie. */
@Composable
private fun Row2(content: @Composable () -> Unit) {
    androidx.compose.foundation.layout.Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) { content() }
}

/** Rappel : le bouton de retrait viendra avec l'appui long, écran suivant. */
@Suppress("unused")
@Composable
private fun PlaceholderRemove(onClick: () -> Unit) {
    IconButton(onClick = onClick) { Text("×") }
}

/**
 * L'annonce d'une nouvelle version, en tête de l'écran d'accueil.
 *
 * Elle ne s'affiche que s'il y a effectivement quelque chose de plus récent.
 * Le bouton télécharge l'APK et le présente au système : c'est Android qui
 * demande ensuite confirmation, rien ne s'installe sans l'accord du joueur.
 */
@Composable
private fun BandeauMiseAJour(
    disponible: UpdateChecker.Disponible,
    occupe: Boolean,
    onInstaller: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("Une nouvelle version est disponible",
                 style = MaterialTheme.typography.titleMedium)
            Text("Version ${disponible.versionName}",
                 style = MaterialTheme.typography.bodySmall)
            Button(
                onClick = onInstaller,
                enabled = !occupe,
                modifier = Modifier.padding(top = 10.dp),
            ) {
                Text(if (occupe) "Téléchargement…" else "Télécharger et installer")
            }
        }
    }
}
