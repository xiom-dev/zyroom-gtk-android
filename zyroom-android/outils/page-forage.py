#!/usr/bin/env python3
"""Fabrique la page de relevé du forage pour xiom.be/forage.

Le classeur de la guilde porte un onglet vierge en **six** bandes d'humidité —
Worst, Bad2, Bad1, Good1, Good2, Best. Les relevés déjà faits montrent que Bad1
vaut toujours Bad2 et Good1 toujours Good2 : huit cent trente-six paires, sans
une exception. Les deux moitiés sont donc réunies ici, ce qui ramène le tableau
à **quatre colonnes par saison**, celles que le jeu rend lui-même — et divise
par deux le nombre de cases à cocher sur le terrain.

La page se coche d'un clic : vide → `x` (ça sort) → `−` (ça ne sort pas) →
vide, et **tout le monde voit les croix de tout le monde** — le relevé vit sur
le serveur, dans un fichier JSON que `releve.php` tient à jour.

**Lecture libre, écriture sur adresse secrète.** Sans clef dans l'adresse, la
page se lit et ne se coche pas. Avec `?k=…`, elle devient inscriptible. La clef
est gardée dans `~/.config/zyroom/forage.cle`, hors du dépôt, et recopiée dans
`releve.php` — que le serveur exécute, et ne montre donc jamais. Si elle fuite,
on en tire une autre et l'ancienne ne vaut plus rien.

Chaque croix porte le nom de la foreuse : sur un tableau rempli à plusieurs sur
des mois, savoir à qui demander vaut cher le jour où deux relevés se
contredisent.

    python3 outils/page-forage.py

Trois fichiers sont écrits dans `site-domaine/forage/`, à monter tels quels :
`index.html`, `releve.php` et `.htaccess`. Le fichier de données et ses
sauvegardes, PHP les crée tout seul.

**Rien de tout cela n'est écrit sur la page.** Les foreuses ne suivent pas le
développement : pourquoi les colonnes ont été réunies, où sont gardées les
croix, comment on fusionne deux relevés — ce sont des explications d'auteur, et
trop d'information tue l'information. La page dit comment cocher, et s'arrête.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from table_forage import CLASSEUR, feuilles                      # noqa: E402

_ANDROID = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPOT = os.path.dirname(_ANDROID)
CIBLE = os.path.join(_DEPOT, "site-domaine", "forage", "index.html")

#: La clef d'ecriture. Hors du depot, comme le jeton du tracker : elle finit
#: recopiee dans `releve.php`, que le serveur execute et ne montre jamais.
CLE_FICHIER = os.path.expanduser("~/.config/zyroom/forage.cle")

ONGLET = "Original vierge"
SAISONS = ("Printemps", "Été", "Automne", "Hiver")

#: Les quatre zones des Primes. Le classeur leur donne un onglet chacune, et
#: elles ne sortent pas les memes matieres au meme moment -- c'est meme tout
#: l'interet du releve. Une page sans elles ne voulait rien dire.
ZONES = ("Sources Interdites", "Terre de la Continuité",
         "Cité Engloutie", "Profondeurs Interdites")

#: Les quatre conditions du jeu, avec la fourchette d'humidite que le tracker
#: affiche. Le nom anglais est garde : c'est celui du classeur et du tracker,
#: donc celui que les foreuses ont sous les yeux.
CONDITIONS = (("Exécrable", "Worst", "84 – 100 %"),
              ("Mauvaise", "Bad", "50 – 83 %"),
              ("Bonne", "Good", "17 – 49 %"),
              ("Excellente", "Best", "0 – 16 %"))

QUALITES = ("Supp", "XL", "Choix")


def clef() -> str:
    """La clef d'écriture, lue une fois pour toutes."""
    if not os.path.isfile(CLE_FICHIER):
        raise SystemExit(
            f"Clef absente : {CLE_FICHIER}\n"
            "En tirer une : python3 -c \"import secrets; "
            "print('forage-' + secrets.token_hex(6))\" > " + CLE_FICHIER)
    with open(CLE_FICHIER, encoding="utf-8") as fh:
        return fh.read().strip()


