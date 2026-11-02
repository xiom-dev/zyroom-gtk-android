<?php
// Le sommaire https://xiom.be/index/, la porte principale du site : un code
// personnel et une question (garde.php, ecrit par outils/page-index.py).
// Entre : le sommaire (page.html, illisible en direct). Pas entre : le formulaire.
declare(strict_types=1);
require __DIR__ . '/garde.php';

// Ni cache, ni index, ni cadre d'un autre site, ni script venu d'ailleurs, ni
// adresse de provenance transmise aux pages citees.
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');
header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');
// Seuls scripts permis : musique.js du site ; seul son : le morceau de l'accueil.
header("Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
     . "script-src 'self'; media-src https://xiom-dev.github.io; "
     . "form-action 'self'; frame-ancestors 'none'; base-uri 'none'");
header('Strict-Transport-Security: max-age=31536000');

// Le formulaire de l'accueil (xiom.be, par-dessus l'image) parle en JSON :
// la page ne change pas, la musique continue pendant la saisie.
$json = str_contains((string) ($_SERVER['HTTP_ACCEPT'] ?? ''), 'application/json');

function repond_json(int $code, array $corps): never
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

// Le journal des codes, pour l'admin : par jour, de combien de reseaux
// chaque code a servi (porte.php).
function journal_page(): void
{
    $journal = porte_journal(14);
    $noms = array_keys(PORTE_CODES);
    sort($noms, SORT_NATURAL | SORT_FLAG_CASE);
    echo '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
       . '<meta name="viewport" content="width=device-width, initial-scale=1">'
       . '<title>Journal des codes</title><style>'
       . 'body{margin:0;padding:16px;background:#10171a;color:#e2e8e6;font:14px system-ui,sans-serif}'
       . 'h1{color:#e8c15a;font-size:1.2rem}p{color:#9aa8a5}div{overflow-x:auto}'
       . 'table{border-collapse:collapse}th,td{border:1px solid #24343a;padding:4px 8px;text-align:center}'
       . 'th:first-child,td:first-child{text-align:left}.haut{background:#5a1f18;color:#fff}'
       . '.zero{color:#4a5a57}a{color:#8fbfae}</style></head><body>'
       . '<h1>Journal des codes</h1><p>Nombre de réseaux différents d’où chaque code a servi, par jour (UTC). '
       . 'En rouge : ' . PORTE_SEUIL . ' ou plus. <a href="./">Sommaire</a></p><div><table><tr><th>Joueur</th>';
    foreach (array_keys($journal) as $jour) {
        echo '<th>' . htmlspecialchars(substr($jour, 8, 2) . '/' . substr($jour, 5, 2)) . '</th>';
    }
    echo '</tr>';
    foreach ($noms as $nom) {
        echo '<tr><td>' . htmlspecialchars((string) $nom) . '</td>';
        foreach ($journal as $jour => $comptes) {
            $n = (int) ($comptes[$nom] ?? 0);
            $classe = $n >= PORTE_SEUIL ? ' class="haut"' : ($n === 0 ? ' class="zero"' : '');
            echo '<td' . $classe . '>' . ($n ?: '·') . '</td>';
        }
        echo '</tr>';
    }
    echo '</table></div></body></html>';
}

$message = '';
$attente = bloque();
// La question et ses choix, pour le formulaire de l'accueil.
if ($json && ($_SERVER['REQUEST_METHOD'] ?? '') === 'GET') {
    repond_json(200, ['question' => QUESTION, 'choix' => CHOIX, 'attente' => $attente,
                      'entre' => entre()]);
}
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    // Un formulaire envoye depuis un autre site n'entre pas.
    $origine = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
    $hote = 'https://' . (string) ($_SERVER['HTTP_HOST'] ?? '');
    // Un essai par seconde au plus, rate ou non : bcrypt coute deja, ceci
    // finit le travail.
    sleep(1);
    if ($origine !== '' && $origine !== $hote) {
        http_response_code(403);
        $message = 'Demande refusée.';
    } elseif ($attente > 0) {
        http_response_code(429);
    } else {
        $mdp = (string) ($_POST['mdp'] ?? '');
        $choix = (string) ($_POST['choix'] ?? '');
        // Les deux sont toujours verifies, dans le meme temps : on ne dit pas
        // lequel est faux, et la duree n'en dit rien non plus.
        $qui = mdp_qui($mdp);
        $bon_choix = hash_equals(REPONSE, $choix);
        if ($qui !== null && $bon_choix) {
            reussi();
            ouvrir($qui);
            if ($json) {
                repond_json(200, ['ok' => true]);
            }
            header('Location: ./', true, 303);
            exit;
        }
        rate();
        $attente = bloque();
        $message = 'Code ou réponse incorrects.';
    }
}
if ($attente > 0) {
    $message = 'Trop d’essais : la porte est fermée encore '
        . max(1, (int) ceil($attente / 60)) . ' min.';
}

if ($json) {
    repond_json(http_response_code() === 200 ? 401 : (int) http_response_code(),
                ['ok' => false, 'message' => $message, 'attente' => $attente]);
}

