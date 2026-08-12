package net.ryzom.zyroom.ui

import net.ryzom.zyroom.model.Gisements

/**
 * Les vues de gisements sont embarquées dans cette variante.
 *
 * Ce sont des images du tracker d'atys.us, dessinées sur les données de
 * ballisticmystix.net : des données du jeu republiées par un tiers, même
 * catégorie que la carte d'Atys et les symboles de matières.
 */
const val GISEMENTS_EMBARQUES = true

/**
 * Où sort cette matière, en images — vide si on ne sait pas la situer.
 *
 * Le nom donné est celui qu'affiche l'écran, et les deux tableaux ne nomment
 * pas les matières pareil : « Colle » dans le relevé de la guilde, « Glue »
 * dans les listes de suprêmes. La table sait les deux ; elle a été écrite comme
 * ça à la fabrication, justement pour qu'il n'y ait rien à deviner ici.
 */
internal fun cartesGisement(qualite: String, famille: String, matiere: String):
    List<Int> = Gisements.cartes(qualite, famille, matiere)

/** Les fourchettes d'humidité où la matière sort, en pourcentage. */
internal fun humiditesGisement(qualite: String, famille: String, matiere: String):
    List<Pair<Float, Float>> =
    Gisements.TABLE[Gisements.LIBELLES[famille to matiere]?.let {
        Gisements.Cle(qualite, it.first, it.second)
    }]?.humidites.orEmpty()
