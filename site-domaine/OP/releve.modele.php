<?php
// Le tri commun d'une guerre d'OP, tenu dans un simple fichier JSON.
//
// MODELE : ce fichier est versionne sans aucun secret. `outils/page-op.py`
// y met l'empreinte du mot de passe et le sel, et ecrit `releve.php` -- le
// seul a deposer sur le serveur, et le seul que git ignore.
//
// GET  : rend l'etat entier, a qui a le jeton.
// POST : entrer (mot de passe -> jeton), ranger un nom, ajouter des /who,
//        restaurer une sauvegarde, oublier le tri.
//
// **Ce qui arrive ici, et rien d'autre.** Le journal du jeu est lu dans le
// navigateur de chacun : seuls montent les /who -- heure, region, noms. Les
// tells et le canal de guilde ne quittent jamais le PC de celui qui depose.
declare(strict_types=1);

const EMPREINTE = '__EMPREINTE__';
const SEL = '__SEL__';
const COOKIE = 'op';
// Trente jours, comme le releve du forage : assez pour ne pas le retaper a
// chaque guerre, assez court pour qu'un depart finisse par fermer la porte.
const DUREE = 30 * 24 * 3600;
const FICHIER = __DIR__ . '/releve.json';
const SAUVEGARDES = __DIR__ . '/sauvegardes';
const MAX_SAUVEGARDES = 60;
// Un journal d'une soiree porte quelques dizaines de /who : cinq cents
// kilooctets laissent une grande marge, sans ouvrir la porte a n'importe quoi.
const MAX_CORPS = 512 * 1024;
const MAX_WHOS = 5000;
const MAX_NOMS_PAR_WHO = 500;
const CAMPS = ['kamis', 'opposants', 'neutres'];

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function repond(int $code, array $corps): never
{
    http_response_code($code);
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

// ------------------------------------------------------------- le garde
//
// Pas de session PHP : le jeton porte sa date d'expiration et une signature
// HMAC, que le serveur revalide. Il voyage dans un cookie et, pour les
// navigateurs qui n'en gardent pas, dans l'en-tete X-Op.

function jeton(int $expire): string
{
    return $expire . '.' . hash_hmac('sha256', 'op' . $expire, SEL);
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

function connecte(): bool
{
    foreach ([$_SERVER['HTTP_X_OP'] ?? '', $_COOKIE[COOKIE] ?? ''] as $candidat) {
        if ($candidat !== '' && jeton_valide((string) $candidat)) {
            return true;
        }
    }
    return false;
}

// ------------------------------------------------------------- les formes
//
// On valide tout ce qui entre : un nom, une region ou une heure mal formes
// n'entrent pas dans le fichier. Les noms de Ryzom sont des lettres, avec
// parfois une apostrophe ou un tiret.

function nom_valide($nom): bool
{
    return is_string($nom)
        && preg_match("/^\\p{L}[\\p{L}'-]{0,39}$/u", $nom) === 1;
}

function foreuse(array $demande): string
{
    // Qui a fait le geste : lettres, chiffres, espaces, vingt-quatre au plus.
    $qui = trim((string) ($demande['qui'] ?? ''));
    $qui = (string) preg_replace('/[^\p{L}\p{N} \-\']/u', '', $qui);
    return (string) preg_replace('/^(.{0,24}).*$/us', '$1', $qui);
}

function who_propre($w): ?array
{
    if (!is_array($w)) {
        return null;
    }
    $quand = (string) ($w['quand'] ?? '');
    $region = (string) ($w['region'] ?? '');
    $noms = $w['noms'] ?? null;
    if (preg_match('#^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$#', $quand) !== 1
        || preg_match('/^[^\x00-\x1f"<>]{1,80}$/u', $region) !== 1
        || !is_array($noms) || count($noms) > MAX_NOMS_PAR_WHO) {
        return null;
    }
    $gardes = [];
    foreach ($noms as $n) {
        if (nom_valide($n) && !in_array($n, $gardes, true)) {
            $gardes[] = $n;
        }
    }
    return $gardes ? ['quand' => $quand, 'region' => $region,
                      'noms' => $gardes] : null;
}

// ------------------------------------------------------------- le fichier

function vide(): array
{
    return ['camps' => [], 'whos' => [], 'maj' => null];
}

function lu(string $contenu): array
{
    $lu = json_decode($contenu, true);
    if (!is_array($lu)) {
        return vide();
    }
    return [
        'camps' => is_array($lu['camps'] ?? null) ? $lu['camps'] : [],
        'whos' => is_array($lu['whos'] ?? null) ? $lu['whos'] : [],
        'maj' => $lu['maj'] ?? null,
    ];
}

function pour_json(array $etat): array
{
    // Un tableau PHP vide s'ecrit [] en JSON ; la page attend un objet.
    $etat['camps'] = (object) $etat['camps'];
    return $etat;
}

/**
 * Lire, modifier, reecrire -- sous verrou, pour que deux Kamis qui deplacent
 * un nom dans la meme seconde ne s'effacent pas l'un l'autre. Une sauvegarde
 * part avant chaque ecriture : un tri tenu sur plusieurs guerres ne doit pas
 * disparaitre sur une fausse manoeuvre.
 */
function modifier(callable $changement): array
{
    $fh = fopen(FICHIER, 'c+');
    if ($fh === false || !flock($fh, LOCK_EX)) {
        repond(500, ['erreur' => 'fichier verrouille']);
    }
    $contenu = (string) stream_get_contents($fh);
    $etat = lu($contenu);
    if ($contenu !== '') {
        @mkdir(SAUVEGARDES, 0775, true);
        @file_put_contents(
            SAUVEGARDES . '/releve-' . gmdate('Ymd-His') . '.json', $contenu);
        $vieilles = glob(SAUVEGARDES . '/releve-*.json') ?: [];
        sort($vieilles);
        foreach (array_slice($vieilles, 0,
                             max(0, count($vieilles) - MAX_SAUVEGARDES)) as $v) {
            @unlink($v);
        }
    }
    $etat = $changement($etat);
    $etat['maj'] = gmdate('c');
    ftruncate($fh, 0);
    rewind($fh);
    fwrite($fh, (string) json_encode(pour_json($etat),
                                     JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    return $etat;
}

function ajouter_whos(array $etat, array $liste): array
{
    $connus = [];
    foreach ($etat['whos'] as $w) {
        $connus[$w['quand'] . '|' . $w['region']] = true;
    }
    foreach ($liste as $brut) {
        $w = who_propre($brut);
        if ($w === null || isset($connus[$w['quand'] . '|' . $w['region']])) {
            continue;
        }
        if (count($etat['whos']) >= MAX_WHOS) {
            break;
        }
        $etat['whos'][] = $w;
        $connus[$w['quand'] . '|' . $w['region']] = true;
    }
    usort($etat['whos'], fn($a, $b) => strcmp($a['quand'], $b['quand']));
    return $etat;
}

// ------------------------------------------------------------- les requetes

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    if (!connecte()) {
        repond(401, ['erreur' => 'mot de passe']);
    }
    $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
    repond(200, pour_json(lu($contenu)));
}

$demande = json_decode(
    (string) file_get_contents('php://input', false, null, 0, MAX_CORPS), true);
if (!is_array($demande)) {
    repond(400, ['erreur' => 'requete illisible']);
}
$action = (string) ($demande['action'] ?? '');

if ($action === 'entrer') {
    // Une seconde de retard : les essais successifs deviennent interminables,
    // et un Kami qui se trompe ne le remarque pas.
    usleep(1000000);
    if (!password_verify((string) ($demande['mdp'] ?? ''), EMPREINTE)) {
        repond(403, ['erreur' => 'mot de passe']);
    }
    $expire = time() + DUREE;
    setcookie(COOKIE, jeton($expire), [
        'expires' => $expire,
        'path' => dirname((string) ($_SERVER['SCRIPT_NAME'] ?? '/')),
        'secure' => true,
        'httponly' => true,
        'samesite' => 'Strict',
    ]);
    repond(200, ['ok' => true, 'jeton' => jeton($expire)]);
}

// Tout le reste ecrit : il faut etre entre.
if (!connecte()) {
    repond(401, ['erreur' => 'mot de passe']);
}
$qui = foreuse($demande);
$quand = gmdate('c');

switch ($action) {
    case 'ranger':
        $nom = $demande['nom'] ?? null;
        $camp = (string) ($demande['camp'] ?? '');
        if (!nom_valide($nom) || ($camp !== '' && !in_array($camp, CAMPS, true))) {
            repond(400, ['erreur' => 'nom ou camp inconnu']);
        }
        $etat = modifier(function (array $etat) use ($nom, $camp, $qui, $quand) {
            if ($camp === '') {
                unset($etat['camps'][$nom]);        // retour au centre
            } else {
                $etat['camps'][$nom] = ['c' => $camp, 'qui' => $qui,
                                        'quand' => $quand];
            }
            return $etat;
        });
        repond(200, pour_json($etat));

    case 'whos':
        $liste = $demande['liste'] ?? null;
        if (!is_array($liste)) {
            repond(400, ['erreur' => 'liste absente']);
        }
        $etat = modifier(fn(array $etat) => ajouter_whos($etat, $liste));
        repond(200, pour_json($etat));

    case 'restaurer':
        // Une sauvegarde de la page : son tri remplace le tri commun -- ou
        // le complete seulement, avec `fusion` -- et ses /who s'ajoutent.
        $camps = $demande['camps'] ?? null;
        if (!is_array($camps)) {
            repond(400, ['erreur' => 'sauvegarde illisible']);
        }
        $fusion = ($demande['fusion'] ?? false) === true;
        $whos = is_array($demande['whos'] ?? null) ? $demande['whos'] : [];
        $etat = modifier(function (array $etat) use ($camps, $whos, $fusion,
                                                    $qui, $quand) {
            $neufs = [];
            foreach ($camps as $nom => $valeur) {
                // L'ancien format ne gardait que le camp, le nouveau un objet.
                $camp = is_array($valeur) ? (string) ($valeur['c'] ?? '')
                                          : (string) $valeur;
                if (nom_valide((string) $nom) && in_array($camp, CAMPS, true)) {
                    $neufs[(string) $nom] = ['c' => $camp, 'qui' => $qui,
                                             'quand' => $quand];
                }
            }
            $etat['camps'] = $fusion ? $etat['camps'] + $neufs : $neufs;
            return ajouter_whos($etat, $whos);
        });
        repond(200, pour_json($etat));

    case 'oublier':
        $etat = modifier(function (array $etat) {
            $etat['camps'] = [];
            return $etat;
        });
        repond(200, pour_json($etat));
}

repond(400, ['erreur' => 'action inconnue']);