if (entre()) {
    header('Content-Type: text/html; charset=utf-8');
    // Pour l'admin seul : le journal des codes (?journal), et l'alerte en haut
    // du sommaire quand un code sert depuis trop de reseaux un meme jour.
    if (porte_nom() === PORTE_ADMIN) {
        if (isset($_GET['journal'])) {
            journal_page();
            exit;
        }
        $alertes = porte_alertes();
        $html = (string) file_get_contents(__DIR__ . '/page.html');
        // The journal link, next to the title: red with the number of alerts
        // when a code is over the threshold.
        $lien = '<a href="?journal" style="margin-left:12px;font-size:.8rem;font-weight:400;'
            . 'vertical-align:middle;padding:3px 10px;border-radius:8px;text-decoration:none;'
            . ($alertes ? 'background:#5a1f18;color:#fff;border:1px solid #e07a6a">Journal des codes ⚠ '
                          . count($alertes)
                        : 'color:#8fbfae;border:1px solid #3f7a68">Journal des codes')
            . '</a>';
        $html = preg_replace('#<h1>Sommaire</h1>#', '<h1>Sommaire' . $lien . '</h1>', $html, 1);
        if ($alertes) {
            $lignes = [];
            foreach ($alertes as [$jour, $nom, $n]) {
                $lignes[] = htmlspecialchars($nom) . ' : ' . $n . ' réseaux le ' . htmlspecialchars($jour);
            }
            // Just after <body>, so the page keeps its doctype (no quirks mode).
            $bandeau = '<div style="position:relative;z-index:9999;background:#5a1f18;color:#fff;'
               . 'padding:10px 16px;font:15px system-ui,sans-serif">Code peut-être donné — '
               . implode(' ; ', $lignes) . ' — <a style="color:#e8c15a" href="?journal">journal</a></div>';
            $html = preg_replace('/<body[^>]*>/i', '$0' . str_replace(['\\', '$'], ['\\\\', '\\$'], $bandeau), $html, 1);
        }
        echo $html;
        exit;
    }
    readfile(__DIR__ . '/page.html');
    exit;
}

header('Content-Type: text/html; charset=utf-8');
?><!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Sommaire Xiom</title>
<meta name="theme-color" content="#10171a">
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="../favicon.png" type="image/png">
<style>
  :root { color-scheme: dark; --fond: #10171a; --surface: #172226; --sarcelle: #3f7a68;
          --clair: #8fbfae; --or: #e8c15a; --texte: #e2e8e6; --faible: #9aa8a5; --non: #e07a6a; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 0 16px; min-height: 100vh; display: flex; align-items: center;
         justify-content: center; background: var(--fond); color: var(--texte);
         font-family: system-ui, sans-serif; font-size: 15px; }
  form { width: 100%; max-width: 360px; background: var(--surface); border: 1px solid var(--sarcelle);
         border-radius: 12px; padding: 24px; }
  h1 { font-size: 1.3rem; margin: 0 0 6px; color: var(--or); }
  p { margin: 0 0 16px; color: var(--faible); line-height: 1.5; }
  fieldset { border: 0; padding: 0; margin: 0 0 16px; }
  fieldset:disabled, input:disabled, button:disabled { opacity: .5; }
  legend { padding: 0; margin-bottom: 8px; color: var(--texte); }
  label { display: flex; gap: 8px; align-items: center; padding: 4px 0; cursor: pointer; }
  input[type=radio] { accent-color: var(--sarcelle); margin: 0; }
  input.mdp, button { width: 100%; font: inherit; border-radius: 8px; padding: 10px 12px; }
  input.mdp { background: var(--fond); color: var(--texte); border: 1px solid #24343a;
                         margin-bottom: 16px; }
  input.mdp:focus { outline: 2px solid var(--sarcelle); outline-offset: 1px; }
  button { background: var(--sarcelle); color: var(--texte); border: 0; cursor: pointer; font-weight: 600; }
  .non { color: var(--non); }
  .pied { margin: 14px 0 0; font-size: .82rem; text-align: center; }
</style>
</head>
<body>
<form method="post" action="./">
  <h1>Sommaire</h1>
  <p>Accès réservé. Ton code personnel et la réponse sont demandés ensemble.</p>
<?php if ($message !== ''): ?>
  <p class="non" role="alert"><?= htmlspecialchars($message) ?></p>
<?php endif; ?>
  <fieldset<?= $attente > 0 ? ' disabled' : '' ?>>
    <input class="mdp" type="password" name="mdp" autocomplete="current-password" placeholder="Code personnel"
           maxlength="200" autofocus required>
    <fieldset>
      <legend><?= htmlspecialchars(QUESTION) ?></legend>
<?php foreach (CHOIX as $i => $c): ?>
      <label><input type="radio" name="choix" value="<?= htmlspecialchars($c) ?>" required>
        <?= ($i + 1) . '/ le ' . htmlspecialchars($c) ?></label>
<?php endforeach; ?>
    </fieldset>
    <button type="submit">Entrer</button>
  </fieldset>
  <p class="pied">Connexion chiffrée · 5 essais ratés ferment la porte</p>
</form>
<!-- La musique de l'accueil de xiom.be, reprise la ou elle en etait (../musique.js). -->
<audio id="musique" src="https://xiom-dev.github.io/zyroom-gtk-android/sielu-cuovggas.mp3"
       loop preload="auto"></audio>
<script src="../musique.js"></script>
<script src="../oeil.js"></script>
</body>
</html>
