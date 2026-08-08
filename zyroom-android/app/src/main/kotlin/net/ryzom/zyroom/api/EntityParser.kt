package net.ryzom.zyroom.api

import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.ItemColor
import net.ryzom.zyroom.model.Skill
import net.ryzom.zyroom.model.SkillPoints
import org.w3c.dom.Element
import org.w3c.dom.Node
import net.ryzom.zyroom.MASQUE_COFFRES
import java.io.ByteArrayInputStream
import java.text.Normalizer
import javax.xml.parsers.DocumentBuilderFactory
import kotlin.math.floor
import kotlin.math.roundToInt

/**
 * Lecture des flux `character.php` et `guild.php`, portée de `ryzom_api.py`.
 *
 * On passe par DOM plutôt que par le lecteur en flux d'Android : le document
 * fait quelques dizaines de kilo-octets, et le code reste lisible à côté du
 * Python dont il vient. Il tourne aussi bien sur la machine de développement,
 * ce qui permet de le couvrir par des tests unitaires ordinaires.
 */
object EntityParser {

    /** Capacités connues, reprises de `volume.py`. */
    private const val CAPACITY_BAG = 300
    private const val CAPACITY_ROOM = 2000
    private const val CAPACITY_MEKTOUB = 500
    private const val CAPACITY_MOUNT = 300
    private const val CAPACITY_ZIG = 150

    /**
     * Les items d'une guilde tiennent dans un seul `<room>`, répartis en
     * coffres par tranche de cinq cents emplacements.
     */
    private const val CHEST_SEGMENT = 500

    /**
     * Coffres dont l'application ne montre pas le contenu.
     *
     * Le coffre reste dans la liste, avec son nom et sa capacité, mais il
     * apparaît **vide**. Le faire disparaître amenait les joueurs à demander
     * pourquoi il manquait un coffre ; vide, il ne pose plus de question.
     *
     * C'est un masque d'affichage, rien de plus : le contenu voyage toujours
     * dans le flux de l'API et dort dans le cache. Quiconque a la clé de la
     * guilde peut l'y lire.
     *
     * La comparaison se fait sur le nom normalisé et par inclusion, car ces
     * noms sont saisis à la main par les joueurs : article en tête, espace en
     * fin, casse et accents variables, et l'API les tronque à trente et un
     * caractères. Une égalité stricte laissait passer « Le petit coffre de
     * Nizy » — le masque ne s'appliquait donc à rien.
     */
    private val HIDDEN_CHESTS = listOf("petit coffre de nizy")

    /** Vrai si ce nom de coffre figure dans le masque d'affichage. */
    internal fun isHiddenChest(name: String): Boolean {
        val normalise = Normalizer.normalize(name, Normalizer.Form.NFKD)
            .replace(ACCENTS, "")
            .lowercase()
            .replace(ESPACES, " ")
            .trim()
        return HIDDEN_CHESTS.any { it in normalise }
    }

    private val ACCENTS = Regex("\\p{Mn}+")
    private val ESPACES = Regex("\\s+")

    /**
     * Toutes les entités d'un flux, rangées par la clé qui les a demandées.
     *
     * L'API rend un `<character>` par clé quand on en passe plusieurs ; chacun
     * porte la sienne en attribut, et peut porter son erreur — une clé fausse
     * n'empêche pas les autres d'arriver.
     */
    @Throws(ApiException::class)
    fun parseAll(xml: ByteArray, kind: Entity.Kind): Map<String, Entity> {
        val root = document(xml)
        checkError(root)
        val balise = if (kind == Entity.Kind.CHARACTER) "character" else "guild"
        return root.children(balise)
            .filter { it.child("error") == null }
            .mapNotNull { node ->
                val cle = node.getAttribute("apikey")
                val entite = runCatching {
                    if (kind == Entity.Kind.CHARACTER) character(node) else guild(node)
                }.getOrNull()
                if (cle.isEmpty() || entite == null) null else cle to entite
            }
            .toMap()
    }

    @Throws(ApiException::class)
    fun parseCharacter(xml: ByteArray): Entity {
        val root = document(xml)
        checkError(root)
        val node = root.child("character")
            ?: throw ApiException("flux invalide : nœud <character> absent")
        raise(node.child("error"))
        return character(node)
    }

