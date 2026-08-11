package net.ryzom.zyroom.names

import net.ryzom.zyroom.model.NOMS_AVANT_POSTES
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
    /**
     * Le nom lisible d'une fiche, ou sa clé si personne ne sait la nommer.
     *
     * Le pack du client passe en premier : c'est la source du jeu, et elle
     * suit ses mises à jour. À son défaut, les avant-postes ont une table
     * embarquée — la variante F-Droid ne peut pas emporter le pack, et
     * affichait « fyros_outpost_04 » là où il faut lire « Ferme de
     * Malmontagne ».
     */
    fun nameOf(sheet: String): String = names[sheet]
        ?: NOMS_AVANT_POSTES[sheet.removeSuffix(".outpost")]
        ?: sheet

    companion object {

        private const val MAX_KEY = 200
        private const val MAX_VALUE = 100_000

        /**
         * Les codes de l'arbre des compétences : `sf`, `sfm`, `scahbem`…
         *
         * Le flux personnage ne nomme les compétences que par ces codes, et
         * c'est le pack qui porte leur nom français. Ils ne finissent pas en
         * `.sitem` : la règle des items les laissait tomber, et l'écran des
         * compétences n'aurait affiché que des codes.
         *
         * La règle retient un peu plus large que l'arbre — quatre clés comme
         * `sapalchemy` passent aussi. Sans conséquence : on ne cherche jamais
         * qu'un code venu du flux, et une clé du pack n'a qu'une valeur.
         */
        private val SKILL_CODE = Regex("^s[a-z0-9]{1,9}$")

        val EMPTY = NameDb(emptyMap())

        fun read(file: File): NameDb = parse(file.readBytes())

        /**
         * N'extrait que ce que l'application sait nommer : les fiches d'items,
         * les codes de compétences et les avant-postes — le pack en contient
         * vingt-six mille, dialogues et missions compris.
         *
         * Les avant-postes se nomment `fyros_outpost_04.outpost` ; l'API, elle,
         * ne rend que `fyros_outpost_04`, à quoi on rajoute le suffixe pour
         * chercher ici.
         */
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

                // Une clé du pack est un identifiant : ni espace, ni octet de
                // texte accentué, ni caractère de contrôle. Sans cette
                // vérification, une suite d'octets quelconque tombant au bon
                // endroit passait pour un enregistrement, et le vrai qui
                // commençait à l'intérieur était sauté. Six codes de
                // compétences y disparaissaient — dont « Expert en création de
                // manches lourdes » —, et une fiche d'item avec eux.
                if (!isIdentifier(data, index + 4, keyLength)) {
                    index++
                    continue
                }

                val key = String(data, index + 4, keyLength, Charsets.ISO_8859_1)
                val raw = data.copyOfRange(valuePosition + 4,
                                           valuePosition + 4 + width * valueLength)
                val value = String(raw, if (width == 2) Charsets.UTF_16LE else Charsets.UTF_8)
                if (key.endsWith(".sitem") || key.endsWith(".outpost") ||
                    SKILL_CODE.matches(key)) {
                    names[key] = value
                }
                index = valuePosition + 4 + width * valueLength
            }
            return NameDb(names)
        }

        /** Vrai si ces octets sont tous des caractères imprimables sans espace. */
        private fun isIdentifier(data: ByteArray, from: Int, length: Int): Boolean {
            for (index in from until from + length) {
                val octet = data[index].toInt() and 0xFF
                if (octet < 0x21 || octet > 0x7E) return false
            }
            return true
        }
    }
}
