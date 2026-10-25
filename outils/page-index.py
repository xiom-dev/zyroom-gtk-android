#!/usr/bin/env python3
"""Écrit le garde du sommaire https://xiom.be/index/ (site-domaine/index/garde.php).

La porte principale du site : elle est plus dure que les autres pages.

- **Les mots de passe de tout le site** (outils/acces.py) : le code personnel
  des six joueurs de confiance, ou le mot de passe commun de la guilde.
  garde.php n'en garde que les empreintes bcrypt (coût 11).
- **Et la bonne réponse** à la question (QUESTION, CHOIX, REPONSE ci-dessous).
- **Essais limités par adresse** : 5 ratés en 15 min ferment la porte 15 min,
  puis le double à chaque nouvel échec, jusqu'à 24 h.
- **Cookie** `__Host-` (HTTPS, tout le domaine, inaccessible au JavaScript,
  jamais envoyé depuis un autre site), valable 7 jours. Il est signé avec le
  secret **et** les empreintes : changer un mot de passe déconnecte tout le monde.

    python3 outils/page-index.py                   réécrit garde.php
    python3 outils/page-index.py --nouveau-secret  déconnecte tout le monde

Puis déposer garde.php.
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
// On entre une fois, par l'accueil (code personnel ou mot de passe commun,
// et la question) : le navigateur recoit un laissez-passer de sept jours, que
// chaque page protegee verifie ici. Sans lui, retour a l'entree.
declare(strict_types=1);

const PORTE_CLE = '__CLE__';
// __Host- : le navigateur ne l'accepte qu'en HTTPS, pour tout le domaine et
// sans attribut Domain -- un sous-domaine ne peut ni le poser ni l'ecraser.
const PORTE_COOKIE = '__Host-xiom';
const PORTE_DUREE = 7 * 24 * 3600;

// Le laissez-passer : "echeance.signature" ; on ne peut ni l'inventer ni le
// prolonger.
function porte_signe(int $echeance): string
{
    return $echeance . '.' . hash_hmac('sha256', (string) $echeance, PORTE_CLE);
}

function porte_ouverte(): bool
{
    $valeur = (string) ($_COOKIE[PORTE_COOKIE] ?? '');
    $morceaux = explode('.', $valeur, 2);
    if (count($morceaux) !== 2 || !ctype_digit($morceaux[0])) {
        return false;
    }
    $echeance = (int) $morceaux[0];
    return $echeance > time() && $echeance <= time() + PORTE_DUREE
        && hash_equals(porte_signe($echeance), $valeur);
}

function porte_ouvrir(): void
{
    $echeance = time() + PORTE_DUREE;
    setcookie(PORTE_COOKIE, porte_signe($echeance), [
        'expires' => $echeance, 'path' => '/', 'secure' => true,
        'httponly' => true, 'samesite' => 'Lax',
    ]);
}

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
    # PHP lit les empreintes $2y$, bcrypt en Python rend $2b$ : même calcul.
    empreintes = acces.php_empreintes(11)
    question = "'" + QUESTION.replace("'", "\\'") + "'"
    choix = "[" + ", ".join("'%s'" % c for c in CHOIX) + "]"
    reponse = "'%s'" % REPONSE
    php = f"""<?php
// Le garde de https://xiom.be/index/ : ecrit par outils/page-index.py, ne pas
// modifier a la main. Inclus par index.php ; le .htaccess en refuse la
// lecture directe.
//
// Les empreintes des mots de passe (bcrypt), et le secret qui signe le cookie
// d'entree. Le mot de passe en clair n'est jamais monte ici.
declare(strict_types=1);
require __DIR__ . '/porte.php';
// Les empreintes de tout ce qui ouvre la porte : les six codes personnels et
// le mot de passe commun (outils/acces.py).
const EMPREINTES = {{empreintes}};
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

function ouvrir(): void
{{
    porte_ouvrir();
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
    cle_porte = hashlib.sha256((sel + "|" + empreintes).encode()).hexdigest()
    with open(PORTE, "w", encoding="utf-8") as f:
        f.write(PORTE_PHP.replace("__CLE__", cle_porte))
    with open(GARDE, "w", encoding="utf-8") as f:
        f.write(php)
    print(f"{GARDE} écrit (codes et mot de passe commun : outils/acces.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
