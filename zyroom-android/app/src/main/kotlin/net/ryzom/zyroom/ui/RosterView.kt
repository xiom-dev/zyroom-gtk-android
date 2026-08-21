package net.ryzom.zyroom.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import net.ryzom.zyroom.model.Member
import net.ryzom.zyroom.model.MouvementMembre
import net.ryzom.zyroom.model.decrireMouvement
import net.ryzom.zyroom.model.nomGrade
import net.ryzom.zyroom.model.rangGrade
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * Le registre du personnel : l'effectif, et qui va et vient.
 *
 * L'effectif vient du flux de la guilde ; les mouvements, eux, sont tenus par
 * l'application — **l'API ne rend qu'un état, jamais une histoire.** Deux
 * relevés comparés donnent les arrivées, les départs et les promotions, et ce
 * qui se passe entre deux ouvertures ne se voit pas.
 */
@Composable
fun RosterView(
    membres: List<Member>,
    mouvements: List<MouvementMembre>,
    premierReleve: Boolean,
    recherche: String,
    onRecherche: (String) -> Unit,
) {
    var journal by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize()) {
        // Le champ ne paraît que sur l'effectif : il ne filtre pas le journal,
        // qui se lit par sa date, et un champ qui ne fait rien est pire qu'un
        // champ absent — on tape dedans, rien ne bouge, et on croit à une
        // panne. C'est ZyRoom-GTK qui a tranché ainsi le 20 août ; les deux
        // écrans se conduisent maintenant pareil.
        if (!journal) {
            OutlinedTextField(
                value = recherche,
                onValueChange = onRecherche,
                label = { Text("Rechercher un membre") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp),
            )
        }
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            FilterChip(
                selected = !journal,
                onClick = { journal = false },
                label = { Text("Effectif · ${membres.size}") },
            )
            FilterChip(
                selected = journal,
                onClick = { journal = true },
                label = {
                    Text(if (mouvements.isEmpty()) "Arrivées et départs"
                         else "Arrivées et départs · ${mouvements.size}")
                },
            )
        }

        if (journal) Mouvements(mouvements, premierReleve)
        else Effectif(membres, normalise(recherche.trim()))
    }
}

/**
 * Largeur minimale d'une colonne de noms.
 *
 * Les noms de Ryzom dépassent rarement la douzaine de caractères ; en dessous de
 * cette largeur, ils se feraient couper plus souvent qu'ils ne se liraient.
 */
private val COLONNE_MINIMALE = 116.dp

/**
 * L'effectif, par grade, du chef aux membres — sur autant de colonnes que
 * l'écran en tient.
 *
 * Cent soixante-dix noms sur une seule colonne faisaient un ruban plus haut que
 * dix écrans, où l'on ne trouvait rien : deux ou trois colonnes de portrait, le
 * double couché. Comme la version GTK, à ceci près qu'elle en tient six.
 */
@Composable
private fun Effectif(membres: List<Member>, cherche: String) {
    // Le chef d'abord, les membres ensuite : on lit une liste de guilde par le
    // haut, et l'API la rend dans un ordre qui n'en est pas un.
    val parGrade = remember(membres, cherche) {
        membres.filter { cherche.isEmpty() || cherche in normalise(it.name) }
            .sortedWith(compareBy({ rangGrade(it.grade) }, { it.name.lowercase() }))
            .groupBy { it.grade }
    }
    if (parGrade.isEmpty()) {
        // La puce « Effectif » n'existe que sur une guilde qui a des membres :
        // une liste vide ici ne peut venir que de la recherche, et le message
        // peut le dire. Le même qu'en GTK, mot pour mot.
        Box(Modifier.fillMaxSize(), Alignment.Center) {
            Text("Aucun membre de ce nom.", textAlign = TextAlign.Center,
                 modifier = Modifier.padding(24.dp))
        }
        return
    }
    // Le nombre de colonnes se calcule ici, et non par `GridCells.Adaptive` :
    // le zébrage a besoin de le connaître pour compléter les rangées.
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val colonnes = ((maxWidth - 24.dp) / COLONNE_MINIMALE).toInt().coerceIn(2, 6)
        LazyVerticalGrid(
            columns = GridCells.Fixed(colonnes),
            contentPadding = PaddingValues(vertical = 8.dp),
        ) {
            parGrade.entries.forEachIndexed { rang, (grade, gens) ->
                // Le zébrage sépare les grades et non les lignes : un nom n'a
                // rien à droite de lui qu'on doive relier, et une teinte par
                // ligne n'y servirait à rien — alors qu'une teinte par groupe
                // montre d'un coup d'œil où finissent les officiers.
                val teinte = rang % 2 == 0
                item(key = "grade-$grade", span = { GridItemSpan(maxLineSpan) }) {
                    Text(
                        "${nomGrade(grade)} · ${gens.size}",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.secondary,
                        modifier = Modifier.fillMaxWidth()
                            .background(fondZebre(teinte))
                            .padding(start = 14.dp, end = 14.dp,
                                     top = 10.dp, bottom = 2.dp),
                    )
                }
                // La rangée est toujours remplie, au besoin de cases vides :
                // sans elles, la dernière rangée d'un grade laisse un trou clair
                // dans la bande teintée, là où le grade n'est pas fini.
                val cases = gens.size + (-gens.size).mod(colonnes)
                items(cases, key = { "$grade-$it" }) { index ->
                    Text(
                        gens.getOrNull(index)?.name.orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.fillMaxWidth()
                            .background(fondZebre(teinte))
                            .padding(horizontal = 8.dp, vertical = 3.dp),
                    )
                }
            }
        }
    }
}

