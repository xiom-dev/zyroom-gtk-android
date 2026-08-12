"""Où sortent les matières, en images.

Fichier produit par ../zyroom-android/outils/table_gisements.py — ne pas
modifier à la main.

L'écran météo dit *quoi* sort ; ces vues disent *où*. Elles viennent du tracker
d'atys.us — vues de 320 × 300 portant le marqueur et le nom du gisement — et
les données de gisements sont celles de ballisticmystix.net.

La clé est en français, comme ce qu'affiche l'écran.
"""
import os

LARGEUR = 320
HAUTEUR = 300

#: Les images, à côté de ce fichier : le Makefile recopie le paquet en entier.
DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gisements")

#: (qualité, famille, matière) -> ([fourchettes d'humidité], [fichiers])
GISEMENTS = {
    ("excellent", "amber", "beng"): ([(16.7, 83.3)], ["gis_excellent_amber_beng_1.webp", "gis_excellent_amber_beng_2.webp"]),
    ("excellent", "amber", "hash"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_amber_hash_1.webp", "gis_excellent_amber_hash_2.webp"]),
    ("excellent", "amber", "pha"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_amber_pha_1.webp", "gis_excellent_amber_pha_2.webp", "gis_excellent_amber_pha_3.webp"]),
    ("excellent", "amber", "sha"): ([(0.0, 49.9)], ["gis_excellent_amber_sha_1.webp", "gis_excellent_amber_sha_2.webp"]),
    ("excellent", "amber", "soo"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_amber_soo_1.webp", "gis_excellent_amber_soo_2.webp"]),
    ("excellent", "amber", "zun"): ([(50.0, 100.0)], ["gis_excellent_amber_zun_1.webp", "gis_excellent_amber_zun_2.webp"]),
    ("excellent", "bark", "adriel"): ([(0.0, 49.9)], ["gis_excellent_bark_adriel_1.webp", "gis_excellent_bark_adriel_2.webp"]),
    ("excellent", "bark", "beckers"): ([(16.7, 83.3)], ["gis_excellent_bark_beckers_1.webp", "gis_excellent_bark_beckers_2.webp", "gis_excellent_bark_beckers_3.webp", "gis_excellent_bark_beckers_4.webp", "gis_excellent_bark_beckers_5.webp", "gis_excellent_bark_beckers_6.webp"]),
    ("excellent", "bark", "mitexi"): ([(50.0, 100.0)], ["gis_excellent_bark_mitexi_1.webp", "gis_excellent_bark_mitexi_2.webp", "gis_excellent_bark_mitexi_3.webp", "gis_excellent_bark_mitexi_4.webp", "gis_excellent_bark_mitexi_5.webp"]),
    ("excellent", "bark", "oath"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_bark_oath_1.webp", "gis_excellent_bark_oath_2.webp", "gis_excellent_bark_oath_3.webp", "gis_excellent_bark_oath_4.webp", "gis_excellent_bark_oath_5.webp", "gis_excellent_bark_oath_6.webp"]),
    ("excellent", "bark", "perfling"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_bark_perfling_1.webp", "gis_excellent_bark_perfling_2.webp", "gis_excellent_bark_perfling_3.webp", "gis_excellent_bark_perfling_4.webp", "gis_excellent_bark_perfling_5.webp", "gis_excellent_bark_perfling_6.webp"]),
    ("excellent", "fiber", "anete"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_fiber_anete_1.webp", "gis_excellent_fiber_anete_2.webp", "gis_excellent_fiber_anete_3.webp", "gis_excellent_fiber_anete_4.webp", "gis_excellent_fiber_anete_5.webp", "gis_excellent_fiber_anete_6.webp"]),
    ("excellent", "fiber", "buo"): ([(50.0, 100.0)], ["gis_excellent_fiber_buo_1.webp"]),
    ("excellent", "fiber", "dzao"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_fiber_dzao_1.webp", "gis_excellent_fiber_dzao_2.webp", "gis_excellent_fiber_dzao_3.webp", "gis_excellent_fiber_dzao_4.webp", "gis_excellent_fiber_dzao_5.webp"]),
    ("excellent", "fiber", "shu"): ([(0.0, 49.9)], ["gis_excellent_fiber_shu_1.webp", "gis_excellent_fiber_shu_2.webp", "gis_excellent_fiber_shu_3.webp", "gis_excellent_fiber_shu_4.webp", "gis_excellent_fiber_shu_5.webp", "gis_excellent_fiber_shu_6.webp"]),
    ("excellent", "oil", "gulatch"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_oil_gulatch_1.webp", "gis_excellent_oil_gulatch_2.webp"]),
    ("excellent", "oil", "irin"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_oil_irin_1.webp", "gis_excellent_oil_irin_2.webp"]),
    ("excellent", "oil", "koorin"): ([(16.7, 83.3)], ["gis_excellent_oil_koorin_1.webp", "gis_excellent_oil_koorin_2.webp"]),
    ("excellent", "oil", "pilan"): ([(50.0, 100.0)], ["gis_excellent_oil_pilan_1.webp", "gis_excellent_oil_pilan_2.webp"]),
    ("excellent", "resin", "dung"): ([(0.0, 49.9)], ["gis_excellent_resin_dung_1.webp", "gis_excellent_resin_dung_2.webp"]),
    ("excellent", "resin", "fung"): ([(50.0, 100.0)], ["gis_excellent_resin_fung_1.webp", "gis_excellent_resin_fung_2.webp", "gis_excellent_resin_fung_3.webp", "gis_excellent_resin_fung_4.webp", "gis_excellent_resin_fung_5.webp", "gis_excellent_resin_fung_6.webp"]),
    ("excellent", "resin", "glue"): ([(16.7, 83.3)], ["gis_excellent_resin_glue_1.webp", "gis_excellent_resin_glue_2.webp", "gis_excellent_resin_glue_3.webp", "gis_excellent_resin_glue_4.webp", "gis_excellent_resin_glue_5.webp", "gis_excellent_resin_glue_6.webp"]),
    ("excellent", "resin", "moon"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_resin_moon_1.webp", "gis_excellent_resin_moon_2.webp", "gis_excellent_resin_moon_3.webp", "gis_excellent_resin_moon_4.webp", "gis_excellent_resin_moon_5.webp"]),
    ("excellent", "sap", "dante"): ([(50.0, 100.0)], ["gis_excellent_sap_dante_1.webp", "gis_excellent_sap_dante_2.webp", "gis_excellent_sap_dante_3.webp", "gis_excellent_sap_dante_4.webp", "gis_excellent_sap_dante_5.webp", "gis_excellent_sap_dante_6.webp"]),
    ("excellent", "sap", "enola"): ([(0.0, 49.9)], ["gis_excellent_sap_enola_1.webp", "gis_excellent_sap_enola_2.webp", "gis_excellent_sap_enola_3.webp", "gis_excellent_sap_enola_4.webp", "gis_excellent_sap_enola_5.webp", "gis_excellent_sap_enola_6.webp"]),
    ("excellent", "sap", "redhot"): ([(16.7, 83.3)], ["gis_excellent_sap_redhot_1.webp", "gis_excellent_sap_redhot_2.webp", "gis_excellent_sap_redhot_3.webp", "gis_excellent_sap_redhot_4.webp", "gis_excellent_sap_redhot_5.webp"]),
    ("excellent", "sap", "silverweed"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_sap_silverweed_1.webp", "gis_excellent_sap_silverweed_2.webp", "gis_excellent_sap_silverweed_3.webp", "gis_excellent_sap_silverweed_4.webp", "gis_excellent_sap_silverweed_5.webp"]),
    ("excellent", "sap", "viscous"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_sap_viscous_1.webp", "gis_excellent_sap_viscous_2.webp", "gis_excellent_sap_viscous_3.webp", "gis_excellent_sap_viscous_4.webp", "gis_excellent_sap_viscous_5.webp", "gis_excellent_sap_viscous_6.webp"]),
    ("excellent", "seed", "caprice"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_seed_caprice_1.webp", "gis_excellent_seed_caprice_2.webp"]),
    ("excellent", "seed", "sarina"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_seed_sarina_1.webp", "gis_excellent_seed_sarina_2.webp"]),
    ("excellent", "seed", "saurona"): ([(16.7, 83.3)], ["gis_excellent_seed_saurona_1.webp"]),
    ("excellent", "seed", "silvio"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_seed_silvio_1.webp", "gis_excellent_seed_silvio_2.webp"]),
    ("excellent", "shell", "big"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_shell_big_1.webp", "gis_excellent_shell_big_2.webp", "gis_excellent_shell_big_3.webp", "gis_excellent_shell_big_4.webp", "gis_excellent_shell_big_5.webp", "gis_excellent_shell_big_6.webp"]),
    ("excellent", "shell", "cuty"): ([(16.7, 83.3)], ["gis_excellent_shell_cuty_1.webp", "gis_excellent_shell_cuty_2.webp", "gis_excellent_shell_cuty_3.webp", "gis_excellent_shell_cuty_4.webp", "gis_excellent_shell_cuty_5.webp", "gis_excellent_shell_cuty_6.webp"]),
    ("excellent", "shell", "horny"): ([(0.0, 49.9)], ["gis_excellent_shell_horny_1.webp", "gis_excellent_shell_horny_2.webp", "gis_excellent_shell_horny_3.webp", "gis_excellent_shell_horny_4.webp", "gis_excellent_shell_horny_5.webp", "gis_excellent_shell_horny_6.webp"]),
    ("excellent", "shell", "smart"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_shell_smart_1.webp", "gis_excellent_shell_smart_2.webp", "gis_excellent_shell_smart_3.webp", "gis_excellent_shell_smart_4.webp", "gis_excellent_shell_smart_5.webp", "gis_excellent_shell_smart_6.webp"]),
    ("excellent", "shell", "splinter"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_shell_splinter_1.webp", "gis_excellent_shell_splinter_2.webp", "gis_excellent_shell_splinter_3.webp", "gis_excellent_shell_splinter_4.webp", "gis_excellent_shell_splinter_5.webp", "gis_excellent_shell_splinter_6.webp"]),
    ("excellent", "wood", "abhaya"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_excellent_wood_abhaya_1.webp", "gis_excellent_wood_abhaya_2.webp"]),
    ("excellent", "wood", "eyota"): ([(0.0, 49.9)], ["gis_excellent_wood_eyota_1.webp", "gis_excellent_wood_eyota_2.webp", "gis_excellent_wood_eyota_3.webp", "gis_excellent_wood_eyota_4.webp", "gis_excellent_wood_eyota_5.webp", "gis_excellent_wood_eyota_6.webp"]),
    ("excellent", "wood", "kachine"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_wood_kachine_1.webp", "gis_excellent_wood_kachine_2.webp", "gis_excellent_wood_kachine_3.webp", "gis_excellent_wood_kachine_4.webp", "gis_excellent_wood_kachine_5.webp", "gis_excellent_wood_kachine_6.webp"]),
    ("excellent", "wood", "motega"): ([(50.0, 100.0)], ["gis_excellent_wood_motega_1.webp"]),
    ("excellent", "wood", "tama"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_wood_tama_1.webp", "gis_excellent_wood_tama_2.webp", "gis_excellent_wood_tama_3.webp", "gis_excellent_wood_tama_4.webp", "gis_excellent_wood_tama_5.webp", "gis_excellent_wood_tama_6.webp"]),
    ("excellent", "wood_node", "nita"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_excellent_wood_node_nita_1.webp", "gis_excellent_wood_node_nita_2.webp"]),
    ("excellent", "wood_node", "patee"): ([(0.0, 49.9)], ["gis_excellent_wood_node_patee_1.webp", "gis_excellent_wood_node_patee_2.webp"]),
    ("excellent", "wood_node", "scrath"): ([(16.7, 83.3)], ["gis_excellent_wood_node_scrath_1.webp", "gis_excellent_wood_node_scrath_2.webp"]),
    ("excellent", "wood_node", "tansy"): ([(50.0, 100.0)], ["gis_excellent_wood_node_tansy_1.webp", "gis_excellent_wood_node_tansy_2.webp", "gis_excellent_wood_node_tansy_3.webp", "gis_excellent_wood_node_tansy_4.webp", "gis_excellent_wood_node_tansy_5.webp"]),
    ("excellent", "wood_node", "yana"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_excellent_wood_node_yana_1.webp", "gis_excellent_wood_node_yana_2.webp"]),
    ("supreme", "amber", "beng"): ([(16.7, 83.3)], ["gis_supreme_amber_beng_1.webp", "gis_supreme_amber_beng_2.webp"]),
    ("supreme", "amber", "hash"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_amber_hash_1.webp"]),
    ("supreme", "amber", "pha"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_amber_pha_1.webp", "gis_supreme_amber_pha_2.webp"]),
    ("supreme", "amber", "sha"): ([(0.0, 49.9)], ["gis_supreme_amber_sha_1.webp", "gis_supreme_amber_sha_2.webp"]),
    ("supreme", "amber", "soo"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_amber_soo_1.webp", "gis_supreme_amber_soo_2.webp"]),
    ("supreme", "amber", "zun"): ([(50.0, 100.0)], ["gis_supreme_amber_zun_1.webp", "gis_supreme_amber_zun_2.webp"]),
    ("supreme", "bark", "adriel"): ([(0.0, 49.9)], ["gis_supreme_bark_adriel_1.webp"]),
    ("supreme", "bark", "beckers"): ([(16.7, 83.3)], ["gis_supreme_bark_beckers_1.webp", "gis_supreme_bark_beckers_2.webp"]),
    ("supreme", "bark", "mitexi"): ([(50.0, 100.0)], ["gis_supreme_bark_mitexi_1.webp"]),
    ("supreme", "bark", "oath"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_bark_oath_1.webp", "gis_supreme_bark_oath_2.webp"]),
    ("supreme", "bark", "perfling"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_bark_perfling_1.webp", "gis_supreme_bark_perfling_2.webp"]),
    ("supreme", "fiber", "anete"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_fiber_anete_1.webp", "gis_supreme_fiber_anete_2.webp"]),
    ("supreme", "fiber", "buo"): ([(50.0, 100.0)], ["gis_supreme_fiber_buo_1.webp", "gis_supreme_fiber_buo_2.webp"]),
    ("supreme", "fiber", "dzao"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_fiber_dzao_1.webp"]),
    ("supreme", "fiber", "shu"): ([(0.0, 49.9)], ["gis_supreme_fiber_shu_1.webp"]),
    ("supreme", "oil", "gulatch"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_oil_gulatch_1.webp", "gis_supreme_oil_gulatch_2.webp"]),
    ("supreme", "oil", "irin"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_oil_irin_1.webp", "gis_supreme_oil_irin_2.webp"]),
    ("supreme", "oil", "koorin"): ([(16.7, 83.3)], ["gis_supreme_oil_koorin_1.webp"]),
    ("supreme", "oil", "pilan"): ([(50.0, 100.0)], ["gis_supreme_oil_pilan_1.webp", "gis_supreme_oil_pilan_2.webp"]),
    ("supreme", "resin", "dung"): ([(0.0, 49.9)], ["gis_supreme_resin_dung_1.webp", "gis_supreme_resin_dung_2.webp"]),
    ("supreme", "resin", "glue"): ([(16.7, 83.3)], ["gis_supreme_resin_glue_1.webp", "gis_supreme_resin_glue_2.webp"]),
    ("supreme", "resin", "moon"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_resin_moon_1.webp", "gis_supreme_resin_moon_2.webp"]),
    ("supreme", "sap", "dante"): ([(50.0, 100.0)], ["gis_supreme_sap_dante_1.webp", "gis_supreme_sap_dante_2.webp"]),
    ("supreme", "sap", "enola"): ([(0.0, 49.9)], ["gis_supreme_sap_enola_1.webp"]),
    ("supreme", "sap", "redhot"): ([(16.7, 83.3)], ["gis_supreme_sap_redhot_1.webp", "gis_supreme_sap_redhot_2.webp"]),
    ("supreme", "sap", "silverweed"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_sap_silverweed_1.webp", "gis_supreme_sap_silverweed_2.webp"]),
    ("supreme", "sap", "viscous"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_sap_viscous_1.webp"]),
    ("supreme", "seed", "caprice"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_seed_caprice_1.webp", "gis_supreme_seed_caprice_2.webp"]),
    ("supreme", "seed", "sarina"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_seed_sarina_1.webp"]),
    ("supreme", "seed", "saurona"): ([(16.7, 83.3)], ["gis_supreme_seed_saurona_1.webp", "gis_supreme_seed_saurona_2.webp"]),
    ("supreme", "seed", "silvio"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_seed_silvio_1.webp", "gis_supreme_seed_silvio_2.webp"]),
    ("supreme", "shell", "big"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_shell_big_1.webp", "gis_supreme_shell_big_2.webp"]),
    ("supreme", "shell", "cuty"): ([(16.7, 83.3)], ["gis_supreme_shell_cuty_1.webp", "gis_supreme_shell_cuty_2.webp"]),
    ("supreme", "shell", "horny"): ([(0.0, 49.9)], ["gis_supreme_shell_horny_1.webp"]),
    ("supreme", "shell", "smart"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_shell_smart_1.webp", "gis_supreme_shell_smart_2.webp"]),
    ("supreme", "shell", "splinter"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_shell_splinter_1.webp", "gis_supreme_shell_splinter_2.webp"]),
    ("supreme", "wood", "abhaya"): ([(16.7, 49.9), (83.4, 100.0)], ["gis_supreme_wood_abhaya_1.webp"]),
    ("supreme", "wood", "eyota"): ([(0.0, 49.9)], ["gis_supreme_wood_eyota_1.webp", "gis_supreme_wood_eyota_2.webp"]),
    ("supreme", "wood", "kachine"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_wood_kachine_1.webp"]),
    ("supreme", "wood", "motega"): ([(50.0, 100.0)], ["gis_supreme_wood_motega_1.webp"]),
    ("supreme", "wood", "tama"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_wood_tama_1.webp", "gis_supreme_wood_tama_2.webp"]),
    ("supreme", "wood_node", "nita"): ([(0.0, 16.6), (83.4, 100.0)], ["gis_supreme_wood_node_nita_1.webp", "gis_supreme_wood_node_nita_2.webp"]),
    ("supreme", "wood_node", "patee"): ([(0.0, 49.9)], ["gis_supreme_wood_node_patee_1.webp", "gis_supreme_wood_node_patee_2.webp"]),
    ("supreme", "wood_node", "scrath"): ([(16.7, 83.3)], ["gis_supreme_wood_node_scrath_1.webp", "gis_supreme_wood_node_scrath_2.webp"]),
    ("supreme", "wood_node", "tansy"): ([(50.0, 100.0)], ["gis_supreme_wood_node_tansy_1.webp"]),
    ("supreme", "wood_node", "yana"): ([(0.0, 16.6), (50.0, 83.3)], ["gis_supreme_wood_node_yana_1.webp", "gis_supreme_wood_node_yana_2.webp"]),
}

#: (famille, libellé affiché) -> (famille, matière) du tracker.
#:
#: Les deux écrans ne nomment pas les matières pareil — « Colle » ici, « Glue »
#: là — et le classeur de la guilde porte les annotations de ceux qui l'ont
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


def cartes(qualite: str, famille: str, matiere: str) -> list:
    """Les chemins des vues d'une matière, ou une liste vide si on ne l'a pas."""
    trouve = _trouve(qualite, famille, matiere)
    return [os.path.join(DOSSIER, nom) for nom in trouve[1]] if trouve else []


def humidites(qualite: str, famille: str, matiere: str) -> list:
    """Les fourchettes d'humidité où la matière sort, en pourcentage."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[0]) if trouve else []
