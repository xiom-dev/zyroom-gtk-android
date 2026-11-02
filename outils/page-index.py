#!/usr/bin/env python3
"""Écrit le garde du sommaire https://xiom.be/index/ (site-domaine/index/garde.php).

La porte principale du site : elle est plus dure que les autres pages.

- **Un code personnel par joueur** (outils/acces.py) : officiers, officiers
  supérieurs et chef de la guilde. Plus de mot de passe commun (02/11/2026).
  garde.php et porte.php n'en gardent qu'une empreinte par joueur.
- **Et la bonne réponse** à la question (QUESTION, CHOIX, REPONSE ci-dessous).
- **Essais limités par adresse** : 5 ratés en 15 min ferment la porte 15 min,
  puis le double à chaque nouvel échec, jusqu'à 24 h.
- **Cookie** `__Host-` (HTTPS, tout le domaine, inaccessible au JavaScript,
  jamais envoyé depuis un autre site), valable 7 jours, **au nom du joueur** et
  signé avec l'empreinte de son code : changer un code ne déconnecte que lui.
- **Le journal** (index/journal/) : par jour et par code, de combien de
  réseaux différents il sert. À 4 réseaux un même jour, le sommaire prévient
  Xiom : le code a peut-être été donné. Xiom voit le tableau sur /index/?journal.

    python3 outils/page-index.py                   réécrit garde.php et porte.php
    python3 outils/page-index.py --nouveau-secret  déconnecte tout le monde

Puis déposer garde.php et porte.php.
"""

import hashlib
import os
import re
import secrets
import sys

