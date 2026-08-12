#!/usr/bin/env python3
"""Range les mini-cartes de gisements dans les deux portages.

En amont : `outils/cartes_gisements.py` a rempli `cartes-gisements/` avec les
images du tracker et leur manifeste. Ici on les recompresse, on les recopie là
où chaque application les cherche, et on écrit la table qui va du nom **français**
qu'on affiche au fichier qu'il faut montrer.

    python3 outils/table_gisements.py

**Pourquoi une table de traduction.** Le classeur de la guilde dit « Cornée »,
« Colle », « Ardente » ; le tracker dit `horny`, `glue`, `redhot`. Et le
classeur porte les annotations de ceux qui l'ont rempli — « Beng Agro »,
« Yana ? », « Visc agro KKT » — qu'il faut ramener au nom de la matière. Le
script **échoue** si une matière du classeur ne trouve pas son fichier : c'est
le seul moyen de s'apercevoir qu'une matière est apparue sans qu'on l'ait vue.

**Taille.** 320 × 300 en WebP 70 : trois mégaoctets et des poussières pour les
deux cent soixante vues, et le nom incrusté sur l'image reste lisible. À 256 il
ne l'est plus vraiment ; à 512 les applications doublaient de poids.

Ces images ne vont pas dans la variante F-Droid : ce sont des données du jeu
republiées par un tiers, même catégorie que la carte d'Atys et les symboles de
matières.

Attribution : tracker de Tgwaste sur atys.us, données de ballisticmystix.net.
"""
import json
import os
import shutil
import sys

try:
    from PIL import Image
except ImportError:                                     # pragma: no cover
    raise SystemExit("Pillow est nécessaire : apt install python3-pil")

LARGEUR, HAUTEUR, QUALITE = 320, 300, 70

#: Famille française -> nom de famille du tracker.
FAMILLES = {
    "Ambres": "amber", "Écorce": "bark", "Fibres": "fiber", "Huile": "oil",
    "Résine": "resin", "Sève": "sap", "Graines": "seed", "Carapace": "shell",
    "Bois": "wood", "Boucles": "wood_node",
}

#: Matière française -> nom de matière du tracker.
#:
#: La plupart se devinent ; quelques-unes sont traduites (« Colle » pour `glue`,
#: « Lune » pour `moon`, « Ardente » pour `redhot`, « Grosse » pour `big`,
#: « Mignonne » pour `cuty`, « Inteligente » pour `smart`, « Cornée » pour
#: `horny`, « Visc » pour `viscous`). Et `scrath` est une coquille du site pour
#: Scratch — on la garde telle quelle, c'est le nom du fichier.
MATIERES = {
    "Beng": "beng", "Hash": "hash", "Pha": "pha", "Sha": "sha", "Soo": "soo",
    "Zun": "zun",
    "Adriel": "adriel", "Beckers": "beckers", "Mitexi": "mitexi",
    "Oath": "oath", "Perfling": "perfling",
    "Anète": "anete", "Buo": "buo", "Dzao": "dzao", "Shu": "shu",
    "Gulatch": "gulatch", "Irin": "irin", "Koorin": "koorin", "Pilan": "pilan",
    "Colle": "glue", "Dung": "dung", "Fung": "fung", "Lune": "moon",
    "Ardente": "redhot", "Dante": "dante", "Enola": "enola",
    "Silverweed": "silverweed", "Visc": "viscous",
    "Caprice": "caprice", "Sarina": "sarina", "Saurona": "saurona",
    "Silvio": "silvio",
    "Cornée": "horny", "Grosse": "big", "Inteligente": "smart",
    "Mignonne": "cuty", "Splinter": "splinter",
    "Abhaya": "abhaya", "Eyota": "eyota", "Kachine": "kachine",
    "Motega": "motega", "Tama": "tama",
    "Nita": "nita", "Patee": "patee", "Scratch": "scrath", "Tansy": "tansy",
    "Yana": "yana",
}

