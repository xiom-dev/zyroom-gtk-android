package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.data.OutpostStore
import net.ryzom.zyroom.model.Outpost
import net.ryzom.zyroom.model.niveauDe
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/** Les quatre peuples, dans l'ordre où le jeu les présente. */
private val PEUPLES = listOf(
    "fyros" to "Fyros", "matis" to "Matis",
    "tryker" to "Tryker", "zorai" to "Zoraï",
)

// Les mêmes verts et rouges que le journal des mouvements : ce qui entre, ce
// qui sort.
private val ENTREE_OUTPOST = androidx.compose.ui.graphics.Color(0xFF4CAF50)
private val SORTIE_OUTPOST = androidx.compose.ui.graphics.Color(0xFFE05252)

/** Largeurs fixes des deux colonnes de droite, pour que tout s'aligne. */
private val LARGEUR_NIVEAU = 44.dp
private val LARGEUR_GUILDE = 132.dp

/**
 * Le symbole de la pastille — deux flèches qui tournent — **dessiné et non
 * écrit**.
 *
 * Le caractère du recyclage existe (U+267B), mais aucune police d'interface ne
 * le porte : ni Cantarell sous GNOME, ni Roboto ici. Le repli tombe sur Noto
 * Color Emoji, qui l'impose en couleur — un vert qui n'est pas le nôtre, à côté
 * d'un nom qui l'est. Dessiné, le symbole a la couleur qu'on lui donne, la même
 * taille partout, et le même tracé dans les trois portages : `page_outposts.py`
 * répète ces mêmes valeurs pour Cairo et pour QPainter.
 *
 * Les deux arcs, en degrés, dans le sens des aiguilles à l'écran. Rayon et
 * épaisseur sont tenus par une contrainte : la pointe va jusqu'à
 * `rayon + trait * barbe`, et ce total doit rester sous la moitié du côté,
 * sinon la zone de dessin rogne les barbes.
 */
private val PASTILLE_ARCS = listOf(25f to 155f, 205f to 335f)
private const val PASTILLE_RAYON = 0.31f    // du cote de la pastille
private const val PASTILLE_TRAIT = 0.15f    // epaisseur, du cote aussi
private const val PASTILLE_BARBE = 1.20f    // demi-hauteur de la barbe, en parts du trait
private const val PASTILLE_POINTE = 28f     // les degres que la pointe parcourt en plus

/** Le cote de la pastille, et le vert d'accent des deux autres portages. */
private val COTE_PASTILLE = 20.dp
private val VERT_PASTILLE = Color(0xFF7FB3A2)

private val HORODATAGE_JOUR: DateTimeFormatter =
    DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm").withZone(ZoneId.systemDefault())

/**
 * Les avant-postes d'Atys : qui tient quoi, et ce qui a changé de main.
 *
 * La source n'est pas le flux de la guilde — il ne donne que la liste de la
 * sienne, et il faut sa clé — mais l'annuaire public des guildes, qui les
 * déclare toutes. La guilde consultée est mise en avant ; les autres sont là
 * pour situer.
 *
 * Le journal se déduit de deux relevés successifs, comme celui des mouvements :
 * l'API ne garde aucune histoire. Tant qu'il n'y a eu qu'un relevé, il n'a rien
 * à dire, et le texte l'explique plutôt que de laisser croire à un calme plat.
 *
 * Il se signale dans « Qui tient quoi » : [recents] pose une pastille sur les
 * lignes qui ont changé de main, et [nonLus] compte sur la puce du journal
 * celles qui nous concernent. Sans cela, le journal existait et ne se voyait
 * pas — il fallait penser à l'ouvrir.
 */
@Composable
fun OutpostsView(
    carte: List<Outpost>?,
    changements: List<OutpostStore.Change>,
    recents: Map<String, OutpostStore.Change>,
    nonLus: Int,
    premierReleve: Boolean,
    erreur: String?,
    guilde: String,
    nameOf: (String) -> String,
    onJournalOuvert: () -> Unit,
) {
    var journal by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize()) {
        LazyRow(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item {
                FilterChip(
                    selected = !journal,
                    onClick = { journal = false },
                    label = { Text("Qui tient quoi") },
                )
            }
            item {
                FilterChip(
                    selected = journal,
                    // Ouvrir le journal, c'est le lire : le compte tombe a
                    // zero et les pastilles de la carte s'effacent avec lui.
                    onClick = { journal = true; onJournalOuvert() },
                    label = {
                        // Le compte est celui des prises qui nous concernent,
                        // pas celui de tout Atys : un nombre jamais a zero ne
                        // se regarde plus.
                        Text(if (nonLus == 0) "Journal" else "Journal · $nonLus")
                    },
                )
            }
        }

        erreur?.let {
            Text(
                it,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp),
            )
        }

        if (carte == null) {
            Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
            return@Column
        }

        if (journal) Journal(changements, premierReleve, nameOf)
        else Possessions(carte, guilde, recents, nameOf)
    }
}

