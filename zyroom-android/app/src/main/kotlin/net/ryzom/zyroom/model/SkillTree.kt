package net.ryzom.zyroom.model

/**
 * L'arbre des compétences, déduit des codes.
 *
 * Rien ne décrit la hiérarchie dans le flux de l'API : c'est le code qui la
 * porte, une compétence préfixant toutes celles qui en descendent — `sf`
 * « Combat », `sfm` « Mêlée », `sfms` « Manier épée ». L'ordre alphabétique des
 * codes est donc déjà celui de l'arbre, parents avant enfants.
 *
 * Ce calcul vit hors de l'écran pour être couvert par des tests : le repli, lui,
 * ne se vérifie qu'à l'œil.
 */
data class SkillNode(
    val skill: Skill,
    /** Racine de la branche : `sf`, `sm`, `sh`, `sc`. */
    val root: String,
    /** Parent immédiat, ou `null` pour une racine. */
    val parent: String?,
    val depth: Int,
    val hasChildren: Boolean,
)

/** Range les compétences dans l'ordre de l'arbre, chacune avec sa place. */
fun skillTree(skills: List<Skill>): List<SkillNode> =
    skills.sortedBy { it.code }.map { skill ->
        val ancetres = skills.filter {
            it.code != skill.code && skill.code.startsWith(it.code)
        }
        SkillNode(
            skill = skill,
            root = ancetres.minByOrNull { it.code.length }?.code ?: skill.code,
            // Le parent est le plus proche des ancêtres, non le premier : l'API
            // saute parfois un échelon, et remonter à la racine décalerait tout
            // l'affichage.
            parent = ancetres.maxByOrNull { it.code.length }?.code,
            depth = ancetres.size,
            hasChildren = skills.any {
                it.code != skill.code && it.code.startsWith(skill.code)
            },
        )
    }

/**
 * Ce qui se voit, `expanded` disant quelles compétences sont ouvertes.
 *
 * Une compétence n'apparaît que si son parent est ouvert **et lui-même
 * visible** : replier une racine referme donc tout ce qu'elle contient, sans
 * qu'on ait à oublier l'état des échelons du dessous — le rouvrir les retrouve
 * comme on les avait laissés. Les codes étant triés, un parent est toujours
 * décidé avant ses enfants : une seule passe suffit.
 */
fun visibleSkills(tree: List<SkillNode>, expanded: Set<String>): List<SkillNode> {
    val montrees = mutableSetOf<String>()
    return tree.filter { noeud ->
        val visible = noeud.parent == null ||
            (noeud.parent in montrees && noeud.parent in expanded)
        if (visible) montrees += noeud.skill.code
        visible
    }
}
