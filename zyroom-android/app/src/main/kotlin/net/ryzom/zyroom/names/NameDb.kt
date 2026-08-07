package net.ryzom.zyroom.names

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Noms d'items lisibles, tirés du `string_client.pack` de Ryzom.
 *
 * Deux formats se rencontrent, tous deux en-têtés « STR_PACK ». Un
 * enregistrement vaut keylen(4 o, petit-boutiste) + clé(latin-1) + un octet
 * séparateur + vallen(4 o) + valeur, et c'est le séparateur qui dit comment
 * lire la valeur :
 *
 *     0x01  valeur en UTF-16LE, `vallen` comptant des unités
 *     0x02  valeur en UTF-8, `vallen` comptant des octets
 *
 * Le 0x02 est ce qu'écrivent les clients récents. Un pack récent lu comme
 * l'ancien ne rend rien du tout — c'est la panne qui faisait retomber tous les
 * items sur leur identifiant de fiche dans la version GTK.
 *
 * Sur un téléphone il n'y a pas d'installation de Ryzom : le fichier est
 * importé une fois par l'utilisateur, puis conservé tel quel.
 */
class NameDb private constructor(private val names: Map<String, String>) {

    val size: Int get() = names.size

    val isLoaded: Boolean get() = names.isNotEmpty()

    /** Nom lisible d'une fiche, ou son identifiant quand il est inconnu. */
    fun nameOf(sheet: String): String = names[sheet] ?: sheet

    companion object {

        private const val MAX_KEY = 200
        private const val MAX_VALUE = 100_000

        val EMPTY = NameDb(emptyMap())

        fun read(file: File): NameDb = parse(file.readBytes())

        /** N'extrait que les fiches d'items — le pack en contient bien d'autres. */
        fun parse(data: ByteArray): NameDb {
            val buffer = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
            val names = HashMap<String, String>()
            var index = 0

            while (index < data.size - 8) {
                // Bourrage éventuel entre enregistrements.
                while (index < data.size && data[index] == 0.toByte()) index++
                if (index >= data.size - 8) break

                val keyLength = buffer.getInt(index)
                if (keyLength !in 1..MAX_KEY || index + 4 + keyLength + 1 > data.size) {
                    index++
                    continue
                }

                val separator = data[index + 4 + keyLength]
                if (separator != 1.toByte() && separator != 2.toByte()) {
                    index++
                    continue
                }
                // Largeur d'un caractère : deux octets en UTF-16, un en UTF-8.
                val width = if (separator == 1.toByte()) 2 else 1

                val valuePosition = index + 4 + keyLength + 1
                if (valuePosition + 4 > data.size) break
                val valueLength = buffer.getInt(valuePosition)
                if (valueLength > MAX_VALUE ||
                    valuePosition + 4 + width * valueLength > data.size) {
                    index++
                    continue
                }

                val key = String(data, index + 4, keyLength, Charsets.ISO_8859_1)
                val raw = data.copyOfRange(valuePosition + 4,
                                           valuePosition + 4 + width * valueLength)
                val value = String(raw, if (width == 2) Charsets.UTF_16LE else Charsets.UTF_8)
                if (key.endsWith(".sitem")) names[key] = value
                index = valuePosition + 4 + width * valueLength
            }
            return NameDb(names)
        }
    }
}
