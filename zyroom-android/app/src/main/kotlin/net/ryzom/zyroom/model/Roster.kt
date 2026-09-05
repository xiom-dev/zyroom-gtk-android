package net.ryzom.zyroom.model

/**
 * Un membre de guilde : son nom, son grade, et le jour de son entrée.
 *
 * L'API rend les grades en anglais ; le jeu les affiche en français. `joined`
 * est le compteur brut du flux — [dateEntree] le ramène à un temps Unix.
 */
data class Member(val name: String, val grade: String, val joined: Long = 0L)

/**
 * L'unité du compteur de dates de l'API : le dixième de seconde.
 *
 * `api.ryzom.com/time.php` — qui n'exige aucune clé — rend la même horloge et
 * avance de dix pas par seconde réelle. C'est le tic du serveur de Ryzom.
 */
const val TICK_SECONDES = 0.1

/**
 * L'origine de ce compteur, en secondes Unix.
 *
 * Le flux rend pour chaque membre un `joined` — 6402485271 pour Xiom — que les
 * deux applications ont longtemps jeté faute d'en connaître la clé. L'unité une
 * fois trouvée, il ne manquait que l'origine, et elle se déduit de nos propres
 * relevés : chaque arrivée constatée encadre le `joined` du nouveau venu entre
 * le relevé qui ne le voyait pas encore et celui qui l'a vu. Sept arrivées de
 * La Lune Eternelle, dont une constatée trente minutes après le relevé
 * précédent, la ramènent à un quart d'heure près.
 *
 * **Le calage vaut pour les dates récentes**, celles du journal. Loin en
 * arrière il dérive — un compteur de tics ne compte sans doute pas les arrêts
 * du serveur — et une entrée de 2012 ne se lit qu'à quelques mois près. C'est
 * sans conséquence ici : le journal ne garde qu'un mois.
 *
 * La même valeur vit dans `roster.py` de ZyRoom-GTK, et pour la même raison.
 */
const val ORIGINE_JOINED = 908_581_304L

/** Avant l'ouverture de Ryzom, aucune date d'entrée n'est croyable. */
private const val OUVERTURE_DU_JEU = 1_095_638_400L      // 20 septembre 2004

/**
 * Le `joined` de l'API en secondes Unix, ou 0 s'il n'est pas croyable.
 *
 * Une date d'avant l'ouverture du jeu, ou dans l'avenir, trahit un champ
 * absent, un compteur remis à zéro ou une horloge locale fausse. On rend alors
 * zéro plutôt qu'une date inventée, et l'appelant retombe sur celle du relevé —
 * la moins bonne des deux, mais jamais absurde.
 */
fun dateEntree(joined: Long, maintenant: Long): Long {
    val quand = ORIGINE_JOINED + (joined * TICK_SECONDES).toLong()
    return if (quand < OUVERTURE_DU_JEU || quand > maintenant + 3600) 0L else quand
}

/**
 * Les grades, du plus haut au plus bas, avec leur nom français.
 *
 * L'ordre sert au classement du registre : on lit une liste de guilde par le
 * haut, et l'API la rend dans un ordre qui n'en est pas un.
 */
val GRADES: List<Pair<String, String>> = listOf(
    "Leader" to "Chef",
    "HighOfficer" to "Officier supérieur",
    "Officer" to "Officier",
    "Member" to "Membre",
)

/** « HighOfficer » → « Officier supérieur ». Un grade inconnu reste lisible. */
fun nomGrade(code: String): String =
    GRADES.firstOrNull { it.first == code }?.second ?: code.ifEmpty { "—" }

/** Pour trier : le chef d'abord, les membres ensuite. */
fun rangGrade(code: String): Int =
    GRADES.indexOfFirst { it.first == code }.takeIf { it >= 0 } ?: GRADES.size

/**
 * Un mouvement de personnel.
 *
 * `kind` vaut `arrivee`, `depart` ou `grade`. Pour un changement de grade,
 * `from` et `to` portent les deux grades ; pour une arrivée, seul `to`, et pour
 * un départ, seul `from`.
 */
data class MouvementMembre(
    /** Secondes Unix, comme les autres journaux. */
    val at: Long,
    val member: String,
    val kind: String,
    val from: String = "",
    val to: String = "",
) {
    /** Vrai si le grade a monté. Un rang plus petit est un grade plus haut. */
    val promotion: Boolean
        get() = kind == "grade" && rangGrade(to) < rangGrade(from)
}

/**
 * Ce qui a changé entre deux relevés : arrivées, départs, grades.
 *
 * `entrees` porte, par nom, la date d'entrée en guilde rendue par l'API.
 * **Seules les arrivées en profitent** : de ceux qui partent ou qui changent de
 * grade, l'API ne dit rien, et leur ligne garde la date du relevé.
 *
 * `depuis` est la date du relevé précédent. Elle borne les arrivées par le bas,
 * comme l'instant présent les borne par le haut : **un nouveau venu est
 * forcément entré entre les deux relevés**, puisque le premier ne le voyait pas
 * encore. Le compteur de l'API dérive — dix pas par seconde mesurés sur cinq
 * minutes, neuf sur trente — et cette fourchette-là, elle, ne dérive pas : la
 * date décodée s'y range, ou s'y fait ranger.
 */
