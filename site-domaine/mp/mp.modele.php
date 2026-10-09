<?php
// Les recettes et les reglages de la page des MP du hall de guilde.
//
// MODELE : ce fichier est versionne sans aucun secret. `outils/page-mp.py`
// y met les empreintes des mots de passe et le sel, et ecrit `mp.php` -- le
// seul a deposer sur le serveur, et le seul que git ignore.
//
// GET  : a un editeur, les recettes et les reglages ; a un joueur, les
//        reglages et les resultats du calcul, sans les recettes.
// POST : entrer (nom + mot de passe -> jeton), puis, avec un jeton
//        d'editeur : enregistrer une recette, en supprimer une, changer les
//        reglages.
//
// **Deux portes.** Un nom de joueur de l'effectif de la guilde et le mot de
// passe de la guilde ouvrent la lecture. Un nom de la liste des editeurs et
// son mot de passe personnel ouvrent tout, recettes comprises.
//
// **Les recettes ne sortent pas du serveur pour un joueur** (Ludo et
// Nizyros, 9 octobre 2026). Cacher l'onglet ne suffisait pas : la page
// calculait dans le navigateur, et recevait donc les recettes. Pour un joueur,
// le calcul se fait ici, et seuls les totaux par MP partent.
//
// **Un mot de passe par personne pour ecrire.** Le jeton porte le nom de celui qui l'a
// recu : chaque modification est signee, et le journal dit qui a change
// quoi. Retirer quelqu'un de la liste ferme sa porte aussitot, meme si son
// jeton n'a pas expire.
//
// **Le point de depart.** Tant que rien n'a ete enregistre, la page lit
// `mp.depart.json` (les recettes de KipeeCraft lues par l'outil). La
// premiere modification ecrit `mp.json`, et c'est lui qui fait foi ensuite :
// redeposer `mp.depart.json` n'efface donc rien.
declare(strict_types=1);