#: Ce que les joueurs ajoutent au nom en remplissant le classeur, et qui n'est
#: pas le nom de la matière : le point d'interrogation du doute, et la mention
#: d'un gisement gardé par une bête. On les retire plutôt que de les traduire.
BRUIT = ("?", "agro", "aggro", "omg", "kkt")

#: Une seule matière est classée ailleurs chez Ballistic Mystix que dans le
#: classeur : Enola y est une sève, pas une huile. On suit le site, puisque
#: c'est lui qui nomme les fichiers.
FAMILLE_CORRIGEE = {"Enola": "Sève"}


def normalise(matiere: str) -> str:
    """« Migno Omg AGGRO » -> « Mignonne ». Le nom seul, sans les annotations."""
    mots = [m for m in matiere.split()
            if m.lower().strip("?").strip() not in BRUIT and m not in ("?",)]
    nom = " ".join(mots).strip(" ?")
    if nom in MATIERES:
        return nom
    # Le nom anglais, qui se glisse parfois tel quel dans le classeur.
    for connu, anglais in MATIERES.items():
        if nom.lower() == anglais:
            return connu
    # Les abrégés — « Migno » pour Mignonne. On n'accepte le rapprochement que
    # s'il est **sans ambiguïté** : deux matières commençant pareil, et le
    # script préfère échouer plutôt que d'afficher la carte de la voisine.
    proches = [c for c in MATIERES if c.lower().startswith(nom.lower())]
    return proches[0] if len(proches) == 1 else nom


def images(manifeste: dict) -> dict:
    """(qualité, famille, matière) du tracker -> (humidités, [fichiers])."""
    table = {}
    for gisement in manifeste["gisements"]:
        cle = (gisement["qualite"], gisement["famille"], gisement["matiere"])
        table[cle] = (gisement["humidites"],
                      [c["fichier"] for c in gisement["cartes"]])
    return table


def libelles() -> dict:
    """Tout ce que les deux écrans peuvent afficher -> le couple du tracker.

    Les deux tables de l'application ne nomment pas les matières pareil : le
    classeur de la guilde est en français — « Colle », « Ardente », « Cornée » —
    et les listes de suprêmes sont en anglais — « Glue », « Redhot », « Horny ».
    S'y ajoutent les annotations des joueurs, « Beng Agro » ou « Migno Omg
    AGGRO ».

    On résout tout ici, à la fabrication, et on écrit le résultat en clair. À
    l'exécution il ne reste qu'un accès direct : pas de découpage de chaîne, pas
    de rapprochement par préfixe, rien qui puisse afficher la carte de la
    voisine.
    """
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(racine), "zyroom-gtk"))
    from zyroom import armory                            # noqa: E402
    from zyroom.pop import POP                           # noqa: E402

    paires = set()
    for zones in POP.values():
        for conditions in zones.values():
            for familles in conditions.values():
                for famille, matieres in familles.items():
                    paires.update((famille, m) for m in matieres)
    for saison in armory.SUPREMES.values():
        for groupes in saison.values():
            for famille, matieres in groupes.items():
                paires.update((famille, m) for m in matieres)
    for saison in armory.EXCELLENTES.values():
        for groupes in saison.values():
            for famille, matieres in groupes.items():
                paires.update((famille, m) for m in matieres)

    table, orphelins = {}, []
    for famille, brute in sorted(paires):
        nom = normalise(brute)
        vraie = FAMILLE_CORRIGEE.get(nom, famille)
        couple = (FAMILLES.get(vraie), MATIERES.get(nom))
        if None in couple:
            orphelins.append(f"{famille} / « {brute} »")
        else:
            table[(famille, brute)] = couple
    if orphelins:
        print("Des matières affichées n'ont pas de carte :", file=sys.stderr)
        for ligne in orphelins:
            print("  " + ligne, file=sys.stderr)
        raise SystemExit("ajoute-les à MATIERES, ou vérifie les tables")
    return table


