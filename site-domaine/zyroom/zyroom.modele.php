<?php
// Le hall de guilde pour la version web de ZyRoom (xiom.be/zyroom).
//
// MODELE : versionne sans secret. `outils/page-zyroom.py` y met la cle API
// de la guilde, le sel des jetons et la liste des editeurs, et ecrit
// `zyroom.php` -- le seul a deposer, et le seul que git ignore.
//
// **La cle de la guilde ne quitte pas le serveur.** Les joueurs ne l'ont
// pas : c'est ce fichier qui interroge l'API pour eux et ne rend le flux
// qu'a un membre connecte (Ludo, 10 octobre 2026).
//
// **La meme porte que la page des MP.** Le jeton est celui de mp.php, signe
// avec le meme sel : se connecter sur l'une ouvre l'autre. Un joueur doit
// etre dans l'effectif de la guilde, un editeur dans la liste.
//
// **La cle ne part pas non plus.** L'API la recopie dans le flux, en
// attribut `apikey` : on la retire, et un flux qui la porterait encore n'est
// pas envoye.
//
// **Le coffre masque ne part pas.** L'application montre le petit coffre de
// Nizy vide, mais son contenu voyage dans le flux et dort dans le cache de
// qui a la cle. Ici, le flux part chez chaque membre : on en retire donc les
// objets avant l'envoi.
declare(strict_types=1);

// Les cles API des guildes servies, par numero de guilde (JSON).
const CLES = '__CLES__';
const SEL = '__SEL__';
const EDITEURS = '__EDITEURS__';
// La guilde dont l'effectif ouvre la porte : La Lune Eternelle. Rod of Heaven,
// la guilde des alts, se consulte mais ne donne pas acces.
const GUILDE = 105906237;
const API = 'https://api.ryzom.com/guild.php?apikey=';
const STATUT = 'https://app.ryzom.com/app_arcc/get_services_status.php?command=status&shard=atys';
const DEPOT = 'https://raw.githubusercontent.com/xiom-dev/zyroom-gtk-android/journaux/';
const CACHE = __DIR__ . '/cache';
// L'API ne recalcule pas plus vite que ca : cinq minutes suffisent, et
// trente membres qui ouvrent la page ne font qu'un appel.
const CACHE_DUREE = 5 * 60;
// Comme ryzom_api._HIDDEN_CHESTS : un fragment du nom, compare sans
// accents ni majuscules.
const COFFRES_MASQUES = ['petit coffre de nizy'];
// Comme ryzom_api._CHEST_SEGMENT_SIZE : le coffre i tient les cases
// [i*500, i*500+499] de la salle.
const TRANCHE = 500;

header('Cache-Control: no-store');

function refuse(int $code, string $erreur): never
{
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['erreur' => $erreur], JSON_UNESCAPED_UNICODE);
    exit;
}

// ------------------------------------------------------------- le jeton
//
// Meme forme et meme signature que dans mp.modele.php ; qui change l'un
// change l'autre.

function b64(string $s): string
{
    return rtrim(strtr(base64_encode($s), '+/', '-_'), '=');
}

function jeton(string $nom, string $role, int $expire): string
{
    $tete = b64($nom) . '.' . $role . '.' . $expire;
    return $tete . '.' . hash_hmac('sha256', $tete, SEL);
}

function porteur(): ?string
{
    $recu = (string) ($_SERVER['HTTP_X_MP'] ?? '');
    $morceaux = explode('.', $recu);
    if (count($morceaux) !== 4 || !in_array($morceaux[1], ['e', 'j'], true)
        || !preg_match('/^[0-9]{1,12}$/', $morceaux[2]) || (int) $morceaux[2] < time()) {
        return null;
    }
    $nom = (string) base64_decode(strtr($morceaux[0], '-_', '+/'), true);
    if ($nom === '' || !hash_equals(jeton($nom, $morceaux[1], (int) $morceaux[2]), $recu)) {
        return null;
    }
    if ($morceaux[1] === 'e') {
        $editeurs = json_decode(EDITEURS, true);
        return (is_array($editeurs) && in_array($nom, $editeurs, true)) ? $nom : null;
    }
    // Un effectif illisible ne ferme pas la porte a qui l'a deja passee.
    $effectif = effectif();
    if ($effectif === null) {
        return $nom;
    }
    foreach (array_keys($effectif) as $connu) {
        if (strcasecmp((string) $connu, trim($nom)) === 0) {
            return $nom;
        }
    }
    return null;
}