@Composable
private fun Possessions(
    carte: List<Outpost>,
    guilde: String,
    recents: Map<String, OutpostStore.Change>,
    nameOf: (String) -> String,
) {
    val parPeuple = remember(carte) { carte.groupBy { it.people } }
    val miens = remember(carte, guilde) { carte.count { it.guild == guilde } }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
    ) {
        item {
            Text(
                "${carte.size} avant-postes tenus sur Atys, dont $miens à $guilde.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 8.dp),
            )
        }
        PEUPLES.forEach { (code, nom) ->
            val siens = parPeuple[code].orEmpty()
                // Du plus haut niveau au plus bas, comme on lit une carte de
                // conquête : les enjeux d'abord.
                .sortedWith(compareByDescending<Outpost> { niveauDe(it.code) ?: -1 }
                    .thenBy { nameOf(it.nameKey) })
            if (siens.isEmpty()) return@forEach
            item(key = "peuple-$code") { EnTetePeuple(nom) }
            itemsIndexed(siens, key = { _, o -> o.code }) { rang, avantPoste ->
                Ligne(avantPoste, avantPoste.guild == guilde, rang % 2 == 0,
                      recents[avantPoste.code], recents.isNotEmpty(), nameOf)
            }
        }
        val orphelins = carte.filterNot { PEUPLES.any { (c, _) -> c == it.people } }
        if (orphelins.isNotEmpty()) {
            item(key = "orphelins") {
                Text(
                    "Hors carte : " + orphelins.joinToString(", ") {
                        "${it.code} (${it.guild})"
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 12.dp),
                )
            }
        }
    }
}

/** L'en-tête d'un peuple, qui sert aussi d'en-tête de colonnes. */
@Composable
private fun EnTetePeuple(nom: String) {
    Column(Modifier.padding(top = 14.dp)) {
        // Les quatre peuples sont les repères du tableau : ils doivent se
        // trouver d'un coup d'œil en faisant défiler.
        Text(
            nom,
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.secondary,
        )
        Row(Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 2.dp)) {
            Text("Avant-poste", style = MaterialTheme.typography.labelSmall,
                 color = MaterialTheme.colorScheme.onSurfaceVariant,
                 modifier = Modifier.weight(1f))
            Text("Niv.", style = MaterialTheme.typography.labelSmall,
                 color = MaterialTheme.colorScheme.onSurfaceVariant,
                 textAlign = TextAlign.Center, modifier = Modifier.width(LARGEUR_NIVEAU))
            Text("Guilde", style = MaterialTheme.typography.labelSmall,
                 color = MaterialTheme.colorScheme.onSurfaceVariant,
                 modifier = Modifier.width(LARGEUR_GUILDE))
        }
        HorizontalDivider()
    }
}

/**
 * Une ligne du tableau : l'avant-poste, son niveau, la guilde qui le tient.
 *
 * Trois colonnes, comme sur les sites qui recensent les avant-postes. Le nom
 * peut passer sur deux lignes — « Centre de Recherche de la Promenade
 * Caverneuse » ne tient pas sur un téléphone — et les deux autres colonnes
 * gardent leur largeur pour que les niveaux restent alignés d'une ligne à
 * l'autre.
 */
