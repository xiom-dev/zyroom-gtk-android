package net.ryzom.zyroom.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
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
 * Les coordonnées sont écrites en clair, et pas seulement portées sur la carte :
 * ce sont elles qu'on tape en jeu pour poser un repère.
 */
@Composable
fun BetesView(betes: List<Bete>) {
    val dehors = betes.filter { it.dehors }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(vertical = 8.dp)) {
        item { CarteBetes(dehors) }
        item {
            Text(
                if (dehors.isEmpty()) "Aucune bête dehors : toutes sont rangées."
                else "${dehors.size} bête${if (dehors.size > 1) "s" else ""} " +
                    "dehors" + if (CARTE_EMBARQUEE) "" else
                    " — les coordonnées se tapent en jeu pour poser un repère.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
            )
        }
        itemsIndexed(betes, key = { _, b -> b.etiquette }) { rang, bete ->
            LigneBete(bete, rang % 2 == 0)
        }
    }
}

@Composable
private fun LigneBete(bete: Bete, zebre: Boolean) {
    Row(
        Modifier.fillMaxWidth()
            .background(fondZebre(zebre))
            .padding(horizontal = 14.dp, vertical = 6.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Column(Modifier.weight(1f)) {
            Text(bete.nom.ifEmpty { bete.etiquette },
                 style = MaterialTheme.typography.bodyMedium,
                 fontWeight = FontWeight.Medium)
            Text(
                if (bete.nom.isEmpty()) etatDe(bete)
                else "${bete.etiquette} · ${etatDe(bete)}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        // À droite, ce qu'on recopie : la position, telle qu'on la tape en jeu.
        Text(
            if (bete.dehors) "${bete.x}  ${bete.y}" else "—",
            style = MaterialTheme.typography.bodyMedium,
            color = if (bete.dehors) MaterialTheme.colorScheme.secondary
                    else MaterialTheme.colorScheme.onSurfaceVariant,
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
