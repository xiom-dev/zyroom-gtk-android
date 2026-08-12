package net.ryzom.zyroom.model

// Fichier produit par outils/table_gisements.py — ne pas modifier à la main.

/**
 * Où sortent les matières, en coordonnées de jeu.
 *
 * L'écran météo dit *quoi* sort ; ceci dit *où*. Les positions viennent du
 * relevé que Ballistic Mystix publie, dont l'auteur a donné son accord écrit
 * pour qu'on s'en serve et qu'on le redistribue. Les applications dessinent
 * elles-mêmes, sur la carte d'Atys embarquée : sept kilooctets de coordonnées
 * au lieu de trois mégaoctets d'images rendues ailleurs, et un zoom libre au
 * lieu d'une vue figée.
 *
 * La clé est en français, comme ce qu'affiche l'écran ; la traduction vers les
 * noms du jeu est faite à la fabrication.
 */
object Gisements {
    data class Cle(val qualite: String, val famille: String, val matiere: String)

    /** Un gisement : sa position de jeu, et le lieu où il se trouve. */
    data class Point(val x: Int, val y: Int, val lieu: String)

    data class Gisement(
        /** Les fourchettes d'humidité où la matière sort, en pourcentage. */
        val humidites: List<Pair<Float, Float>>,
        /** Les positions de jeu de ses gisements, avec leur lieu. */
        val points: List<Point>,
    )

