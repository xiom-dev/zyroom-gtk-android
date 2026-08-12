package net.ryzom.zyroom.ui

/**
 * Cette variante n'embarque aucune vue de gisement.
 *
 * Ce sont des images du tracker d'atys.us, dessinées sur les données de
 * ballisticmystix.net : des données du jeu republiées par un tiers, dont la
 * licence n'est pas établie de bout en bout. Même choix que pour la carte
 * d'Atys et les symboles de matières — une logithèque ne publie que ce dont
 * elle peut répondre.
 *
 * L'écran météo reste entier sans elles : il dit toujours quelles matières
 * sortent, à quelle saison et par quel temps. Il ne dit pas où — c'était le
 * rôle de ces vues, et les noms restent alors du texte ordinaire, que rien
 * n'invite à toucher.
 */
const val GISEMENTS_EMBARQUES = false

internal fun cartesGisement(qualite: String, famille: String, matiere: String):
    List<Int> = emptyList()

internal fun humiditesGisement(qualite: String, famille: String, matiere: String):
    List<Pair<Float, Float>> = emptyList()
