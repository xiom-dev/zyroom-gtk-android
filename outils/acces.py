"""Les mots de passe de xiom.be, en un seul endroit.

Une seule sorte d'accès, la même sur toutes les pages protégées (sommaire,
padui, forage, OP, applis de la Lune, MP du hall, ZyRoom web) : **le code
personnel** de chaque officier, officier supérieur et du chef de la guilde
(plus Luz et Cibou), dans ~/.config/zyroom/acces.codes ({joueur: code}).
Plus de mot de passe commun depuis le 02/11/2026 : il passait de main en main.

Le droit de déposer ses drapeaux sur PadUI est une autre liste, plus courte :
~/.config/zyroom/padui.deposants (outils/page-padui.py).

Les pages ne gardent qu'une empreinte par joueur (HMAC-SHA256 du code) : les
codes sont tirés au hasard, seize caractères, introuvables par essais ; pas
besoin de bcrypt, qui coûterait des secondes à trente joueurs. Et l'empreinte
dit **qui** entre : la porte le met dans le laissez-passer et le journal.

Donner, changer ou retirer un code : modifier acces.codes, relancer l'outil
de chaque page (page-index, page-padui, page-mp, page-op, page-forage),
redéposer ses fichiers PHP. Seul le joueur dont le code change est déconnecté.
"""

import hashlib
import hmac
import json
import os

SECRETS = os.path.expanduser("~/.config/zyroom")
CODES = os.path.join(SECRETS, "acces.codes")
# Fixed label of the HMAC: the same in PHP (PHP_VERIFIE).
EPICE = "xiom.be|acces|v1"


def codes() -> dict:
    """{joueur: code personnel}."""
    with open(CODES, encoding="utf-8") as f:
        return json.load(f)


def phrases() -> list:
    """Tout ce qui ouvre une page : les codes personnels."""
    return list(codes().values())


def empreinte(code: str) -> str:
    return hmac.new(EPICE.encode(), code.encode(), hashlib.sha256).hexdigest()


def php_empreintes(cout: int = 10, noms=None) -> str:
    """Le tableau PHP des empreintes, à coller dans un modèle :
    ['Joueur' => 'hex', ...].

    Avec noms, seulement les codes de ces joueurs : l'écriture du forage,
    réservée à trois d'entre eux. cout ne sert plus (ancien bcrypt), gardé
    pour les appels existants."""
    tous = codes()
    choisis = noms or list(tous)
    for n in choisis:
        if not n.isalnum():
            raise SystemExit(f"Nom de joueur illisible dans {CODES} : {n!r}")
    return "[" + ", ".join("'%s' => '%s'" % (n, empreinte(tous[n])) for n in choisis) + "]"


# The PHP functions that check a code against EMPREINTES. Every entry is
# always compared, so the time taken does not tell which one matched.
PHP_VERIFIE = """function mdp_qui(string $mdp): ?string
{
    if ($mdp === '' || strlen($mdp) > 200) {
        return null;
    }
    $e = hash_hmac('sha256', $mdp, 'xiom.be|acces|v1');
    $qui = null;
    foreach (EMPREINTES as $nom => $ref) {
        if (hash_equals($ref, $e)) {
            $qui = (string) $nom;
        }
    }
    return $qui;
}

function mdp_ok(string $mdp): bool
{
    return mdp_qui($mdp) !== null;
}
"""