import acces

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GARDE = os.path.join(RACINE, "site-domaine", "index", "garde.php")
PORTE = os.path.join(RACINE, "site-domaine", "index", "porte.php")
SECRETS = os.path.expanduser("~/.config/zyroom")
# La question posee avec le mot de passe, ses trois choix, et le bon.
QUESTION = "Quel est l'animal que je déteste ?"
CHOIX = ("hamster", "dragon", "chat")
REPONSE = "chat"
# La porte de tout le site, incluse par chaque page protegee : elle verifie le
# laissez-passer pose a l'entree (index.php) et renvoie a l'entree sans lui.
PORTE_PHP = """<?php
// La porte de tout xiom.be : ecrite par outils/page-index.py, ne pas modifier
// a la main. Le .htaccess de index/ en refuse la lecture directe.
//
// On entre une fois, par l'accueil (son code personnel et la question) : le
// navigateur recoit un laissez-passer de sept jours, a son nom, que chaque
// page protegee verifie ici. Sans lui, retour a l'entree.
declare(strict_types=1);

const PORTE_CLE = '__CLE__';
// __Host- : le navigateur ne l'accepte qu'en HTTPS, pour tout le domaine et
// sans attribut Domain -- un sous-domaine ne peut ni le poser ni l'ecraser.
const PORTE_COOKIE = '__Host-xiom';
const PORTE_DUREE = 7 * 24 * 3600;
// Les empreintes des codes personnels, par joueur (outils/acces.py). Le
// laissez-passer est signe avec celle de son joueur : changer un code ne
// deconnecte que lui.
const PORTE_CODES = __CODES__;
// Le journal : par jour et par code, les reseaux (adresse IPv4 en /24, IPv6
// en /48) d'ou il sert, en empreintes. Au-dela de PORTE_SEUIL reseaux un
// meme jour, le sommaire previent PORTE_ADMIN : le code a peut-etre ete donne.
const PORTE_JOURNAL = __DIR__ . '/journal';
const PORTE_SEUIL = 4;
const PORTE_ADMIN = 'Xiom';
const PORTE_GARDE_JOURS = 30;

// Le laissez-passer : "echeance.joueur.signature" ; on ne peut ni l'inventer,
// ni le prolonger, ni changer de nom.
function porte_signe(int $echeance, string $nom): string
{
    $code = PORTE_CODES[$nom] ?? '';
    return $echeance . '.' . $nom . '.'
        . hash_hmac('sha256', $echeance . '|' . $nom . '|' . $code, PORTE_CLE);
}

// Le joueur du laissez-passer, ou null.
function porte_nom(): ?string
{
    static $nom = false;
    if ($nom !== false) {
        return $nom;
    }
    $nom = null;
    $valeur = (string) ($_COOKIE[PORTE_COOKIE] ?? '');
    $morceaux = explode('.', $valeur, 3);
    if (count($morceaux) !== 3 || !ctype_digit($morceaux[0]) || !ctype_alnum($morceaux[1])
        || !isset(PORTE_CODES[$morceaux[1]])) {
        return null;
    }
    $echeance = (int) $morceaux[0];
    if ($echeance > time() && $echeance <= time() + PORTE_DUREE
        && hash_equals(porte_signe($echeance, $morceaux[1]), $valeur)) {
        $nom = $morceaux[1];
        porte_note($nom);
    }
    return $nom;
}

function porte_ouverte(): bool
{
    return porte_nom() !== null;
}

function porte_ouvrir(string $nom): void
{
    $echeance = time() + PORTE_DUREE;
    setcookie(PORTE_COOKIE, porte_signe($echeance, $nom), [
        'expires' => $echeance, 'path' => '/', 'secure' => true,
        'httponly' => true, 'samesite' => 'Lax',
    ]);
    porte_note($nom);
}

// ------------------------------------------------------------- le journal

// Le reseau de l'adresse, en empreinte : l'adresse n'est jamais ecrite.
function porte_reseau(): string
{
    $ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '?');
    $bin = @inet_pton($ip);
    if ($bin !== false) {
        $bin = strlen($bin) === 4 ? substr($bin, 0, 3) : substr($bin, 0, 6);
        $ip = bin2hex($bin);
    }
    return substr(hash_hmac('sha256', 'reseau|' . $ip, PORTE_CLE), 0, 16);
}

function porte_fichier_jour(int $t): string
{
    return PORTE_JOURNAL . '/' . gmdate('Y-m-d', $t) . '.json';
}

function porte_lire_jour(int $t): array
{
    $lu = @json_decode((string) @file_get_contents(porte_fichier_jour($t)), true);
    return is_array($lu) ? $lu : [];
}

// Note le reseau du joueur pour aujourd'hui ; n'ecrit que s'il est nouveau.
function porte_note(string $nom): void
{
    $t = time();
    $r = porte_reseau();
    $jour = porte_lire_jour($t);
    if (in_array($r, $jour[$nom] ?? [], true)) {
        return;
    }
    if (!is_dir(PORTE_JOURNAL)) {
        @mkdir(PORTE_JOURNAL, 0700, true);
        @file_put_contents(PORTE_JOURNAL . '/.htaccess', "Require all denied\\n");
    }
    $f = @fopen(porte_fichier_jour($t), 'c+');
    if ($f === false) {
        return;
    }
    if (flock($f, LOCK_EX)) {
        $jour = json_decode((string) stream_get_contents($f), true);
        $jour = is_array($jour) ? $jour : [];
        if (!in_array($r, $jour[$nom] ?? [], true)) {
            $jour[$nom][] = $r;
            ftruncate($f, 0);
            rewind($f);
            fwrite($f, json_encode($jour));
        }
        flock($f, LOCK_UN);
    }
    fclose($f);
    // Le menage : les jours de plus d'un mois s'en vont.
    if (random_int(1, 50) === 1) {
        foreach (glob(PORTE_JOURNAL . '/*.json') ?: [] as $g) {
            if (@filemtime($g) < $t - PORTE_GARDE_JOURS * 24 * 3600) {
                @unlink($g);
            }
        }
    }
}

// Les jours recents : [jour => [joueur => nombre de reseaux]], le plus recent
// en premier.
function porte_journal(int $jours = 7): array
{
    $t = time();
    $sortie = [];
    for ($i = 0; $i < $jours; $i++) {
        $u = $t - $i * 24 * 3600;
        $sortie[gmdate('Y-m-d', $u)] = array_map('count', porte_lire_jour($u));
    }
    return $sortie;
}

// Les alertes : [[jour, joueur, reseaux]] au-dela du seuil.
function porte_alertes(int $jours = 7): array
{
    $alertes = [];
    foreach (porte_journal($jours) as $jour => $noms) {
        foreach ($noms as $nom => $n) {
            if ($n >= PORTE_SEUIL) {
                $alertes[] = [$jour, (string) $nom, $n];
            }
        }
    }
    return $alertes;
}

// ------------------------------------------------------------- les pages

// Sans laissez-passer : une page renvoie a l'entree (qui ramene ici une fois
// entre), une API repond 401.
function porte_exige(bool $api = false): void
{
    if (porte_ouverte()) {
        return;
    }
    header('Cache-Control: no-store');
    if ($api) {
        http_response_code(401);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['erreur' => 'entree']);
        exit;
    }
    header('Location: /?retour=' . rawurlencode((string) ($_SERVER['REQUEST_URI'] ?? '/index/')), true, 303);
    exit;
}

// Une page statique derriere la porte : entree.php de son dossier la sert.
function porte_page(string $chemin): void
{
    porte_exige();
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-cache, must-revalidate');
    header('X-Robots-Tag: noindex, nofollow');
    readfile($chemin);
    exit;
}
"""


