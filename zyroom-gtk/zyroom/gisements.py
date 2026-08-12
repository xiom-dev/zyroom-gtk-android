"""Où sortent les matières, en coordonnées de jeu.

Fichier produit par ../zyroom-android/outils/table_gisements.py — ne pas
modifier à la main.

L'écran météo dit *quoi* sort ; ceci dit *où*. Les positions viennent du relevé
que Ballistic Mystix publie, dont l'auteur a donné son accord écrit pour qu'on
s'en serve et qu'on le redistribue. L'application dessine elle-même, sur la
carte d'Atys embarquée.

La clé est en français, comme ce qu'affiche l'écran.
"""

#: (qualité, famille, matière) -> ([fourchettes d'humidité], [positions de jeu])
GISEMENTS = {
    ("excellent", "amber", "beng"): ([(16.7, 83.3)], [(1397, -10706, "Gouffre d'Ichor"), (6492, -12960, "Forêt Insaisissable"), (6759, -15383, "Porte de l'Obscurité")]),
    ("excellent", "amber", "hash"): ([(0.0, 16.6), (83.4, 100.0)], [(964, -10598, "Gouffre d'Ichor"), (5810, -10186, "Porte des Vents"), (6653, -13071, "Forêt Insaisissable"), (6812, -15271, "Porte de l'Obscurité")]),
    ("excellent", "amber", "pha"): ([(16.7, 49.9), (83.4, 100.0)], [(1507, -10745, "Gouffre d'Ichor"), (5897, -12987, "Forêt Insaisissable"), (6330, -11381, "Porte des Vents"), (6988, -16238, "La Fosse aux Epreuves")]),
    ("excellent", "amber", "sha"): ([(0.0, 49.9)], [(1435, -10968, "Gouffre d'Ichor"), (5757, -10772, "Porte des Vents"), (6015, -13496, "Forêt Insaisissable"), (6186, -16018, "La Fosse aux Epreuves"), (6250, -15147, "Porte de l'Obscurité")]),
    ("excellent", "amber", "soo"): ([(0.0, 16.6), (50.0, 83.3)], [(1204, -10793, "Gouffre d'Ichor"), (6061, -11046, "Porte des Vents"), (6110, -16088, "La Fosse aux Epreuves"), (6532, -13518, "Forêt Insaisissable"), (6552, -15222, "Porte de l'Obscurité")]),
    ("excellent", "amber", "zun"): ([(50.0, 100.0)], [(1534, -10963, "Gouffre d'Ichor"), (5996, -13239, "Forêt Insaisissable"), (6171, -10148, "Porte des Vents")]),
    ("excellent", "bark", "adriel"): ([(0.0, 49.9)], [(832, -10683, "Gouffre d'Ichor"), (5655, -10065, "Porte des Vents"), (6210, -16139, "La Fosse aux Epreuves"), (6387, -14575, "Porte de l'Obscurité")]),
    ("excellent", "bark", "beckers"): ([(16.7, 83.3)], [(1533, -10337, "Gouffre d'Ichor"), (5880, -9778, "Porte des Vents"), (6539, -13414, "Forêt Insaisissable")]),
    ("excellent", "bark", "mitexi"): ([(50.0, 100.0)], [(654, -10580, "Gouffre d'Ichor"), (5563, -9834, "Porte des Vents"), (6408, -13180, "Forêt Insaisissable"), (6423, -14400, "Porte de l'Obscurité"), (6572, -16034, "La Fosse aux Epreuves")]),
    ("excellent", "bark", "oath"): ([(16.7, 49.9), (83.4, 100.0)], [(5583, -9692, "Porte des Vents"), (6534, -15960, "La Fosse aux Epreuves"), (6595, -13272, "Forêt Insaisissable")]),
    ("excellent", "bark", "perfling"): ([(0.0, 16.6), (83.4, 100.0)], [(783, -10249, "Gouffre d'Ichor"), (6901, -16476, "La Fosse aux Epreuves")]),
    ("excellent", "fiber", "anete"): ([(0.0, 16.6), (50.0, 83.3)], [(768, -10956, "Gouffre d'Ichor"), (6052, -11616, "Porte des Vents"), (6745, -16684, "La Fosse aux Epreuves")]),
    ("excellent", "fiber", "buo"): ([(50.0, 100.0)], [(6004, -11335, "Porte des Vents"), (6611, -14115, "Porte de l'Obscurité"), (6780, -12786, "Forêt Insaisissable")]),
    ("excellent", "fiber", "dzao"): ([(0.0, 16.6), (83.4, 100.0)], [(813, -11122, "Gouffre d'Ichor"), (5827, -16821, "La Fosse aux Epreuves"), (5931, -11220, "Porte des Vents"), (6774, -13018, "Forêt Insaisissable")]),
    ("excellent", "fiber", "shu"): ([(0.0, 49.9)], [(570, -10872, "Gouffre d'Ichor"), (6212, -11421, "Porte des Vents"), (6882, -16861, "La Fosse aux Epreuves"), (6963, -12804, "Forêt Insaisissable")]),
    ("excellent", "oil", "gulatch"): ([(0.0, 16.6), (50.0, 83.3)], [(926, -10207, "Gouffre d'Ichor"), (5974, -10005, "Porte des Vents"), (6553, -16567, "La Fosse aux Epreuves"), (6623, -15768, "Porte de l'Obscurité")]),
    ("excellent", "oil", "irin"): ([(16.7, 49.9), (83.4, 100.0)], [(1200, -10365, "Gouffre d'Ichor"), (5814, -9880, "Porte des Vents"), (6421, -14359, "Porte de l'Obscurité"), (6874, -12449, "Forêt Insaisissable")]),
    ("excellent", "oil", "koorin"): ([(16.7, 83.3)], [(817, -10931, "Gouffre d'Ichor"), (5634, -9847, "Porte des Vents"), (6030, -14194, "Porte de l'Obscurité"), (6099, -13144, "Forêt Insaisissable"), (6376, -15987, "La Fosse aux Epreuves")]),
    ("excellent", "oil", "pilan"): ([(50.0, 100.0)], [(1326, -10846, "Gouffre d'Ichor"), (5810, -10016, "Porte des Vents"), (5831, -16535, "La Fosse aux Epreuves"), (5951, -12100, "Forêt Insaisissable"), (6619, -15416, "Porte de l'Obscurité")]),
    ("excellent", "resin", "dung"): ([(0.0, 49.9)], [(2206, -15691, "Profondeurs Interdites"), (5794, -10627, "Porte des Vents"), (6032, -16153, "La Fosse aux Epreuves"), (6408, -12358, "Forêt Insaisissable"), (6478, -15280, "Porte de l'Obscurité")]),
    ("excellent", "resin", "fung"): ([(50.0, 100.0)], [(6229, -11255, "Porte des Vents"), (6384, -16335, "La Fosse aux Epreuves"), (6523, -14817, "Porte de l'Obscurité")]),
    ("excellent", "resin", "glue"): ([(16.7, 83.3)], [(633, -11140, "Gouffre d'Ichor"), (5704, -10309, "Porte des Vents"), (5890, -16432, "La Fosse aux Epreuves"), (6466, -13108, "Forêt Insaisissable"), (6492, -14162, "Porte de l'Obscurité")]),
    ("excellent", "resin", "moon"): ([(16.7, 49.9), (83.4, 100.0)], [(5969, -11477, "Porte des Vents")]),
    ("excellent", "sap", "dante"): ([(50.0, 100.0)], [(1080, -10575, "Gouffre d'Ichor"), (5847, -10492, "Porte des Vents"), (6149, -12550, "Forêt Insaisissable"), (6256, -15408, "Porte de l'Obscurité")]),
    ("excellent", "sap", "enola"): ([(0.0, 49.9)], [(1389, -10723, "Gouffre d'Ichor"), (6137, -10287, "Porte des Vents"), (6162, -12744, "Forêt Insaisissable"), (6656, -16641, "La Fosse aux Epreuves")]),
    ("excellent", "sap", "redhot"): ([(16.7, 83.3)], [(838, -10484, "Gouffre d'Ichor"), (5776, -12371, "Forêt Insaisissable"), (6190, -16574, "La Fosse aux Epreuves")]),
    ("excellent", "sap", "silverweed"): ([(0.0, 16.6), (50.0, 83.3)], [(1376, -10769, "Gouffre d'Ichor"), (6116, -10004, "Porte des Vents"), (6291, -16494, "La Fosse aux Epreuves"), (6460, -14922, "Porte de l'Obscurité")]),
    ("excellent", "sap", "viscous"): ([(16.7, 49.9), (83.4, 100.0)], [(6087, -12470, "Forêt Insaisissable")]),
    ("excellent", "seed", "caprice"): ([(0.0, 16.6), (50.0, 83.3)], [(1425, -10337, "Gouffre d'Ichor"), (6013, -10369, "Porte des Vents"), (6196, -15914, "La Fosse aux Epreuves"), (6537, -14437, "Porte de l'Obscurité")]),
    ("excellent", "seed", "sarina"): ([(0.0, 16.6), (83.4, 100.0)], [(5519, -10584, "Porte des Vents"), (6137, -16673, "La Fosse aux Epreuves"), (6374, -12082, "Forêt Insaisissable")]),
    ("excellent", "seed", "saurona"): ([(16.7, 83.3)], [(6169, -11057, "Porte des Vents"), (6309, -14363, "Porte de l'Obscurité"), (6585, -12413, "Forêt Insaisissable"), (6793, -16291, "La Fosse aux Epreuves")]),
    ("excellent", "seed", "silvio"): ([(16.7, 49.9), (83.4, 100.0)], [(6095, -11378, "Porte des Vents"), (6298, -14215, "Porte de l'Obscurité"), (6501, -12446, "Forêt Insaisissable"), (6691, -16171, "La Fosse aux Epreuves")]),
    ("excellent", "shell", "big"): ([(0.0, 16.6), (83.4, 100.0)], [(1034, -10017, "Gouffre d'Ichor"), (5672, -10435, "Porte des Vents"), (6480, -16342, "La Fosse aux Epreuves"), (6539, -13992, "Porte de l'Obscurité")]),
    ("excellent", "shell", "cuty"): ([(16.7, 83.3)], [(960, -9872, "Gouffre d'Ichor"), (5846, -10716, "Porte des Vents"), (6118, -14017, "Porte de l'Obscurité"), (6484, -12667, "Forêt Insaisissable"), (7116, -16911, "La Fosse aux Epreuves")]),
    ("excellent", "shell", "horny"): ([(0.0, 49.9)], [(901, -11118, "Gouffre d'Ichor"), (5976, -16547, "La Fosse aux Epreuves"), (6001, -10167, "Porte des Vents"), (6361, -15185, "Porte de l'Obscurité"), (6573, -12125, "Forêt Insaisissable")]),
    ("excellent", "shell", "smart"): ([(0.0, 16.6), (50.0, 83.3)], [(1151, -10641, "Gouffre d'Ichor"), (5900, -10316, "Porte des Vents"), (6160, -16401, "La Fosse aux Epreuves"), (6643, -12887, "Forêt Insaisissable")]),
    ("excellent", "shell", "splinter"): ([(16.7, 49.9), (83.4, 100.0)], [(6029, -12614, "Forêt Insaisissable"), (6146, -14208, "Porte de l'Obscurité"), (6794, -16578, "La Fosse aux Epreuves")]),
    ("excellent", "wood", "abhaya"): ([(16.7, 49.9), (83.4, 100.0)], [(6113, -11508, "Porte des Vents"), (6788, -15633, "Porte de l'Obscurité"), (7180, -12433, "Forêt Insaisissable")]),
    ("excellent", "wood", "eyota"): ([(0.0, 49.9)], [(6084, -11141, "Porte des Vents"), (6512, -15684, "Porte de l'Obscurité"), (6707, -16030, "La Fosse aux Epreuves")]),
    ("excellent", "wood", "kachine"): ([(0.0, 16.6), (83.4, 100.0)], [(698, -10168, "Gouffre d'Ichor"), (5769, -10816, "Porte des Vents"), (6426, -16461, "La Fosse aux Epreuves")]),
    ("excellent", "wood", "motega"): ([(50.0, 100.0)], [(5859, -11398, "Porte des Vents"), (6480, -12240, "Forêt Insaisissable"), (6724, -15782, "Porte de l'Obscurité")]),
    ("excellent", "wood", "tama"): ([(0.0, 16.6), (50.0, 83.3)], [(5925, -10899, "Porte des Vents"), (6314, -15856, "La Fosse aux Epreuves"), (6660, -15666, "Porte de l'Obscurité")]),
    ("excellent", "wood_node", "nita"): ([(0.0, 16.6), (83.4, 100.0)], [(6093, -11331, "Porte des Vents"), (6465, -13363, "Forêt Insaisissable")]),
    ("excellent", "wood_node", "patee"): ([(0.0, 49.9)], [(587, -10749, "Gouffre d'Ichor"), (6136, -16797, "La Fosse aux Epreuves"), (6310, -12211, "Forêt Insaisissable")]),
    ("excellent", "wood_node", "scrath"): ([(16.7, 83.3)], [(6274, -11214, "Porte des Vents"), (6321, -14878, "Porte de l'Obscurité"), (6918, -16642, "La Fosse aux Epreuves")]),
    ("excellent", "wood_node", "tansy"): ([(50.0, 100.0)], [(5623, -16839, "La Fosse aux Epreuves"), (6035, -14292, "Porte de l'Obscurité"), (6061, -10916, "Porte des Vents")]),
    ("excellent", "wood_node", "yana"): ([(0.0, 16.6), (50.0, 83.3)], [(548, -11131, "Gouffre d'Ichor"), (5991, -15755, "La Fosse aux Epreuves")]),
    ("supreme", "amber", "beng"): ([(16.7, 83.3)], [(898, -14639, "Terre de la Continuité"), (1980, -15815, "Profondeurs Interdites"), (2661, -13887, "Cité Engloutie"), (3580, -10412, "Sources Interdites")]),
    ("supreme", "amber", "hash"): ([(0.0, 16.6), (83.4, 100.0)], [(1345, -14497, "Terre de la Continuité"), (1542, -14848, "Profondeurs Interdites"), (1753, -13673, "Cité Engloutie"), (3518, -10219, "Sources Interdites")]),
    ("supreme", "amber", "pha"): ([(16.7, 49.9), (83.4, 100.0)], [(1279, -13981, "Terre de la Continuité"), (1427, -15032, "Profondeurs Interdites"), (1726, -13628, "Cité Engloutie"), (2971, -10137, "Sources Interdites")]),
    ("supreme", "amber", "sha"): ([(0.0, 49.9)], [(1589, -14309, "Terre de la Continuité"), (1990, -13481, "Cité Engloutie"), (1997, -15205, "Profondeurs Interdites"), (3347, -10042, "Sources Interdites")]),
    ("supreme", "amber", "soo"): ([(0.0, 16.6), (50.0, 83.3)], [(1562, -14497, "Terre de la Continuité"), (1712, -14674, "Profondeurs Interdites"), (1845, -13616, "Cité Engloutie"), (3444, -10139, "Sources Interdites")]),
    ("supreme", "amber", "zun"): ([(50.0, 100.0)], [(1476, -13704, "Terre de la Continuité"), (2023, -13749, "Cité Engloutie"), (2487, -15129, "Profondeurs Interdites"), (3193, -10084, "Sources Interdites")]),
    ("supreme", "bark", "adriel"): ([(0.0, 49.9)], [(470, -14030, "Terre de la Continuité"), (2444, -14723, "Profondeurs Interdites"), (2628, -14215, "Cité Engloutie"), (3098, -10512, "Sources Interdites")]),
    ("supreme", "bark", "beckers"): ([(16.7, 83.3)], [(1039, -13520, "Terre de la Continuité"), (1515, -14715, "Profondeurs Interdites"), (2105, -13415, "Cité Engloutie"), (3362, -9889, "Sources Interdites")]),
    ("supreme", "bark", "mitexi"): ([(50.0, 100.0)], [(998, -13352, "Terre de la Continuité"), (2390, -14952, "Profondeurs Interdites"), (2692, -14032, "Cité Engloutie"), (3298, -10694, "Sources Interdites")]),
    ("supreme", "bark", "oath"): ([(16.7, 49.9), (83.4, 100.0)], [(966, -13688, "Terre de la Continuité"), (2163, -15002, "Profondeurs Interdites"), (2257, -13304, "Cité Engloutie"), (3560, -10632, "Sources Interdites")]),
    ("supreme", "bark", "perfling"): ([(0.0, 16.6), (83.4, 100.0)], [(1248, -13477, "Terre de la Continuité"), (1820, -14770, "Profondeurs Interdites"), (1939, -13251, "Cité Engloutie"), (3264, -10193, "Sources Interdites")]),
    ("supreme", "fiber", "anete"): ([(0.0, 16.6), (50.0, 83.3)], [(349, -13950, "Terre de la Continuité"), (1876, -13423, "Cité Engloutie"), (2589, -14987, "Profondeurs Interdites"), (3371, -10945, "Sources Interdites")]),
    ("supreme", "fiber", "buo"): ([(50.0, 100.0)], [(1123, -13389, "Terre de la Continuité"), (2245, -13958, "Cité Engloutie"), (2566, -14883, "Profondeurs Interdites"), (2787, -10739, "Sources Interdites")]),
    ("supreme", "fiber", "dzao"): ([(0.0, 16.6), (83.4, 100.0)], [(902, -14477, "Terre de la Continuité"), (2345, -13833, "Cité Engloutie"), (2819, -15078, "Profondeurs Interdites"), (3378, -10286, "Sources Interdites")]),
    ("supreme", "fiber", "shu"): ([(0.0, 49.9)], [(576, -13903, "Terre de la Continuité"), (1913, -13829, "Cité Engloutie"), (1919, -15041, "Profondeurs Interdites"), (3056, -10898, "Sources Interdites")]),
    ("supreme", "oil", "gulatch"): ([(0.0, 16.6), (50.0, 83.3)], [(492, -13380, "Terre de la Continuité"), (2079, -13661, "Cité Engloutie"), (2282, -14952, "Profondeurs Interdites"), (3413, -10319, "Sources Interdites")]),
    ("supreme", "oil", "irin"): ([(16.7, 49.9), (83.4, 100.0)], [(601, -13999, "Terre de la Continuité"), (1558, -15244, "Profondeurs Interdites"), (2345, -13542, "Cité Engloutie"), (2998, -10359, "Sources Interdites")]),
    ("supreme", "oil", "koorin"): ([(16.7, 83.3)], [(658, -13669, "Terre de la Continuité"), (2060, -14092, "Cité Engloutie"), (2470, -15223, "Profondeurs Interdites"), (3200, -10952, "Sources Interdites")]),
    ("supreme", "oil", "pilan"): ([(50.0, 100.0)], [(966, -13247, "Terre de la Continuité"), (2072, -15584, "Profondeurs Interdites"), (2138, -14186, "Cité Engloutie"), (3329, -11078, "Sources Interdites")]),
    ("supreme", "resin", "dung"): ([(0.0, 49.9)], [(1220, -13366, "Terre de la Continuité"), (2206, -15697, "Profondeurs Interdites"), (2585, -14444, "Cité Engloutie"), (3458, -10630, "Sources Interdites")]),
    ("supreme", "resin", "fung"): ([], [(1386, -13540, "Terre de la Continuité"), (1650, -14891, "Profondeurs Interdites"), (1909, -13987, "Cité Engloutie"), (2869, -10432, "Sources Interdites")]),
    ("supreme", "resin", "glue"): ([(16.7, 83.3)], [(1466, -14186, "Terre de la Continuité"), (2396, -14260, "Cité Engloutie"), (2778, -15229, "Profondeurs Interdites"), (3418, -10048, "Sources Interdites")]),
    ("supreme", "resin", "moon"): ([(16.7, 49.9), (83.4, 100.0)], [(1412, -15182, "Profondeurs Interdites"), (1482, -13864, "Terre de la Continuité"), (2417, -14030, "Cité Engloutie"), (2987, -10677, "Sources Interdites")]),
    ("supreme", "sap", "dante"): ([(50.0, 100.0)], [(406, -13391, "Terre de la Continuité"), (1898, -15135, "Profondeurs Interdites"), (2183, -13813, "Cité Engloutie"), (3147, -10796, "Sources Interdites")]),
    ("supreme", "sap", "enola"): ([(0.0, 49.9)], [(795, -13227, "Terre de la Continuité"), (1667, -14952, "Profondeurs Interdites"), (2195, -13555, "Cité Engloutie"), (2964, -10594, "Sources Interdites")]),
    ("supreme", "sap", "redhot"): ([(16.7, 83.3)], [(420, -13710, "Terre de la Continuité"), (2230, -14290, "Cité Engloutie"), (2599, -15088, "Profondeurs Interdites"), (2853, -10870, "Sources Interdites")]),
    ("supreme", "sap", "silverweed"): ([(0.0, 16.6), (50.0, 83.3)], [(1125, -13212, "Terre de la Continuité"), (1480, -14981, "Profondeurs Interdites"), (2089, -13280, "Cité Engloutie"), (2789, -10521, "Sources Interdites")]),
    ("supreme", "sap", "viscous"): ([(16.7, 49.9), (83.4, 100.0)], [(293, -13741, "Terre de la Continuité"), (1816, -15133, "Profondeurs Interdites"), (1919, -14303, "Cité Engloutie"), (3216, -11027, "Sources Interdites")]),
    ("supreme", "seed", "caprice"): ([(0.0, 16.6), (50.0, 83.3)], [(689, -14510, "Terre de la Continuité"), (2437, -15389, "Profondeurs Interdites"), (2499, -14350, "Cité Engloutie"), (3129, -10324, "Sources Interdites")]),
    ("supreme", "seed", "sarina"): ([(0.0, 16.6), (83.4, 100.0)], [(1281, -14094, "Terre de la Continuité"), (2345, -15346, "Profondeurs Interdites"), (2405, -14499, "Cité Engloutie"), (2818, -10361, "Sources Interdites")]),
    ("supreme", "seed", "saurona"): ([(16.7, 83.3)], [(1644, -14003, "Terre de la Continuité"), (2198, -14374, "Cité Engloutie"), (2202, -15133, "Profondeurs Interdites"), (2682, -10515, "Sources Interdites")]),
    ("supreme", "seed", "silvio"): ([(16.7, 49.9), (83.4, 100.0)], [(1289, -13673, "Terre de la Continuité"), (2341, -14180, "Cité Engloutie"), (2853, -10659, "Sources Interdites"), (2882, -14930, "Profondeurs Interdites")]),
    ("supreme", "shell", "big"): ([(0.0, 16.6), (83.4, 100.0)], [(642, -14606, "Terre de la Continuité"), (1820, -14122, "Cité Engloutie"), (2458, -14924, "Profondeurs Interdites"), (3291, -10981, "Sources Interdites")]),
    ("supreme", "shell", "cuty"): ([(16.7, 83.3)], [(1523, -14008, "Terre de la Continuité"), (2312, -14014, "Cité Engloutie"), (2675, -15389, "Profondeurs Interdites"), (3391, -11111, "Sources Interdites")]),
    ("supreme", "shell", "horny"): ([(0.0, 49.9)], [(441, -13778, "Terre de la Continuité"), (2335, -14352, "Cité Engloutie"), (2704, -14983, "Profondeurs Interdites"), (3733, -10457, "Sources Interdites")]),
    ("supreme", "shell", "smart"): ([(0.0, 16.6), (50.0, 83.3)], [(734, -14325, "Terre de la Continuité"), (1839, -14932, "Profondeurs Interdites"), (2023, -14299, "Cité Engloutie"), (3407, -10745, "Sources Interdites")]),
    ("supreme", "shell", "splinter"): ([(16.7, 49.9), (83.4, 100.0)], [(1632, -14385, "Terre de la Continuité"), (2417, -13741, "Cité Engloutie"), (2880, -15205, "Profondeurs Interdites"), (3182, -11140, "Sources Interdites")]),
    ("supreme", "wood", "abhaya"): ([(16.7, 49.9), (83.4, 100.0)], [(711, -14180, "Terre de la Continuité"), (2403, -15625, "Profondeurs Interdites"), (2753, -13901, "Cité Engloutie"), (3353, -10375, "Sources Interdites")]),
    ("supreme", "wood", "eyota"): ([(0.0, 49.9)], [(748, -13862, "Terre de la Continuité"), (2292, -15149, "Profondeurs Interdites"), (2446, -14180, "Cité Engloutie"), (3087, -10630, "Sources Interdites")]),
    ("supreme", "wood", "kachine"): ([(0.0, 16.6), (83.4, 100.0)], [(705, -13561, "Terre de la Continuité"), (1650, -15194, "Profondeurs Interdites"), (1917, -14176, "Cité Engloutie"), (3322, -10785, "Sources Interdites")]),
    ("supreme", "wood", "motega"): ([(50.0, 100.0)], [(677, -13979, "Terre de la Continuité"), (2366, -15100, "Profondeurs Interdites"), (2757, -14383, "Cité Engloutie"), (3262, -10519, "Sources Interdites")]),
    ("supreme", "wood", "tama"): ([(0.0, 16.6), (50.0, 83.3)], [(408, -13825, "Terre de la Continuité"), (2118, -14143, "Cité Engloutie"), (2183, -14811, "Profondeurs Interdites"), (3176, -10670, "Sources Interdites")]),
    ("supreme", "wood_node", "nita"): ([(0.0, 16.6), (83.4, 100.0)], [(943, -14856, "Terre de la Continuité"), (2042, -13413, "Cité Engloutie"), (2239, -14678, "Profondeurs Interdites"), (3456, -10035, "Sources Interdites")]),
    ("supreme", "wood_node", "patee"): ([(0.0, 49.9)], [(1128, -14309, "Terre de la Continuité"), (2269, -13225, "Cité Engloutie"), (2888, -14805, "Profondeurs Interdites"), (2933, -10432, "Sources Interdites")]),
    ("supreme", "wood_node", "scrath"): ([(16.7, 83.3)], [(787, -14399, "Terre de la Continuité"), (1749, -13350, "Cité Engloutie"), (1972, -14672, "Profondeurs Interdites"), (3600, -10095, "Sources Interdites")]),
    ("supreme", "wood_node", "tansy"): ([(50.0, 100.0)], [(1447, -14440, "Terre de la Continuité"), (1812, -13194, "Cité Engloutie"), (2651, -10734, "Sources Interdites"), (2983, -14803, "Profondeurs Interdites")]),
    ("supreme", "wood_node", "yana"): ([(0.0, 16.6), (50.0, 83.3)], [(1068, -14670, "Terre de la Continuité"), (2284, -13487, "Cité Engloutie"), (2648, -14727, "Profondeurs Interdites"), (3282, -10330, "Sources Interdites")]),
}