    private fun character(node: Element): Entity {

        val inventories = buildList {
            node.child("bag")?.let {
                add(Inventory("bag", "Sac", items(it), CAPACITY_BAG,
                              group = "Personnage"))
            }
            node.child("room")?.let {
                add(Inventory("room", "Appartement", items(it), CAPACITY_ROOM,
                              group = "Personnage"))
            }
            // Chaque bête porte son propre inventaire. La fiche de créature dit
            // laquelle : « chj… » un mektoub de bât, « …zig… » un zig, sinon une
            // monture — chacune avec sa capacité, comme dans l'original.
            val compteurs = mutableMapOf<Monture, Int>()
            node.child("pets")?.children("animal")?.forEach { animal ->
                val inventory = animal.child("inventory") ?: return@forEach
                val espece = montureDe(animal.text("sheet"))
                val rang = compteurs.merge(espece, 1, Int::plus)!!
                // Le nom donné en jeu est une chaîne multilingue à rallonge :
                // « Zig 1 », « Zig 2 » se lisent mieux dans un menu.
                val etiquette = "${espece.label} $rang"
                add(Inventory("animal${animal.getAttribute("index")}", etiquette,
                              items(inventory), espece.capacity,
                              group = espece.label))
            }
            node.child("shop")?.let {
                val sales = items(it, tag = "shopitem")
                if (sales.isNotEmpty()) add(Inventory("shop", "Ventes", sales,
                                                     group = "Ventes"))
            }
        }

        return Entity(
            kind = Entity.Kind.CHARACTER,
            id = node.text("id"),
            name = node.text("name"),
            shard = node.text("shard"),
            guild = node.child("guild")?.text("name").orEmpty(),
            dappers = node.text("money").toLongOrNull() ?: 0,
            created = node.getAttribute("created").toLongOrNull() ?: 0,
            cachedUntil = node.getAttribute("cached_until").toLongOrNull() ?: 0,
            inventories = inventories,
            skills = skills(node),
            skillPoints = skillPoints(node),
        )
    }

    /**
     * L'arbre des compétences : une balise par compétence, nommée par son code,
     * dont le texte est le niveau.
     *
     * Le niveau arrive décimal quand la compétence monte — `164.52` : la partie
     * entière est le niveau atteint, la décimale l'avancement dans le suivant.
     * Sur un personnage de longue date, la douzaine de compétences en cours sont
     * les seules à porter une décimale ; les autres sont des entiers.
     *
     * Le bloc peut manquer : c'est un module de l'API, et toutes les clés ne
     * l'accordent pas. L'écran des compétences s'efface alors de lui-même.
     */
    private fun skills(node: Element): List<Skill> =
        node.child("skills")?.elements()?.mapNotNull { skill ->
            val valeur = skill.textContent.trim().toDoubleOrNull() ?: return@mapNotNull null
            val niveau = floor(valeur).toInt()
            Skill(
                code = skill.nodeName,
                level = niveau,
                // Coupé à 99 : un arrondi ne doit pas afficher « 100 % » d'un
                // niveau qui n'est pas franchi.
                progress = ((valeur - niveau) * 100).roundToInt().coerceIn(0, 99),
            )
        }.orEmpty()

    /** Les quatre branches de l'API, sous le code de leur racine dans le pack. */
    private val BRANCHES = mapOf(
        "fight" to "sf", "magic" to "sm", "craft" to "sc", "harvest" to "sh")

    private fun skillPoints(node: Element): Map<String, SkillPoints> =
        node.child("skillpoints")?.elements()?.mapNotNull { branche ->
            val code = BRANCHES[branche.nodeName] ?: return@mapNotNull null
            code to SkillPoints(
                available = branche.textContent.trim().toIntOrNull() ?: 0,
                spent = branche.getAttribute("spent").toIntOrNull() ?: 0,
            )
        }?.toMap().orEmpty()

    @Throws(ApiException::class)
    fun parseGuild(xml: ByteArray, masquer: Boolean = MASQUE_COFFRES): Entity {
        val root = document(xml)
        checkError(root)
        val node = root.child("guild")
            ?: throw ApiException("flux invalide : nœud <guild> absent")
        raise(node.child("error"))
        return guild(node, masquer)
    }

    private fun guild(
        node: Element,
        masquer: Boolean = MASQUE_COFFRES,
    ): Entity {

        // Les coffres se déclarent à part, avec leur nom et leur capacité ; les
        // items, eux, sont tous dans la salle, répartis par tranche de cinq
        // cents emplacements. C'est le rang qui les réunit.
        val declares = node.child("chests")?.children("chest")?.map { chest ->
            cleanName(chest.child("name")?.textContent.orEmpty()) to
                (chest.text("bulkmax").toIntOrNull() ?: 0)
        }.orEmpty()

        val parRang = node.child("room")?.let { items(it) }.orEmpty()
            .groupBy { it.slot / CHEST_SEGMENT }
        val nombre = maxOf(declares.size, (parRang.keys.maxOrNull() ?: -1) + 1)

        val chests = (0 until nombre).mapNotNull { rang ->
            val contenu = parRang[rang].orEmpty()
            val (nom, capacite) = declares.getOrElse(rang) { "" to 0 }
            // Un coffre ni déclaré ni garni n'existe pas.
            if (contenu.isEmpty() && capacite <= 0) return@mapNotNull null
            // Le coffre masqué garde sa place et son nom, mais se présente vide.
            val estMasque = masquer && isHiddenChest(nom)
            val etiquette = if (nom.isEmpty() || nom == node.text("name"))
                "Coffre ${rang + 1}" else "Coffre ${rang + 1} — $nom"
            Inventory("chest${rang + 1}", etiquette,
                      if (estMasque) emptyList() else contenu, capacite,
                      group = "Coffres", masked = estMasque)
        }

        return Entity(
            kind = Entity.Kind.GUILD,
            id = node.text("gid").ifEmpty { node.text("id") },
            name = node.text("name"),
            shard = node.text("shard"),
            motd = node.text("motd"),
            dappers = node.text("money").toLongOrNull() ?: 0,
            created = node.getAttribute("created").toLongOrNull() ?: 0,
            cachedUntil = node.getAttribute("cached_until").toLongOrNull() ?: 0,
            inventories = chests,
        )
    }