def kotlin(table: dict, noms: dict) -> str:
    lignes = []
    for (qualite, famille, matiere), (humidites, fichiers) in sorted(table.items()):
        h = ", ".join(f"{bas}f to {haut}f" for bas, haut in humidites)
        r = ", ".join("R.drawable." + os.path.splitext(f)[0] for f in fichiers)
        lignes.append(f'        Cle("{qualite}", "{famille}", "{matiere}") to '
                      f'Gisement(listOf({h}), listOf({r})),')
    corps = "\n".join(lignes)
    libelles = "\n".join(
        f'        ("{f}" to "{b}") to ("{cf}" to "{cm}"),'
        for (f, b), (cf, cm) in sorted(noms.items()))
    return f"""package net.ryzom.zyroom.model

import net.ryzom.zyroom.R

// Fichier produit par outils/table_gisements.py — ne pas modifier à la main.

/**
 * Où sortent les matières, en images.
 *
 * L'écran météo dit *quoi* sort ; ces vues disent *où*. Elles viennent du
 * tracker d'atys.us — vues de {LARGEUR} × {HAUTEUR} portant le marqueur et le nom du
 * gisement — et les données de gisements sont celles de ballisticmystix.net.
 *
 * La clé est en français, comme ce qu'affiche l'écran ; la traduction vers les
 * noms du site est faite à la fabrication.
 */
object Gisements {{
    data class Cle(val qualite: String, val famille: String, val matiere: String)

    data class Gisement(
        /** Les fourchettes d'humidité où la matière sort, en pourcentage. */
        val humidites: List<Pair<Float, Float>>,
        val images: List<Int>,
    )

    val TABLE: Map<Cle, Gisement> = mapOf(
{corps}
    )

    /**
     * Le libellé affiché -> le couple du tracker.
     *
     * Les deux écrans ne nomment pas les matières pareil — « Colle » ici,
     * « Glue » là — et le classeur de la guilde porte les annotations de ceux
     * qui l'ont rempli. Tout est résolu à la fabrication : ici, un simple accès.
     */
    val LIBELLES: Map<Pair<String, String>, Pair<String, String>> = mapOf(
{libelles}
    )

    /** Les vues d'une matière telle qu'elle s'affiche, ou rien si on ne l'a pas. */
    fun cartes(qualite: String, famille: String, matiere: String): List<Int> {{
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.images ?: emptyList()
    }}
}}
"""


def python(table: dict, noms: dict) -> str:
    lignes = []
    for (qualite, famille, matiere), (humidites, fichiers) in sorted(table.items()):
        h = "[" + ", ".join(f"({bas}, {haut})" for bas, haut in humidites) + "]"
        f = "[" + ", ".join(f'"{n}"' for n in fichiers) + "]"
        lignes.append(f'    ("{qualite}", "{famille}", "{matiere}"): ({h}, {f}),')
    corps = "\n".join(lignes)
    libelles = "\n".join(f'    ("{f}", "{b}"): ("{cf}", "{cm}"),'
                         for (f, b), (cf, cm) in sorted(noms.items()))
    return f'''"""Où sortent les matières, en images.

Fichier produit par ../zyroom-android/outils/table_gisements.py — ne pas
modifier à la main.

L'écran météo dit *quoi* sort ; ces vues disent *où*. Elles viennent du tracker
d'atys.us — vues de {LARGEUR} × {HAUTEUR} portant le marqueur et le nom du gisement — et
les données de gisements sont celles de ballisticmystix.net.

La clé est en français, comme ce qu'affiche l'écran.
"""
import os

LARGEUR = {LARGEUR}
HAUTEUR = {HAUTEUR}

#: Les images, à côté de ce fichier : le Makefile recopie le paquet en entier.
DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gisements")

#: (qualité, famille, matière) -> ([fourchettes d'humidité], [fichiers])
GISEMENTS = {{
{corps}
}}

#: (famille, libellé affiché) -> (famille, matière) du tracker.
#:
#: Les deux écrans ne nomment pas les matières pareil — « Colle » ici, « Glue »
#: là — et le classeur de la guilde porte les annotations de ceux qui l'ont
#: rempli. Tout est résolu à la fabrication : ici, un simple accès.
LIBELLES = {{
{libelles}
}}


def _trouve(qualite: str, famille: str, matiere: str):
    couple = LIBELLES.get((famille, matiere))
    return GISEMENTS.get((qualite,) + couple) if couple else None


def cartes(qualite: str, famille: str, matiere: str) -> list:
    """Les chemins des vues d'une matière, ou une liste vide si on ne l'a pas."""
    trouve = _trouve(qualite, famille, matiere)
    return [os.path.join(DOSSIER, nom) for nom in trouve[1]] if trouve else []


def humidites(qualite: str, famille: str, matiere: str) -> list:
    """Les fourchettes d'humidité où la matière sort, en pourcentage."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[0]) if trouve else []
'''