const UTILISATEURS = '__UTILISATEURS__';
// L'empreinte du mot de passe de lecture, commun a la guilde.
const LECTURE = '__LECTURE__';
const SEL = '__SEL__';
// Trente jours, comme le releve du forage.
const DUREE = 30 * 24 * 3600;
const FICHIER = __DIR__ . '/mp.json';
const DEPART = __DIR__ . '/mp.depart.json';
const SAUVEGARDES = __DIR__ . '/sauvegardes';
const MAX_SAUVEGARDES = 60;
// Au plus une sauvegarde toutes les cinq minutes : un reglage retouche dix
// fois de suite n'en ecrit qu'une.
const ECART_SAUVEGARDES = 5 * 60;
const MAX_CORPS = 64 * 1024;
const MAX_JOURNAL = 300;
const MAX_RECETTES = 1000;
const MAX_PIECES = 12;
// Un nom de MP de KipeeCraft : grade, ecosysteme, matiere, type.
const FORME_MP = '/^[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+_[A-Za-z0-9]+$/';
// Ce que le releve du hall publie : le stock, coffre par coffre, et
// l'effectif de la guilde.
const DEPOT = 'https://raw.githubusercontent.com/xiom-dev/zyroom-gtk-android/journaux/';
const NOMS = __DIR__ . '/noms.json';
const CACHE = __DIR__ . '/cache';
// Le releve passe tous les quarts d'heure : cinq minutes de cache suffisent.
const CACHE_DUREE = 5 * 60;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function repond(int $code, array $corps): never
{
    http_response_code($code);
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

function utilisateurs(): array
{
    $liste = json_decode(UTILISATEURS, true);
    return is_array($liste) ? $liste : [];
}

// ------------------------------------------------------------- le jeton
//
// "nom.role.expiration.signature", le nom en base64 (il peut porter un
// accent), le role "e" (editeur) ou "j" (joueur). Pas de session PHP : le
// serveur ne garde rien, il revalide la signature.

function b64(string $s): string
{
    return rtrim(strtr(base64_encode($s), '+/', '-_'), '=');
}

function jeton(string $nom, string $role, int $expire): string
{
    $tete = b64($nom) . '.' . $role . '.' . $expire;
    return $tete . '.' . hash_hmac('sha256', $tete, SEL);
}

// [nom, editeur ?] pour un jeton valide ; null si le jeton est absent, faux,
// expire, ou si son porteur a perdu son droit : editeur retire de la liste,
// joueur sorti de la guilde.
function porteur(): ?array
{
    $recu = (string) ($_SERVER['HTTP_X_MP'] ?? '');
    $morceaux = explode('.', $recu);
    if (count($morceaux) !== 4 || !in_array($morceaux[1], ['e', 'j'], true)
        || !preg_match('/^[0-9]{1,12}$/', $morceaux[2])) {
        return null;
    }
    if ((int) $morceaux[2] < time()) {
        return null;
    }
    $nom = (string) base64_decode(strtr($morceaux[0], '-_', '+/'), true);
    // hash_equals : la comparaison ne doit pas fuir la signature par le temps
    // qu'elle met a echouer.
    if ($nom === '' || !hash_equals(jeton($nom, $morceaux[1], (int) $morceaux[2]), $recu)) {
        return null;
    }
    if ($morceaux[1] === 'e') {
        return isset(utilisateurs()[$nom]) ? [$nom, true] : null;
    }
    // Un effectif illisible ne ferme pas la porte a qui l'a deja passee.
    $effectif = effectif();
    return ($effectif === null || membre($nom, $effectif) !== '') ? [$nom, false] : null;
}

// Le nom de qui peut ecrire, ou '' (joueur ou inconnu).
function qui(): string
{
    $p = porteur();
    return ($p !== null && $p[1]) ? $p[0] : '';
}

// ------------------------------------------------------------- le releve
//
// Lu sur GitHub et garde quelques minutes : chaque page ouverte ne doit pas
// aller y frapper.

function distant(string $nom): ?array
{
    $local = CACHE . '/' . $nom;
    if (is_file($local) && time() - (int) filemtime($local) < CACHE_DUREE) {
        return lire($local);
    }
    $contexte = stream_context_create(['http' => ['timeout' => 10]]);
    $brut = @file_get_contents(DEPOT . $nom, false, $contexte);
    $lu = $brut !== false ? json_decode($brut, true) : null;
    if (is_array($lu)) {
        @mkdir(CACHE, 0775, true);
        @file_put_contents($local, $brut);
        return $lu;
    }
    // GitHub injoignable : la derniere copie vaut mieux que rien.
    return is_file($local) ? lire($local) : null;
}

function guilde(): int
{
    $lu = lire(FICHIER) ?? lire(DEPART) ?? [];
    return (int) ($lu['reglages']['guilde'] ?? 0);
}

// Les membres de la guilde, nom -> grade ; null si illisible.
function effectif(): ?array
{
    return distant('roster-' . guilde() . '.json');
}

// Le nom tel que l'effectif l'ecrit, sans tenir compte des majuscules ; ''
// s'il n'y est pas.
function membre(string $nom, array $effectif): string
{
    foreach (array_keys($effectif) as $connu) {
        if (strcasecmp((string) $connu, trim($nom)) === 0) {
            return (string) $connu;
        }
    }
    return '';
}

// ------------------------------------------------------------- l'etat

function lire(string $chemin): ?array
{
    if (!is_file($chemin)) {
        return null;
    }
    $lu = json_decode((string) file_get_contents($chemin), true);
    return is_array($lu) ? $lu : null;
}

function etat(): array
{
    $lu = lire(FICHIER) ?? lire(DEPART) ?? [];
    return [
        'version' => 1,
        'reglages' => $lu['reglages'] ?? [],
        'recettes' => $lu['recettes'] ?? [],
        'journal' => $lu['journal'] ?? [],
        'maj' => $lu['maj'] ?? null,
        'depart' => lire(FICHIER) === null,
    ];
}

// ------------------------------------------------------------- le calcul
//
// Le meme que celui de la page (calculer, dans index.html), pour les joueurs :
// qui change l'un change l'autre.

// Le stock du hall, fiche -> [[qualite, quantite], ...], tous coffres.
function stock(): array
{
    $releve = distant('guild-' . guilde() . '-etat.json') ?? [];
    $stock = [];
    foreach ($releve as $coffre => $contenu) {
        if (!str_starts_with((string) $coffre, 'chest') || !is_array($contenu)) {
            continue;
        }
        foreach ($contenu as $cle => $quantite) {
            [$fiche, $q] = array_pad(explode('|', (string) $cle), 2, '0');
            $stock[$fiche][] = [(int) $q, (int) $quantite];
        }
    }
    return $stock;
}

function resultats(array $etat): array
{
    $noms = (lire(NOMS) ?? [])['mp'] ?? [];
    $stock = stock();
    $reg = $etat['reglages'];
    $utile = function (string $mp, int $qmin) use ($noms, $stock): int {
        $total = 0;
        foreach ($noms[$mp]['fiches'] ?? [] as $f) {
            foreach ($stock[$f] ?? [] as [$q, $n]) {
                if ($q >= $qmin) {
                    $total += $n;
                }
            }
        }
        return $total;
    };
    $presqueVide = fn(int $crafts): bool =>
        $crafts > 0 && $crafts < (int) $reg['rupture'];

    $demandes = [];
    foreach ($etat['recettes'] as $r) {
        $objectif = (int) ($r['objectif'] ?? $reg['objectif']);
        $qc = (int) ($r['qualite'] ?? $reg['qualite']);
        $parMp = [];
        foreach ($r['pieces'] as $p) {
            $min = max($qc, (int) (((array) ($r['minimums'] ?? []))[$p['mp']] ?? 0));
            $parMp[$p['mp']] ??= ['n' => 0, 'min' => $min];
            $parMp[$p['mp']]['n'] += (int) $p['n'];
        }
        foreach ($parMp as $mp => $b) {
            $demandes[$mp][] = ['min' => $b['min'], 'besoin' => $objectif * $b['n'],
                                'parCraft' => $b['n']];
        }
    }

    $mps = [];
    foreach ($demandes as $mp => $liste) {
        $seuils = array_values(array_unique(array_column($liste, 'min')));
        sort($seuils);
        $manque = 0;
        foreach ($seuils as $t) {
            $voulu = 0;
            foreach ($liste as $d) {
                if ($d['min'] >= $t) {
                    $voulu += $d['besoin'];
                }
            }
            $manque = max($manque, $voulu - $utile($mp, $t));
        }
        $qmin = $seuils[0];
        $s = $utile($mp, $qmin);
        $besoin = array_sum(array_column($liste, 'besoin'));
        $parCraft = array_sum(array_column($liste, 'parCraft'));
        $couverture = intdiv($s, max(1, $parCraft));
        $statut = $presqueVide($couverture) ? 'rupture'
            : ($manque > 0 || $couverture === 0 ? 'forer'
            : ($besoin > 0 && $s > $reg['stop'] * $besoin ? 'stop' : 'ok'));
        $mps[] = ['mp' => $mp, 'nom' => $noms[$mp]['nom'] ?? null,
                  'eco' => explode('_', $mp)[1] ?? '', 'qmin' => $qmin,
                  'stock' => $s, 'besoin' => $besoin, 'manque' => $manque,
                  'couverture' => $couverture, 'statut' => $statut,
                  'nbRecettes' => count($liste)];
    }
    return $mps;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    $p = porteur();
    if ($p === null) {
        repond(401, ['erreur' => 'mot de passe']);
    }
    [$nom, $editeur] = $p;
    $etat = etat();
    if ($editeur) {
        $etat['qui'] = $nom;
        $etat['editeur'] = true;
        repond(200, $etat);
    }
    repond(200, ['version' => 1, 'reglages' => $etat['reglages'],
                 'resultats' => resultats($etat), 'qui' => $nom,
                 'editeur' => false]);
}

$brut = (string) file_get_contents('php://input', false, null, 0, MAX_CORPS);
$demande = json_decode($brut, true);
if (!is_array($demande)) {
    repond(400, ['erreur' => 'requete illisible']);
}

if (($demande['action'] ?? '') === 'entrer') {
    $nom = (string) ($demande['nom'] ?? '');
    $mdp = (string) ($demande['mdp'] ?? '');
    // Une seconde de retard : une attaque par essais successifs devient
    // interminable, et qui se trompe ne le remarque pas.
    usleep(1000000);
    if (trim($nom) === '') {
        repond(403, ['erreur' => 'nom ou mot de passe']);
    }
    // Un editeur et son mot de passe personnel. Le nom sans tenir compte des
    // majuscules : "xiom" entre comme "Xiom".
    foreach (utilisateurs() as $connu => $empreinte) {
        if (strcasecmp($connu, trim($nom)) === 0 && password_verify($mdp, $empreinte)) {
            repond(200, ['ok' => true, 'qui' => $connu, 'editeur' => true,
                         'jeton' => jeton($connu, 'e', time() + DUREE)]);
        }
    }
    // Un joueur de la guilde et le mot de passe de la guilde.
    if (!password_verify($mdp, LECTURE)) {
        repond(403, ['erreur' => 'nom ou mot de passe']);
    }
    $effectif = effectif();
    if ($effectif === null) {
        repond(503, ['erreur' => "effectif de la guilde illisible, réessaie dans un moment"]);
    }
    $joueur = membre($nom, $effectif);
    if ($joueur === '') {
        repond(403, ['erreur' => "ce nom n'est pas dans la guilde"]);
    }
    repond(200, ['ok' => true, 'qui' => $joueur, 'editeur' => false,
                 'jeton' => jeton($joueur, 'j', time() + DUREE)]);
}

$auteur = qui();
if ($auteur === '') {
    repond(401, ['erreur' => 'mot de passe']);
}

// ------------------------------------------------------------- les controles
//
// On valide champ par champ et on recopie ce qui est valide : rien de ce que
// la page envoie n'entre tel quel dans le fichier.

function entier($v, int $min, int $max): ?int
{
    if (!is_int($v) || $v < $min || $v > $max) {
        return null;
    }
    return $v;
}

function texte($v, int $max): string
{
    $s = (string) preg_replace('/[\x00-\x1f\x7f<>]/u', '', (string) $v);
    // Ni mbstring ni substr : PCRE en mode /u coupe sans casser un accent.
    return trim((string) preg_replace('/^(.{0,' . $max . '}).*$/us', '$1', $s));
}

function recette_valide($r): ?array
{
    if (!is_array($r)) {
        return null;
    }
    $id = (string) ($r['id'] ?? '');
    $nom = texte($r['nom'] ?? '', 80);
    $plan = entier($r['plan'] ?? null, 0, 500);
    if (!preg_match('/^[a-z0-9-]{1,60}$/', $id) || $nom === '' || $plan === null) {
        return null;
    }
    $pieces = [];
    foreach ((array) ($r['pieces'] ?? []) as $p) {
        if (!is_array($p)) {
            return null;
        }
        $n = entier($p['n'] ?? null, 1, 99);
        $mp = (string) ($p['mp'] ?? '');
        if ($n === null || !preg_match(FORME_MP, $mp)) {
            return null;
        }
        $pieces[] = ['n' => $n, 'mp' => $mp];
    }
    if (!$pieces || count($pieces) > MAX_PIECES) {
        return null;
    }
    $mps = array_column($pieces, 'mp');
    $minimums = [];
    foreach ((array) ($r['minimums'] ?? []) as $mp => $q) {
        if (!in_array($mp, $mps, true) || entier($q, 1, 300) === null) {
            return null;
        }
        $minimums[$mp] = $q;
    }
    $sortie = ['id' => $id, 'nom' => $nom, 'plan' => $plan,
               'pieces' => $pieces, 'minimums' => (object) $minimums];
    // Absents : la recette suit les reglages communs.
    foreach (['objectif' => [0, 100000], 'qualite' => [1, 300]] as $cle => [$a, $b]) {
        if (array_key_exists($cle, $r) && $r[$cle] !== null) {
            $v = entier($r[$cle], $a, $b);
            if ($v === null) {
                return null;
            }
            $sortie[$cle] = $v;
        }
    }
    return $sortie;
}

function reglages_valides($r): ?array
{
    if (!is_array($r)) {
        return null;
    }
    $sortie = [
        'objectif' => entier($r['objectif'] ?? null, 0, 100000),
        'qualite' => entier($r['qualite'] ?? null, 1, 300),
        'stop' => entier($r['stop'] ?? null, 1, 100),
        'rupture' => entier($r['rupture'] ?? null, 0, 100000),
        'guilde' => entier($r['guilde'] ?? null, 1, PHP_INT_MAX),
    ];
    return in_array(null, $sortie, true) ? null : $sortie;
}

// ------------------------------------------------------------- l'ecriture
//
// Le verrou tient le temps de lire, modifier et reecrire : deux chefs qui
// enregistrent dans la meme seconde ne doivent pas s'effacer l'un l'autre.

$action = (string) ($demande['action'] ?? '');
$fh = fopen(FICHIER, 'c+');
if ($fh === false || !flock($fh, LOCK_EX)) {
    repond(500, ['erreur' => 'fichier verrouille']);
}
$contenu = (string) stream_get_contents($fh);
$lu = $contenu !== '' ? json_decode($contenu, true) : lire(DEPART);
if (!is_array($lu)) {
    flock($fh, LOCK_UN);
    repond(500, ['erreur' => 'fichier illisible']);
}
$recettes = $lu['recettes'] ?? [];
$reglages = $lu['reglages'] ?? [];
$journal = $lu['journal'] ?? [];

function refuse($fh, int $code, string $erreur): never
{
    flock($fh, LOCK_UN);
    fclose($fh);
    repond($code, ['erreur' => $erreur]);
}

if ($action === 'recette') {
    $r = recette_valide($demande['recette'] ?? null);
    if ($r === null) {
        refuse($fh, 400, 'recette invalide');
    }
    $place = null;
    foreach ($recettes as $i => $existante) {
        if (($existante['id'] ?? '') === $r['id']) {
            $place = $i;
        }
    }
    if ($place === null) {
        if (count($recettes) >= MAX_RECETTES) {
            refuse($fh, 400, 'trop de recettes');
        }
        $recettes[] = $r;
        $quoi = 'ajoute la recette « ' . $r['nom'] . ' »';
    } else {
        $recettes[$place] = $r;
        $quoi = 'modifie la recette « ' . $r['nom'] . ' »';
    }
} elseif ($action === 'supprimer') {
    $id = (string) ($demande['id'] ?? '');
    $avant = count($recettes);
    $nom = $id;
    foreach ($recettes as $existante) {
        if (($existante['id'] ?? '') === $id) {
            $nom = (string) ($existante['nom'] ?? $id);
        }
    }
    $recettes = array_values(array_filter(
        $recettes, fn($e) => ($e['id'] ?? '') !== $id));
    if (count($recettes) === $avant) {
        refuse($fh, 404, 'recette inconnue');
    }
    $quoi = 'supprime la recette « ' . $nom . ' »';
} elseif ($action === 'reglages') {
    $r = reglages_valides($demande['reglages'] ?? null);
    if ($r === null) {
        refuse($fh, 400, 'reglages invalides');
    }
    $reglages = $r;
    $quoi = 'change les réglages';
} else {
    refuse($fh, 400, 'action inconnue');
}

// Une sauvegarde avant d'ecrire, espacee : des mois de reglages ne doivent
// pas disparaitre sur une fausse manoeuvre.
if ($contenu !== '') {
    @mkdir(SAUVEGARDES, 0775, true);
    $vieilles = glob(SAUVEGARDES . '/mp-*.json') ?: [];
    sort($vieilles);
    $derniere = $vieilles ? filemtime((string) end($vieilles)) : 0;
    if (time() - (int) $derniere >= ECART_SAUVEGARDES) {
        @file_put_contents(SAUVEGARDES . '/mp-' . gmdate('Ymd-His') . '.json',
                           $contenu);
        $vieilles = glob(SAUVEGARDES . '/mp-*.json') ?: [];
        sort($vieilles);
        foreach (array_slice($vieilles, 0,
                             max(0, count($vieilles) - MAX_SAUVEGARDES)) as $v) {
            @unlink($v);
        }
    }
}

array_unshift($journal, ['quand' => gmdate('c'), 'qui' => $auteur, 'quoi' => $quoi]);
$journal = array_slice($journal, 0, MAX_JOURNAL);
$sortie = json_encode(['version' => 1, 'reglages' => $reglages,
                       'recettes' => array_values($recettes),
                       'journal' => $journal, 'maj' => gmdate('c')],
                      JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
ftruncate($fh, 0);
rewind($fh);
fwrite($fh, (string) $sortie);
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);
repond(200, ['ok' => true]);