def catalogue() -> list:
    """[(famille, [matières])] — dans l'ordre exact de l'onglet vierge."""
    familles: list = []
    for ligne in feuilles(CLASSEUR)[ONGLET]:
        ligne = (list(ligne) + [""] * 26)[:26]
        nom, qualite = ligne[0].strip(), ligne[1].strip()
        if nom and "/" in nom and not qualite:
            familles.append((nom, []))
        elif qualite == "Choix" and nom and familles:
            familles[-1][1].append(nom)
    return familles


def grille(familles: list) -> str:
    """Le tableau d'une saison : familles, matières, trois qualités."""
    lignes = []
    for rang_famille, (famille, matieres) in enumerate(familles):
        # Les quatre conditions redites sur la ligne jaune de chaque famille.
        # Le tableau fait cent quarante et une lignes : meme avec l'en-tete
        # colle en haut, on perd la colonne ou l'on vise en descendant.
        # La premiere famille n'en a pas besoin : le vrai en-tete est juste
        # au-dessus d'elle, et le redire ferait deux lignes identiques collees.
        if rang_famille == 0:
            lignes.append(f'<tr class="famille"><th colspan="6">'
                          f'{html.escape(famille)}</th></tr>')
        else:
            lignes.append(
                f'<tr class="famille"><th colspan="2">{html.escape(famille)}'
                f'</th>'
                + "".join(f'<th class="rappel">{fr}</th>'
                          for fr, _c, _p in CONDITIONS)
                + "</tr>")
        for matiere in matieres:
            # Le « ² » du classeur marquait les matieres a stocker en priorite
            # pour le GH. On le retire : ces listes datent de 2009 et une partie
            # n'est plus vraie, et de toute facon cela n'aide pas a remplir le
            # tableau -- qui est le seul but de cette page.
            propre = matiere.replace("²", "").strip()
            for rang, qualite in enumerate(QUALITES):
                cles = "".join(
                    f'<td class="case" data-cle="{html.escape(propre)}|{qualite}'
                    f'|{court}"></td>'
                    for _fr, court, _plage in CONDITIONS)
                if rang == 0:
                    debut = (f'<th class="matiere" rowspan="3">'
                             f'{html.escape(propre)}</th>')
                else:
                    debut = ""
                lignes.append(f'<tr class="q-{qualite.lower()}">{debut}'
                              f'<th class="qualite">{qualite}</th>{cles}</tr>')
    return "\n".join(lignes)



