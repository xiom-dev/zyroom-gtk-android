package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.RangeSlider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import net.ryzom.zyroom.model.Filtres
import net.ryzom.zyroom.model.ItemClass
import net.ryzom.zyroom.model.ItemEcosystem
import net.ryzom.zyroom.model.ItemEquip
import net.ryzom.zyroom.model.ItemType
import net.ryzom.zyroom.model.Jauge

/**
 * Le panneau des filtres, porté du popover GTK.
 *
 * Le bureau empile ses cases dans une colonne déroulante ; un téléphone n'a
 * pas cette largeur, et quarante cases à cocher les unes sous les autres
 * feraient un panneau qu'on parcourt au lieu de le lire. Chaque groupe tient
 * donc en pastilles qui se replient sur la largeur disponible — le même geste
 * que les chips de tri, juste au-dessus.
 *
 * **Les bonus d'abord** : c'est le tri qu'on vient chercher le plus souvent
 * dans un coffre d'équipement, et ce qui est en tête est ce qu'on atteint sans
 * faire défiler.
 *
 * Chaque touche s'applique immédiatement, sans bouton de validation : le
 * panneau ne couvre pas toute la hauteur, et l'on voit la grille se resserrer
 * derrière lui.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun PanneauFiltres(
    filtres: Filtres,
    onFiltres: (Filtres) -> Unit,
    onFermer: () -> Unit,
) {
    ModalBottomSheet(
        onDismissRequest = onFermer,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Filtres", style = MaterialTheme.typography.titleMedium)
                // « Tout remontrer » plutot que « Reinitialiser » : ce que le
                // bouton fait est visible dans la grille, et c'est cela qu'on
                // cherche quand on ne sait plus quelle case a tout vide.
                TextButton(onClick = { onFiltres(Filtres()) }) { Text("Tout remontrer") }
            }

            Titre("Bonus")
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Jauge.entries.forEach { jauge ->
                    FilterChip(
                        selected = jauge in filtres.jauges,
                        onClick = { onFiltres(filtres.copy(jauges = filtres.jauges.bascule(jauge))) },
                        label = { Text(jauge.label) },
                        // La goutte plutot qu'une coche : dans la grille,
                        // c'est la couleur — et non un nom — qui marque les
                        // objets. Une case portant « Sève » sans sa goutte
                        // verte obligerait a traduire de tete a chaque coup
                        // d'oeil.
                        leadingIcon = { Goutte(COULEUR_JAUGE.getValue(jauge)) },
                    )
                }
            }

            Titre("Qualité ${filtres.qualiteMin} à ${filtres.qualiteMax}")
            RangeSlider(
                value = filtres.qualiteMin.toFloat()..filtres.qualiteMax.toFloat(),
                onValueChange = { plage ->
                    onFiltres(
                        filtres.copy(
                            qualiteMin = plage.start.toInt(),
                            qualiteMax = plage.endInclusive.toInt(),
                        )
                    )
                },
                valueRange = Filtres.QUALITE_MIN.toFloat()..Filtres.QUALITE_MAX.toFloat(),
                // Par dizaines, comme sur le bureau : la qualite d'un objet
                // du jeu tombe sur un rond, et un pas de un donnerait une
                // borne impossible a poser au pouce.
                steps = (Filtres.QUALITE_MAX - Filtres.QUALITE_MIN) / 10 - 1,
            )

            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Bascule("Cadenas", filtres.cadenas) { onFiltres(filtres.copy(cadenas = it)) }
                Bascule("Avec bonus", filtres.avecBonus) { onFiltres(filtres.copy(avecBonus = it)) }
                Bascule("En vente", filtres.enVente) { onFiltres(filtres.copy(enVente = it)) }
            }

            Groupe("Type d'objet", ItemType.entries, filtres.types, { it.label }) {
                onFiltres(filtres.copy(types = it))
            }
            Groupe("Classe", ItemClass.entries, filtres.classes, { it.label }) {
                onFiltres(filtres.copy(classes = it))
            }
            Groupe("Écosystème", ItemEcosystem.entries, filtres.ecosystemes, { it.label }) {
                onFiltres(filtres.copy(ecosystemes = it))
            }
            Groupe("Équipement", ItemEquip.entries, filtres.equipements, { it.label }) {
                onFiltres(filtres.copy(equipements = it))
            }

            // De quoi faire remonter le dernier groupe au-dessus de la barre
            // de navigation, qu'on ne connait pas d'ici.
            Text("", modifier = Modifier.padding(bottom = 24.dp))
        }
    }
}

/** Un groupe de pastilles, une par valeur de l'énumération. */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun <T> Groupe(
    titre: String,
    valeurs: List<T>,
    coches: Set<T>,
    label: (T) -> String,
    onCoches: (Set<T>) -> Unit,
) {
    Titre(titre)
    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        valeurs.forEach { valeur ->
            FilterChip(
                selected = valeur in coches,
                onClick = { onCoches(coches.bascule(valeur)) },
                label = { Text(label(valeur)) },
            )
        }
    }
}

@Composable
private fun Titre(texte: String) {
    Text(
        texte,
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.secondary,
        modifier = Modifier.padding(top = 12.dp, bottom = 2.dp),
    )
}

@Composable
private fun Bascule(texte: String, actif: Boolean, onActif: (Boolean) -> Unit) {
    FilterChip(selected = actif, onClick = { onActif(!actif) }, label = { Text(texte) })
}

/** La goutte d'une jauge, seule, à la taille d'une icône de pastille. */
@Composable
private fun Goutte(couleur: Color) {
    Canvas(Modifier.size(10.dp, 13.dp)) {
        drawPath(cheminDeGoutte(size.width, size.height), couleur)
    }
}

/** Ajoute ou retire, selon que la valeur y est déjà. */
private fun <T> Set<T>.bascule(valeur: T): Set<T> =
    if (valeur in this) this - valeur else this + valeur
