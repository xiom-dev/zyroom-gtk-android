#!/usr/bin/env python3
"""Fabrique la page de relevé du forage pour xiom.be/forage.

Le classeur de la guilde porte un onglet vierge en **six** bandes d'humidité —
Worst, Bad2, Bad1, Good1, Good2, Best. Les relevés déjà faits montrent que Bad1
vaut toujours Bad2 et Good1 toujours Good2 : huit cent trente-six paires, sans
une exception. Les deux moitiés sont donc réunies ici, ce qui ramène le tableau
à **quatre colonnes par saison**, celles que le jeu rend lui-même — et divise
par deux le nombre de cases à cocher sur le terrain.

La page se coche d'un clic : vide → `x` (ça sort) → `−` (ça ne sort pas) →
vide. Tout est gardé dans le navigateur de la foreuse ; le bouton « Exporter »
en tire un texte court, à coller dans le canal de guilde ou à renvoyer, et
« Importer » fusionne celui d'une autre.

    python3 outils/page-forage.py

La page produite est autonome : un seul fichier, rien à installer sur
l'hébergement.

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

ONGLET = "Original vierge"
SAISONS = ("Printemps", "Été", "Automne", "Hiver")

#: Les quatre conditions du jeu, avec la fourchette d'humidite que le tracker
#: affiche. Le nom anglais est garde : c'est celui du classeur et du tracker,
#: donc celui que les foreuses ont sous les yeux.
CONDITIONS = (("Exécrable", "Worst", "84 – 100 %"),
              ("Mauvaise", "Bad", "50 – 83 %"),
              ("Bonne", "Good", "17 – 49 %"),
              ("Excellente", "Best", "0 – 16 %"))

QUALITES = ("Supp", "XL", "Choix")


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
    for famille, matieres in familles:
        lignes.append(
            f'<tr class="famille"><th colspan="6">{html.escape(famille)}</th></tr>')
        for matiere in matieres:
            # Le « ² » du classeur marquait les matieres a stocker en priorite
            # pour le GH. On le retire : ces listes datent de 2009 et une partie
            # n'est plus vraie, et de toute facon cela n'aide pas a remplir le
            # tableau -- qui est le seul but de cette page.
            propre = matiere.replace("²", "").strip()
            # Le tableau fait cent quarante et une lignes : meme avec l'en-tete
            # qui reste colle en haut, on perd la colonne ou l'on vise. Les
            # quatre conditions sont donc redites au-dessus de chaque matiere,
            # en petit -- c'est trois lignes de tableau plus loin, jamais plus.
            lignes.append(
                '<tr class="rappel"><td colspan="2"></td>'
                + "".join(f'<td>{fr}</td>' for fr, _c, _p in CONDITIONS)
                + "</tr>")
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
  .matiere { text-align: left; white-space: nowrap; font-weight: 600;
             width: 170px; }
  .qualite { color: var(--faible); font-weight: 400; font-size: .85rem;
             width: 54px; }
  /* Le rappel des conditions au-dessus de chaque matiere : assez lisible pour
     qu'on s'y repere, assez terne pour ne pas concurrencer les cases. */
  .rappel td { font-size: .72rem; color: var(--faible); padding: 2px 6px;
               border-top: 2px solid #24343a; border-bottom: none;
               letter-spacing: .02em; }
  .rappel td:first-child { border-left: none; border-right: none; }
  .q-supp .qualite { color: var(--or); }

  .case { cursor: pointer; height: 26px; font-weight: 700; user-select: none; }
  .case:hover { background: #1d2b30; }
  .case[data-v="x"] { color: var(--oui); background: rgba(75,191,114,.13); }
  .case[data-v="x"]::after { content: "x"; }
  .case[data-v="-"] { color: var(--non); }
  .case[data-v="-"]::after { content: "\\2212"; }

  dialog {
    background: var(--surface); color: var(--texte); border: 1px solid #24343a;
    border-radius: 10px; max-width: 560px; width: 92%;
  }
  textarea { width: 100%; height: 170px; background: var(--fond);
             color: var(--texte); border: 1px solid #24343a; border-radius: 7px;
             padding: 8px; font-family: ui-monospace, monospace; font-size: .85rem; }
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
  __ONGLETS__
  <button id="exporter">Exporter</button>
  <button id="importer">Importer</button>
  <span class="compte" id="compte"></span>
</div>

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

<dialog id="boite">
  <form method="dialog">
    <p id="boite-titre"></p>
    <textarea id="boite-texte" spellcheck="false"></textarea>
    <div class="barre" style="margin-bottom:0">
      <button id="boite-ok" value="ok">Fusionner</button>
      <button value="annuler">Fermer</button>
    </div>
  </form>
</dialog>

<script>
  "use strict";
  // Les saisons, dans l'ordre du classeur. L'onglet choisi ne change que
  // l'etiquette des cases : la grille, elle, est dessinee une seule fois.
  const SAISONS = __SAISONS__;
  const CLE = "forage-primes-v1";

  let saison = 0;
  let releve = {};
  try { releve = JSON.parse(localStorage.getItem(CLE) || "{}"); } catch (e) {}

  const corps = document.getElementById("corps");
  const compte = document.getElementById("compte");

  function cle(td) { return SAISONS[saison] + "|" + td.dataset.cle; }

  function peindre() {
    document.getElementById("titre-saison").textContent = SAISONS[saison];
    for (const td of corps.querySelectorAll(".case")) {
      const v = releve[cle(td)];
      if (v) { td.dataset.v = v; } else { delete td.dataset.v; }
    }
    const n = Object.keys(releve).length;
    compte.textContent = n ? n + " case" + (n > 1 ? "s" : "") + " cochée"
                             + (n > 1 ? "s" : "") : "aucune case cochée";
  }

  function garder() {
    try { localStorage.setItem(CLE, JSON.stringify(releve)); } catch (e) {}
  }

  corps.addEventListener("click", (e) => {
    const td = e.target.closest(".case");
    if (!td) return;
    const k = cle(td);
    // vide -> x -> moins -> vide : un seul doigt, trois etats.
    const suite = { undefined: "x", "x": "-", "-": undefined };
    const v = suite[releve[k]];
    if (v) { releve[k] = v; } else { delete releve[k]; }
    garder();
    peindre();
  });

  for (const b of document.querySelectorAll("[data-saison]")) {
    b.addEventListener("click", () => {
      saison = Number(b.dataset.saison);
      for (const a of document.querySelectorAll("[data-saison]")) {
        a.setAttribute("aria-pressed", a === b ? "true" : "false");
      }
      peindre();
    });
  }

  const boite = document.getElementById("boite");
  const texte = document.getElementById("boite-texte");
  const titre = document.getElementById("boite-titre");
  const ok = document.getElementById("boite-ok");
  let mode = "exporter";

  document.getElementById("exporter").addEventListener("click", () => {
    mode = "exporter";
    titre.textContent = "À copier et renvoyer :";
    ok.style.display = "none";
    // Une ligne par case : court, lisible, et fusionnable a la main au besoin.
    texte.value = Object.entries(releve).sort()
      .map(([k, v]) => k + "=" + v).join("\\n");
    boite.showModal();
    texte.select();
  });

  document.getElementById("importer").addEventListener("click", () => {
    mode = "importer";
    titre.textContent = "Coller le relevé d'une autre foreuse :";
    ok.style.display = "";
    texte.value = "";
    boite.showModal();
  });

  boite.addEventListener("close", () => {
    if (mode !== "importer" || boite.returnValue !== "ok") return;
    for (const ligne of texte.value.split("\\n")) {
      const [k, v] = ligne.trim().split("=");
      // On ne fusionne que ce qu'on reconnait : une ligne abimee par un
      // copier-coller ne doit pas s'ajouter au releve en silence.
      if (k && (v === "x" || v === "-") && k.split("|").length === 4) {
        releve[k] = v;
      }
    }
    garder();
    peindre();
  });

  peindre();
</script>
</body>
</html>
"""


def main() -> int:
    familles = catalogue()
    entetes = "\n        ".join(
        f'<th class="cond">{fr}<span class="plage">{court} · {plage}</span></th>'
        for fr, court, plage in CONDITIONS)
    onglets = "\n  ".join(
        f'<button data-saison="{i}" aria-pressed="{"true" if i == 0 else "false"}">'
        f'{s}</button>' for i, s in enumerate(SAISONS))
    page = (GABARIT
            .replace("__ONGLETS__", onglets)
            .replace("__ENTETES__", entetes)
            .replace("__GRILLE__", grille(familles))
            .replace("__SAISONS__", repr(list(SAISONS)).replace("'", '"')))
    os.makedirs(os.path.dirname(CIBLE), exist_ok=True)
    with open(CIBLE, "w", encoding="utf-8") as fh:
        fh.write(page)
    matieres = sum(len(m) for _f, m in familles)
    print(f"{len(familles)} familles, {matieres} matières, "
          f"{matieres * len(QUALITES) * len(CONDITIONS)} cases par saison")
    print(f"{len(page) // 1024} Kio → {CIBLE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