PHP = """<?php
// Le releve commun du forage des Primes, tenu dans un simple fichier JSON.
//
// GET  : rend l'etat entier. Lecture libre.
// POST : une case a la fois, et seulement avec la bonne clef.
//
// Pourquoi un fichier et pas une base : le releve tient en quelques dizaines
// de kilooctets, il s'ouvre dans un editeur de texte le jour ou quelque chose
// cloche, et il se sauvegarde en le recopiant. Une base pour cela couterait
// plus d'ennuis qu'elle n'en eviterait.
declare(strict_types=1);

const CLE = '__CLE__';
const FICHIER = __DIR__ . '/releve.json';
const SAUVEGARDES = __DIR__ . '/sauvegardes';
const MAX_SAUVEGARDES = 60;
const MAX_CORPS = 4096;

// Ce qu'une case a le droit d'etre. On valide contre ces listes plutot que
// contre une expression : une cle inventee n'entrera pas dans le fichier, et
// le relever se lit encore dans six mois.
const ZONES = __ZONES__;
const SAISONS = __SAISONS__;
const QUALITES = __QUALITES__;
const CONDITIONS = __CONDITIONS__;
const MATIERES = __MATIERES__;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function etat(): array
{
    if (!is_file(FICHIER)) {
        return ['cases' => (object) [], 'maj' => null];
    }
    $lu = json_decode((string) file_get_contents(FICHIER), true);
    if (!is_array($lu) || !isset($lu['cases']) || !is_array($lu['cases'])) {
        return ['cases' => (object) [], 'maj' => null];
    }
    return ['cases' => (object) $lu['cases'], 'maj' => $lu['maj'] ?? null];
}

function repond(int $code, array $corps): never
{
    http_response_code($code);
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    repond(200, etat());
}

$brut = (string) file_get_contents('php://input', false, null, 0, MAX_CORPS);
$demande = json_decode($brut, true);
if (!is_array($demande)) {
    repond(400, ['erreur' => 'requete illisible']);
}
// hash_equals plutot que == : la comparaison ne doit pas fuir la clef par le
// temps qu'elle met a echouer.
if (!hash_equals(CLE, (string) ($demande['cle'] ?? ''))) {
    repond(403, ['erreur' => 'clef']);
}

$case = (string) ($demande['case'] ?? '');
$valeur = (string) ($demande['valeur'] ?? '');
$foreuse = trim((string) ($demande['foreuse'] ?? ''));
// Ni mbstring ni substr : l'un n'est pas garanti sur tous les hebergements,
// l'autre couperait un caractere accentue en deux. PCRE en mode /u fait
// les deux -- ne garder que des lettres, puis s'arreter a vingt-quatre.
$foreuse = (string) preg_replace('/[^\\p{L}\\p{N} \\-\\']/u', '', $foreuse);
$foreuse = (string) preg_replace('/^(.{0,24}).*$/us', '$1', $foreuse);

$morceaux = explode('|', $case);
if (count($morceaux) !== 5
    || !in_array($morceaux[0], ZONES, true)
    || !in_array($morceaux[1], SAISONS, true)
    || !in_array($morceaux[2], MATIERES, true)
    || !in_array($morceaux[3], QUALITES, true)
    || !in_array($morceaux[4], CONDITIONS, true)) {
    repond(400, ['erreur' => 'case inconnue']);
}
if (!in_array($valeur, ['x', '-', ''], true)) {
    repond(400, ['erreur' => 'valeur inconnue']);
}

// Le verrou tient le temps de lire, modifier et reecrire : deux foreuses qui
// cochent dans la meme seconde ne doivent pas s'effacer l'une l'autre.
$fh = fopen(FICHIER, 'c+');
if ($fh === false || !flock($fh, LOCK_EX)) {
    repond(500, ['erreur' => 'fichier verrouille']);
}
$contenu = stream_get_contents($fh);
$lu = json_decode((string) $contenu, true);
$cases = (is_array($lu) && isset($lu['cases']) && is_array($lu['cases']))
    ? $lu['cases'] : [];

// Une sauvegarde avant chaque ecriture : un tableau rempli sur des mois par
// plusieurs foreuses ne doit pas pouvoir disparaitre sur une fausse manoeuvre.
if ($contenu !== '') {
    @mkdir(SAUVEGARDES, 0775, true);
    @file_put_contents(
        SAUVEGARDES . '/releve-' . gmdate('Ymd-His') . '.json', $contenu);
    $vieilles = glob(SAUVEGARDES . '/releve-*.json') ?: [];
    sort($vieilles);
    foreach (array_slice($vieilles, 0, max(0, count($vieilles) - MAX_SAUVEGARDES)) as $v) {
        @unlink($v);
    }
}

if ($valeur === '') {
    unset($cases[$case]);
} else {
    $cases[$case] = ['v' => $valeur, 'qui' => $foreuse,
                     'quand' => gmdate('c')];
}
$sortie = json_encode(['cases' => (object) $cases, 'maj' => gmdate('c')],
                      JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
ftruncate($fh, 0);
rewind($fh);
fwrite($fh, (string) $sortie);
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);

repond(200, ['ok' => true, 'case' => $case, 'valeur' => $valeur]);
"""

HTACCESS = """# Le releve et ses sauvegardes ne se lisent que par releve.php, jamais en
# direct : le fichier porte le nom des foreuses, et les sauvegardes
# s'enumereraient une a une.
<FilesMatch "\\.json$">
    Require all denied
</FilesMatch>
<IfModule mod_autoindex.c>
    Options -Indexes
</IfModule>
"""