@Composable
private fun Ligne(
    avantPoste: Outpost,
    notre: Boolean,
    zebre: Boolean,
    change: OutpostStore.Change?,
    pastilles: Boolean,
    nameOf: (String) -> String,
) {
    val niveau = niveauDe(avantPoste.code)
    Row(
        Modifier.fillMaxWidth()
            // Une ligne sur deux teintée du vert de l'application, très
            // diluée : sur trois colonnes dont deux étroites, l'œil perd sa
            // ligne en traversant. Le zébrage la tient mieux qu'un filet, qui
            // hachait la lecture à chaque rang.
            .background(fondZebre(zebre))
            .padding(vertical = 6.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // En tete de ligne, et la colonne n'existe que les jours ou quelque
        // chose a bouge : le reste du temps, reserver sa place volerait
        // vingt points a la colonne des noms pour ne rien y mettre. Les jours
        // ou elle existe, en revanche, elle est reservee sur toutes les
        // lignes -- sans quoi les noms sauteraient d'un rang a l'autre.
        if (pastilles) Pastille(change != null)
        Text(
            nameOf(avantPoste.nameKey),
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = if (notre) FontWeight.Bold else FontWeight.Normal,
            color = if (notre) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f).padding(end = 6.dp),
        )
        Text(
            // Un niveau inconnu se dit, plutôt que de laisser une case vide
            // qu'on prendrait pour un zéro.
            niveau?.toString() ?: "—",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.secondary,
            textAlign = TextAlign.Center,
            modifier = Modifier.width(LARGEUR_NIVEAU),
        )
        Row(
            Modifier.width(LARGEUR_GUILDE),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // L'emblème dit la guilde d'un coup d'œil, mieux que son nom écrit :
            // c'est ce qu'on voit en jeu au-dessus des têtes.
            AsyncImage(
                model = RyzomApi.guildIconUrl(avantPoste.icon),
                contentDescription = null,
                modifier = Modifier.size(28.dp).padding(end = 6.dp),
            )
            Text(
                avantPoste.guild,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

/** Les degres de la carte de conquete, en radians pour le dessin. */
private fun radians(degres: Float): Float = (degres * Math.PI / 180.0).toFloat()

/**
 * Deux arcs opposés, chacun terminé par une pointe qui suit le cercle.
 *
 * La barbe de la pointe est **radiale** et sa pointe **tangente** : c'est ce
 * qui fait lire une flèche qui tourne plutôt qu'un trait posé en travers. Le
 * tracé est celui de `page_outposts.py`, au degré près.
 *
 * Dessinée même quand [marque] est faux — elle ne peint alors rien et ne fait
 * que tenir sa largeur. Les jours où la colonne existe, elle doit exister sur
 * toutes les lignes : sinon les noms ne s'alignent plus d'un rang à l'autre.
 */
@Composable
private fun Pastille(marque: Boolean) {
    Canvas(Modifier.padding(end = 4.dp).size(COTE_PASTILLE)) {
        if (!marque) return@Canvas
        val cote = min(size.width, size.height)
        val cx = size.width / 2f
        val cy = size.height / 2f
        val rayon = cote * PASTILLE_RAYON
        val trait = cote * PASTILLE_TRAIT
        val barbe = trait * PASTILLE_BARBE
        PASTILLE_ARCS.forEach { (depart, fin) ->
            drawArc(
                color = VERT_PASTILLE,
                startAngle = depart,
                sweepAngle = fin - depart,
                useCenter = false,
                topLeft = Offset(cx - rayon, cy - rayon),
                size = Size(rayon * 2f, rayon * 2f),
                style = Stroke(width = trait, cap = StrokeCap.Round),
            )
            // La pointe : deux points sur le rayon de la fin de l'arc, et un
            // troisieme un peu plus loin sur le cercle.
            val a = radians(fin)
            val b = radians(fin + PASTILLE_POINTE)
            drawPath(
                Path().apply {
                    moveTo(cx + (rayon + barbe) * cos(a), cy + (rayon + barbe) * sin(a))
                    lineTo(cx + (rayon - barbe) * cos(a), cy + (rayon - barbe) * sin(a))
                    lineTo(cx + rayon * cos(b), cy + rayon * sin(b))
                    close()
                },
                VERT_PASTILLE,
            )
        }
    }
}

@Composable
private fun Journal(
    changements: List<OutpostStore.Change>,
    premierReleve: Boolean,
    nameOf: (String) -> String,
) {
    if (changements.isEmpty()) {
        Box(Modifier.fillMaxSize(), Alignment.Center) {
            Text(
                if (premierReleve)
                    "Premier relevé enregistré.\nLe journal se remplira au prochain " +
                        "changement de main : l'API ne garde aucune histoire, tout " +
                        "se déduit de deux relevés comparés."
                else "Aucun changement depuis le premier relevé.",
                textAlign = TextAlign.Center,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(24.dp),
            )
        }
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(vertical = 8.dp),
    ) {
        // Le retrait latéral passe dans la ligne : la bande de couleur doit
        // aller d'un bord à l'autre, sinon elle flotte au milieu.
        itemsIndexed(changements) { rang, c ->
            Row(
                Modifier.fillMaxWidth()
                    .background(fondZebre(rang % 2 == 0))
                    .padding(horizontal = 12.dp, vertical = 7.dp),
            ) {
                Text(
                    if (c.lost) "▼" else "▲",
                    color = if (c.lost) SORTIE_OUTPOST else ENTREE_OUTPOST,
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.width(32.dp),
                )
                Column {
                    Text(nameOf("${c.outpost}.outpost"),
                         style = MaterialTheme.typography.bodyMedium)
                    Text(
                        when {
                            c.taken -> "pris par ${c.to}"
                            c.lost -> "perdu par ${c.from}"
                            else -> "${c.from} → ${c.to}"
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        HORODATAGE_JOUR.format(Instant.ofEpochSecond(c.at)),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
