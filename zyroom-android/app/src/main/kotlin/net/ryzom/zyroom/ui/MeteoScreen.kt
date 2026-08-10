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
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.model.CONTINENT_DE_ZONE
import net.ryzom.zyroom.model.EXCELLENTES
import net.ryzom.zyroom.model.SAISONS
import net.ryzom.zyroom.model.SUPREMES
import net.ryzom.zyroom.model.MINUTES_PAR_CYCLE
import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.nomSaison
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
            val paysage = LocalConfiguration.current.orientation ==
                android.content.res.Configuration.ORIENTATION_LANDSCAPE
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
                // Tout défile ensemble, courbe comprise. La figer en paysage
                // avait l'air d'une bonne idée — lire la fenêtre de forage en
                // parcourant ce qu'elle fait sortir — mais un écran couché est
                // deux fois moins haut : il ne restait plus qu'un ou deux
                // rangs de matières sous elle. Mieux vaut pousser la courbe
                // hors de vue et lire le tableau.
                //
                // Les cinq continents des Primes rendent la même série météo —
                // vérifié sur quarante cycles. La répéter sous chaque zone
                // n'apprendrait rien : elle est en tête, une fois. En paysage
                // l'en-tête se resserre sur une ligne, pour que le tableau
                // commence plus tôt.
                item { EnTeteMeteo(donnees, compact = paysage) }
                item {
                    CourbeMeteo(
                        releve = donnees,
                        cycles = cyclesDesPrimes(donnees),
                        hauteur = if (paysage) 190 else 200,
                    )
                }
                item { TitreTableau("Suprêmes — " + nomSaison(donnees.saison)) }
                itemsIndexed(SUPREMES[saisonCle(donnees.saison)]
                                 ?.entries?.toList().orEmpty()) { rang, (zone, groupes) ->
                    BlocMatieres(zone, groupes, rang % 2 == 0)
                }
                item { TitreTableau("Excellentes — " + nomSaison(donnees.saison)) }
                itemsIndexed(EXCELLENTES[saisonCle(donnees.saison)]
                                 ?.entries?.toList().orEmpty()) { rang, (moment, groupes) ->
                    // Il fait nuit sur Atys de 22 h à 3 h : dire laquelle des
                    // deux listes vaut en ce moment évite d'aller forer ce qui
                    // ne sortira que dans huit heures.
                    val maintenant = (moment == "NUIT") == donnees.nuit
                    BlocMatieres(
                        titre = (if (moment == "JOUR") "De jour" else "De nuit") +
                            if (maintenant) "  ·  en ce moment" else "",
                        groupes = groupes,
                        zebre = rang % 2 == 0,
                        souligne = maintenant,
                    )
                }
            }
        }
    }
}

/**
 * Le temps qu'il fait dans les Primes, et ce qui vient ensuite.
 *
 * `compact` sert le mode paysage, où la hauteur est comptée : les bascules
 * passent sur la même ligne que la condition, et la phrase d'explication saute
 * — elle se lit une fois, pas à chaque consultation.
 */