GABARIT = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Relevé de forage des Primes</title>
<meta name="description" content="Où et quand sortent les matières des Primes : le relevé de la guilde La Lune Éternelle, à remplir en forant.">
<meta name="theme-color" content="#10171a">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='13' fill='%233f7a68'/><circle cx='20' cy='12' r='11' fill='%2310171a'/></svg>">
<meta property="og:type" content="website">
<meta property="og:title" content="Relevé de forage des Primes">
<meta property="og:url" content="https://xiom.be/forage/">
<style>
  /* Les couleurs de xiom.be, reprises telles quelles. */
  :root {
    color-scheme: dark;
    --fond: #10171a; --surface: #172226; --sarcelle: #3f7a68;
    --clair: #8fbfae; --or: #e8c15a; --texte: #e2e8e6; --faible: #9aa8a5;
    --oui: #4bbf72; --non: #55605e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 0 16px 48px;
    background: var(--fond); color: var(--texte);
    font-family: system-ui, sans-serif; font-size: 15px;
  }
  header { max-width: 900px; margin: 0 auto; padding: 24px 0 8px; }
  h1 { font-size: 1.4rem; margin: 0 0 8px; color: var(--or); }
  p { margin: 0 0 10px; color: var(--faible); line-height: 1.5; }
  a { color: var(--clair); }

  .barre { display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
           max-width: 900px; margin: 12px auto; }
  button {
    background: var(--surface); color: var(--texte); cursor: pointer;
    border: 1px solid #24343a; border-radius: 7px; padding: 7px 13px;
    font: inherit;
  }
  button:hover { border-color: var(--sarcelle); }
  button[aria-pressed="true"] {
    background: var(--sarcelle); color: #08120f; border-color: var(--sarcelle);
    font-weight: 600;
  }
  .compte { margin-left: auto; color: var(--faible); font-size: .9rem; }

  /* Le tableau deborde volontiers : il defile seul, sans pousser la page. */
  .cadre { max-width: 900px; margin: 0 auto; overflow-x: auto; }
  /* Largeurs posees : laissee libre, la colonne des noms s'etirait sur la
     moitie de l'ecran et les quatre conditions se serraient a droite. */
  table { border-collapse: collapse; width: auto; margin: 0 auto; }
  th, td { border: 1px solid #24343a; padding: 4px 6px; text-align: center; }
  thead th { position: sticky; top: 0; background: var(--surface); z-index: 2; }
  thead .cond { font-weight: 600; color: var(--clair); white-space: nowrap;
                width: 108px; }
  thead .plage { display: block; font-weight: 400; font-size: .75rem;
                 color: var(--faible); white-space: nowrap; }
  .famille th { background: #1d2b30; color: var(--or); text-align: left;
                letter-spacing: .02em; }
  .matiere { text-align: center; white-space: nowrap; font-weight: 600;
             width: 170px; }
  .qualite { color: var(--faible); font-weight: 400; font-size: .85rem;
             width: 54px; }
  /* Le rappel des conditions sur la ligne de la famille : assez lisible pour
     qu'on s'y repere, assez terne pour ne pas voler la vedette au nom jaune. */
  /* Centres : `.famille th` aligne tout a gauche pour le nom de la famille,
     et les rappels heritaient de cet alignement -- ils flottaient donc au bord
     gauche de colonnes larges de cent huit points, loin de la case visee. */
  .famille .rappel { font-size: .75rem; font-weight: 400; color: var(--clair);
                     letter-spacing: .02em; text-align: center; }
  .q-supp .qualite { color: var(--or); }

  .case { cursor: pointer; height: 26px; font-weight: 700; user-select: none; }
  .case:hover { background: #1d2b30; }
  .case[data-v="x"] { color: var(--oui); background: rgba(75,191,114,.13); }
  .case[data-v="x"]::after { content: "x"; }
  .case[data-v="-"] { color: var(--non); }
  .case[data-v="-"]::after { content: "\\2212"; }

  #bloc-nom { color: var(--faible); font-size: .9rem; }
  #nom { background: var(--fond); color: var(--texte); font: inherit;
         border: 1px solid #24343a; border-radius: 7px; padding: 6px 8px;
         margin-left: 4px; }
  #lecture { max-width: 900px; margin: 0 auto 10px; color: var(--or); }
  /* En lecture seule, rien ne doit laisser croire qu'un clic fera quelque
     chose : ni main de souris, ni case qui s'allume au survol. */
  .lecture-seule .case { cursor: default; }
  .lecture-seule .case:hover { background: none; }
</style>
</head>
<body>

<header>
  <h1>Relevé de forage des Primes</h1>
  <p>Quand on fore une source dans les Primes, on coche ici. Un clic&nbsp;:
     <b style="color:var(--oui)">x</b> ça sort, <b style="color:var(--non)">−</b>
     ça ne sort pas, un clic de plus efface. Utilisez une stanza précise —
     suprême seulement, ou excellent seulement, ou choix seulement — et lisez le
     message du jeu&nbsp;: <i>pas à cette saison</i>, <i>vidé</i>,
     <i>mauvaises conditions climatiques</i>.</p>
  <p>Les conditions climatiques se lisent sur
     <a href="http://ballisticmystix.net/?p=atys_calendar#">ballistic mystix</a>
     ou dans ZyRoom. Vérifiez l'heure avant de corriger une case&nbsp;: il y a
     parfois plusieurs heures de décalage.</p>
</header>

<div class="barre">
  __ZONES__
</div>

<div class="barre">
  __ONGLETS__
  <label id="bloc-nom">Ton nom&nbsp;:
    <input id="nom" maxlength="24" size="12" placeholder="Xiom" spellcheck="false">
  </label>
  <span class="compte" id="compte">chargement…</span>
</div>

<p id="lecture" hidden>Lecture seule&nbsp;: demande le lien de saisie dans le
   canal de guilde pour pouvoir cocher.</p>

<div class="cadre">
  <table>
    <thead>
      <tr>
        <th colspan="2" id="titre-saison"></th>
        __ENTETES__
      </tr>
    </thead>
    <tbody id="corps">__GRILLE__</tbody>
  </table>
</div>

<script>
  "use strict";
  const SAISONS = __SAISONS__;
  const ZONES = __LISTE_ZONES__;
  // La clef de saisie voyage dans l'adresse : sans elle, la page se lit et ne
  // se coche pas. C'est le lien qu'on colle dans le canal de guilde.
  const CLE = new URLSearchParams(location.search).get("k") || "";

  let saison = 0;
  let zone = 0;
  let cases = {};              // "saison|matiere|qualite|condition" -> {v, qui}
  let enVol = 0;

  const corps = document.getElementById("corps");
  const compte = document.getElementById("compte");
  const nom = document.getElementById("nom");

  if (!CLE) {
    document.getElementById("lecture").hidden = false;
    document.getElementById("bloc-nom").hidden = true;
    document.body.classList.add("lecture-seule");
  }
  try { nom.value = localStorage.getItem("forage-nom") || ""; } catch (e) {}
  nom.addEventListener("change", () => {
    try { localStorage.setItem("forage-nom", nom.value.trim()); } catch (e) {}
  });

  function cle(td) {
    return ZONES[zone] + "|" + SAISONS[saison] + "|" + td.dataset.cle;
  }

  function peindre() {
    document.getElementById("titre-saison").textContent =
      ZONES[zone] + " — " + SAISONS[saison];
    for (const td of corps.querySelectorAll(".case")) {
      const c = cases[cle(td)];
      if (c) {
        td.dataset.v = c.v;
        // Qui a coche, et quand : sur un tableau rempli a plusieurs sur des
        // mois, c'est a quoi on se raccroche quand deux releves divergent.
        td.title = (c.qui || "quelqu'un") + (c.quand ? " — " + c.quand.slice(0, 10) : "");
      } else {
        delete td.dataset.v;
        td.removeAttribute("title");
      }
    }
    const n = Object.keys(cases).length;
    compte.textContent = n + " case" + (n > 1 ? "s" : "") + " cochée"
                         + (n > 1 ? "s" : "") + (CLE ? "" : " · lecture seule");
  }

  async function charger() {
    try {
      const r = await fetch("releve.php", { cache: "no-store" });
      const d = await r.json();
      cases = d.cases || {};
      peindre();
    } catch (e) {
      compte.textContent = "relevé injoignable";
    }
  }

  async function envoyer(k, v) {
    enVol++;
    try {
      const r = await fetch("releve.php", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cle: CLE, case: k, valeur: v,
                               foreuse: nom.value.trim() })
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.erreur || r.status);
      }
      return true;
    } catch (e) {
      compte.textContent = "refusé : " + e.message;
      return false;
    } finally {
      enVol--;
    }
  }

  corps.addEventListener("click", async (e) => {
    if (!CLE) return;
    const td = e.target.closest(".case");
    if (!td) return;
    const k = cle(td);
    const avant = cases[k];
    const suite = { undefined: "x", "x": "-", "-": undefined };
    const v = suite[avant ? avant.v : undefined];
    // On peint d'abord et on demande ensuite : le clic doit repondre tout de
    // suite. Si le serveur refuse, on remet ce qui etait la.
    if (v) {
      cases[k] = { v: v, qui: nom.value.trim(), quand: new Date().toISOString() };
    } else {
      delete cases[k];
    }
    peindre();
    if (!await envoyer(k, v || "")) {
      if (avant) { cases[k] = avant; } else { delete cases[k]; }
      peindre();
    }
  });

  // Les deux rangees d'onglets marchent pareil : on change l'indice, on
  // rallume le bouton choisi, et la meme grille se repeint. Seize tableaux --
  // quatre zones par quatre saisons -- et une seule grille dessinee.
  for (const [attribut, poser] of [["data-saison", (n) => { saison = n; }],
                                   ["data-zone", (n) => { zone = n; }]]) {
    for (const b of document.querySelectorAll("[" + attribut + "]")) {
      b.addEventListener("click", () => {
        poser(Number(b.dataset[attribut === "data-zone" ? "zone" : "saison"]));
        for (const a of document.querySelectorAll("[" + attribut + "]")) {
          a.setAttribute("aria-pressed", a === b ? "true" : "false");
        }
        peindre();
      });
    }
  }

  // On relit regulierement : deux foreuses sur le meme creneau doivent voir
  // les croix l'une de l'autre sans recharger la page. Jamais pendant qu'une
  // ecriture est en vol, sinon elle reviendrait effacee.
  setInterval(() => { if (enVol === 0) charger(); }, 45000);
  // Peindre d'abord : sans cela, le titre du tableau reste vide tant que le
  // serveur n'a pas repondu -- et vide pour toujours s'il ne repond jamais.
  peindre();
  charger();
