package net.ryzom.zyroom.model

/**
 * Le niveau de chaque avant-poste.
 *
 * **L'API ne le donne pas.** Elle dit qui tient quoi, rien d'autre : ni niveau,
 * ni production, ni horaire d'attaque. Le niveau est pourtant une donnée fixe,
 * qui ne dépend ni du propriétaire ni du moment — le wiki de Ryzom l'énonce
 * ainsi : « la qualité des produits correspond au niveau de récolte maximal
 * dans la région où se situe l'avant-poste ». Un avant-poste ne change donc de
 * niveau que si le jeu change, et une table figée est ici la bonne réponse.
 *
 * Source : fr.wiki.ryzom.com/wiki/Avant-postes, qui les classe par étoiles —
 * une étoile pour cinquante niveaux. Recoupée avec mymap.ryzom.eu.org :
 * vingt-sept valeurs communes, aucun désaccord.
 *
 * Les quatre `primes_outpost_*` n'y figurent pas : le pack les annonce « en
 * test, instable ». Ils n'ont pas de niveau, et la table ne ment pas en leur
 * en inventant un.
 */
val NIVEAUX_AVANT_POSTES: Map<String, Int> = mapOf(
    "fyros_outpost_04" to 200,
    "fyros_outpost_09" to 150,
    "fyros_outpost_13" to 100,
    "fyros_outpost_14" to 50,
    "fyros_outpost_25" to 200,
    "fyros_outpost_27" to 250,
    "fyros_outpost_28" to 250,
    "matis_outpost_03" to 200,
    "matis_outpost_07" to 100,
    "matis_outpost_15" to 50,
    "matis_outpost_17" to 150,
    "matis_outpost_24" to 250,
    "matis_outpost_27" to 250,
    "matis_outpost_30" to 200,
    "tryker_outpost_06" to 50,
    "tryker_outpost_10" to 150,
    "tryker_outpost_16" to 200,
    "tryker_outpost_22" to 200,
    "tryker_outpost_24" to 100,
    "tryker_outpost_29" to 250,
    "tryker_outpost_31" to 250,
    "zorai_outpost_02" to 200,
    "zorai_outpost_08" to 50,
    "zorai_outpost_10" to 100,
    "zorai_outpost_15" to 250,
    "zorai_outpost_16" to 250,
    "zorai_outpost_22" to 150,
    "zorai_outpost_29" to 200,
)

/** Le niveau, ou `null` quand il n'est pas connu. */
fun niveauDe(code: String): Int? = NIVEAUX_AVANT_POSTES[code]