#: (famille, libellé affiché) -> (famille, matière) du jeu.
#:
#: Les deux écrans ne nomment pas les matières pareil — « Colle » ici, « Glue »
#: là — et le relevé de la guilde porte les annotations de ceux qui l'ont
#: rempli. Tout est résolu à la fabrication : ici, un simple accès.
LIBELLES = {
    ("Ambres", "Beng"): ("amber", "beng"),
    ("Ambres", "Beng Agro"): ("amber", "beng"),
    ("Ambres", "Hash"): ("amber", "hash"),
    ("Ambres", "Pha"): ("amber", "pha"),
    ("Ambres", "Sha"): ("amber", "sha"),
    ("Ambres", "Soo"): ("amber", "soo"),
    ("Ambres", "Zun"): ("amber", "zun"),
    ("Bois", "Abhaya"): ("wood", "abhaya"),
    ("Bois", "Eyota"): ("wood", "eyota"),
    ("Bois", "Kachine"): ("wood", "kachine"),
    ("Bois", "Motega"): ("wood", "motega"),
    ("Bois", "Tama"): ("wood", "tama"),
    ("Boucles", "Nita"): ("wood_node", "nita"),
    ("Boucles", "Patee"): ("wood_node", "patee"),
    ("Boucles", "Scratch"): ("wood_node", "scrath"),
    ("Boucles", "Scrath"): ("wood_node", "scrath"),
    ("Boucles", "Tansy"): ("wood_node", "tansy"),
    ("Boucles", "Yana"): ("wood_node", "yana"),
    ("Boucles", "Yana ?"): ("wood_node", "yana"),
    ("Carapace", "Big"): ("shell", "big"),
    ("Carapace", "Cornée"): ("shell", "horny"),
    ("Carapace", "Cuty"): ("shell", "cuty"),
    ("Carapace", "Grosse"): ("shell", "big"),
    ("Carapace", "Horny"): ("shell", "horny"),
    ("Carapace", "Inteligente"): ("shell", "smart"),
    ("Carapace", "Migno Omg AGGRO"): ("shell", "cuty"),
    ("Carapace", "Mignonne"): ("shell", "cuty"),
    ("Carapace", "Smart"): ("shell", "smart"),
    ("Carapace", "Splinter"): ("shell", "splinter"),
    ("Fibres", "Anete"): ("fiber", "anete"),
    ("Fibres", "Anète"): ("fiber", "anete"),
    ("Fibres", "Buo"): ("fiber", "buo"),
    ("Fibres", "Dzao"): ("fiber", "dzao"),
    ("Fibres", "Shu"): ("fiber", "shu"),
    ("Graines", "Caprice"): ("seed", "caprice"),
    ("Graines", "Sarina"): ("seed", "sarina"),
    ("Graines", "Saurona"): ("seed", "saurona"),
    ("Graines", "Silvio"): ("seed", "silvio"),
    ("Huile", "Enola"): ("sap", "enola"),
    ("Huile", "Gulatch"): ("oil", "gulatch"),
    ("Huile", "Irin"): ("oil", "irin"),
    ("Huile", "Koorin"): ("oil", "koorin"),
    ("Huile", "Pilan"): ("oil", "pilan"),
    ("Résine", "Colle"): ("resin", "glue"),
    ("Résine", "Dung"): ("resin", "dung"),
    ("Résine", "Fung"): ("resin", "fung"),
    ("Résine", "Glue"): ("resin", "glue"),
    ("Résine", "Lune"): ("resin", "moon"),
    ("Résine", "Moon"): ("resin", "moon"),
    ("Sève", "Ardente"): ("sap", "redhot"),
    ("Sève", "Ardente ?"): ("sap", "redhot"),
    ("Sève", "Dante"): ("sap", "dante"),
    ("Sève", "Enola"): ("sap", "enola"),
    ("Sève", "Redhot"): ("sap", "redhot"),
    ("Sève", "Silverweed"): ("sap", "silverweed"),
    ("Sève", "Visc"): ("sap", "viscous"),
    ("Sève", "Visc agro KKT"): ("sap", "viscous"),
    ("Écorce", "Adriel"): ("bark", "adriel"),
    ("Écorce", "Beckers"): ("bark", "beckers"),
    ("Écorce", "Mitexi"): ("bark", "mitexi"),
    ("Écorce", "Oath"): ("bark", "oath"),
    ("Écorce", "Perfling"): ("bark", "perfling"),
}


def _trouve(qualite: str, famille: str, matiere: str):
    couple = LIBELLES.get((famille, matiere))
    return GISEMENTS.get((qualite,) + couple) if couple else None


def points(qualite: str, famille: str, matiere: str) -> list:
    """Où sort une matière, en coordonnées de jeu ; vide si on ne sait pas."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[1]) if trouve else []


def humidites(qualite: str, famille: str, matiere: str) -> list:
    """Les fourchettes d'humidité où la matière sort, en pourcentage."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[0]) if trouve else []