def main() -> int:
    # Le secret du cookie : gardé d'une fois sur l'autre, sauf demande.
    sel = None
    if os.path.isfile(GARDE) and "--nouveau-secret" not in sys.argv:
        m = re.search(r"const SEL = '([0-9a-f]+)';", open(GARDE, encoding="utf-8").read())
        sel = m.group(1) if m else None
    sel = sel or secrets.token_hex(24)
    # Une empreinte par joueur (outils/acces.py) : la porte sait qui entre.
    empreintes = acces.php_empreintes()
    question = "'" + QUESTION.replace("'", "\\'") + "'"
    choix = "[" + ", ".join("'%s'" % c for c in CHOIX) + "]"
    reponse = "'%s'" % REPONSE
    php = f"""<?php
// Le garde de https://xiom.be/index/ : ecrit par outils/page-index.py, ne pas
// modifier a la main. Inclus par index.php ; le .htaccess en refuse la
// lecture directe.
//
// Les empreintes des codes personnels, et le secret qui signe le cookie
// d'entree. Aucun code en clair n'est monte ici.
declare(strict_types=1);
require __DIR__ . '/porte.php';
// Les empreintes de ce qui ouvre la porte : un code personnel par joueur
// (outils/acces.py). Plus de mot de passe commun.
const EMPREINTES = PORTE_CODES;
const SEL = '{{sel}}';
// La question du formulaire, ses choix, et la bonne reponse.
const QUESTION = {{question}};
const CHOIX = {{choix}};
const REPONSE = {{reponse}};
// Essais : 5 rates en 15 min ferment 15 min, puis le double a chaque echec.
const ESSAIS = __DIR__ . '/essais';
const ESSAIS_MAX = 5;
const FENETRE = 15 * 60;
const BLOCAGE = 15 * 60;
const BLOCAGE_MAX = 24 * 3600;

__VERIFIE__
// Le laissez-passer de tout le site (porte.php) : entre() et ouvrir() pour
// index.php.
function entre(): bool
{{
    return porte_ouverte();
}}

function ouvrir(string $nom): void
{{
    porte_ouvrir($nom);
}}

// ------------------------------------------------------------- les essais
// Un fichier par adresse, nomme par son empreinte (l'adresse n'est pas
// ecrite en clair) : {{"rates": [horodatages], "jusqu": fin du blocage, "n": blocages}}.

function fichier_essais(): string
{{
    if (!is_dir(ESSAIS)) {{
        @mkdir(ESSAIS, 0700, true);
        @file_put_contents(ESSAIS . '/.htaccess', "Require all denied\n");
    }}
    $ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '?');
    return ESSAIS . '/' . hash_hmac('sha256', $ip, SEL) . '.json';
}}

function lire_essais(): array
{{
    $lu = @json_decode((string) @file_get_contents(fichier_essais()), true);
    return is_array($lu) ? $lu + ['rates' => [], 'jusqu' => 0, 'n' => 0] : ['rates' => [], 'jusqu' => 0, 'n' => 0];
}}

// Secondes avant de pouvoir reessayer ; 0 si la porte est ouverte.
function bloque(): int
{{
    return max(0, (int) lire_essais()['jusqu'] - time());
}}

function rate(): void
{{
    $e = lire_essais();
    $t = time();
    $e['rates'] = array_values(array_filter($e['rates'], fn($r) => $r > $t - FENETRE));
    $e['rates'][] = $t;
    if (count($e['rates']) >= ESSAIS_MAX) {{
        $e['jusqu'] = $t + min(BLOCAGE_MAX, BLOCAGE * (2 ** min(10, (int) $e['n'])));
        $e['n'] = (int) $e['n'] + 1;
        $e['rates'] = [];
    }}
    @file_put_contents(fichier_essais(), json_encode($e), LOCK_EX);
    // Le menage : les traces de plus de deux jours s'en vont.
    if (random_int(1, 50) === 1) {{
        foreach (glob(ESSAIS . '/*.json') ?: [] as $f) {{
            if (@filemtime($f) < $t - 2 * 24 * 3600) {{
                @unlink($f);
            }}
        }}
    }}
}}

function reussi(): void
{{
    @unlink(fichier_essais());
}}
"""
    php = php.replace("{empreintes}", empreintes).replace("__VERIFIE__", acces.PHP_VERIFIE).replace("{sel}", sel).replace(
        "{question}", question).replace("{choix}", choix).replace("{reponse}", reponse)
    # La porte de tout le site : la cle du laissez-passer tient au secret et
    # aux empreintes -- un nouveau mot de passe le retire a tout le monde.
    # La cle ne tient plus qu'au secret : chaque laissez-passer est signe avec
    # l'empreinte de son joueur, un code change ne deconnecte que lui.
    cle_porte = hashlib.sha256((sel + "|porte-v2").encode()).hexdigest()
    with open(PORTE, "w", encoding="utf-8") as f:
        f.write(PORTE_PHP.replace("__CLE__", cle_porte).replace("__CODES__", empreintes))
    with open(GARDE, "w", encoding="utf-8") as f:
        f.write(php)
    print(f"{GARDE} et porte.php écrits ({len(acces.codes())} codes personnels : outils/acces.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
