"""Les mots de passe de xiom.be, en un seul endroit.

Deux sortes d'accès, les mêmes sur toutes les pages protégées (sommaire,
padui, forage, OP, applis de la Lune, MP du hall, ZyRoom web) :

- **le code personnel** des six joueurs de confiance (Xiom, Yamaa, Yzatis,
  Thysela, Arudy, Azileth) : ~/.config/zyroom/padui.deposants, écrit par
  outils/page-padui.py. Le même sert à déposer ses drapeaux ;
- **le mot de passe commun** des autres joueurs de la guilde :
  ~/.config/zyroom/commun.motdepasse.

Les pages ne gardent que les empreintes bcrypt (EMPREINTES) et essaient
chacune. Changer un code ou le mot de passe commun : modifier le fichier,
relancer l'outil de chaque page, redéposer ses fichiers PHP.
"""

import json
import os

import bcrypt

SECRETS = os.path.expanduser("~/.config/zyroom")
CODES = os.path.join(SECRETS, "padui.deposants")
COMMUN = os.path.join(SECRETS, "commun.motdepasse")


def codes() -> dict:
    """{joueur: code personnel}."""
    with open(CODES, encoding="utf-8") as f:
        return json.load(f)


def commun() -> str:
    with open(COMMUN, encoding="utf-8") as f:
        return f.read().strip()


def phrases() -> list:
    """Tout ce qui ouvre une page : les six codes, puis le mot de passe commun."""
    return list(codes().values()) + [commun()]


def empreintes(cout: int = 10) -> list:
    """Les empreintes bcrypt ($2y$, lues par PHP) de chaque phrase.

    Coût 10 et non 12 : une page en essaie jusqu'à sept, il faut que le
    tout reste sous la seconde.
    """
    return ["$2y$" + bcrypt.hashpw(p.encode(), bcrypt.gensalt(cout)).decode()[4:] for p in phrases()]


def php_empreintes(cout: int = 10, noms=None) -> str:
    """Le tableau PHP des empreintes, à coller dans un modèle : ['$2y$...', ...].

    Avec noms, seulement les codes personnels de ces joueurs (sans le mot de
    passe commun) : l'écriture du forage, réservée à trois d'entre eux."""
    phrases_ = [codes()[n] for n in noms] if noms else phrases()
    return "[" + ", ".join("'$2y$%s'" % bcrypt.hashpw(p.encode(), bcrypt.gensalt(cout)).decode()[4:]
                           for p in phrases_) + "]"


# La fonction PHP qui essaie chaque empreinte. Toutes sont toujours essayées,
# pour que la durée ne dise pas laquelle a réussi.
PHP_VERIFIE = """function mdp_ok(string $mdp): bool
{
    if (strlen($mdp) > 200) {
        return false;
    }
    $ok = false;
    foreach (EMPREINTES as $e) {
        $ok = password_verify($mdp, $e) || $ok;
    }
    return $ok;
}
"""
