package net.ryzom.zyroom.model

// Fichier produit par outils/table_avant_postes.py — ne pas
// modifier à la main.

/**
 * Le nom français de chaque avant-poste, à défaut du pack du jeu.
 *
 * Relevé de `nimetu/ryzom_extra` (LGPL-3.0), que la documentation de
 * l'API de Ryzom recommande pour les traductions. Le pack du client
 * reste prioritaire quand il est là : c'est la source du jeu lui-même,
 * et elle suit ses mises à jour. Ceci sert la variante F-Droid, qui ne
 * peut pas embarquer le pack, et tout exemplaire dont l'import a échoué.
 */
val NOMS_AVANT_POSTES: Map<String, String> = mapOf(
    "fyros_outpost_04" to "Ferme de Malmontagne",
    "fyros_outpost_09" to "Ferme des Hautes Tours",
    "fyros_outpost_13" to "Poste Frontière Ouest de la Combustion",
    "fyros_outpost_14" to "Poste d'Échange de la Combustion",
    "fyros_outpost_25" to "Ferme des Dunes du Bas",
    "fyros_outpost_27" to "Pôle Magique des Bois Calcifiés",
    "fyros_outpost_28" to "Forteresse des Bois Calcifiés",
    "matis_outpost_03" to "Ferme du Marécage de l'Angoisse",
    "matis_outpost_07" to "Ferme de l'Inventeur",
    "matis_outpost_15" to "Poste d'Échange du Monticule des Psykoplas",
    "matis_outpost_17" to "Atelier du Réveil",
    "matis_outpost_24" to "Forteresse du Bosquet Ouest",
    "matis_outpost_27" to "Atelier de Ginti",
    "matis_outpost_30" to "Poste Frontière de la Gorge de Berello",
    "tryker_outpost_06" to "Poste d'Échange de Vertval",
    "tryker_outpost_10" to "Poste d'Échange du Porche des Sources",
    "tryker_outpost_16" to "Centre de Recherche de la Promenade Caverneuse",
    "tryker_outpost_22" to "Atelier des Cimes Jumelles",
    "tryker_outpost_24" to "Atelier de la Route des Vents",
    "tryker_outpost_29" to "Forteresse de Loria",
    "tryker_outpost_31" to "Forteresse du Tourbillon",
    "zorai_outpost_02" to "Atelier de Gu-Qin",
    "zorai_outpost_08" to "Atelier de Qai-Du",
    "zorai_outpost_10" to "Forteresse de Sai-Shun",
    "zorai_outpost_15" to "Atelier des Ruines de Zo-Kian",
    "zorai_outpost_16" to "Forteresse de la Vallée Perdue",
    "zorai_outpost_22" to "Avant-Poste Diplomatique du Croisement du Démon",
    "zorai_outpost_29" to "Atelier de l'Arrière-pays",
)