@Composable
private fun EnTeteMeteo(releve: MeteoAtys, compact: Boolean = false) {
    val cycles = cyclesDesPrimes(releve)
    val maintenant = maintenantDansLesPrimes(releve) ?: return
    if (compact) {
        EnTeteCompact(releve, maintenant, cycles)
        return
    }
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
                    duree(minutesAvant(releve, prochain.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition(prochain.condition),
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        if (maintenant.condition != "best") {
            suite.firstOrNull { it.condition == "best" }?.let { meilleur ->
                Text(
                    "Excellente dans " + duree(minutesAvant(releve, meilleur.cycle)),
                    style = MaterialTheme.typography.bodyMedium,
                    color = couleurCondition("best"),
                    modifier = Modifier.padding(top = 2.dp),
                )
            }
        }
        Text(
            "Les Primes partagent une seule météo : celle-ci vaut pour les quatre zones. " +
                "Il est ${releve.heureDuJour} h sur Atys, " +
                (if (releve.nuit) "il y fait nuit." else "il y fait jour."),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
}

/** Tout sur une ligne : la condition, la bascule qui vient, la fenêtre excellente. */
@Composable
private fun EnTeteCompact(releve: MeteoAtys, maintenant: Meteo, cycles: List<Meteo>) {
    val suite = cycles.filter { it.cycle > releve.cycleCourant }
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            "${(maintenant.value * 100).toInt()} %  ",
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            texteCondition(maintenant.condition),
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            color = couleurCondition(maintenant.condition),
        )
        suite.firstOrNull { it.condition != maintenant.condition }?.let { prochain ->
            Text(
                "  →  ${texteCondition(prochain.condition)} dans " +
                    duree(minutesAvant(releve, prochain.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition(prochain.condition),
            )
        }
        if (maintenant.condition != "best") {
            suite.firstOrNull { it.condition == "best" }?.let { meilleur ->
                Text(
                    "   ✦ Excellente dans " + duree(minutesAvant(releve, meilleur.cycle)),
                    style = MaterialTheme.typography.bodyMedium,
                    color = couleurCondition("best"),
                )
            }
        }
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
}

private fun cyclesDesPrimes(releve: MeteoAtys): List<Meteo> =
    releve.continents[CONTINENT_DE_ZONE.values.first()].orEmpty()

private fun maintenantDansLesPrimes(releve: MeteoAtys): Meteo? {
    val cycles = cyclesDesPrimes(releve)
    return cycles.firstOrNull { it.cycle == releve.cycleCourant } ?: cycles.firstOrNull()
}

/** Un titre de section du tableau. */
@Composable
private fun TitreTableau(titre: String) {
    Text(
        titre,
        style = MaterialTheme.typography.titleMedium,
        color = MaterialTheme.colorScheme.secondary,
        modifier = Modifier.padding(start = 14.dp, end = 14.dp, top = 18.dp, bottom = 4.dp),
    )
}

/**
 * Une zone — ou un moment de la journée — et ce qu'on y fore.
 *
 * Le groupe à gauche, les matières à droite : c'est la disposition d'un
 * tableau, et elle se lit en travers sans chercher.
 */
@Composable
private fun BlocMatieres(
    titre: String,
    groupes: Map<String, List<String>>,
    zebre: Boolean,
    souligne: Boolean = false,
) {
    Column(
        Modifier.fillMaxWidth()
            .background(fondZebre(zebre))
            .padding(horizontal = 14.dp, vertical = 8.dp),
    ) {
        Text(
            titre,
            style = MaterialTheme.typography.titleSmall,
            color = if (souligne) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.onSurface,
        )
        groupes.toSortedMap().forEach { (groupe, matieres) ->
            Row(Modifier.fillMaxWidth().padding(top = 2.dp)) {
                Text(
                    groupe,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.width(72.dp),
                )
                Text(matieres.joinToString(", "),
                     style = MaterialTheme.typography.bodySmall,
                     modifier = Modifier.weight(1f))
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

/** La clé de saison du relevé, « PRINTEMPS »… */
private fun saisonCle(saison: Int): String = SAISONS.getOrElse(saison) { "" }

/**
 * Minutes réelles avant le début d'un cycle à venir.
 *
 * Compter les cycles pleins surestimait l'attente de neuf minutes au pire :
 * quand on regarde, on est déjà quelque part **dans** le cycle en cours, et
 * l'API dit où par les décimales de son heure d'Atys.
 */
private fun minutesAvant(releve: MeteoAtys, cycle: Int): Int =
    ((cycle - releve.cycleCourant - releve.avancementDuCycle) * MINUTES_PAR_CYCLE)
        .toInt().coerceAtLeast(0)

/** « 27 min », « 1 h 12 » — un compte à rebours se lit, pas se calcule. */
private fun duree(minutes: Int): String = when {
    // À cheval sur la bascule, l'arrondi rendait « dans 0 min », qui se lit
    // comme une panne plutôt que comme une imminence.
    minutes <= 0 -> "moins d'une minute"
    minutes < 60 -> "$minutes min"
    else -> "${minutes / 60} h ${(minutes % 60).toString().padStart(2, '0')}"
}