function effectif(): ?array
{
    $local = CACHE . '/roster.json';
    if (is_file($local) && time() - (int) filemtime($local) < CACHE_DUREE) {
        $lu = json_decode((string) file_get_contents($local), true);
        return is_array($lu) ? $lu : null;
    }
    $brut = @file_get_contents(DEPOT . 'roster-' . GUILDE . '.json', false,
                               stream_context_create(['http' => ['timeout' => 10]]));
    $lu = $brut !== false ? json_decode($brut, true) : null;
    if (is_array($lu)) {
        @mkdir(CACHE, 0775, true);
        @file_put_contents($local, $brut);
        return $lu;
    }
    if (is_file($local)) {
        $lu = json_decode((string) file_get_contents($local), true);
        return is_array($lu) ? $lu : null;
    }
    return null;
}

// ------------------------------------------------------------- le flux

function plat(string $s): string
{
    $s = (string) iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $s);
    return trim((string) preg_replace('/\s+/', ' ', strtolower($s)));
}

// Les accents que l'API rend en UTF-8 relu comme du latin-1 (voir
// ryzom_api.repare_accents).
function repare(string $s): string
{
    $octets = @mb_convert_encoding($s, 'ISO-8859-1', 'UTF-8');
    return ($octets !== false && mb_check_encoding($octets, 'UTF-8')) ? $octets : $s;
}

// Ce qui ne doit pas partir chez les membres : la cle de la guilde, que
// l'API recopie dans un attribut `apikey`, et les objets des coffres masques.
// Un flux qu'on ne sait pas lire ne part pas du tout : il porte la cle.
function nettoie(string $xml): ?string
{
    $doc = new DOMDocument();
    if (!@$doc->loadXML($xml)) {
        return null;
    }
    $xp = new DOMXPath($doc);
    foreach (iterator_to_array($xp->query('//@apikey')) as $attribut) {
        $attribut->ownerElement->removeAttributeNode($attribut);
    }
    $masques = [];
    foreach ($xp->query('/*/guild/chests/chest') as $i => $coffre) {
        $nom = plat(repare((string) $xp->evaluate('string(name)', $coffre)));
        foreach (COFFRES_MASQUES as $fragment) {
            if ($nom !== '' && str_contains($nom, $fragment)) {
                $masques[] = $i;
            }
        }
    }
    if (!$masques) {
        return (string) $doc->saveXML();
    }
    foreach (iterator_to_array($xp->query('/*/guild/room/item')) as $objet) {
        $case = (int) $objet->getAttribute('slot');
        if (in_array(intdiv($case, TRANCHE), $masques, true)) {
            $objet->parentNode->removeChild($objet);
        }
    }
    return (string) $doc->saveXML();
}

function cles(): array
{
    $cles = json_decode(CLES, true);
    return is_array($cles) ? $cles : [];
}

function flux(string $id, string $cle): string
{
    $local = CACHE . '/guilde-' . $id . '.xml';
    if (is_file($local) && time() - (int) filemtime($local) < CACHE_DUREE) {
        return (string) file_get_contents($local);
    }
    $brut = @file_get_contents(API . $cle, false,
                               stream_context_create(['http' => ['timeout' => 20]]));
    $propre = ($brut !== false && str_contains($brut, '<guild') && !str_contains($brut, '<error'))
        ? nettoie($brut) : null;
    if ($propre !== null && !str_contains($propre, $cle)) {
        @mkdir(CACHE, 0775, true);
        @file_put_contents($local, $propre);
        return $propre;
    }
    // API injoignable : la derniere copie vaut mieux que rien.
    if (is_file($local)) {
        return (string) file_get_contents($local);
    }
    refuse(502, "l'API Ryzom ne répond pas");
}

// ------------------------------------------------------------- la requete

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    refuse(405, 'GET seulement');
}
if (porteur() === null) {
    refuse(401, 'connexion requise');
}
// L'etat du serveur, que lit Ryztart : le serveur de Ryzom ne laisse pas une
// page web le lire elle-meme (pas d'en-tete CORS).
if (($_GET['quoi'] ?? '') === 'statut') {
    $local = CACHE . '/statut.json';
    if (!is_file($local) || time() - (int) filemtime($local) >= CACHE_DUREE) {
        $brut = @file_get_contents(STATUT, false, stream_context_create(['http' => ['timeout' => 10]]));
        if ($brut !== false && is_array(json_decode($brut, true))) {
            @mkdir(CACHE, 0775, true);
            @file_put_contents($local, $brut);
        }
    }
    header('Content-Type: application/json; charset=utf-8');
    echo is_file($local) ? (string) file_get_contents($local) : '[]';
    exit;
}
// La guilde demandee, La Lune par defaut ; seulement celles dont on a la cle.
$id = (string) ($_GET['guilde'] ?? GUILDE);
$cle = cles()[$id] ?? null;
if ($cle === null) {
    refuse(404, 'guilde inconnue');
}
$xml = flux($id, $cle);
header('Content-Type: application/xml; charset=utf-8');
// La date du fichier : la page la montre comme heure de synchro.
$local = CACHE . '/guilde-' . $id . '.xml';
if (is_file($local)) {
    header('X-Releve: ' . filemtime($local));
}
echo $xml;
