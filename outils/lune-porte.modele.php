<?php
// La porte de xiom.be/Lune-eternelle/.
//
// Modele versionne SANS secret : outils/site-domaine.py y met l'empreinte
// bcrypt du mot de passe et le sel des jetons, gardes dans ~/.config/zyroom/
// (lune.motdepasse, lune.sel), et l'ecrit en Lune-eternelle/index.php.
//
// La page elle-meme s'appelle page.html et le .htaccess du dossier en refuse
// la lecture directe : elle ne sort que par ici, et seulement a qui a le
// jeton. readfile() lit le fichier sur le disque, sans repasser par Apache,
// donc sans buter sur ce refus.
//
// Meme garde que xiom.be/OP : pas de session PHP, un jeton qui porte sa date
// d'expiration et une signature HMAC, dans un cookie.

const EMPREINTE = '__EMPREINTE__';
const SEL = '__SEL__';
const COOKIE = 'lune';
const DUREE = 30 * 24 * 3600;
const PAGE = __DIR__ . '/page.html';

function jeton(int $expire): string
{
    return $expire . '.' . hash_hmac('sha256', 'lune' . $expire, SEL);
}

function jeton_valide(string $recu): bool
{
    $morceaux = explode('.', $recu, 2);
    if (count($morceaux) !== 2 || !ctype_digit($morceaux[0])) {
        return false;
    }
    $expire = (int) $morceaux[0];
    if ($expire < time()) {
        return false;
    }
    return hash_equals(jeton($expire), $recu);
}

// Rien de ce qui passe par ici ne doit rester dans un cache partage : ni la
// page, reservee, ni la porte, qui deviendrait la reponse de tout le monde.
header('Cache-Control: private, no-cache, must-revalidate');

$refuse = false;
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    // Une seconde de retard : les essais en serie deviennent interminables,
    // et quelqu'un qui se trompe ne le remarque pas.
    usleep(1000000);
    if (password_verify((string) ($_POST['mdp'] ?? ''), EMPREINTE)) {
        $expire = time() + DUREE;
        setcookie(COOKIE, jeton($expire), [
            'expires' => $expire,
            'path' => dirname((string) ($_SERVER['SCRIPT_NAME'] ?? '/')),
            'secure' => true,
            'httponly' => true,
            'samesite' => 'Lax',
        ]);
        // Redirection apres le POST : recharger la page ne redemande pas de
        // renvoyer le formulaire.
        header('Location: ' . strtok((string) ($_SERVER['REQUEST_URI'] ?? './'), '?'), true, 303);
        exit;
    }
    $refuse = true;
}

if (jeton_valide((string) ($_COOKIE[COOKIE] ?? ''))) {
    header('Content-Type: text/html; charset=utf-8');
    readfile(PAGE);
    exit;
}

// 200 et non plus 401 tant qu'aucun mot de passe faux n'a ete donne :
// Discord n'affiche pas l'apercu d'une page qui repond par une erreur. Rien
// ne change pour la securite, la reponse reste ce formulaire.
http_response_code($refuse ? 403 : 200);
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Les applications de La Lune Éternelle</title>
<!-- Apercu des liens (Discord...) : la meme image que la page sur GitHub -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="La Lune Éternelle">
<meta property="og:title" content="Les applications de La Lune Éternelle">
<meta property="og:description" content="Vos inventaires Ryzom et les coffres de la guilde, hors ligne. ZyRoom pour Linux et Windows, V-RyLune pour Android, KipeeCraft pour les recettes de craft.">
<meta property="og:url" content="https://xiom.be/Lune-eternelle/">
<meta property="og:image" content="https://xiom.be/Lune-eternelle/apercu.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Les quatre applications côte à côte : ZyRoom-GTK, ZyRoom-Qt, KipeeCraft-GTK et V-RyLune.">
<meta property="og:locale" content="fr_FR">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="favicon.png" sizes="512x512" type="image/png">
<style>
  /* Les couleurs de la page qu'elle garde. */
  :root {
    --fond: #10171a;
    --surface: #172226;
    --texte: #e2e8e6;
    --texte-faible: #9aa8a5;
    --sarcelle: #3f7a68;
    --or: #e8c15a;
    --trait: rgba(226, 232, 230, .16);
    --refus: #e07a6a;
  }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    box-sizing: border-box;
    background: var(--fond);
    color: var(--texte);
    font-family: system-ui, sans-serif;
  }
  form {
    background: var(--surface);
    border: 1px solid var(--trait);
    border-radius: 12px;
    padding: 22px;
    max-width: 380px;
    width: 100%;
    box-sizing: border-box;
  }
  h1 { color: var(--or); margin: 0 0 8px; font-size: 1.2rem; }
  p { color: var(--texte-faible); margin: 0 0 14px; line-height: 1.4; }
  input, button {
    font: inherit;
    border-radius: 7px;
    padding: 7px 9px;
    box-sizing: border-box;
  }
  input {
    width: 100%;
    margin-bottom: 10px;
    background: var(--fond);
    color: var(--texte);
    border: 1px solid var(--trait);
  }
  button {
    background: var(--sarcelle);
    color: var(--texte);
    border: 0;
    cursor: pointer;
  }
  .refus { color: var(--refus); margin: 10px 0 0; }
</style>
</head>
<body>
<form method="post">
  <h1>La Lune Éternelle</h1>
  <p>Les applications de la guilde ne sont pas publiques. Demande le mot de
    passe à un officier.</p>
  <input type="password" name="mdp" autocomplete="current-password"
         placeholder="mot de passe" required autofocus>
  <button type="submit">Entrer</button>
<?php if ($refuse): ?>
  <p class="refus">Mot de passe refusé.</p>
<?php endif; ?>
</form>
</body>
</html>
