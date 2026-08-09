package net.ryzom.zyroom.ui

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
import androidx.compose.ui.graphics.Color
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
 */
@Composable
fun OutpostsView(
    carte: List<Outpost>?,
    changements: List<OutpostStore.Change>,
    premierReleve: Boolean,
    erreur: String?,
    guilde: String,
    nameOf: (String) -> String,
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
                    onClick = { journal = true },
                    label = {
                        Text(if (changements.isEmpty()) "Journal"
                             else "Journal · ${changements.size}")
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
        else Possessions(carte, guilde, nameOf)
    }
}

@Composable
private fun Possessions(carte: List<Outpost>, guilde: String, nameOf: (String) -> String) {
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
                Ligne(avantPoste, avantPoste.guild == guilde, rang % 2 == 0, nameOf)
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
        Text(nom, style = MaterialTheme.typography.titleSmall)
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
    nameOf: (String) -> String,
) {
    val niveau = niveauDe(avantPoste.code)
    Row(
        Modifier.fillMaxWidth()
            // Une ligne sur deux teintée du vert de l'application, très
            // diluée : sur trois colonnes dont deux étroites, l'œil perd sa
            // ligne en traversant. Le zébrage la tient mieux qu'un filet, qui
            // hachait la lecture à chaque rang.
            .background(
                if (zebre) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.22f)
                else Color.Transparent
            )
            .padding(vertical = 6.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
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
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        items(changements) { c ->
            Row(Modifier.fillMaxWidth()) {
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
