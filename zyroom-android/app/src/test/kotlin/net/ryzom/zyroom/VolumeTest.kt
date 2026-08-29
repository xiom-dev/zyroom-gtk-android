package net.ryzom.zyroom

import net.ryzom.zyroom.model.ItemType
import net.ryzom.zyroom.model.Volume
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Le volume des objets, porté de `zyroom/volume.py`.
 *
 * Les cas ne sont pas inventés : ce sont des fiches relevées dans les
 * inventaires réels d'un personnage et de deux guildes — 1628 fiches distinctes,
 * dont on a gardé quelques exemplaires de chacun des 21 couples
 * (type, coefficient) rencontrés. Les valeurs attendues sont celles que le
 * calcul de référence, celui du bureau, leur donne.
 *
 * Ce qu'on protège ici : un portage qui dérive. Le volume ne vient pas du
 * flux, il se déduit du nom de fiche par un enchaînement de motifs où l'ordre
 * compte — déplacer un test dans cet enchaînement change silencieusement le
 * remplissage de tous les coffres.
 */
class VolumeTest {

    private data class Cas(val fiche: String, val type: ItemType, val coef: Double)

    private val cas = listOf(
        Cas("m0009chafe01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("m0009chajc01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("m0009chajd01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("m0677chuje01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("m0667ccopd01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("m0619chhpe01.sitem", ItemType.ANIMAL_MAT, 0.5),
        Cas("ixpca01.sitem", ItemType.CATA, 0.01),
        Cas("ixpca03.sitem", ItemType.CATA, 0.01),
        Cas("ic_anlor_weapon01.sitem", ItemType.EQUIPMENT, 0.0),
        Cas("ic_anlor_weapon01b.sitem", ItemType.EQUIPMENT, 0.0),
        Cas("ic_anlor_weapon02.sitem", ItemType.EQUIPMENT, 0.0),
        Cas("ic_ice_stick.sitem", ItemType.EQUIPMENT, 0.0),
        Cas("icmp1pp.sitem", ItemType.EQUIPMENT, 0.04),
        Cas("ictp2bp.sitem", ItemType.EQUIPMENT, 0.1),
        Cas("ictp2rp.sitem", ItemType.EQUIPMENT, 0.1),
        Cas("iczp2rp.sitem", ItemType.EQUIPMENT, 0.1),
        Cas("icfja.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("icfja_3.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("icfjb.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("icfjr.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("iczjd.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("iczjb_3.sitem", ItemType.EQUIPMENT, 2.0),
        Cas("icfsbb.sitem", ItemType.EQUIPMENT, 5.0),
        Cas("icmm1pdl.sitem", ItemType.EQUIPMENT, 5.0),
        Cas("icmsbl.sitem", ItemType.EQUIPMENT, 5.0),
        Cas("icokamm1pd_1.sitem", ItemType.EQUIPMENT, 5.0),
        Cas("ic_anlor_helmet01.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("iccacp_boss_fyros_e1.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("iccalb.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("ictahb_2.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("icmamg_2.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("ictams_3.sitem", ItemType.EQUIPMENT, 7.0),
        Cas("iccm1sa.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("icfm1bm_2.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("icfm1bs_3.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("icfm2ms.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("ictm2ms_2.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("iczm1ps.sitem", ItemType.EQUIPMENT, 10.0),
        Cas("iccm2bm.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("iccm2pp.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("iccm2sa.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("icmr2rl.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("iczm2ss_3.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("icfm2ss.sitem", ItemType.EQUIPMENT, 15.0),
        Cas("iccahb.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("iccahb_b.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("iccahg.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("iccahh_b.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("iccahg_b.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("iccahs.sitem", ItemType.EQUIPMENT, 20.0),
        Cas("ic_candy_stick.sitem", ItemType.EQUIPMENT, 30.0),
        Cas("ic_halloween_stick.sitem", ItemType.EQUIPMENT, 30.0),
        Cas("icokamr2a_1.sitem", ItemType.EQUIPMENT, 30.0),
        Cas("icokamr2a_2.sitem", ItemType.EQUIPMENT, 30.0),
        Cas("icokamr2l_2.sitem", ItemType.EQUIPMENT, 30.0),
        Cas("m0001dxadf01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("m0001dxaff01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("m0001dxajf01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("m0823dxacc01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("m0117dxaje01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("m0102dxalf01.sitem", ItemType.NATURAL_MAT, 0.5),
        Cas("anniversary_dance_conso.sitem", ItemType.OTHER, 0.0),
        Cas("chopper_2.sitem", ItemType.OTHER, 0.0),
        Cas("conso_fireworks_a.sitem", ItemType.OTHER, 0.0),
        Cas("steak_rendor_2.sitem", ItemType.OTHER, 0.0),
        Cas("slaughter_week_token.sitem", ItemType.OTHER, 0.0),
        Cas("rpjobitem_201_c5.sitem", ItemType.OTHER, 0.0),
        Cas("compo_mark1.sitem", ItemType.OTHER, 0.5),
        Cas("compo_mark2.sitem", ItemType.OTHER, 0.5),
        Cas("compo_weapon_mark1.sitem", ItemType.OTHER, 0.5),
        Cas("s2e1_seve_suc.sitem", ItemType.OTHER, 0.5),
        Cas("ipk_major_artisan.sitem", ItemType.OTHER, 1.0),
        Cas("ipk_major_life.sitem", ItemType.OTHER, 1.0),
        Cas("ipk_major_mage.sitem", ItemType.OTHER, 1.0),
        Cas("ipk_minor_reju.sitem", ItemType.OTHER, 1.0),
        Cas("ipmf05.sitem", ItemType.OTHER, 1.0),
        Cas("if2.sitem", ItemType.OTHER, 5.0),
        Cas("teddyubo.sitem", ItemType.OTHER, 5.0),
        Cas("if3.sitem", ItemType.OTHER, 9.0),
        Cas("if1.sitem", ItemType.OTHER, 15.0),
        Cas("system_mp_choice.sitem", ItemType.SYSTEM_MAT, 0.0),
        Cas("system_mp_choice_black.sitem", ItemType.SYSTEM_MAT, 0.0),
        Cas("system_mp_choice_blue.sitem", ItemType.SYSTEM_MAT, 0.0),
        Cas("system_mp_choice_white.sitem", ItemType.SYSTEM_MAT, 0.0),
        Cas("system_mp_choice_purple.sitem", ItemType.SYSTEM_MAT, 0.0),
        Cas("tp_kami_almati.sitem", ItemType.TELEPORTER, 0.0),
        Cas("tp_kami_bountybeaches.sitem", ItemType.TELEPORTER, 0.0),
        Cas("tp_kami_dewdrops.sitem", ItemType.TELEPORTER, 0.0),
        Cas("tp_kami_groveofumbra.sitem", ItemType.TELEPORTER, 0.0),
        Cas("tp_kami_the_under_spring_fyros.sitem", ItemType.TELEPORTER, 0.0),
        Cas("tp_kami_oflovaksoasis.sitem", ItemType.TELEPORTER, 0.0),
    )

    @Test
    fun `chaque fiche relevée garde le coefficient du bureau`() {
        for (c in cas) {
            assertEquals("coefficient de ${c.fiche}", c.coef,
                         Volume.coefficient(c.fiche), 0.0001)
        }
    }

    @Test
    fun `chaque fiche relevée garde le type du bureau`() {
        for (c in cas) {
            assertEquals("type de ${c.fiche}", c.type, Volume.type(c.fiche))
        }
    }

    @Test
    fun `le volume est le coefficient par la taille de la pile`() {
        // Une matiere premiere : coefficient 0,5.
        assertEquals(0.5, Volume.volume("m0001dxadf01.sitem", 1), 0.0001)
        assertEquals(50.0, Volume.volume("m0001dxadf01.sitem", 100), 0.0001)
        // Une pile negative reste un encombrement : le bureau prend la valeur
        // absolue, et un volume negatif viderait le coffre a l'affichage.
        assertEquals(50.0, Volume.volume("m0001dxadf01.sitem", -100), 0.0001)
        // Coefficient nul : un teleporteur n'encombre rien, quelle que soit
        // la pile.
        assertEquals(0.0, Volume.volume("tp_kami_almati.sitem", 40), 0.0001)
    }

    @Test
    fun `les matieres de coffre de guilde ne pesent rien`() {
        // Ecart assume avec l'original, repris du bureau : UnitRyzom leur
        // donne 0,1, mais le jeu affiche 0,00 -- et le 0,1 faisait deborder
        // tout coffre qui en stockait beaucoup.
        for (fiche in listOf("mp_hard.sitem", "mp_soft.sitem", "mp_colonne.sitem",
                             "mp_ornement.sitem", "mp_revetement.sitem",
                             "mp_socle.sitem")) {
            assertEquals(fiche, 0.0, Volume.coefficient(fiche), 0.0001)
        }
    }

    @Test
    fun `une fiche inconnue ne pese rien et ne casse rien`() {
        assertEquals(0.0, Volume.coefficient("bidule.sitem"), 0.0001)
        assertEquals(ItemType.OTHER, Volume.type("bidule.sitem"))
        assertEquals(0.0, Volume.coefficient(""), 0.0001)
    }
}
