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
// Les statistiques : un resume chiffre par journal et par guerre, calcule
// dans le navigateur de celui qui depose. Un fichier par guerre, pour que la
// page ne telecharge que celle qu'on regarde.
const COMBATS = __DIR__ . '/combats';
const MAX_RESUME = 200 * 1024;
// Le bilan ecrit a la main : un texte par guerre, range avec ses resumes.
// Compte en octets -- mbstring n'est pas garanti sur tous les hebergements :
// soixante kilooctets, une vingtaine de pages de texte accentue.
const MAX_BILAN = 60 * 1024;

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

// ------------------------------------------------------------- les guerres

// Deux formes d'identifiant : le jour du premier round (les guerres
// reconnues a leurs rounds, avant le calendrier), et « g » suivi de l'instant
// de creation, pour celles qu'on ouvre avec « Nouvelle guerre ».
function guerre_valide($id): bool
{
    return is_string($id)
        && preg_match('/^(\d{4}-\d{2}-\d{2}(-\d{1,2})?|g\d{8}-\d{6}(-\d{1,2})?)$/', $id) === 1;
}

function fichier_guerre(string $id): string
{
    return COMBATS . '/' . $id . '.json';
}

/** Une guerre complete, champs manquants remplis : les anciennes n'ont ni
 *  nom, ni mois, ni /who a elles. */
function guerre_complete(array $lu, string $id): array
{
    $jour = preg_match('/^(\d{4})-(\d{2})/', $id, $m) ? $m : null;
    return [
        'id' => $id,
        'nom' => (string) ($lu['nom'] ?? ''),
        'annee' => (int) ($lu['annee'] ?? ($jour ? $jour[1] : gmdate('Y'))),
        'mois' => (int) ($lu['mois'] ?? ($jour ? $jour[2] : gmdate('n'))),
        'cree_le' => $lu['cree_le'] ?? null,
        'cree_par' => $lu['cree_par'] ?? null,
        'enregistree_le' => $lu['enregistree_le'] ?? null,
        'enregistree_par' => $lu['enregistree_par'] ?? null,
        'whos' => is_array($lu['whos'] ?? null) ? $lu['whos'] : [],
        'journaux' => is_array($lu['journaux'] ?? null) ? $lu['journaux'] : [],
        'bilan' => $lu['bilan'] ?? null,
        'camps_figes' => is_array($lu['camps_figes'] ?? null) ? $lu['camps_figes'] : null,
    ];
}

/**
 * Lire, modifier, reecrire une guerre -- entiere, sous verrou. Toutes les
 * ecritures passent par ici : un champ oublie par une action ne doit pas
 * effacer ce qu'une autre a pose.
 */
function modifier_guerre(string $id, callable $changement, bool $creer = false): array
{
    $f = fichier_guerre($id);
    if (!$creer && !is_file($f)) {
        repond(404, ['erreur' => 'guerre inconnue']);
    }
    @mkdir(COMBATS, 0775, true);
    $fh = fopen($f, 'c+');
    if ($fh === false || !flock($fh, LOCK_EX)) {
        repond(500, ['erreur' => 'fichier verrouille']);
    }
    $lu = json_decode((string) stream_get_contents($fh), true);
    $g = $changement(guerre_complete(is_array($lu) ? $lu : [], $id));
    ftruncate($fh, 0);
    rewind($fh);
    $g['journaux'] = (object) $g['journaux'];
    fwrite($fh, (string) json_encode($g, JSON_UNESCAPED_UNICODE));
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
    clearstatcache();
    return $g;
}

function lire_guerre(string $id): ?array
{
    $f = fichier_guerre($id);
    if (!is_file($f)) {
        return null;
    }
    $lu = json_decode((string) file_get_contents($f), true);
    return guerre_complete(is_array($lu) ? $lu : [], $id);
}

/** Les guerres connues : de quoi remplir la liste, sans leur contenu. */
function guerres(): array
{
    $liste = [];
    foreach (glob(COMBATS . '/*.json') ?: [] as $f) {
        $id = basename($f, '.json');
        if (!guerre_valide($id)) {
            continue;
        }
        $g = lire_guerre($id);
        $liste[] = ['id' => $id, 'maj' => filemtime($f), 'nom' => $g['nom'],
                    'annee' => $g['annee'], 'mois' => $g['mois'],
                    'enregistree_le' => $g['enregistree_le'],
                    'cree_le' => $g['cree_le'],
                    'proprios' => array_keys($g['journaux'])];
    }
    usort($liste, fn($a, $b) => strcmp($b['id'], $a['id']));
    return $liste;
}

