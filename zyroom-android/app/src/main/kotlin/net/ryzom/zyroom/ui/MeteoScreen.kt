package net.ryzom.zyroom.ui

import androidx.compose.foundation.Image
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
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.LinkAnnotation
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextLinkStyles
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withLink
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.data.Repository
import net.ryzom.zyroom.model.CONTINENT_DE_ZONE
import net.ryzom.zyroom.model.EXCELLENTES
import net.ryzom.zyroom.model.Gisements
import net.ryzom.zyroom.model.SAISONS
import net.ryzom.zyroom.model.ZONES
import net.ryzom.zyroom.model.popDe
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
    // Deux états : ce que l'API a rendu, et le même recalé sur l'instant
    // présent. Le second seul est affiché ; le premier sert de base au calcul.
    var releve by remember { mutableStateOf<MeteoAtys?>(null) }
    var affiche by remember { mutableStateOf<MeteoAtys?>(null) }
    var erreur by remember { mutableStateOf<String?>(null) }
    var occupe by remember { mutableStateOf(true) }
    val portee = rememberCoroutineScope()

    suspend fun charger() {
        occupe = true
        erreur = null
        try {
            releve = repository.meteo()
            affiche = releve
        } catch (echec: ApiException) {
            erreur = echec.message
        }
        occupe = false
    }

    LaunchedEffect(Unit) { charger() }

    // Le temps d'Atys avance tout seul : on ne redemande rien, on recale
    // l'affichage. Toutes les dix secondes, soit un pas de trois heures et
    // vingt d'Atys — le trait glisse au lieu de sauter. Les cycles reçus
    // couvrent plusieurs heures ; quand le présent approche du bout de la
    // prévision, on redemande une fois.
    LaunchedEffect(releve) {
        while (true) {
            delay(10_000)
            val base = releve ?: break
            val avance = base.aPresent()
            val dernier = avance.continents.values.firstOrNull()?.lastOrNull()
            if (dernier != null && avance.cycleCourant > dernier.cycle - 4) {
                // Bientôt à court de prévision : on va en rechercher, une fois.
                charger()
                break
            }
            affiche = avance
        }
    }

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
            val donnees = affiche
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
                // Ce qui sort maintenant, avant les tables figées : c'est la
                // seule chose de cet écran qui dépende de l'instant, et donc
                // la seule sur laquelle on agit tout de suite.
                item { CeQuiSort(donnees) }
                item { TableauxMatieres(donnees) }
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
        val prochain = suite.firstOrNull { it.condition != maintenant.condition }
        prochain?.let {
            Text(
                "${texteCondition(it.condition)} dans " +
                    duree(minutesAvant(releve, it.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition(it.condition),
                modifier = Modifier.padding(top = 4.dp),
            )
        }
        // La fenêtre excellente, seulement si elle n'est pas déjà annoncée
        // au-dessus : quand la prochaine bascule est justement celle-là, les
        // deux lignes disaient mot pour mot la même chose.
        val meilleur = suite.firstOrNull { it.condition == "best" }
        if (maintenant.condition != "best" && meilleur != null &&
            meilleur.cycle != prochain?.cycle) {
            Text(
                "Excellente dans " + duree(minutesAvant(releve, meilleur.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition("best"),
                modifier = Modifier.padding(top = 2.dp),
            )
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
    val prochain = suite.firstOrNull { it.condition != maintenant.condition }
    val meilleur = suite.firstOrNull { it.condition == "best" }
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
        prochain?.let {
            Text(
                "  →  ${texteCondition(it.condition)} dans " +
                    duree(minutesAvant(releve, it.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition(it.condition),
            )
        }
        // Tue dans l'œuf la répétition : quand la prochaine bascule est la
        // fenêtre excellente, les deux annonces se valent mot pour mot.
        if (maintenant.condition != "best" && meilleur != null &&
            meilleur.cycle != prochain?.cycle) {
            Text(
                "   ✦ Excellente dans " + duree(minutesAvant(releve, meilleur.cycle)),
                style = MaterialTheme.typography.bodyMedium,
                color = couleurCondition("best"),
            )
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
        // Sur une demi-largeur, le corps précédent passait à la ligne au
        // milieu d'un mot : celui-ci tient le titre sur une ligne, deux au
        // pire, sans lui ôter son rang de titre.
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.secondary,
        modifier = Modifier.padding(start = 10.dp, end = 8.dp, top = 16.dp, bottom = 4.dp),
    )
}

/**
 * Ce que la météo du moment fait sortir, zone par zone.
 *
 * L'humidité décide de la condition de gisement — quatre paliers découpés par
 * les seuils du jeu — et la condition décide de ce qu'on trouve. Les deux
 * tableaux du dessous disent ce qui est suprême *à cette saison* ; celui-ci dit
 * ce qui sort **en ce moment**, et il change tout seul à chaque bascule de
 * cycle, sans rien redemander.
 *
 * Le relevé est celui de La Lune Eternelle, et c'est la seule source connue
 * pour cette correspondance : les sites publics disent quelles matières sont
 * suprêmes à une saison, jamais dans quelle météo elles sortent.
 */
@Composable
private fun CeQuiSort(releve: MeteoAtys) {
    val maintenant = maintenantDansLesPrimes(releve) ?: return
    val condition = texteCondition(maintenant.condition)
    val humidite = (maintenant.value * 100).toInt()
    TitreTableau("Suprêmes — ce qui sort : $condition, $humidite %")
    // Deux zones par rangée : les quatre tenaient sur quatre écrans, et c'est
    // le tableau qu'on consulte en jouant. Le fond teinté est porté par la
    // rangée et non par chaque zone — l'une est souvent plus courte que
    // l'autre, et deux fonds séparés laissaient un trou sous la plus courte.
    val remplies = ZONES.map { it to popDe(releve.saison, it, maintenant.condition) }
        .filter { (_, groupes) -> groupes.isNotEmpty() }
    remplies.chunked(2).forEachIndexed { rang, rangee ->
        Row(
            Modifier.fillMaxWidth()
                .background(fondZebre(rang % 2 == 0))
                .padding(horizontal = 10.dp, vertical = 8.dp),
        ) {
            rangee.forEach { (zone, groupes) ->
                Box(Modifier.weight(1f)) { CorpsMatieres(zone, groupes) }
            }
            // La rangée impaire garde sa moitié vide, pour que la colonne de
            // gauche reste alignée d'une rangée à l'autre.
            if (rangee.size == 1) Box(Modifier.weight(1f)) {}
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
    }
}

/**
 * Ce que la saison fait sortir d'excellent.
 *
 * Le tableau des suprêmes de la saison a été retiré : « ce qui sort » les donne
 * déjà, et au temps qu'il fait plutôt qu'à la saison entière — c'est la même
 * liste, mais à jour. Les excellentes restent, seules et sur toute la largeur :
 * elles ne dépendent que du jour et de la nuit, que la météo ne change pas.
 */
@Composable
private fun TableauxMatieres(releve: MeteoAtys) {
    val saison = saisonCle(releve.saison)
    val moments = EXCELLENTES[saisonCle(releve.saison)]?.entries?.toList().orEmpty()
    Column(Modifier.fillMaxWidth()) {
        TitreTableau("Cette saison")
        TitreTableau("Excellentes — " + nomSaison(releve.saison))
        // Il fait nuit sur Atys de 22 h à 3 h, et le jeu n'y fait pas sortir
        // les mêmes matières. Les deux listes sont montrées — ce qui sortira
        // dans une heure vaut la peine d'être su —, et celle qui vaut
        // maintenant est dite et mise en couleur : sans cela, il fallait
        // connaître l'heure d'Atys pour savoir laquelle lire.
        //
        // Jour à gauche, nuit à droite. L'un sous l'autre, il fallait dérouler
        // la liste de jour pour atteindre celle de nuit, alors que le seul
        // geste utile est de les comparer. Le fond teinté est porté par la
        // rangée et non par chaque moitié : l'une est bien plus courte que
        // l'autre, et deux fonds séparés laissaient un trou sous la plus
        // courte — c'est la leçon des zones de « ce qui sort ».
        Row(
            Modifier.fillMaxWidth()
                .background(fondZebre(true))
                .padding(horizontal = 10.dp, vertical = 8.dp),
        ) {
            listOf("JOUR", "NUIT").forEach { moment ->
                val groupes = moments.firstOrNull { it.key == moment }?.value
                val maintenant = (moment == "NUIT") == releve.nuit
                Box(Modifier.weight(1f)) {
                    CorpsMatieres(
                        titre = (if (moment == "JOUR") "De jour" else "De nuit") +
                            if (maintenant) " · en ce moment" else "",
                        groupes = groupes.orEmpty(),
                        souligne = maintenant,
                        qualite = "excellent",
                    )
                }
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
    }
}

/**
 * Une zone et ce qu'on y fore.
 *
 * Le groupe à gauche, les matières à droite : c'est la disposition d'un
 * tableau, et elle se lit en travers sans chercher. Un titre nul quand il n'y a
 * rien à nommer — le tableau des excellentes n'a qu'un bloc, et son titre le
 * dit déjà.
 */
@Composable
private fun BlocMatieres(
    titre: String?,
    groupes: Map<String, List<String>>,
    zebre: Boolean,
    souligne: Boolean = false,
    qualite: String = "supreme",
) {
    Column(
        Modifier.fillMaxWidth()
            .background(fondZebre(zebre))
            .padding(horizontal = 10.dp, vertical = 8.dp),
    ) {
        CorpsMatieres(titre, groupes, souligne, qualite)
    }
    HorizontalDivider(color = MaterialTheme.colorScheme.surfaceVariant)
}

/**
 * Le contenu d'un bloc — son titre et ses familles — sans fond ni filet.
 *
 * Séparé de `BlocMatieres` pour qu'une rangée puisse en tenir deux et porter
 * elle-même la teinte : posée sur chaque bloc, elle s'arrêtait au bas du plus
 * court des deux.
 */
@Composable
private fun CorpsMatieres(
    titre: String?,
    groupes: Map<String, List<String>>,
    souligne: Boolean = false,
    qualite: String = "supreme",
) {
    // La matière dont on regarde la carte. Portée par le bloc et non par
    // l'écran : deux blocs ne sont jamais ouverts en même temps, et la remonter
    // plus haut ferait recomposer tout le tableau à chaque ouverture.
    var choix by remember { mutableStateOf<Triple<String, String, String>?>(null) }
    choix?.let { (q, famille, matiere) ->
        CarteGisement(q, famille, matiere) { choix = null }
    }
    Column {
        if (titre != null) {
            Text(
                titre,
                style = MaterialTheme.typography.titleSmall,
                color = if (souligne) MaterialTheme.colorScheme.primary
                        else MaterialTheme.colorScheme.onSurface,
            )
        }
        groupes.toSortedMap().forEach { (groupe, matieres) ->
            Row(Modifier.fillMaxWidth().padding(top = 2.dp)) {
                // Deux colonnes valent deux fois moins de largeur. Le nom du
                // groupe s'y serre, mais pas au-delà de « Carapace » : plus
                // étroit, le plus long des dix se coupait en deux lignes.
                Column(Modifier.width(68.dp)) {
                    Text(
                        groupe,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    // Le symbole du jeu sous le nom de la famille : une
                    // coquille pour la carapace, une goutte pour la sève. Ce
                    // sont ceux qu'on a sous les yeux en forant, et l'œil les
                    // reconnaît plus vite qu'il ne lit « Carapace ».
                    symboleDe(groupe)?.let { dessin ->
                        Image(
                            painterResource(dessin),
                            contentDescription = null,
                            modifier = Modifier.size(20.dp).padding(top = 1.dp),
                        )
                    }
                }
                // Les matières qu'on sait situer deviennent des liens. Un lien
                // et non un bouton : la liste garde son allure de phrase et
                // continue de se replier toute seule dans une demi-largeur.
                // Celles qu'on ne sait pas situer restent du texte ordinaire —
                // rien n'invite à toucher ce qui ne répondrait pas.
                val couleur = MaterialTheme.colorScheme.primary
                Text(
                    buildAnnotatedString {
                        matieres.forEachIndexed { rang, matiere ->
                            if (rang > 0) append(", ")
                            if (Gisements.points(qualite, groupe, matiere).isEmpty()) {
                                append(matiere)
                            } else {
                                withLink(
                                    LinkAnnotation.Clickable(
                                        tag = matiere,
                                        styles = TextLinkStyles(
                                            SpanStyle(
                                                color = couleur,
                                                textDecoration =
                                                    TextDecoration.Underline,
                                            ),
                                        ),
                                    ) { choix = Triple(qualite, groupe, matiere) },
                                ) { append(matiere) }
                            }
                        }
                    },
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
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
