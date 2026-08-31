package net.ryzom.zyroom.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp

/**
 * Le nom de l'application, et les avis que la licence demande.
 *
 * L'AGPL ne se contente pas d'un remerciement : quand un programme qu'elle
 * couvre a une interface, celle-ci doit porter le copyright, l'absence de
 * garantie, le droit de redistribuer et le moyen de lire la licence. Le dépôt et
 * les README le disent déjà — mais un joueur n'ira jamais les lire, et c'est à
 * lui que l'obligation s'adresse.
 *
 * Xiom est l'auteur de V-RyLune, et la ligne du bas le dit. La filiation reste
 * écrite ici, en dessous : cette application a été écrite en traduisant le
 * zyRoom Delphi de Misugi — coefficients de volume, capacités des contenants,
 * ordre des énumérations qui part dans les URL d'icônes, logique de lecture des
 * flux. C'est une œuvre dérivée, et l'AGPL interdit d'en effacer la paternité
 * d'origine. Se dire seul auteur serait faux, et illégal.
 *
 * L'adresse de courriel est celle que Xiom a choisi de publier. Elle a un coût
 * connu — une adresse dans un APK public finit ramassée par les robots — et un
 * bénéfice : on peut écrire sans compte GitHub, ce que tout le monde n'a pas.
 * Le dépôt reste le meilleur endroit pour signaler un défaut, puisqu'il en
 * garde la trace et que d'autres la lisent.
 */
const val SIGNATURE = "V-RyLune, une application de Xiom"

const val DEPOT = "https://github.com/xiom-dev/zyroom-gtk-android"
const val COURRIEL = "ludopika@ikmail.com"
const val DEPOT_ORIGINE = "https://github.com/misugi/zyroom"

/** La ligne discrète, sous la liste : le nom, et l'accès au reste. */
@Composable
fun LigneSignature(onClick: () -> Unit) {
    Text(
        SIGNATURE,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        textAlign = TextAlign.Center,
        textDecoration = TextDecoration.Underline,
        modifier = Modifier.fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 10.dp, horizontal = 12.dp),
    )
}

@Composable
fun AboutDialog(onDismiss: () -> Unit) {
    val contexte = LocalContext.current
    // Le numéro n'est pas écrit ici : il vient du paquet installé, donc il ne
    // peut pas mentir sur ce qui tourne.
    val version = remember {
        runCatching {
            val info = contexte.packageManager.getPackageInfo(contexte.packageName, 0)
            @Suppress("DEPRECATION")
            "${info.versionName} (${info.versionCode})"
        }.getOrDefault("")
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("V-RyLune $version") },
        text = {
            // Cinq paragraphes ne tiennent pas sur un petit écran, et le corps
            // d'un AlertDialog ne défile pas de lui-même : sans cela, la fin du
            // texte — le lien du code source, justement — serait coupée.
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.verticalScroll(rememberScrollState()),
            ) {
                Text(
                    "Vos inventaires Ryzom et les coffres de la guilde, hors du jeu.\n" +
                        "Une application de Xiom, pour La Lune Eternelle.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "© 2026 Xiom, pour V-RyLune.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "Dérivée du zyRoom de Misugi, écrit en Delphi pour Windows, " +
                        "© Misugi : V-RyLune en reprend les algorithmes et la lecture " +
                        "de l'API de Ryzom, et hérite donc de sa licence.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "Sous licence GNU AGPL v3. Vous pouvez utiliser, étudier, " +
                        "modifier et redistribuer cette application ; ceux à qui " +
                        "vous la donnez ont droit au code source, sous la même " +
                        "licence. Fournie sans aucune garantie, dans la mesure " +
                        "permise par la loi.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "Code source, licence complète et signalement de défauts :\n$DEPOT\n\n" +
                        "Écrire à l'auteur :\n$COURRIEL\n\n" +
                        "Projet dont elle dérive :\n$DEPOT_ORIGINE",
                    style = MaterialTheme.typography.bodySmall,
                )
                // La SIL Open Font License veut que son texte et sa mention de
                // droits voyagent avec la police : le fichier est dans l'APK
                // (assets/OFL-PirataOne.txt) et dans le dépôt.
                Text(
                    "Lettrage : Pirata One, © Rodrigo Fuenzalida et Nicolas Massi ; " +
                        "capitale Cinzel Decorative, © Natanael Gama. Toutes deux " +
                        "sous SIL Open Font License 1.1.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                // Les symboles des familles de matières sont des images du jeu,
                // reprises de Ryzom Armory et embarquées dans l'APK : elles ne
                // sont ni de nous, ni libres de mention.
                Text(
                    "Relevé des matières suprêmes et excellentes : Ryzom Armory." +
                        if (SYMBOLES_EMBARQUES)
                            " Les symboles des familles sont des images du jeu, " +
                                "© Winch Gate."
                        else "",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                // Les noms d'avant-postes viennent d'un dépôt tiers sous LGPL :
                // la licence oblige à le dire et à nommer son auteur.
                Text(
                    "Noms des avant-postes : RyzomExtra, © Meelis Mägi, sous " +
                        "GNU LGPL v3 — employés quand le pack du jeu n'est pas " +
                        "disponible.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                // Même auteur, même licence, même obligation : la carte d'Atys
                // vient de son dépôt de tuiles.
                if (CARTE_EMBARQUEE) {
                    Text(
                        "Carte d'Atys : Ryzom Map Tiles, © Meelis Mägi, sous " +
                            "GNU LGPL v3.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                // Les positions de gisements ne sont pas des images du jeu
                // mais des faits, et leur auteur a donne son accord ecrit :
                // les deux variantes les portent.
                Text(
                    "Positions des gisements : relevé de ballisticmystix.net, " +
                        "avec l'accord de son auteur.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    "V-RyLune n'est pas affiliée à Winch Gate, éditeur de Ryzom.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { ouvrir(contexte, DEPOT) }) { Text("Voir le code") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Fermer") } },
    )
}

/** Ouvre une adresse dans le navigateur ; sans navigateur, ne fait rien. */
private fun ouvrir(contexte: Context, adresse: String) {
    runCatching {
        contexte.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(adresse))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