/** L'etat du tri, et la liste des guerres a cote. */
function reponse(array $etat): array
{
    return pour_json($etat) + ['guerres' => guerres()];
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    if (!connecte()) {
        repond(401, ['erreur' => 'mot de passe']);
    }
    if (isset($_GET['guerre'])) {
        $id = (string) $_GET['guerre'];
        $g = guerre_valide($id) ? lire_guerre($id) : null;
        if ($g === null) {
            repond(404, ['erreur' => 'guerre inconnue']);
        }
        $g['journaux'] = (object) $g['journaux'];
        if ($g['camps_figes'] !== null) {
            $g['camps_figes'] = (object) $g['camps_figes'];
        }
        repond(200, $g);
    }
    $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
    repond(200, reponse(lu($contenu)));
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
        // Une guerre deja enregistree garde son propre tri : le geste fait en
        // la consultant la corrige elle aussi.
        $id = $demande['guerre'] ?? null;
        if (guerre_valide($id) && ($g = lire_guerre($id)) && $g['camps_figes'] !== null) {
            modifier_guerre($id, function (array $g) use ($nom, $camp, $qui, $quand) {
                if ($camp === '') {
                    unset($g['camps_figes'][$nom]);
                } else {
                    $g['camps_figes'][$nom] = ['c' => $camp, 'qui' => $qui,
                                               'quand' => $quand];
                }
                return $g;
            });
        }
        repond(200, reponse($etat));

    case 'whos':
        $liste = $demande['liste'] ?? null;
        if (!is_array($liste)) {
            repond(400, ['erreur' => 'liste absente']);
        }
        $etat = modifier(fn(array $etat) => ajouter_whos($etat, $liste));
        repond(200, reponse($etat));

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
        repond(200, reponse($etat));

    case 'combats':
        // Un resume par journal et par guerre. Deposer a nouveau le meme
        // journal -- plus long, la guerre suivante -- remplace le resume de
        // son proprietaire pour cette guerre : rien ne se compte deux fois.
        $resumes = $demande['resumes'] ?? null;
        if (!is_array($resumes)) {
            repond(400, ['erreur' => 'resumes absents']);
        }
        $gardes = 0;
        foreach ($resumes as $r) {
            if (!is_array($r) || !nom_valide($r['proprio'] ?? null)
                || !guerre_valide($r['guerre'] ?? null)
                || strlen((string) json_encode($r)) > MAX_RESUME) {
                continue;
            }
            $r['depose_par'] = $qui;
            $r['depose_le'] = $quand;
            modifier_guerre($r['guerre'], function (array $g) use ($r) {
                $g['journaux'][$r['proprio']] = $r;
                return $g;
            }, true);
            $gardes++;
        }
        $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
        repond(200, reponse(lu($contenu)) + ['resumes_gardes' => $gardes]);

    case 'bilan':
        // Le dernier qui ecrit l'emporte : c'est un bloc-notes de guilde, en
        // general tenu par une seule personne. La page dit qui l'a touche en
        // dernier, et quand.
        $id = $demande['guerre'] ?? null;
        $texte = $demande['texte'] ?? null;
        if (!guerre_valide($id) || !is_string($texte)
            || strlen($texte) > MAX_BILAN) {
            repond(400, ['erreur' => 'bilan illisible ou trop long']);
        }
        $bilan = ['texte' => $texte, 'qui' => $qui, 'quand' => $quand];
        modifier_guerre($id, function (array $g) use ($bilan) {
            $g['bilan'] = $bilan;
            return $g;
        });
        repond(200, ['ok' => true, 'bilan' => $bilan, 'guerres' => guerres()]);

    case 'nouvelle':
        // Une guerre vide, rangee d'emblee dans le mois choisi a gauche.
        $annee = (int) ($demande['annee'] ?? 0);
        $mois = (int) ($demande['mois'] ?? 0);
        if ($annee < 2000 || $annee > 2100 || $mois < 1 || $mois > 12) {
            repond(400, ['erreur' => 'mois inconnu']);
        }
        $base = 'g' . gmdate('Ymd-His');
        $id = $base;
        for ($n = 2; is_file(fichier_guerre($id)); $n++) {
            $id = $base . '-' . $n;
        }
        $g = modifier_guerre($id, function (array $g) use ($annee, $mois, $qui, $quand) {
            $g['annee'] = $annee;
            $g['mois'] = $mois;
            $g['cree_le'] = $quand;
            $g['cree_par'] = $qui;
            return $g;
        }, true);
        $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
        repond(200, reponse(lu($contenu)) + ['ouverte' => $id]);

    case 'journal':
        // Ce qu'un journal apporte a la guerre ouverte : ses /who et le resume
        // de ses combats. Redeposer le meme journal ne double rien : les /who
        // se reconnaissent a leur heure et leur region, le resume remplace
        // celui du meme joueur.
        $id = $demande['guerre'] ?? null;
        if (!guerre_valide($id)) {
            repond(400, ['erreur' => 'guerre inconnue']);
        }
        $liste = is_array($demande['whos'] ?? null) ? $demande['whos'] : [];
        $resumes = is_array($demande['resumes'] ?? null) ? $demande['resumes'] : [];
        modifier_guerre($id, function (array $g) use ($liste, $resumes, $id, $qui, $quand) {
            $g = ajouter_whos($g, $liste);
            foreach ($resumes as $r) {
                if (!is_array($r) || !nom_valide($r['proprio'] ?? null)
                    || strlen((string) json_encode($r)) > MAX_RESUME) {
                    continue;
                }
                $r['guerre'] = $id;
                $r['depose_par'] = $qui;
                $r['depose_le'] = $quand;
                $g['journaux'][$r['proprio']] = $r;
            }
            return $g;
        });
        $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
        repond(200, reponse(lu($contenu)));

    case 'enregistrer':
        // Ranger la guerre dans un mois, sous un nom, et figer son tri : un
        // joueur qui changera de camp plus tard n'y changera pas.
        $id = $demande['guerre'] ?? null;
        $nomGuerre = trim((string) ($demande['nom'] ?? ''));
        $annee = (int) ($demande['annee'] ?? 0);
        $mois = (int) ($demande['mois'] ?? 0);
        $participants = $demande['participants'] ?? [];
        if (!guerre_valide($id) || preg_match('/^[^\x00-\x1f<>]{1,80}$/u', $nomGuerre) !== 1
            || $annee < 2000 || $annee > 2100 || $mois < 1 || $mois > 12
            || !is_array($participants)) {
            repond(400, ['erreur' => 'nom ou mois invalide']);
        }
        $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
        $etat = lu($contenu);
        modifier_guerre($id, function (array $g) use ($nomGuerre, $annee, $mois,
                                                     $participants, $etat, $qui, $quand) {
            $g['nom'] = $nomGuerre;
            $g['annee'] = $annee;
            $g['mois'] = $mois;
            $g['enregistree_le'] = $quand;
            $g['enregistree_par'] = $qui;
            $figes = [];
            foreach ($participants as $n) {
                if (nom_valide($n) && isset($etat['camps'][$n])) {
                    $figes[$n] = $etat['camps'][$n];
                }
            }
            $g['camps_figes'] = $figes;
            return $g;
        });
        repond(200, reponse($etat));

    case 'supprimer':
        // Une guerre supprimee n'est pas perdue : elle part dans les
        // sauvegardes, d'ou on peut la ressortir a la main.
        $id = $demande['guerre'] ?? null;
        if (!guerre_valide($id) || !is_file(fichier_guerre($id))) {
            repond(404, ['erreur' => 'guerre inconnue']);
        }
        @mkdir(SAUVEGARDES, 0775, true);
        rename(fichier_guerre($id),
               SAUVEGARDES . '/guerre-' . $id . '-supprimee-' . gmdate('Ymd-His') . '.json');
        $contenu = is_file(FICHIER) ? (string) file_get_contents(FICHIER) : '';
        repond(200, reponse(lu($contenu)));

    case 'oublier':
        $etat = modifier(function (array $etat) {
            $etat['camps'] = [];
            return $etat;
        });
        repond(200, reponse($etat));
}

repond(400, ['erreur' => 'action inconnue']);