</script>
</body>
</html>
"""


def _liste_php(elements) -> str:
    """Une liste PHP littérale, guillemets simples échappés."""
    return "[" + ", ".join("'" + str(e).replace("\\", "\\\\")
                           .replace("'", "\\'") + "'" for e in elements) + "]"


def main() -> int:
    familles = catalogue()
    matieres = [m.replace("²", "").strip()
                for _f, ms in familles for m in ms]
    entetes = "\n        ".join(
        f'<th class="cond">{fr}<span class="plage">{court} · {plage}</span></th>'
        for fr, court, plage in CONDITIONS)
    onglets = "\n  ".join(
        f'<button data-saison="{i}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{s}</button>' for i, s in enumerate(SAISONS))
    zones = "\n  ".join(
        f'<button data-zone="{i}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{z}</button>' for i, z in enumerate(ZONES))
    page = (GABARIT
            .replace("__ONGLETS__", onglets)
            .replace("__ZONES__", zones)
            .replace("__LISTE_ZONES__", repr(list(ZONES)).replace("'", '"'))
            .replace("__ENTETES__", entetes)
            .replace("__GRILLE__", grille(familles))
            .replace("__SAISONS__", repr(list(SAISONS)).replace("'", '"')))
    php = (PHP
           .replace("__CLE__", clef())
           .replace("__ZONES__", _liste_php(ZONES))
           .replace("__SAISONS__", _liste_php(SAISONS))
           .replace("__QUALITES__", _liste_php(QUALITES))
           .replace("__CONDITIONS__", _liste_php(c[0] for c in CONDITIONS))
           .replace("__MATIERES__", _liste_php(matieres)))

    dossier = os.path.dirname(CIBLE)
    os.makedirs(dossier, exist_ok=True)
    ecrits = []
    for nom, contenu in (("index.html", page), ("releve.php", php),
                         (".htaccess", HTACCESS)):
        chemin = os.path.join(dossier, nom)
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        ecrits.append((nom, len(contenu)))

    par_tableau = len(matieres) * len(QUALITES) * len(CONDITIONS)
    print(f"{len(familles)} familles, {len(matieres)} matières, "
          f"{par_tableau} cases par tableau — {len(ZONES)} zones × "
          f"{len(SAISONS)} saisons = "
          f"{par_tableau * len(ZONES) * len(SAISONS)} au total")
    for nom, poids in ecrits:
        print(f"  {nom:12s} {poids // 1024 or 1:3d} Kio")
    print(f"→ {dossier}")
    print("clef d'écriture : voir " + CLE_FICHIER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
