package net.ryzom.zyroom.model

import net.ryzom.zyroom.R

// Fichier produit par outils/table_gisements.py — ne pas modifier à la main.

/**
 * Où sortent les matières, en images.
 *
 * L'écran météo dit *quoi* sort ; ces vues disent *où*. Elles viennent du
 * tracker d'atys.us — vues de 320 × 300 portant le marqueur et le nom du
 * gisement — et les données de gisements sont celles de ballisticmystix.net.
 *
 * La clé est en français, comme ce qu'affiche l'écran ; la traduction vers les
 * noms du site est faite à la fabrication.
 */
object Gisements {
    data class Cle(val qualite: String, val famille: String, val matiere: String)

    data class Gisement(
        /** Les fourchettes d'humidité où la matière sort, en pourcentage. */
        val humidites: List<Pair<Float, Float>>,
        val images: List<Int>,
    )

    val TABLE: Map<Cle, Gisement> = mapOf(
        Cle("excellent", "amber", "beng") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_amber_beng_1, R.drawable.gis_excellent_amber_beng_2)),
        Cle("excellent", "amber", "hash") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_amber_hash_1, R.drawable.gis_excellent_amber_hash_2)),
        Cle("excellent", "amber", "pha") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_amber_pha_1, R.drawable.gis_excellent_amber_pha_2, R.drawable.gis_excellent_amber_pha_3)),
        Cle("excellent", "amber", "sha") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_amber_sha_1, R.drawable.gis_excellent_amber_sha_2)),
        Cle("excellent", "amber", "soo") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_amber_soo_1, R.drawable.gis_excellent_amber_soo_2)),
        Cle("excellent", "amber", "zun") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_amber_zun_1, R.drawable.gis_excellent_amber_zun_2)),
        Cle("excellent", "bark", "adriel") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_bark_adriel_1, R.drawable.gis_excellent_bark_adriel_2)),
        Cle("excellent", "bark", "beckers") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_bark_beckers_1, R.drawable.gis_excellent_bark_beckers_2, R.drawable.gis_excellent_bark_beckers_3, R.drawable.gis_excellent_bark_beckers_4, R.drawable.gis_excellent_bark_beckers_5, R.drawable.gis_excellent_bark_beckers_6)),
        Cle("excellent", "bark", "mitexi") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_bark_mitexi_1, R.drawable.gis_excellent_bark_mitexi_2, R.drawable.gis_excellent_bark_mitexi_3, R.drawable.gis_excellent_bark_mitexi_4, R.drawable.gis_excellent_bark_mitexi_5)),
        Cle("excellent", "bark", "oath") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_bark_oath_1, R.drawable.gis_excellent_bark_oath_2, R.drawable.gis_excellent_bark_oath_3, R.drawable.gis_excellent_bark_oath_4, R.drawable.gis_excellent_bark_oath_5, R.drawable.gis_excellent_bark_oath_6)),
        Cle("excellent", "bark", "perfling") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_bark_perfling_1, R.drawable.gis_excellent_bark_perfling_2, R.drawable.gis_excellent_bark_perfling_3, R.drawable.gis_excellent_bark_perfling_4, R.drawable.gis_excellent_bark_perfling_5, R.drawable.gis_excellent_bark_perfling_6)),
        Cle("excellent", "fiber", "anete") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_fiber_anete_1, R.drawable.gis_excellent_fiber_anete_2, R.drawable.gis_excellent_fiber_anete_3, R.drawable.gis_excellent_fiber_anete_4, R.drawable.gis_excellent_fiber_anete_5, R.drawable.gis_excellent_fiber_anete_6)),
        Cle("excellent", "fiber", "buo") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_fiber_buo_1)),
        Cle("excellent", "fiber", "dzao") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_fiber_dzao_1, R.drawable.gis_excellent_fiber_dzao_2, R.drawable.gis_excellent_fiber_dzao_3, R.drawable.gis_excellent_fiber_dzao_4, R.drawable.gis_excellent_fiber_dzao_5)),
        Cle("excellent", "fiber", "shu") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_fiber_shu_1, R.drawable.gis_excellent_fiber_shu_2, R.drawable.gis_excellent_fiber_shu_3, R.drawable.gis_excellent_fiber_shu_4, R.drawable.gis_excellent_fiber_shu_5, R.drawable.gis_excellent_fiber_shu_6)),
        Cle("excellent", "oil", "gulatch") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_oil_gulatch_1, R.drawable.gis_excellent_oil_gulatch_2)),
        Cle("excellent", "oil", "irin") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_oil_irin_1, R.drawable.gis_excellent_oil_irin_2)),
        Cle("excellent", "oil", "koorin") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_oil_koorin_1, R.drawable.gis_excellent_oil_koorin_2)),
        Cle("excellent", "oil", "pilan") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_oil_pilan_1, R.drawable.gis_excellent_oil_pilan_2)),
        Cle("excellent", "resin", "dung") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_resin_dung_1, R.drawable.gis_excellent_resin_dung_2)),
        Cle("excellent", "resin", "fung") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_resin_fung_1, R.drawable.gis_excellent_resin_fung_2, R.drawable.gis_excellent_resin_fung_3, R.drawable.gis_excellent_resin_fung_4, R.drawable.gis_excellent_resin_fung_5, R.drawable.gis_excellent_resin_fung_6)),
        Cle("excellent", "resin", "glue") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_resin_glue_1, R.drawable.gis_excellent_resin_glue_2, R.drawable.gis_excellent_resin_glue_3, R.drawable.gis_excellent_resin_glue_4, R.drawable.gis_excellent_resin_glue_5, R.drawable.gis_excellent_resin_glue_6)),
        Cle("excellent", "resin", "moon") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_resin_moon_1, R.drawable.gis_excellent_resin_moon_2, R.drawable.gis_excellent_resin_moon_3, R.drawable.gis_excellent_resin_moon_4, R.drawable.gis_excellent_resin_moon_5)),
        Cle("excellent", "sap", "dante") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_sap_dante_1, R.drawable.gis_excellent_sap_dante_2, R.drawable.gis_excellent_sap_dante_3, R.drawable.gis_excellent_sap_dante_4, R.drawable.gis_excellent_sap_dante_5, R.drawable.gis_excellent_sap_dante_6)),
        Cle("excellent", "sap", "enola") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_sap_enola_1, R.drawable.gis_excellent_sap_enola_2, R.drawable.gis_excellent_sap_enola_3, R.drawable.gis_excellent_sap_enola_4, R.drawable.gis_excellent_sap_enola_5, R.drawable.gis_excellent_sap_enola_6)),
        Cle("excellent", "sap", "redhot") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_sap_redhot_1, R.drawable.gis_excellent_sap_redhot_2, R.drawable.gis_excellent_sap_redhot_3, R.drawable.gis_excellent_sap_redhot_4, R.drawable.gis_excellent_sap_redhot_5)),
        Cle("excellent", "sap", "silverweed") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_sap_silverweed_1, R.drawable.gis_excellent_sap_silverweed_2, R.drawable.gis_excellent_sap_silverweed_3, R.drawable.gis_excellent_sap_silverweed_4, R.drawable.gis_excellent_sap_silverweed_5)),
        Cle("excellent", "sap", "viscous") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_sap_viscous_1, R.drawable.gis_excellent_sap_viscous_2, R.drawable.gis_excellent_sap_viscous_3, R.drawable.gis_excellent_sap_viscous_4, R.drawable.gis_excellent_sap_viscous_5, R.drawable.gis_excellent_sap_viscous_6)),
        Cle("excellent", "seed", "caprice") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_seed_caprice_1, R.drawable.gis_excellent_seed_caprice_2)),
        Cle("excellent", "seed", "sarina") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_seed_sarina_1, R.drawable.gis_excellent_seed_sarina_2)),
        Cle("excellent", "seed", "saurona") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_seed_saurona_1)),
        Cle("excellent", "seed", "silvio") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_seed_silvio_1, R.drawable.gis_excellent_seed_silvio_2)),
        Cle("excellent", "shell", "big") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_shell_big_1, R.drawable.gis_excellent_shell_big_2, R.drawable.gis_excellent_shell_big_3, R.drawable.gis_excellent_shell_big_4, R.drawable.gis_excellent_shell_big_5, R.drawable.gis_excellent_shell_big_6)),
        Cle("excellent", "shell", "cuty") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_shell_cuty_1, R.drawable.gis_excellent_shell_cuty_2, R.drawable.gis_excellent_shell_cuty_3, R.drawable.gis_excellent_shell_cuty_4, R.drawable.gis_excellent_shell_cuty_5, R.drawable.gis_excellent_shell_cuty_6)),
        Cle("excellent", "shell", "horny") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_shell_horny_1, R.drawable.gis_excellent_shell_horny_2, R.drawable.gis_excellent_shell_horny_3, R.drawable.gis_excellent_shell_horny_4, R.drawable.gis_excellent_shell_horny_5, R.drawable.gis_excellent_shell_horny_6)),
        Cle("excellent", "shell", "smart") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_shell_smart_1, R.drawable.gis_excellent_shell_smart_2, R.drawable.gis_excellent_shell_smart_3, R.drawable.gis_excellent_shell_smart_4, R.drawable.gis_excellent_shell_smart_5, R.drawable.gis_excellent_shell_smart_6)),
        Cle("excellent", "shell", "splinter") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_shell_splinter_1, R.drawable.gis_excellent_shell_splinter_2, R.drawable.gis_excellent_shell_splinter_3, R.drawable.gis_excellent_shell_splinter_4, R.drawable.gis_excellent_shell_splinter_5, R.drawable.gis_excellent_shell_splinter_6)),
        Cle("excellent", "wood", "abhaya") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_wood_abhaya_1, R.drawable.gis_excellent_wood_abhaya_2)),
        Cle("excellent", "wood", "eyota") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_wood_eyota_1, R.drawable.gis_excellent_wood_eyota_2, R.drawable.gis_excellent_wood_eyota_3, R.drawable.gis_excellent_wood_eyota_4, R.drawable.gis_excellent_wood_eyota_5, R.drawable.gis_excellent_wood_eyota_6)),
        Cle("excellent", "wood", "kachine") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_wood_kachine_1, R.drawable.gis_excellent_wood_kachine_2, R.drawable.gis_excellent_wood_kachine_3, R.drawable.gis_excellent_wood_kachine_4, R.drawable.gis_excellent_wood_kachine_5, R.drawable.gis_excellent_wood_kachine_6)),
        Cle("excellent", "wood", "motega") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_wood_motega_1)),
        Cle("excellent", "wood", "tama") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_wood_tama_1, R.drawable.gis_excellent_wood_tama_2, R.drawable.gis_excellent_wood_tama_3, R.drawable.gis_excellent_wood_tama_4, R.drawable.gis_excellent_wood_tama_5, R.drawable.gis_excellent_wood_tama_6)),
        Cle("excellent", "wood_node", "nita") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_excellent_wood_node_nita_1, R.drawable.gis_excellent_wood_node_nita_2)),
        Cle("excellent", "wood_node", "patee") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_excellent_wood_node_patee_1, R.drawable.gis_excellent_wood_node_patee_2)),
        Cle("excellent", "wood_node", "scrath") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_excellent_wood_node_scrath_1, R.drawable.gis_excellent_wood_node_scrath_2)),
        Cle("excellent", "wood_node", "tansy") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_excellent_wood_node_tansy_1, R.drawable.gis_excellent_wood_node_tansy_2, R.drawable.gis_excellent_wood_node_tansy_3, R.drawable.gis_excellent_wood_node_tansy_4, R.drawable.gis_excellent_wood_node_tansy_5)),
        Cle("excellent", "wood_node", "yana") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_excellent_wood_node_yana_1, R.drawable.gis_excellent_wood_node_yana_2)),
        Cle("supreme", "amber", "beng") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_amber_beng_1, R.drawable.gis_supreme_amber_beng_2)),
        Cle("supreme", "amber", "hash") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_amber_hash_1)),
        Cle("supreme", "amber", "pha") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_amber_pha_1, R.drawable.gis_supreme_amber_pha_2)),
        Cle("supreme", "amber", "sha") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_amber_sha_1, R.drawable.gis_supreme_amber_sha_2)),
        Cle("supreme", "amber", "soo") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_amber_soo_1, R.drawable.gis_supreme_amber_soo_2)),
        Cle("supreme", "amber", "zun") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_amber_zun_1, R.drawable.gis_supreme_amber_zun_2)),
        Cle("supreme", "bark", "adriel") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_bark_adriel_1)),
        Cle("supreme", "bark", "beckers") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_bark_beckers_1, R.drawable.gis_supreme_bark_beckers_2)),
        Cle("supreme", "bark", "mitexi") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_bark_mitexi_1)),
        Cle("supreme", "bark", "oath") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_bark_oath_1, R.drawable.gis_supreme_bark_oath_2)),
        Cle("supreme", "bark", "perfling") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_bark_perfling_1, R.drawable.gis_supreme_bark_perfling_2)),
        Cle("supreme", "fiber", "anete") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_fiber_anete_1, R.drawable.gis_supreme_fiber_anete_2)),
        Cle("supreme", "fiber", "buo") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_fiber_buo_1, R.drawable.gis_supreme_fiber_buo_2)),
        Cle("supreme", "fiber", "dzao") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_fiber_dzao_1)),
        Cle("supreme", "fiber", "shu") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_fiber_shu_1)),
        Cle("supreme", "oil", "gulatch") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_oil_gulatch_1, R.drawable.gis_supreme_oil_gulatch_2)),
        Cle("supreme", "oil", "irin") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_oil_irin_1, R.drawable.gis_supreme_oil_irin_2)),
        Cle("supreme", "oil", "koorin") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_oil_koorin_1)),
        Cle("supreme", "oil", "pilan") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_oil_pilan_1, R.drawable.gis_supreme_oil_pilan_2)),
        Cle("supreme", "resin", "dung") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_resin_dung_1, R.drawable.gis_supreme_resin_dung_2)),
        Cle("supreme", "resin", "glue") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_resin_glue_1, R.drawable.gis_supreme_resin_glue_2)),
        Cle("supreme", "resin", "moon") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_resin_moon_1, R.drawable.gis_supreme_resin_moon_2)),
        Cle("supreme", "sap", "dante") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_sap_dante_1, R.drawable.gis_supreme_sap_dante_2)),
        Cle("supreme", "sap", "enola") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_sap_enola_1)),
        Cle("supreme", "sap", "redhot") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_sap_redhot_1, R.drawable.gis_supreme_sap_redhot_2)),
        Cle("supreme", "sap", "silverweed") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_sap_silverweed_1, R.drawable.gis_supreme_sap_silverweed_2)),
        Cle("supreme", "sap", "viscous") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_sap_viscous_1)),
        Cle("supreme", "seed", "caprice") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_seed_caprice_1, R.drawable.gis_supreme_seed_caprice_2)),
        Cle("supreme", "seed", "sarina") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_seed_sarina_1)),
        Cle("supreme", "seed", "saurona") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_seed_saurona_1, R.drawable.gis_supreme_seed_saurona_2)),
        Cle("supreme", "seed", "silvio") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_seed_silvio_1, R.drawable.gis_supreme_seed_silvio_2)),
        Cle("supreme", "shell", "big") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_shell_big_1, R.drawable.gis_supreme_shell_big_2)),
        Cle("supreme", "shell", "cuty") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_shell_cuty_1, R.drawable.gis_supreme_shell_cuty_2)),
        Cle("supreme", "shell", "horny") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_shell_horny_1)),
        Cle("supreme", "shell", "smart") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_shell_smart_1, R.drawable.gis_supreme_shell_smart_2)),
        Cle("supreme", "shell", "splinter") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_shell_splinter_1, R.drawable.gis_supreme_shell_splinter_2)),
        Cle("supreme", "wood", "abhaya") to Gisement(listOf(16.7f to 49.9f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_wood_abhaya_1)),
        Cle("supreme", "wood", "eyota") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_wood_eyota_1, R.drawable.gis_supreme_wood_eyota_2)),
        Cle("supreme", "wood", "kachine") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_wood_kachine_1)),
        Cle("supreme", "wood", "motega") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_wood_motega_1)),
        Cle("supreme", "wood", "tama") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_wood_tama_1, R.drawable.gis_supreme_wood_tama_2)),
        Cle("supreme", "wood_node", "nita") to Gisement(listOf(0.0f to 16.6f, 83.4f to 100.0f), listOf(R.drawable.gis_supreme_wood_node_nita_1, R.drawable.gis_supreme_wood_node_nita_2)),
        Cle("supreme", "wood_node", "patee") to Gisement(listOf(0.0f to 49.9f), listOf(R.drawable.gis_supreme_wood_node_patee_1, R.drawable.gis_supreme_wood_node_patee_2)),
        Cle("supreme", "wood_node", "scrath") to Gisement(listOf(16.7f to 83.3f), listOf(R.drawable.gis_supreme_wood_node_scrath_1, R.drawable.gis_supreme_wood_node_scrath_2)),
        Cle("supreme", "wood_node", "tansy") to Gisement(listOf(50.0f to 100.0f), listOf(R.drawable.gis_supreme_wood_node_tansy_1)),
        Cle("supreme", "wood_node", "yana") to Gisement(listOf(0.0f to 16.6f, 50.0f to 83.3f), listOf(R.drawable.gis_supreme_wood_node_yana_1, R.drawable.gis_supreme_wood_node_yana_2)),
    )

    /**
     * Le libellé affiché -> le couple du tracker.
     *
     * Les deux écrans ne nomment pas les matières pareil — « Colle » ici,
     * « Glue » là — et le classeur de la guilde porte les annotations de ceux
     * qui l'ont rempli. Tout est résolu à la fabrication : ici, un simple accès.
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

    /** Les vues d'une matière telle qu'elle s'affiche, ou rien si on ne l'a pas. */
    fun cartes(qualite: String, famille: String, matiere: String): List<Int> {
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.images ?: emptyList()
    }
}
