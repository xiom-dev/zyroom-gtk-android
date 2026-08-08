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
 * Le crédit d'auteur et les avis que la licence demande.
 *
 * L'AGPL ne se contente pas d'un remerciement : quand un programme qu'elle
 * couvre a une interface, celle-ci doit porter le copyright, l'absence de
 * garantie, le droit de redistribuer et le moyen de lire la licence. Le dépôt et
 * les README le disent déjà — mais un joueur n'ira jamais les lire, et c'est à
 * lui que l'obligation s'adresse.
 *
 * D'où deux morceaux : une ligne toujours sous les yeux, et le détail à une tape.
 * Pas d'adresse de courriel : la licence n'en demande aucune, et une adresse dans
 * un APK public est ramassée par les robots. Le dépôt joue ce rôle, et c'est de
 * toute façon là qu'est le code source que l'AGPL oblige à offrir.
 */
const val SIGNATURE = "Original by Misugi, fork by Xiom"

const val DEPOT = "https://github.com/xiom-dev/zyroom-gtk-android"
const val DEPOT_ORIGINE = "https://github.com/misugi/zyroom"

/** La ligne discrète, sous la liste : le crédit, et l'accès au reste. */
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
        title = { Text("ZyRoom Android $version") },
        text = {
            // Cinq paragraphes ne tiennent pas sur un petit écran, et le corps
            // d'un AlertDialog ne défile pas de lui-même : sans cela, la fin du
            // texte — le lien du code source, justement — serait coupée.
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.verticalScroll(rememberScrollState()),
            ) {
                Text(
                    "Portage du zyRoom de Misugi, écrit en Delphi pour Windows.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    "© Misugi, pour l'œuvre d'origine.\n" +
                        "Portage sur Android et modifications : Xiom, 2026.",
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
                        "Projet d'origine :\n$DEPOT_ORIGINE",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "ZyRoom n'est pas affilié à Winch Gate, éditeur de Ryzom.",
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
