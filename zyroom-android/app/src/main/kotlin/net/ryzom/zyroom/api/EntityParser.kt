package net.ryzom.zyroom.api

import net.ryzom.zyroom.model.Bete
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.ItemColor
import net.ryzom.zyroom.model.Member
import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.Outpost
import net.ryzom.zyroom.model.Skill
import net.ryzom.zyroom.model.SkillPoints
import org.json.JSONObject
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

    /**
     * L'annuaire des guildes, réduit à qui tient quoi.
     *
     * Le document liste toutes les guildes du serveur ; la plupart n'ont aucun
     * avant-poste et ne laissent donc rien ici. Une guilde sans nom serait
     * inexploitable à l'écran comme au journal : on la passe.
     */
    @Throws(ApiException::class)
    fun parseOutposts(xml: ByteArray): List<Outpost> {
        val root = document(xml)
        checkError(root)
        return root.children("guild").flatMap { guilde ->
            val nom = guilde.text("name")
            val emblème = guilde.text("icon")
            if (nom.isEmpty()) emptyList()
            else guilde.child("outposts")?.children("outpost").orEmpty()
                .mapNotNull { it.textContent?.trim() }
                .filter { it.isNotEmpty() }
                .map { Outpost(code = it, guild = nom, icon = emblème) }
        }
    }

    /**
     * La météo rendue par `weather.php`, par continent puis par cycle.
     *
     * Le document est en JSON là où tout le reste de l'API est en XML : on le
     * lit donc à part, avec org.json.
     */
    @Throws(ApiException::class)
    fun parseWeather(json: String): Triple<Int, Double, Map<String, List<Meteo>>> {
        val racine = runCatching { JSONObject(json) }
            .getOrElse { throw ApiException("météo illisible : ${it.message}", it) }
        if (racine.has("errors")) throw ApiException("météo : " + racine.optString("errors"))
        val cycleCourant = racine.optInt("cycle")
        // `hour` est l'heure d'Atys en cours, avec ses décimales : 104011.496
        // au cycle 34670 veut dire qu'on est à la moitié du cycle, celui-ci en
        // couvrant trois heures. Sans elle, un compte à rebours se trompait de
        // neuf minutes au pire, et le trait du « maintenant » sautait de cycle
        // en cycle au lieu d'avancer.
        val heure = racine.optString("hour").toDoubleOrNull() ?: (cycleCourant * 3.0)
        val continents = racine.optJSONObject("continents") ?: JSONObject()
        val out = mutableMapOf<String, List<Meteo>>()
        continents.keys().forEach { nom ->
            val cycles = continents.optJSONObject(nom) ?: return@forEach
            out[nom] = cycles.keys().asSequence().mapNotNull { cle ->
                cycles.optJSONObject(cle)?.let {
                    Meteo(
                        cycle = it.optInt("cycle"),
                        condition = it.optString("condition"),
                        value = it.optString("value").toDoubleOrNull() ?: 0.0,
                        text = it.optString("text"),
                    )
                }
            }.sortedBy { it.cycle }.toList()
        }
        return Triple(cycleCourant, heure, out)
    }

    /** La saison d'Atys, de 0 (printemps) à 3 (hiver), lue sur `time.php`. */
    @Throws(ApiException::class)
    fun parseSeason(xml: ByteArray): Int {
        val root = document(xml)
        checkError(root)
        return root.text("season").toIntOrNull()
            ?: root.child("shard_time")?.text("season")?.toIntOrNull()
            ?: throw ApiException("saison absente du flux de temps")
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

        // Les bêtes se relèvent en même temps que leurs contenants : c'est le
        // même parcours, et leur étiquette — « Zig 2 » — vient du même compte.
        val betes = mutableListOf<Bete>()
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
                // Toutes les bêtes sous un seul bouton. Séparées, montures,
                // mektoubs et zigs prenaient trois places dans une rangée qui
                // en a peu, alors qu'on cherche « dans quelle bête ai-je mis
                // ça ? » sans savoir laquelle avant d'avoir regardé.
                add(Inventory("animal${animal.getAttribute("index")}", etiquette,
                              items(inventory), espece.capacity,
                              group = "Animaux"))
                betes += beteDe(animal, etiquette)
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
            betes = betes,
            x = node.child("position")?.getAttribute("x")?.toDoubleOrNull()?.toInt() ?: 0,
            y = node.child("position")?.getAttribute("y")?.toDoubleOrNull()?.toInt() ?: 0,
            portraitUrl = portraitDe(node),
            skills = skills(node),
            skillPoints = skillPoints(node),
        )
    }

    /**
     * Le buste du personnage, chez Ballistic Mystix.
     *
     * L'API de Ryzom ne dessine pas les personnages ; elle décrit leur corps —
     * gabarit, morphologie, cheveux, yeux — et leur équipement, et ce service
     * en fait une image. `zoom=face` cadre la tête et les épaules ; sans lui on
     * obtient le corps entier, deux fois plus haut que large.
     *
     * Tout l'équipement visible est transmis, et pas seulement le plastron : le
     * personnage apparaissait sinon en sous-vêtements, casque et armure
     * absents. Les bijoux, eux, ne se rendent pas.
     *
     * En HTTPS : Android refuse le trafic en clair depuis Android 9, et le
     * service répond aux deux. Sans bloc `<body>`, il n'y a rien à dessiner.
     */
    private fun portraitDe(node: Element): String {
        val body = node.child("body") ?: return ""
        val gabarit = body.child("gabarit")
        val morph = body.child("morph")
        val equipement = node.child("equipment")
        val taille = listOf("height", "torso", "arms", "legs", "breast")
            .joinToString(",") { gabarit?.getAttribute(it).orEmpty().ifEmpty { "0" } }
        val visage = (1..8)
            .joinToString(",") { morph?.getAttribute("target$it").orEmpty().ifEmpty { "0" } }
        // Les noms de créneaux du service sont ceux du flux, à l'exception du
        // casque : « head » ici, « headdress » là-bas.
        val pieces = listOf(
            "head" to "headdress", "chest" to "chest", "arms" to "arms",
            "hands" to "hands", "legs" to "legs", "feet" to "feet",
            "handl" to "handl", "handr" to "handr",
        ).mapNotNull { (parametre, balise) ->
            val piece = equipement?.child(balise) ?: return@mapNotNull null
            val fiche = piece.textContent?.trim().orEmpty()
            if (fiche.isEmpty()) null
            else "$parametre=$fiche/" + piece.getAttribute("color").ifEmpty { "0" }
        }
        return "https://api.bmsite.net/char/render/3d/180" +
            "?zoom=face" +
            "&race=" + node.text("race").take(2) +
            "&gender=" + node.text("gender") +
            "&hair=" + body.text("hairtype") + "/" + body.text("haircolor") +
            "&tattoo=" + body.text("tattoo") +
            "&eyes=" + body.text("eyescolor") +
            "&gabarit=" + taille +
            "&morph=" + visage +
            pieces.joinToString("") { "&$it" }
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
            portraitUrl = node.text("icon").takeIf { it.isNotEmpty() }
                ?.let { RyzomApi.guildIconUrl(it, "b") }.orEmpty(),
            dappers = node.text("money").toLongOrNull() ?: 0,
            created = node.getAttribute("created").toLongOrNull() ?: 0,
            cachedUntil = node.getAttribute("cached_until").toLongOrNull() ?: 0,
            inventories = chests,
            members = membres(node),
        )
    }

    /**
     * Le registre des membres : leur nom et leur grade.
     *
     * La date d'entrée que rend l'API — un grand entier, 6115304166 — n'est pas
     * un temps Unix, et rien dans le flux n'en donne la clé. On ne la lit donc
     * pas : afficher une date fausse serait pire que de n'en afficher aucune.
     */
    private fun membres(node: Element): List<Member> =
        node.child("members")?.children("member").orEmpty().mapNotNull {
            val nom = it.text("name")
            if (nom.isEmpty()) null else Member(nom, it.text("grade"))
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
     *
     * Le jeu écrit en outre ces espaces en UTF-8 relu comme du latin-1 :
     * « Zig<Â> de » au lieu de « Zig de ». On répare la paire quand le tour se
     * boucle, et on laisse tel quel sinon — un nom qui contient légitimement un
     * « Â » ne doit pas être abîmé.
     */
    fun cleanName(raw: String): String {
        var texte = repareEncodage(raw.trim())
            .removePrefix("$#").removePrefix("$").removeSuffix("$")
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

    /**
     * Une bête et sa position, telles que le flux les donne.
     *
     * La position est absente pour une bête qui n'est nulle part — jamais
     * sortie de l'écurie : on rend alors (0, 0), que `CarteAtys.contient`
     * écarte de lui-même.
     */
    private fun beteDe(animal: Element, etiquette: String): Bete {
        val position = animal.child("position")
        return Bete(
            nom = cleanName(animal.text("name")),
            etiquette = etiquette,
            statut = animal.text("status"),
            x = position?.getAttribute("x")?.toDoubleOrNull()?.toInt() ?: 0,
            y = position?.getAttribute("y")?.toDoubleOrNull()?.toInt() ?: 0,
            satiete = animal.text("satiety").toDoubleOrNull() ?: 0.0,
        )
    }

    /**
     * Défait le double encodage du jeu, s'il en est bien un.
     *
     * Les octets d'un texte UTF-8 relu comme du latin-1 se relisent en UTF-8 :
     * le tour se boucle. Quand il ne se boucle pas, le remplacement laisse un
     * caractère de substitution, et on garde alors le texte d'origine.
     */
    private fun repareEncodage(texte: String): String {
        val repare = String(texte.toByteArray(Charsets.ISO_8859_1), Charsets.UTF_8)
        return if (repare.contains('\uFFFD')) texte else repare
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
