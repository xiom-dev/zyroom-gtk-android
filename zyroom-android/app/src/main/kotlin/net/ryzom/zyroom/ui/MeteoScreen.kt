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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.model.CONTINENT_DE_ZONE
import net.ryzom.zyroom.model.MINUTES_PAR_CYCLE
import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.nomSaison
import net.ryzom.zyroom.model.popDe
import net.ryzom.zyroom.model.texteCondition
import net.ryzom.zyroom.model.texteMeteo

/**
 * La météo d'Atys, et ce qu'elle fait sortir.
 *
 * Deux choses s'y rencontrent. La météo vient de l'API officielle du jeu, qui
 * la **calcule** au lieu de la mesurer et peut donc la donner à l'avance. Le
 * relevé de la guilde, lui, dit quelles sources apparaissent dans quelle
 * condition, zone par zone : c'est un travail de joueurs qu'aucun site public
 * ne fournit.
 *
 * Un cycle dure neuf minutes réelles — une heure d'Atys en vaut trois, et un
 * cycle en compte trois. C'est ce qui permet d'annoncer « dans 27 min » plutôt
 * qu'un numéro de cycle qui ne parle à personne.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MeteoScreen(repository: Repository, onBack: () -> Unit) {
    var releve by remember { mutableStateOf<MeteoAtys?>(null) }
    var erreur by remember { mutableStateOf<String?>(null) }
    var occupe by remember { mutableStateOf(true) }
    val portee = rememberCoroutineScope()

    suspend fun charger() {
        occupe = true
        erreur = null
        try {
            releve = repository.meteo()
        } catch (echec: ApiException) {
            erreur = echec.message
        }
        occupe = false
    }

    LaunchedEffect(Unit) { charger() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    val saison = releve?.saison ?: -1
                    Text(if (saison >= 0) "Météo · ${nomSaison(saison)}" else "Météo")
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Retour",
                             Modifier.size(34.dp))
                    }
                },
                actions = {
                    IconButton(onClick = { portee.launch { charger() } }) {
                        Icon(Icons.Filled.Refresh, "Rafraîchir", Modifier.size(30.dp))
                    }
                },
            )
        },
    ) { marges ->
        Column(Modifier.fillMaxSize().padding(marges)) {
            erreur?.let {
                Text(it, color = MaterialTheme.colorScheme.error,
                     modifier = Modifier.fillMaxWidth().padding(12.dp))
            }
            val donnees = releve
            if (donnees == null) {
                Box(Modifier.fillMaxSize(), Alignment.Center) {
                    if (occupe) CircularProgressIndicator()
                }
                return@Column
            }
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(vertical = 8.dp),
            ) {
                // Les cinq continents des Primes rendent la même série météo —
                // vérifié sur quarante cycles. La répéter sous chaque zone
                // n'apprendrait rien : elle est en tête, une fois.
                item { EnTeteMeteo(donnees) }
                itemsIndexed(CONTINENT_DE_ZONE.keys.toList()) { rang, zone ->
                    Zone(zone, donnees, rang % 2 == 0)
                }
                item {
                    Text(
                        "Le relevé des sources est celui de la guilde, et il se " +
                            "complète au fil des sorties : une case vide veut dire " +
                            "« pas encore noté », pas « rien ».",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(16.dp),
                    )
                }
            }
        }
    }
}

/** Le temps qu'il fait dans les Primes, et ce qui vient ensuite. */
@Composable
private fun EnTeteMeteo(releve: MeteoAtys) {
    val cycles = cyclesDesPrimes(releve)
    val maintenant = maintenantDansLesPrimes(releve) ?: return
    Column(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp)) {
        Row {
            Text(
                "${texteMeteo(maintenant.text)} · ${(maintenant.value * 100).toInt()} %",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(
                "  →  ${texteCondition(maintenant.condition)}",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = couleurCondition(maintenant.condition),
            )
        }
        // On ne montre que les bascules, non les cycles un par un : ce qu'on
        // veut savoir, c'est quand ça change.
        val suite = cycles.filter { it.cycle > releve.cycleCourant }
        suite.firstOrNull { it.condition != maintenant.condition }?.let { prochain ->
            Text(
                "${texteCondition(prochain.condition)} dans " +
                    duree((prochain.cycle - releve.cycleCourant) * MINUTES_PAR_CYCLE),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition(prochain.condition),
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        if (maintenant.condition != "best") {
            suite.firstOrNull { it.condition == "best" }?.let { meilleur ->
                Text(
                    "Excellente dans " +
                        duree((meilleur.cycle - releve.cycleCourant) * MINUTES_PAR_CYCLE),
                    style = MaterialTheme.typography.bodyMedium,
                    color = couleurCondition("best"),
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
        Text(
            "Les Primes partagent une seule météo : celle-ci vaut pour les quatre zones.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
}

private fun cyclesDesPrimes(releve: MeteoAtys): List<Meteo> =
    releve.continents[CONTINENT_DE_ZONE.values.first()].orEmpty()

private fun maintenantDansLesPrimes(releve: MeteoAtys): Meteo? {
    val cycles = cyclesDesPrimes(releve)
    return cycles.firstOrNull { it.cycle == releve.cycleCourant } ?: cycles.firstOrNull()
}

@Composable
private fun Zone(zone: String, releve: MeteoAtys, zebre: Boolean) {
    val maintenant = maintenantDansLesPrimes(releve) ?: return

    Column(
        Modifier.fillMaxWidth()
            .background(fondZebre(zebre))
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Text(zone, style = MaterialTheme.typography.titleMedium,
             color = MaterialTheme.colorScheme.secondary)

        val sortent = popDe(releve.saison, zone, maintenant.condition)
        if (sortent.isEmpty()) {
            Text(
                "Rien de noté pour cette condition.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        } else {
            sortent.forEach { (famille, matieres) ->
                Text(
                    "$famille : ${matieres.joinToString(", ")}",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }

    }
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
}

@Composable
private fun couleurCondition(condition: String) = when (condition.lowercase()) {
    "best" -> MaterialTheme.colorScheme.primary
    "good" -> MaterialTheme.colorScheme.secondary
    else -> MaterialTheme.colorScheme.onSurfaceVariant
}

/** « 27 min », « 1 h 12 » — un compte à rebours se lit, pas se calcule. */
private fun duree(minutes: Int): String =
    if (minutes < 60) "$minutes min"
    else "${minutes / 60} h ${(minutes % 60).toString().padStart(2, '0')}"
