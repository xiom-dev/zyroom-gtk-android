package net.ryzom.zyroom.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import net.ryzom.zyroom.model.Bete

/**
 * Où sont les bêtes du joueur.
 *
 * Un mektoub de bât laissé en pleine terre y reste, et son propriétaire finit
 * par oublier où. L'API donne sa position à chaque relevé ; c'est la seule
 * chose qu'elle sache dire d'un animal qu'on ne retrouve plus.
 *
 * Deux colonnes : les porteurs à gauche — montures et mektoubs de bât —, les
 * zigs à droite. On cherche rarement les uns en pensant aux autres, et les zigs
 * sont souvent nombreux.
 */
@Composable
fun BetesView(betes: List<Bete>, joueur: Triple<String, Int, Int>? = null) {
    val dehors = betes.filter { it.dehors }
    val porteurs = betes.filterNot { it.zig }
    val zigs = betes.filter { it.zig }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(vertical = 8.dp)) {
        item { CarteBetes(dehors, joueur) }
        item {
            Text(
                if (dehors.isEmpty()) "Aucune bête dehors : toutes sont rangées."
                else "${dehors.size} bête${if (dehors.size > 1) "s" else ""} dehors",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
            )
        }
        item {
            Row(Modifier.fillMaxWidth()) {
                Colonne("Porteurs", porteurs, Modifier.weight(1f))
                Colonne("Zigs", zigs, Modifier.weight(1f))
            }
        }
    }
}

/** Une colonne de bêtes, avec son titre. Vide, elle le dit. */
@Composable
private fun Colonne(titre: String, betes: List<Bete>, modifier: Modifier = Modifier) {
    Column(modifier) {
        Text(
            "$titre · ${betes.size}",
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.secondary,
            modifier = Modifier.padding(start = 12.dp, end = 8.dp, bottom = 4.dp),
        )
        betes.forEachIndexed { rang, bete -> LigneBete(bete, rang % 2 == 0) }
        if (betes.isEmpty()) {
            Text(
                "aucune",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 12.dp, bottom = 6.dp),
            )
        }
    }
}

@Composable
private fun LigneBete(bete: Bete, zebre: Boolean) {
    Column(
        Modifier.fillMaxWidth()
            .background(fondZebre(zebre))
            .padding(horizontal = 12.dp, vertical = 6.dp),
    ) {
        Text(bete.nom.ifEmpty { bete.etiquette },
             style = MaterialTheme.typography.bodyMedium,
             fontWeight = FontWeight.Medium)
        Text(
            if (bete.nom.isEmpty()) etatDe(bete) else "${bete.etiquette} · ${etatDe(bete)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/**
 * L'état d'une bête, en français.
 *
 * La satiété n'a pas d'échelle documentée — les valeurs relevées vont de 54 à
 * 933 — donc on la donne telle quelle plutôt que d'inventer un pourcentage qui
 * serait faux.
 */
private fun etatDe(bete: Bete): String {
    val lieu = when (bete.statut) {
        "landscape" -> "dehors"
        "stable" -> "à l'écurie"
        "" -> "état inconnu"
        else -> bete.statut
    }
    return if (bete.satiete > 0) "$lieu · satiété ${bete.satiete.toInt()}" else lieu
}
