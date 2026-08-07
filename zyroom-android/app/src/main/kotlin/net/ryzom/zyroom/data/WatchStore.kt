package net.ryzom.zyroom.data

import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.ItemType
import org.json.JSONObject
import java.io.File

/**
 * Les objets qu'on surveille, et le seuil qui déclenche l'alerte.
 *
 * Porté de `zyroom/watch.py`, lui-même équivalent du `guard.dat` d'origine.
 * Une entrée est identifiée par la signature de l'item — sa fiche et sa
 * qualité — parce que c'est ce qui distingue deux piles d'une même matière.
 *
 * Deux surveillances : la **quantité** d'une matière qui descend sous un seuil,
 * et la **durabilité** d'un équipement.
 */
class WatchStore(private val file: File) {

    enum class Kind { QUANTITY, DURABILITY }

    data class Watch(
        val sheet: String,
        val quality: Int,
        val threshold: Int,
        val kind: Kind,
    ) {
        val signature: String get() = signatureOf(sheet, quality)
    }

    private val watches = linkedMapOf<String, Watch>()

    init {
        load()
    }

    fun all(): List<Watch> = watches.values.toList()

    fun isWatched(item: Item): Boolean = signatureOf(item) in watches

    fun watchOf(item: Item): Watch? = watches[signatureOf(item)]

    fun add(item: Item, threshold: Int) {
        val watch = Watch(item.sheet, item.quality, threshold, kindOf(item))
        watches[watch.signature] = watch
        save()
    }

    fun remove(item: Item) {
        if (watches.remove(signatureOf(item)) != null) save()
    }

    /**
     * Confronte les surveillances à l'état d'une entité.
     *
     * Une matière dont il ne reste rien est signalée comme disparue : c'est
     * souvent l'alerte la plus utile — le stock est tombé à zéro.
     */
    fun alerts(entity: Entity, nameOf: (String) -> String): List<Alert> {
        val presents = mutableMapOf<String, MutableList<Item>>()
        entity.inventories.forEach { inventaire ->
            inventaire.items.forEach { item ->
                presents.getOrPut(signatureOf(item)) { mutableListOf() } += item
            }
        }

        return watches.values.mapNotNull { watch ->
            val nom = nameOf(watch.sheet)
            val qualite = if (watch.quality > 0) " (Q${watch.quality})" else ""
            val trouves = presents[watch.signature]
            when {
                trouves.isNullOrEmpty() -> Alert(
                    Alert.Kind.MISSING, "$nom$qualite : disparu",
                    "Plus rien dans les inventaires")

                watch.kind == Kind.QUANTITY -> {
                    val total = trouves.sumOf { maxOf(it.stack, 1) }
                    if (total < watch.threshold) Alert(
                        Alert.Kind.QUANTITY, "$nom$qualite : stock bas",
                        "$total en réserve, seuil ${watch.threshold}")
                    else null
                }

                else -> {
                    val usure = trouves.minOf { it.hp }
                    if (usure in 1 until watch.threshold) Alert(
                        Alert.Kind.DURABILITY, "$nom$qualite : usé",
                        "Durabilité $usure, seuil ${watch.threshold}")
                    else null
                }
            }
        }
    }

    private fun load() {
        watches.clear()
        if (!file.isFile) return
        runCatching {
            val racine = JSONObject(file.readText())
            racine.keys().forEach { cle ->
                val entree = racine.getJSONObject(cle)
                watches[cle] = Watch(
                    sheet = entree.getString("sheet"),
                    quality = entree.optInt("quality"),
                    threshold = entree.optInt("threshold"),
                    kind = Kind.valueOf(entree.optString("kind", Kind.QUANTITY.name)),
                )
            }
        }
    }

    private fun save() {
        val racine = JSONObject()
        watches.forEach { (cle, watch) ->
            racine.put(cle, JSONObject().apply {
                put("sheet", watch.sheet)
                put("quality", watch.quality)
                put("threshold", watch.threshold)
                put("kind", watch.kind.name)
            })
        }
        file.parentFile?.mkdirs()
        file.writeText(racine.toString())
    }

    companion object {
        /** L'équipement s'use, une matière s'épuise : le type dit quoi surveiller. */
        fun kindOf(item: Item): Kind =
            if (item.type == ItemType.EQUIPMENT) Kind.DURABILITY else Kind.QUANTITY

        fun signatureOf(item: Item): String = signatureOf(item.sheet, item.quality)

        fun signatureOf(sheet: String, quality: Int): String = "$sheet|$quality"
    }
}

/** Ce qu'on montre à la cloche. */
data class Alert(val kind: Kind, val title: String, val detail: String) {
    enum class Kind { QUANTITY, DURABILITY, MISSING, VOLUME }
}

/** Contenants dont le remplissage atteint le seuil, en pourcentage. */
fun volumeAlerts(entity: Entity, threshold: Int = 90): List<Alert> =
    entity.inventories.mapNotNull { inventaire ->
        if (inventaire.capacity <= 0) return@mapNotNull null
        val part = inventaire.totalVolume / inventaire.capacity * 100.0
        if (part >= threshold) Alert(
            Alert.Kind.VOLUME, "${inventaire.label} : ${part.toInt()} % plein",
            "${inventaire.totalVolume.toInt()} sur ${inventaire.capacity}")
        else null
    }