    /** Les trois espèces de bête à inventaire, avec ce qu'elles portent. */
    private enum class Monture(val label: String, val capacity: Int) {
        MEKTOUB("Mektoub", CAPACITY_MEKTOUB),
        MOUNT("Monture", CAPACITY_MOUNT),
        ZIG("Zig", CAPACITY_ZIG),
    }

    /**
     * Nettoie le nom d'une bête, tel que le jeu l'écrit.
     *
     * Ryzom range les traductions dans une seule chaîne :
     * `$#[wk]Xiom's Zig[fr]Zig de Xiom` — un segment par langue, précédé de son
     * code entre crochets, le tout encadré de `$`. Les espaces y sont des
     * espaces insécables. On garde le français quand il est là, le premier
     * segment sinon.
     */
    fun cleanName(raw: String): String {
        var texte = raw.trim().removePrefix("$#").removePrefix("$").removeSuffix("$")
        val segments = Regex("\\[([a-z]{2,3})\\]").findAll(texte).toList()
        if (segments.isNotEmpty()) {
            val choisi = segments.firstOrNull { it.groupValues[1] == "fr" } ?: segments.first()
            val debut = choisi.range.last + 1
            val fin = segments.firstOrNull { it.range.first > debut }?.range?.first
                ?: texte.length
            texte = texte.substring(debut, fin)
        }
        return texte.replace('\u00A0', ' ').trim()
    }

    private fun montureDe(sheet: String): Monture {
        val fiche = sheet.lowercase()
        return when {
            fiche.startsWith("chj") -> Monture.MEKTOUB
            "zig" in fiche -> Monture.ZIG
            else -> Monture.MOUNT
        }
    }

    // ---------------------------------------------------------------- détails

    private fun document(xml: ByteArray): Element {
        val factory = DocumentBuilderFactory.newInstance()
        factory.isNamespaceAware = false
        val parsed = try {
            factory.newDocumentBuilder().parse(ByteArrayInputStream(xml))
        } catch (error: Exception) {
            throw ApiException("XML illisible : ${error.message}", error)
        }
        return parsed.documentElement
    }

    /**
     * Erreur générale du flux.
     *
     * On ne regarde que les enfants directs de la racine : dans un appel à
     * plusieurs clés, chaque entité porte sa propre erreur, et une clé refusée
     * ne doit pas emporter les autres.
     */
    private fun checkError(root: Element) = raise(root.child("error"))

    private fun raise(error: Element?) {
        if (error == null) return
        val code = error.getAttribute("code").ifEmpty { "?" }
        throw ApiException("erreur API $code : ${error.textContent.trim()}")
    }

    private fun items(container: Element, tag: String = "item"): List<Item> =
        container.children(tag).map(::parseItem)

    /** Extrait un item d'un nœud `<item>` ou `<shopitem>`. */
    fun parseItem(node: Element): Item {
        val quality = node.text("quality").toIntOrNull() ?: 0
        return Item(
            sheet = node.text("sheet"),
            id = node.getAttribute("id"),
            slot = node.getAttribute("slot").toIntOrNull() ?: 0,
            color = ItemColor.from(
                node.child("craftparameters")?.text("color")),
            // Une qualité de 1 est ramenée à zéro : elle n'apprend rien et
            // encombrerait toutes les icônes.
            quality = if (quality == 1) 0 else quality,
            stack = node.text("stack").toIntOrNull() ?: 0,
            locked = node.text("locked") == "1",
            sap = node.text("sap").isNotEmpty(),
            destroyed = node.text("destroyed") == "1",
            hp = node.text("hp").toIntOrNull() ?: 0,
            price = node.text("price").toDoubleOrNull() ?: 0.0,
            continent = node.text("continent"),
        )
    }

    private fun Element.child(name: String): Element? =
        children(name).firstOrNull()

    /** Tous les enfants élément, quel que soit leur nom. */
    private fun Element.elements(): List<Element> {
        val out = mutableListOf<Element>()
        val nodes = childNodes
        for (index in 0 until nodes.length) {
            val node = nodes.item(index)
            if (node.nodeType == Node.ELEMENT_NODE) out += node as Element
        }
        return out
    }

    private fun Element.children(name: String): List<Element> {
        val out = mutableListOf<Element>()
        val nodes = childNodes
        for (index in 0 until nodes.length) {
            val node = nodes.item(index)
            if (node.nodeType == Node.ELEMENT_NODE && node.nodeName == name) {
                out += node as Element
            }
        }
        return out
    }

    private fun Element.text(name: String): String =
        child(name)?.textContent?.trim().orEmpty()
}