def main() -> int:
    android = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    depot = os.path.dirname(android)
    source = os.path.join(depot, "cartes-gisements")
    if not os.path.isdir(source):
        raise SystemExit(f"{source} est absent — lance d'abord "
                         "outils/cartes_gisements.py")
    with open(os.path.join(source, "manifeste.json"), encoding="utf-8") as fh:
        manifeste = json.load(fh)
    brutes = images(manifeste)

    noms = libelles()
    orphelines = {c for c in noms.values()
                  if not any(k[1:] == c for k in brutes)}
    if orphelines:
        raise SystemExit("le tracker n'a pas de carte pour : "
                         + ", ".join("/".join(c) for c in sorted(orphelines)))
    print(f"{len(noms)} libellés affichés, tous rattachés à une carte")

    # Les fichiers deviennent du WebP. Le préfixe `gis_` évite qu'un nom de
    # matière heurte une ressource existante d'Android.
    table = {cle: (humidites,
                   ["gis_" + os.path.splitext(n)[0] + ".webp" for n in fichiers])
             for cle, (humidites, fichiers) in brutes.items()}

    cibles = (os.path.join(android, "app/src/packRes/drawable-nodpi"),
              os.path.join(depot, "zyroom-gtk/zyroom/gisements"))
    # On ne balaie que nos propres fichiers : `drawable-nodpi` abrite aussi la
    # carte d'Atys et le reste des ressources du pack.
    for cible in cibles:
        os.makedirs(cible, exist_ok=True)
        for ancien in os.listdir(cible):
            if ancien.startswith("gis_"):
                os.remove(os.path.join(cible, ancien))

    faits, poids = set(), 0
    for _humidites, fichiers in table.values():
        for nom in fichiers:
            if nom in faits:
                continue
            faits.add(nom)
            brut = os.path.join(source,
                                nom[len("gis_"):-len(".webp")] + ".png")
            image = Image.open(brut).convert("RGB").resize(
                (LARGEUR, HAUTEUR), Image.LANCZOS)
            premier = os.path.join(cibles[0], nom)
            image.save(premier, "WEBP", quality=QUALITE, method=6)
            shutil.copyfile(premier, os.path.join(cibles[1], nom))
            poids += os.path.getsize(premier)
    print(f"{len(faits)} vues en {LARGEUR} × {HAUTEUR}, {poids // 1024} ko, "
          f"dans les deux portages")

    sorties = (
        (os.path.join(android,
                      "app/src/packKotlin/net/ryzom/zyroom/model/Gisements.kt"),
         kotlin(table, noms)),
        (os.path.join(depot, "zyroom-gtk/zyroom/gisements.py"),
         python(table, noms)),
    )
    for chemin, contenu in sorties:
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(contenu)
        print(f"→ {chemin}  ({os.path.getsize(chemin) // 1024} ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