fun diffMembres(
    avant: Map<String, String>,
    apres: Map<String, String>,
    maintenant: Long,
    entrees: Map<String, Long> = emptyMap(),
    depuis: Long = 0L,
): List<MouvementMembre> =
    (avant.keys + apres.keys).sorted().mapNotNull { nom ->
        val ancien = avant[nom]
        val nouveau = apres[nom]
        when {
            ancien == null -> MouvementMembre(
                (entrees[nom]?.takeIf { it > 0 } ?: maintenant)
                    .coerceIn(minOf(depuis, maintenant), maintenant),
                nom, "arrivee", to = nouveau.orEmpty())
            nouveau == null -> MouvementMembre(maintenant, nom, "depart", from = ancien)
            ancien != nouveau -> MouvementMembre(maintenant, nom, "grade",
                                                 from = ancien, to = nouveau)
            else -> null
        }
    }

/**
 * Une ligne de journal, lisible telle quelle.
 *
 * Sans le signe : l'écran le pose à part, en couleur, et le répéter dans le
 * texte ferait double emploi.
 */
/**
 * Écart maximal entre deux constats du même mouvement, en secondes.
 *
 * Un mouvement d'effectif n'existe pas dans l'API : il se déduit de deux
 * relevés successifs, et porte donc la date du **constat**, pas celle du fait.
 * Un joueur parti mardi à 14 h est vu partir à 15 h par le relevé horaire, et
 * le samedi suivant par un téléphone resté dans une poche. Même départ, deux
 * dates, et une comparaison stricte en fait deux départs.
 *
 * Une semaine, comme dans les deux applications de bureau : les trois doivent
 * rapprocher les mêmes lignes, sans quoi elles afficheraient encore des
 * listes différentes à partir des mêmes données.
 */
const val TOLERANCE_FUSION = 7L * 86400

/**
 * Deux constats décrivent-ils le même mouvement ?
 *
 * Tout doit concorder sauf la date : le membre, la nature du mouvement, et les
 * deux grades. Un « Membre → Officier » et un « Officier → Membre » du même
 * joueur le même jour sont deux faits, pas un.
 */
private fun memeEvenement(a: MouvementMembre, b: MouvementMembre): Boolean =
    a.member == b.member && a.kind == b.kind && a.from == b.from && a.to == b.to

/**
 * Le registre d'ici, enrichi de ce qu'un autre relevé a vu.
 *
 * Renvoie le registre fusionné et le nombre de mouvements réellement ajoutés.
 *
 * **L'horodatage ne décide pas de l'identité** : il dit quand on a regardé,
 * pas quand la chose est arrivée, et deux observateurs ne regardent pas
 * ensemble. Deux constats concordants séparés de moins de `TOLERANCE_FUSION`
 * sont tenus pour un seul mouvement, et c'est **la date la plus ancienne** qui
 * est gardée : l'événement précède toujours son constat.
 *
 * Un garde-fou empêche de confondre deux faits distincts : si le même membre a
 * bougé autrement entre les deux constats — parti, puis revenu, puis reparti —,
 * le mouvement intercalé les sépare, quelle que soit la tolérance.
 */
fun fusionnerRegistre(
    locaux: List<MouvementMembre>,
    etrangers: List<MouvementMembre>,
): Pair<List<MouvementMembre>, Int> {
    // L'origine voyage a cote du mouvement : deux constats peuvent etre egaux
    // sans etre le meme objet, et le meme objet peut se trouver des deux cotes.
    val tous = (locaux.map { 0 to it } + etrangers.map { 1 to it })
        .sortedWith(compareBy({ it.second.at }, { it.second.member }))

    val gardes = mutableListOf<MouvementMembre>()
    val parMembre = mutableMapOf<String, MutableList<MouvementMembre>>()
    var ajoutes = 0

    for ((origine, mv) in tous) {
        val histoire = parMembre.getOrPut(mv.member) { mutableListOf() }
        val dernier = histoire.lastOrNull()
        // Seul le dernier mouvement du membre est regarde : tout ce qui vient
        // avant en est separe par lui, et un mouvement intercale suffit a dire
        // que les deux constats racontent autre chose.
        val double = dernier != null &&
            mv.at - dernier.at <= TOLERANCE_FUSION &&
            memeEvenement(dernier, mv)
        if (double) continue
        histoire.add(mv)
        gardes.add(mv)
        if (origine == 1) ajoutes++
    }

    return gardes.sortedWith(compareBy({ it.at }, { it.member })) to ajoutes
}

fun decrireMouvement(m: MouvementMembre): String = when (m.kind) {
    "arrivee" -> "${m.member} a rejoint la guilde (${nomGrade(m.to)})"
    "depart" -> "${m.member} a quitté la guilde (${nomGrade(m.from)})"
    else -> "${m.member} : ${nomGrade(m.from)} → ${nomGrade(m.to)}"
}