/** Les allées et venues, du plus récent au plus ancien. */
@Composable
private fun Mouvements(mouvements: List<MouvementMembre>, premierReleve: Boolean) {
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(vertical = 8.dp)) {
        item { Legende() }
        if (mouvements.isEmpty()) {
            item {
                Text(
                    if (premierReleve)
                        "Premier relevé : rien à comparer. Les arrivées et les " +
                            "départs apparaîtront à partir du prochain."
                    else "Aucun mouvement depuis le premier relevé. Le registre " +
                        "compare l'effectif d'une synchronisation à l'autre : l'API " +
                        "ne garde aucune histoire, seule l'application en tient une.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                )
            }
            return@LazyColumn
        }
        itemsIndexed(mouvements, key = { _, m -> "${m.at}-${m.member}-${m.kind}" }) { rang, m ->
            Row(
                Modifier.fillMaxWidth()
                    .background(fondZebre(rang % 2 == 0))
                    .padding(horizontal = 14.dp, vertical = 4.dp),
                // En haut, et non centré : une ligne qui déborde sur deux
                // lignes emportait la date et le signe au milieu, entre les
                // deux — on les cherchait. Ils tiennent maintenant le rang de
                // la première ligne, celle où le nom se lit.
                verticalAlignment = Alignment.Top,
            ) {
                Text(
                    DATE.format(Instant.ofEpochSecond(m.at).atZone(ZoneId.systemDefault())),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(96.dp),
                )
                val (forme, couleur) = signeDe(m)
                Text(forme, color = couleur, fontWeight = FontWeight.Bold,
                     modifier = Modifier.width(20.dp))
                Text(decrireMouvement(m), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

/**
 * Les quatre signes et leur sens.
 *
 * Sans elle, un triangle rouge vers le bas se lit comme une alarme plutôt que
 * comme un départ. La couleur porte le sens, la direction le confirme.
 */
@Composable
private fun Legende() {
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        listOf(
            "▲" to ("arrivée" to VERT),
            "▼" to ("départ" to ROUGE),
            "▲" to ("montée" to Color.Unspecified),
            "▼" to ("rétrogradation" to Color.Unspecified),
        ).forEach { (forme, reste) ->
            val (sens, couleur) = reste
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(forme, color = if (couleur == Color.Unspecified)
                    MaterialTheme.colorScheme.onSurface else couleur,
                     fontWeight = FontWeight.Bold)
                Text(" $sens", style = MaterialTheme.typography.bodySmall,
                     color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun signeDe(m: MouvementMembre): Pair<String, Color> = when {
    m.kind == "arrivee" -> "▲" to VERT
    m.kind == "depart" -> "▼" to ROUGE
    m.promotion -> "▲" to MaterialTheme.colorScheme.onSurface
    else -> "▼" to MaterialTheme.colorScheme.onSurface
}

private val VERT = Color(0xFF4CAF50)
private val ROUGE = Color(0xFFE2696A)

private val DATE: DateTimeFormatter = DateTimeFormatter.ofPattern("dd/MM HH:mm")
