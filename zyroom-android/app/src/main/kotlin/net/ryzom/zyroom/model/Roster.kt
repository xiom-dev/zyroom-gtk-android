package net.ryzom.zyroom.model

/**
 * Un membre de guilde : son nom et son grade.
 *
 * L'API rend les grades en anglais ; le jeu les affiche en français. C'est tout
 * ce qu'elle dit d'un membre — la date d'entrée qu'elle donne en plus n'est pas
 * un temps Unix, et rien n'en donne la clé.
 */
data class Member(val name: String, val grade: String)

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

/** Ce qui a changé entre deux relevés : arrivées, départs, grades. */
fun diffMembres(
    avant: Map<String, String>,
    apres: Map<String, String>,
    maintenant: Long,
): List<MouvementMembre> =
    (avant.keys + apres.keys).sorted().mapNotNull { nom ->
        val ancien = avant[nom]
        val nouveau = apres[nom]
        when {
            ancien == null -> MouvementMembre(maintenant, nom, "arrivee",
                                              to = nouveau.orEmpty())
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
fun decrireMouvement(m: MouvementMembre): String = when (m.kind) {
    "arrivee" -> "${m.member} a rejoint la guilde (${nomGrade(m.to)})"
    "depart" -> "${m.member} a quitté la guilde (${nomGrade(m.from)})"
    else -> "${m.member} : ${nomGrade(m.from)} → ${nomGrade(m.to)}"
}