    val TABLE: Map<Cle, Gisement> = mapOf(
        Cle("excellent", "amber", "beng") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1397, -10706, "Gouffre d'Ichor"), Point(6492, -12960, "Forêt Insaisissable"), Point(6759, -15383, "Porte de l'Obscurité"))),
        Cle("excellent", "amber", "hash") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(964, -10598, "Gouffre d'Ichor"), Point(5810, -10186, "Porte des Vents"), Point(6653, -13071, "Forêt Insaisissable"), Point(6812, -15271, "Porte de l'Obscurité"))),
        Cle("excellent", "amber", "pha") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1507, -10745, "Gouffre d'Ichor"), Point(5897, -12987, "Forêt Insaisissable"), Point(6330, -11381, "Porte des Vents"), Point(6988, -16238, "La Fosse aux Epreuves"))),
        Cle("excellent", "amber", "sha") to Gisement(listOf(0.0f to 49.9f), listOf(Point(1435, -10968, "Gouffre d'Ichor"), Point(5757, -10772, "Porte des Vents"), Point(6015, -13496, "Forêt Insaisissable"), Point(6186, -16018, "La Fosse aux Epreuves"), Point(6250, -15147, "Porte de l'Obscurité"))),
        Cle("excellent", "amber", "soo") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1204, -10793, "Gouffre d'Ichor"), Point(6061, -11046, "Porte des Vents"), Point(6110, -16088, "La Fosse aux Epreuves"), Point(6532, -13518, "Forêt Insaisissable"), Point(6552, -15222, "Porte de l'Obscurité"))),
        Cle("excellent", "amber", "zun") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1534, -10963, "Gouffre d'Ichor"), Point(5996, -13239, "Forêt Insaisissable"), Point(6171, -10148, "Porte des Vents"))),
        Cle("excellent", "bark", "adriel") to Gisement(listOf(0.0f to 49.9f), listOf(Point(832, -10683, "Gouffre d'Ichor"), Point(5655, -10065, "Porte des Vents"), Point(6210, -16139, "La Fosse aux Epreuves"), Point(6387, -14575, "Porte de l'Obscurité"))),
        Cle("excellent", "bark", "beckers") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1533, -10337, "Gouffre d'Ichor"), Point(5880, -9778, "Porte des Vents"), Point(6539, -13414, "Forêt Insaisissable"))),
        Cle("excellent", "bark", "mitexi") to Gisement(listOf(50.0f to 100.0f), listOf(Point(654, -10580, "Gouffre d'Ichor"), Point(5563, -9834, "Porte des Vents"), Point(6408, -13180, "Forêt Insaisissable"), Point(6423, -14400, "Porte de l'Obscurité"), Point(6572, -16034, "La Fosse aux Epreuves"))),
        Cle("excellent", "bark", "oath") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(5583, -9692, "Porte des Vents"), Point(6534, -15960, "La Fosse aux Epreuves"), Point(6595, -13272, "Forêt Insaisissable"))),
        Cle("excellent", "bark", "perfling") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(783, -10249, "Gouffre d'Ichor"), Point(6901, -16476, "La Fosse aux Epreuves"))),
        Cle("excellent", "fiber", "anete") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(768, -10956, "Gouffre d'Ichor"), Point(6052, -11616, "Porte des Vents"), Point(6745, -16684, "La Fosse aux Epreuves"))),
        Cle("excellent", "fiber", "buo") to Gisement(listOf(50.0f to 100.0f), listOf(Point(6004, -11335, "Porte des Vents"), Point(6611, -14115, "Porte de l'Obscurité"), Point(6780, -12786, "Forêt Insaisissable"))),
        Cle("excellent", "fiber", "dzao") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(813, -11122, "Gouffre d'Ichor"), Point(5827, -16821, "La Fosse aux Epreuves"), Point(5931, -11220, "Porte des Vents"), Point(6774, -13018, "Forêt Insaisissable"))),
        Cle("excellent", "fiber", "shu") to Gisement(listOf(0.0f to 49.9f), listOf(Point(570, -10872, "Gouffre d'Ichor"), Point(6212, -11421, "Porte des Vents"), Point(6882, -16861, "La Fosse aux Epreuves"), Point(6963, -12804, "Forêt Insaisissable"))),
        Cle("excellent", "oil", "gulatch") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(926, -10207, "Gouffre d'Ichor"), Point(5974, -10005, "Porte des Vents"), Point(6553, -16567, "La Fosse aux Epreuves"), Point(6623, -15768, "Porte de l'Obscurité"))),
        Cle("excellent", "oil", "irin") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1200, -10365, "Gouffre d'Ichor"), Point(5814, -9880, "Porte des Vents"), Point(6421, -14359, "Porte de l'Obscurité"), Point(6874, -12449, "Forêt Insaisissable"))),
        Cle("excellent", "oil", "koorin") to Gisement(listOf(16.7f to 83.3f), listOf(Point(817, -10931, "Gouffre d'Ichor"), Point(5634, -9847, "Porte des Vents"), Point(6030, -14194, "Porte de l'Obscurité"), Point(6099, -13144, "Forêt Insaisissable"), Point(6376, -15987, "La Fosse aux Epreuves"))),
        Cle("excellent", "oil", "pilan") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1326, -10846, "Gouffre d'Ichor"), Point(5810, -10016, "Porte des Vents"), Point(5831, -16535, "La Fosse aux Epreuves"), Point(5951, -12100, "Forêt Insaisissable"), Point(6619, -15416, "Porte de l'Obscurité"))),
        Cle("excellent", "resin", "dung") to Gisement(listOf(0.0f to 49.9f), listOf(Point(2206, -15691, "Profondeurs Interdites"), Point(5794, -10627, "Porte des Vents"), Point(6032, -16153, "La Fosse aux Epreuves"), Point(6408, -12358, "Forêt Insaisissable"), Point(6478, -15280, "Porte de l'Obscurité"))),
        Cle("excellent", "resin", "fung") to Gisement(listOf(50.0f to 100.0f), listOf(Point(6229, -11255, "Porte des Vents"), Point(6384, -16335, "La Fosse aux Epreuves"), Point(6523, -14817, "Porte de l'Obscurité"))),
        Cle("excellent", "resin", "glue") to Gisement(listOf(16.7f to 83.3f), listOf(Point(633, -11140, "Gouffre d'Ichor"), Point(5704, -10309, "Porte des Vents"), Point(5890, -16432, "La Fosse aux Epreuves"), Point(6466, -13108, "Forêt Insaisissable"), Point(6492, -14162, "Porte de l'Obscurité"))),
        Cle("excellent", "resin", "moon") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(5969, -11477, "Porte des Vents"))),
        Cle("excellent", "sap", "dante") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1080, -10575, "Gouffre d'Ichor"), Point(5847, -10492, "Porte des Vents"), Point(6149, -12550, "Forêt Insaisissable"), Point(6256, -15408, "Porte de l'Obscurité"))),
        Cle("excellent", "sap", "enola") to Gisement(listOf(0.0f to 49.9f), listOf(Point(1389, -10723, "Gouffre d'Ichor"), Point(6137, -10287, "Porte des Vents"), Point(6162, -12744, "Forêt Insaisissable"), Point(6656, -16641, "La Fosse aux Epreuves"))),
        Cle("excellent", "sap", "redhot") to Gisement(listOf(16.7f to 83.3f), listOf(Point(838, -10484, "Gouffre d'Ichor"), Point(5776, -12371, "Forêt Insaisissable"), Point(6190, -16574, "La Fosse aux Epreuves"))),
        Cle("excellent", "sap", "silverweed") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1376, -10769, "Gouffre d'Ichor"), Point(6116, -10004, "Porte des Vents"), Point(6291, -16494, "La Fosse aux Epreuves"), Point(6460, -14922, "Porte de l'Obscurité"))),
        Cle("excellent", "sap", "viscous") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(6087, -12470, "Forêt Insaisissable"))),
        Cle("excellent", "seed", "caprice") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1425, -10337, "Gouffre d'Ichor"), Point(6013, -10369, "Porte des Vents"), Point(6196, -15914, "La Fosse aux Epreuves"), Point(6537, -14437, "Porte de l'Obscurité"))),
        Cle("excellent", "seed", "sarina") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(5519, -10584, "Porte des Vents"), Point(6137, -16673, "La Fosse aux Epreuves"), Point(6374, -12082, "Forêt Insaisissable"))),
        Cle("excellent", "seed", "saurona") to Gisement(listOf(16.7f to 83.3f), listOf(Point(6169, -11057, "Porte des Vents"), Point(6309, -14363, "Porte de l'Obscurité"), Point(6585, -12413, "Forêt Insaisissable"), Point(6793, -16291, "La Fosse aux Epreuves"))),
        Cle("excellent", "seed", "silvio") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(6095, -11378, "Porte des Vents"), Point(6298, -14215, "Porte de l'Obscurité"), Point(6501, -12446, "Forêt Insaisissable"), Point(6691, -16171, "La Fosse aux Epreuves"))),
        Cle("excellent", "shell", "big") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(1034, -10017, "Gouffre d'Ichor"), Point(5672, -10435, "Porte des Vents"), Point(6480, -16342, "La Fosse aux Epreuves"), Point(6539, -13992, "Porte de l'Obscurité"))),
        Cle("excellent", "shell", "cuty") to Gisement(listOf(16.7f to 83.3f), listOf(Point(960, -9872, "Gouffre d'Ichor"), Point(5846, -10716, "Porte des Vents"), Point(6118, -14017, "Porte de l'Obscurité"), Point(6484, -12667, "Forêt Insaisissable"), Point(7116, -16911, "La Fosse aux Epreuves"))),
        Cle("excellent", "shell", "horny") to Gisement(listOf(0.0f to 49.9f), listOf(Point(901, -11118, "Gouffre d'Ichor"), Point(5976, -16547, "La Fosse aux Epreuves"), Point(6001, -10167, "Porte des Vents"), Point(6361, -15185, "Porte de l'Obscurité"), Point(6573, -12125, "Forêt Insaisissable"))),
        Cle("excellent", "shell", "smart") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1151, -10641, "Gouffre d'Ichor"), Point(5900, -10316, "Porte des Vents"), Point(6160, -16401, "La Fosse aux Epreuves"), Point(6643, -12887, "Forêt Insaisissable"))),
        Cle("excellent", "shell", "splinter") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(6029, -12614, "Forêt Insaisissable"), Point(6146, -14208, "Porte de l'Obscurité"), Point(6794, -16578, "La Fosse aux Epreuves"))),
        Cle("excellent", "wood", "abhaya") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(6113, -11508, "Porte des Vents"), Point(6788, -15633, "Porte de l'Obscurité"), Point(7180, -12433, "Forêt Insaisissable"))),
        Cle("excellent", "wood", "eyota") to Gisement(listOf(0.0f to 49.9f), listOf(Point(6084, -11141, "Porte des Vents"), Point(6512, -15684, "Porte de l'Obscurité"), Point(6707, -16030, "La Fosse aux Epreuves"))),
        Cle("excellent", "wood", "kachine") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(698, -10168, "Gouffre d'Ichor"), Point(5769, -10816, "Porte des Vents"), Point(6426, -16461, "La Fosse aux Epreuves"))),
        Cle("excellent", "wood", "motega") to Gisement(listOf(50.0f to 100.0f), listOf(Point(5859, -11398, "Porte des Vents"), Point(6480, -12240, "Forêt Insaisissable"), Point(6724, -15782, "Porte de l'Obscurité"))),
        Cle("excellent", "wood", "tama") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(5925, -10899, "Porte des Vents"), Point(6314, -15856, "La Fosse aux Epreuves"), Point(6660, -15666, "Porte de l'Obscurité"))),
        Cle("excellent", "wood_node", "nita") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(6093, -11331, "Porte des Vents"), Point(6465, -13363, "Forêt Insaisissable"))),
        Cle("excellent", "wood_node", "patee") to Gisement(listOf(0.0f to 49.9f), listOf(Point(587, -10749, "Gouffre d'Ichor"), Point(6136, -16797, "La Fosse aux Epreuves"), Point(6310, -12211, "Forêt Insaisissable"))),
        Cle("excellent", "wood_node", "scrath") to Gisement(listOf(16.7f to 83.3f), listOf(Point(6274, -11214, "Porte des Vents"), Point(6321, -14878, "Porte de l'Obscurité"), Point(6918, -16642, "La Fosse aux Epreuves"))),
        Cle("excellent", "wood_node", "tansy") to Gisement(listOf(50.0f to 100.0f), listOf(Point(5623, -16839, "La Fosse aux Epreuves"), Point(6035, -14292, "Porte de l'Obscurité"), Point(6061, -10916, "Porte des Vents"))),
        Cle("excellent", "wood_node", "yana") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(548, -11131, "Gouffre d'Ichor"), Point(5991, -15755, "La Fosse aux Epreuves"))),
        Cle("supreme", "amber", "beng") to Gisement(listOf(16.7f to 83.3f), listOf(Point(898, -14639, "Terre de la Continuité"), Point(1980, -15815, "Profondeurs Interdites"), Point(2661, -13887, "Cité Engloutie"), Point(3580, -10412, "Sources Interdites"))),
        Cle("supreme", "amber", "hash") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(1345, -14497, "Terre de la Continuité"), Point(1542, -14848, "Profondeurs Interdites"), Point(1753, -13673, "Cité Engloutie"), Point(3518, -10219, "Sources Interdites"))),
        Cle("supreme", "amber", "pha") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1279, -13981, "Terre de la Continuité"), Point(1427, -15032, "Profondeurs Interdites"), Point(1726, -13628, "Cité Engloutie"), Point(2971, -10137, "Sources Interdites"))),
        Cle("supreme", "amber", "sha") to Gisement(listOf(0.0f to 49.9f), listOf(Point(1589, -14309, "Terre de la Continuité"), Point(1990, -13481, "Cité Engloutie"), Point(1997, -15205, "Profondeurs Interdites"), Point(3347, -10042, "Sources Interdites"))),
        Cle("supreme", "amber", "soo") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1562, -14497, "Terre de la Continuité"), Point(1712, -14674, "Profondeurs Interdites"), Point(1845, -13616, "Cité Engloutie"), Point(3444, -10139, "Sources Interdites"))),
        Cle("supreme", "amber", "zun") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1476, -13704, "Terre de la Continuité"), Point(2023, -13749, "Cité Engloutie"), Point(2487, -15129, "Profondeurs Interdites"), Point(3193, -10084, "Sources Interdites"))),
        Cle("supreme", "bark", "adriel") to Gisement(listOf(0.0f to 49.9f), listOf(Point(470, -14030, "Terre de la Continuité"), Point(2444, -14723, "Profondeurs Interdites"), Point(2628, -14215, "Cité Engloutie"), Point(3098, -10512, "Sources Interdites"))),
        Cle("supreme", "bark", "beckers") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1039, -13520, "Terre de la Continuité"), Point(1515, -14715, "Profondeurs Interdites"), Point(2105, -13415, "Cité Engloutie"), Point(3362, -9889, "Sources Interdites"))),
        Cle("supreme", "bark", "mitexi") to Gisement(listOf(50.0f to 100.0f), listOf(Point(998, -13352, "Terre de la Continuité"), Point(2390, -14952, "Profondeurs Interdites"), Point(2692, -14032, "Cité Engloutie"), Point(3298, -10694, "Sources Interdites"))),
        Cle("supreme", "bark", "oath") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(966, -13688, "Terre de la Continuité"), Point(2163, -15002, "Profondeurs Interdites"), Point(2257, -13304, "Cité Engloutie"), Point(3560, -10632, "Sources Interdites"))),
        Cle("supreme", "bark", "perfling") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(1248, -13477, "Terre de la Continuité"), Point(1820, -14770, "Profondeurs Interdites"), Point(1939, -13251, "Cité Engloutie"), Point(3264, -10193, "Sources Interdites"))),
        Cle("supreme", "fiber", "anete") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(349, -13950, "Terre de la Continuité"), Point(1876, -13423, "Cité Engloutie"), Point(2589, -14987, "Profondeurs Interdites"), Point(3371, -10945, "Sources Interdites"))),
        Cle("supreme", "fiber", "buo") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1123, -13389, "Terre de la Continuité"), Point(2245, -13958, "Cité Engloutie"), Point(2566, -14883, "Profondeurs Interdites"), Point(2787, -10739, "Sources Interdites"))),
        Cle("supreme", "fiber", "dzao") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(902, -14477, "Terre de la Continuité"), Point(2345, -13833, "Cité Engloutie"), Point(2819, -15078, "Profondeurs Interdites"), Point(3378, -10286, "Sources Interdites"))),
        Cle("supreme", "fiber", "shu") to Gisement(listOf(0.0f to 49.9f), listOf(Point(576, -13903, "Terre de la Continuité"), Point(1913, -13829, "Cité Engloutie"), Point(1919, -15041, "Profondeurs Interdites"), Point(3056, -10898, "Sources Interdites"))),
        Cle("supreme", "oil", "gulatch") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(492, -13380, "Terre de la Continuité"), Point(2079, -13661, "Cité Engloutie"), Point(2282, -14952, "Profondeurs Interdites"), Point(3413, -10319, "Sources Interdites"))),
        Cle("supreme", "oil", "irin") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(601, -13999, "Terre de la Continuité"), Point(1558, -15244, "Profondeurs Interdites"), Point(2345, -13542, "Cité Engloutie"), Point(2998, -10359, "Sources Interdites"))),
        Cle("supreme", "oil", "koorin") to Gisement(listOf(16.7f to 83.3f), listOf(Point(658, -13669, "Terre de la Continuité"), Point(2060, -14092, "Cité Engloutie"), Point(2470, -15223, "Profondeurs Interdites"), Point(3200, -10952, "Sources Interdites"))),
        Cle("supreme", "oil", "pilan") to Gisement(listOf(50.0f to 100.0f), listOf(Point(966, -13247, "Terre de la Continuité"), Point(2072, -15584, "Profondeurs Interdites"), Point(2138, -14186, "Cité Engloutie"), Point(3329, -11078, "Sources Interdites"))),
        Cle("supreme", "resin", "dung") to Gisement(listOf(0.0f to 49.9f), listOf(Point(1220, -13366, "Terre de la Continuité"), Point(2206, -15697, "Profondeurs Interdites"), Point(2585, -14444, "Cité Engloutie"), Point(3458, -10630, "Sources Interdites"))),
        Cle("supreme", "resin", "fung") to Gisement(listOf(), listOf(Point(1386, -13540, "Terre de la Continuité"), Point(1650, -14891, "Profondeurs Interdites"), Point(1909, -13987, "Cité Engloutie"), Point(2869, -10432, "Sources Interdites"))),
        Cle("supreme", "resin", "glue") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1466, -14186, "Terre de la Continuité"), Point(2396, -14260, "Cité Engloutie"), Point(2778, -15229, "Profondeurs Interdites"), Point(3418, -10048, "Sources Interdites"))),
        Cle("supreme", "resin", "moon") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1412, -15182, "Profondeurs Interdites"), Point(1482, -13864, "Terre de la Continuité"), Point(2417, -14030, "Cité Engloutie"), Point(2987, -10677, "Sources Interdites"))),
        Cle("supreme", "sap", "dante") to Gisement(listOf(50.0f to 100.0f), listOf(Point(406, -13391, "Terre de la Continuité"), Point(1898, -15135, "Profondeurs Interdites"), Point(2183, -13813, "Cité Engloutie"), Point(3147, -10796, "Sources Interdites"))),
        Cle("supreme", "sap", "enola") to Gisement(listOf(0.0f to 49.9f), listOf(Point(795, -13227, "Terre de la Continuité"), Point(1667, -14952, "Profondeurs Interdites"), Point(2195, -13555, "Cité Engloutie"), Point(2964, -10594, "Sources Interdites"))),
        Cle("supreme", "sap", "redhot") to Gisement(listOf(16.7f to 83.3f), listOf(Point(420, -13710, "Terre de la Continuité"), Point(2230, -14290, "Cité Engloutie"), Point(2599, -15088, "Profondeurs Interdites"), Point(2853, -10870, "Sources Interdites"))),
        Cle("supreme", "sap", "silverweed") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1125, -13212, "Terre de la Continuité"), Point(1480, -14981, "Profondeurs Interdites"), Point(2089, -13280, "Cité Engloutie"), Point(2789, -10521, "Sources Interdites"))),
        Cle("supreme", "sap", "viscous") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(293, -13741, "Terre de la Continuité"), Point(1816, -15133, "Profondeurs Interdites"), Point(1919, -14303, "Cité Engloutie"), Point(3216, -11027, "Sources Interdites"))),
        Cle("supreme", "seed", "caprice") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(689, -14510, "Terre de la Continuité"), Point(2437, -15389, "Profondeurs Interdites"), Point(2499, -14350, "Cité Engloutie"), Point(3129, -10324, "Sources Interdites"))),
        Cle("supreme", "seed", "sarina") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(1281, -14094, "Terre de la Continuité"), Point(2345, -15346, "Profondeurs Interdites"), Point(2405, -14499, "Cité Engloutie"), Point(2818, -10361, "Sources Interdites"))),
        Cle("supreme", "seed", "saurona") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1644, -14003, "Terre de la Continuité"), Point(2198, -14374, "Cité Engloutie"), Point(2202, -15133, "Profondeurs Interdites"), Point(2682, -10515, "Sources Interdites"))),
        Cle("supreme", "seed", "silvio") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1289, -13673, "Terre de la Continuité"), Point(2341, -14180, "Cité Engloutie"), Point(2853, -10659, "Sources Interdites"), Point(2882, -14930, "Profondeurs Interdites"))),
        Cle("supreme", "shell", "big") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(642, -14606, "Terre de la Continuité"), Point(1820, -14122, "Cité Engloutie"), Point(2458, -14924, "Profondeurs Interdites"), Point(3291, -10981, "Sources Interdites"))),
        Cle("supreme", "shell", "cuty") to Gisement(listOf(16.7f to 83.3f), listOf(Point(1523, -14008, "Terre de la Continuité"), Point(2312, -14014, "Cité Engloutie"), Point(2675, -15389, "Profondeurs Interdites"), Point(3391, -11111, "Sources Interdites"))),
        Cle("supreme", "shell", "horny") to Gisement(listOf(0.0f to 49.9f), listOf(Point(441, -13778, "Terre de la Continuité"), Point(2335, -14352, "Cité Engloutie"), Point(2704, -14983, "Profondeurs Interdites"), Point(3733, -10457, "Sources Interdites"))),
        Cle("supreme", "shell", "smart") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(734, -14325, "Terre de la Continuité"), Point(1839, -14932, "Profondeurs Interdites"), Point(2023, -14299, "Cité Engloutie"), Point(3407, -10745, "Sources Interdites"))),
        Cle("supreme", "shell", "splinter") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(1632, -14385, "Terre de la Continuité"), Point(2417, -13741, "Cité Engloutie"), Point(2880, -15205, "Profondeurs Interdites"), Point(3182, -11140, "Sources Interdites"))),
        Cle("supreme", "wood", "abhaya") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(Point(711, -14180, "Terre de la Continuité"), Point(2403, -15625, "Profondeurs Interdites"), Point(2753, -13901, "Cité Engloutie"), Point(3353, -10375, "Sources Interdites"))),
        Cle("supreme", "wood", "eyota") to Gisement(listOf(0.0f to 49.9f), listOf(Point(748, -13862, "Terre de la Continuité"), Point(2292, -15149, "Profondeurs Interdites"), Point(2446, -14180, "Cité Engloutie"), Point(3087, -10630, "Sources Interdites"))),
        Cle("supreme", "wood", "kachine") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(705, -13561, "Terre de la Continuité"), Point(1650, -15194, "Profondeurs Interdites"), Point(1917, -14176, "Cité Engloutie"), Point(3322, -10785, "Sources Interdites"))),
        Cle("supreme", "wood", "motega") to Gisement(listOf(50.0f to 100.0f), listOf(Point(677, -13979, "Terre de la Continuité"), Point(2366, -15100, "Profondeurs Interdites"), Point(2757, -14383, "Cité Engloutie"), Point(3262, -10519, "Sources Interdites"))),
        Cle("supreme", "wood", "tama") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(408, -13825, "Terre de la Continuité"), Point(2118, -14143, "Cité Engloutie"), Point(2183, -14811, "Profondeurs Interdites"), Point(3176, -10670, "Sources Interdites"))),
        Cle("supreme", "wood_node", "nita") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(Point(943, -14856, "Terre de la Continuité"), Point(2042, -13413, "Cité Engloutie"), Point(2239, -14678, "Profondeurs Interdites"), Point(3456, -10035, "Sources Interdites"))),
        Cle("supreme", "wood_node", "patee") to Gisement(listOf(0.0f to 49.9f), listOf(Point(1128, -14309, "Terre de la Continuité"), Point(2269, -13225, "Cité Engloutie"), Point(2888, -14805, "Profondeurs Interdites"), Point(2933, -10432, "Sources Interdites"))),
        Cle("supreme", "wood_node", "scrath") to Gisement(listOf(16.7f to 83.3f), listOf(Point(787, -14399, "Terre de la Continuité"), Point(1749, -13350, "Cité Engloutie"), Point(1972, -14672, "Profondeurs Interdites"), Point(3600, -10095, "Sources Interdites"))),
        Cle("supreme", "wood_node", "tansy") to Gisement(listOf(50.0f to 100.0f), listOf(Point(1447, -14440, "Terre de la Continuité"), Point(1812, -13194, "Cité Engloutie"), Point(2651, -10734, "Sources Interdites"), Point(2983, -14803, "Profondeurs Interdites"))),
        Cle("supreme", "wood_node", "yana") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(Point(1068, -14670, "Terre de la Continuité"), Point(2284, -13487, "Cité Engloutie"), Point(2648, -14727, "Profondeurs Interdites"), Point(3282, -10330, "Sources Interdites"))),
    )

    /**
     * Le libellé affiché -> le couple du jeu.
     *
     * Les deux écrans ne nomment pas les matières pareil — « Colle » ici,
     * « Glue » là — et le relevé de la guilde porte les annotations de ceux qui
     * l'ont rempli. Tout est résolu à la fabrication : ici, un simple accès.
     */
    val LIBELLES: Map<Pair<String, String>, Pair<String, String>> = mapOf(
        ("Ambres" to "Beng") to ("amber" to "beng"),
        ("Ambres" to "Beng Agro") to ("amber" to "beng"),
        ("Ambres" to "Hash") to ("amber" to "hash"),
        ("Ambres" to "Pha") to ("amber" to "pha"),
        ("Ambres" to "Sha") to ("amber" to "sha"),
        ("Ambres" to "Soo") to ("amber" to "soo"),
        ("Ambres" to "Zun") to ("amber" to "zun"),
        ("Bois" to "Abhaya") to ("wood" to "abhaya"),
        ("Bois" to "Eyota") to ("wood" to "eyota"),
        ("Bois" to "Kachine") to ("wood" to "kachine"),
        ("Bois" to "Motega") to ("wood" to "motega"),
        ("Bois" to "Tama") to ("wood" to "tama"),
        ("Boucles" to "Nita") to ("wood_node" to "nita"),
        ("Boucles" to "Patee") to ("wood_node" to "patee"),
        ("Boucles" to "Scratch") to ("wood_node" to "scrath"),
        ("Boucles" to "Scrath") to ("wood_node" to "scrath"),
        ("Boucles" to "Tansy") to ("wood_node" to "tansy"),
        ("Boucles" to "Yana") to ("wood_node" to "yana"),
        ("Boucles" to "Yana ?") to ("wood_node" to "yana"),
        ("Carapace" to "Big") to ("shell" to "big"),
        ("Carapace" to "Cornée") to ("shell" to "horny"),
        ("Carapace" to "Cuty") to ("shell" to "cuty"),
        ("Carapace" to "Grosse") to ("shell" to "big"),
        ("Carapace" to "Horny") to ("shell" to "horny"),
        ("Carapace" to "Inteligente") to ("shell" to "smart"),
        ("Carapace" to "Migno Omg AGGRO") to ("shell" to "cuty"),
        ("Carapace" to "Mignonne") to ("shell" to "cuty"),
        ("Carapace" to "Smart") to ("shell" to "smart"),
        ("Carapace" to "Splinter") to ("shell" to "splinter"),
        ("Fibres" to "Anete") to ("fiber" to "anete"),
        ("Fibres" to "Anète") to ("fiber" to "anete"),
        ("Fibres" to "Buo") to ("fiber" to "buo"),
        ("Fibres" to "Dzao") to ("fiber" to "dzao"),
        ("Fibres" to "Shu") to ("fiber" to "shu"),
        ("Graines" to "Caprice") to ("seed" to "caprice"),
        ("Graines" to "Sarina") to ("seed" to "sarina"),
        ("Graines" to "Saurona") to ("seed" to "saurona"),
        ("Graines" to "Silvio") to ("seed" to "silvio"),
        ("Huile" to "Enola") to ("sap" to "enola"),
        ("Huile" to "Gulatch") to ("oil" to "gulatch"),
        ("Huile" to "Irin") to ("oil" to "irin"),
        ("Huile" to "Koorin") to ("oil" to "koorin"),
        ("Huile" to "Pilan") to ("oil" to "pilan"),
        ("Résine" to "Colle") to ("resin" to "glue"),
        ("Résine" to "Dung") to ("resin" to "dung"),
        ("Résine" to "Fung") to ("resin" to "fung"),
        ("Résine" to "Glue") to ("resin" to "glue"),
        ("Résine" to "Lune") to ("resin" to "moon"),
        ("Résine" to "Moon") to ("resin" to "moon"),
        ("Sève" to "Ardente") to ("sap" to "redhot"),
        ("Sève" to "Ardente ?") to ("sap" to "redhot"),
        ("Sève" to "Dante") to ("sap" to "dante"),
        ("Sève" to "Enola") to ("sap" to "enola"),
        ("Sève" to "Redhot") to ("sap" to "redhot"),
        ("Sève" to "Silverweed") to ("sap" to "silverweed"),
        ("Sève" to "Visc") to ("sap" to "viscous"),
        ("Sève" to "Visc agro KKT") to ("sap" to "viscous"),
        ("Écorce" to "Adriel") to ("bark" to "adriel"),
        ("Écorce" to "Beckers") to ("bark" to "beckers"),
        ("Écorce" to "Mitexi") to ("bark" to "mitexi"),
        ("Écorce" to "Oath") to ("bark" to "oath"),
        ("Écorce" to "Perfling") to ("bark" to "perfling"),
    )

    /** Où sort une matière telle qu'elle s'affiche, ou rien si on ne sait pas. */
    fun points(qualite: String, famille: String, matiere: String):
        List<Point> {
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.points ?: emptyList()
    }

    /** Les fourchettes d'humidité, en pourcentage. */
    fun humidites(qualite: String, famille: String, matiere: String):
        List<Pair<Float, Float>> {
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.humidites.orEmpty()
    }
}
