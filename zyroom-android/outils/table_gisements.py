#!/usr/bin/env python3
"""Fabrique la table des gisements des deux portages, à partir du dump de bmsite.

Ce qu'elle dit : pour chaque matière suprême ou excellente, **où elle sort** —
les coordonnées de jeu de chaque gisement. L'écran météo dit déjà *quoi* sort ;
avec ça, les applications dessinent *où* sur leur propre carte d'Atys.

    python3 outils/table_gisements.py

**D'où viennent les coordonnées.** Du relevé que Ballistic Mystix publie à
`ballisticmystix.net/docs/resources.json`. Karu, qui le tient, a donné son
accord écrit pour qu'on s'en serve et qu'on le redistribue — c'est ce qui permet
de l'embarquer dans la variante F-Droid, ce que les vues du tracker
n'autorisaient pas.

**Ce que ça remplace.** On embarquait 260 vues rendues par le tracker d'atys.us,
soit trois mégaoctets d'images. Sept kilooctets de coordonnées disent la même
chose, et laissent dessiner à la bonne échelle plutôt que de montrer une image
figée.

**Comment on sépare les qualités.** Le dump nomme les gisements comme le jeu :
« Beng Amber » sans adjectif dans les quatre zones que la guilde relève — ce
sont les suprêmes —, et « Bundle of Excellent Prime Root Eyota Wood » ailleurs
dans les Primes pour les excellentes. Les deux ensembles font 47 matières
chacun, exactement ceux de nos tables établies de leur côté : ce recoupement est
la meilleure preuve qu'on lit le dump comme il faut, et le script échoue s'il
cesse de tenir.
"""
import collections
import json
import os
import re
import sys
import urllib.request

SOURCE = "https://ballisticmystix.net/docs/resources.json"

#: Les noms de lieux, en français, du même auteur que la carte : un point sur la
#: carte ne dit pas où aller, « Sources Interdites » si. Les quatre zones du
#: classeur de la guilde y portent exactement les noms que la guilde leur donne.
SOURCE_LIEUX = ("https://raw.githubusercontent.com/nimetu/ryzom_maps/"
                "master/src/Bmsite/Maps/Resources/labels.json")

#: Les quatre zones du relevé de la guilde. Le dump y nomme les gisements sans
#: adjectif de qualité : ce sont les suprêmes.
ZONES_SUPREMES = ("region_forbidden_depths", "region_the_land_of_continuty",
                  "region_the_sunken_city", "region_the_under_spring")

#: Ce que le jeu met devant le nom d'une matière selon sa famille — « Bundle of
#: … Wood », « Portion of … Resin ». Rien à en tirer, on l'enlève.
CONTENANTS = ("Bundle", "Portion", "Fragment", "Phial", "Handful")

#: Les qualités du jeu, de la plus basse à la plus haute.
GRADES = ("Basic", "Fine", "Choice", "Excellent", "Supreme", "Select",
          "Prime", "Magnificient", "Superb", "Average")

#: Famille du dump (en anglais, telle qu'elle finit le nom) -> famille chez nous.
FAMILLES = {
    "amber": "amber", "bark": "bark", "fiber": "fiber", "oil": "oil",
    "resin": "resin", "sap": "sap", "seed": "seed", "shell": "shell",
    "wood node": "wood_node", "wood": "wood",
}

#: Les rares matières que le dump nomme autrement que le tracker.
MATIERES = {"visc": "viscous"}

#: Famille française -> famille du jeu.
FAMILLES_FR = {
    "Ambres": "amber", "Écorce": "bark", "Fibres": "fiber", "Huile": "oil",
    "Résine": "resin", "Sève": "sap", "Graines": "seed", "Carapace": "shell",
    "Bois": "wood", "Boucles": "wood_node",
}

#: Matière française -> matière du jeu.
#:
#: La plupart se devinent ; quelques-unes sont traduites (« Colle » pour `glue`,
#: « Lune » pour `moon`, « Ardente » pour `redhot`, « Grosse » pour `big`,
#: « Mignonne » pour `cuty`, « Inteligente » pour `smart`, « Cornée » pour
#: `horny`, « Visc » pour `viscous`). Et `scrath` est une coquille du jeu pour
#: Scratch — on la garde telle quelle, c'est le nom qu'il porte.
MATIERES_FR = {
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
#: d'un gisement gardé par une bête.
BRUIT = ("?", "agro", "aggro", "omg", "kkt")

#: Une seule matière est classée ailleurs par le jeu que dans le classeur :
#: Enola y est une sève, pas une huile.
FAMILLE_CORRIGEE = {"Enola": "Sève"}


def normalise(matiere: str) -> str:
    """« Migno Omg AGGRO » -> « Mignonne ». Le nom seul, sans les annotations."""
    mots = [m for m in matiere.split()
            if m.lower().strip("?").strip() not in BRUIT and m != "?"]
    nom = " ".join(mots).strip(" ?")
    if nom in MATIERES_FR:
        return nom
    for connu, jeu in MATIERES_FR.items():          # le nom anglais tel quel
        if nom.lower() == jeu:
            return connu
    # Les abrégés — « Migno » pour Mignonne. On n'accepte le rapprochement que
    # s'il est **sans ambiguïté** : deux matières commençant pareil, et le
    # script préfère échouer plutôt qu'afficher la carte de la voisine.
    proches = [c for c in MATIERES_FR if c.lower().startswith(nom.lower())]
    return proches[0] if len(proches) == 1 else nom


def libelles() -> dict:
    """Tout ce que les deux écrans peuvent afficher -> le couple du jeu.

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
    for source in (armory.SUPREMES, armory.EXCELLENTES):
        for saison in source.values():
            for groupes in saison.values():
                for famille, matieres in groupes.items():
                    paires.update((famille, m) for m in matieres)

    table, orphelins = {}, []
    for famille, brute in sorted(paires):
        nom = normalise(brute)
        vraie = FAMILLE_CORRIGEE.get(nom, famille)
        couple = (FAMILLES_FR.get(vraie), MATIERES_FR.get(nom))
        if None in couple:
            orphelins.append(f"{famille} / « {brute} »")
        else:
            table[(famille, brute)] = couple
    if orphelins:
        print("Des matières affichées n'ont pas de gisement :", file=sys.stderr)
        for ligne in orphelins:
            print("  " + ligne, file=sys.stderr)
        raise SystemExit("ajoute-les à MATIERES_FR, ou vérifie les tables")
    return table

_MOTIF = re.compile(
    r"^(?:(?:%s) of )?" % "|".join(CONTENANTS)
    + r"(?:(%s) )?" % "|".join(GRADES)
    + r"(?:(Prime Root) )?(.+)$")


def analyse(nom: str):
    """« Bundle of Supreme Prime Root Eyota Wood » -> (Supreme, True, wood, eyota).

    Rend None pour ce qui n'est pas une matière de forage — larves de kitin,
    plantes de mission et le reste.
    """
    trouve = _MOTIF.match(nom)
    if trouve is None:
        return None
    grade, primes, reste = trouve.group(1), trouve.group(2), trouve.group(3)
    mots = reste.split()
    # « Wood Node » avant « Wood » : la famille la plus longue gagne, sinon les
    # boucles de bois seraient rangées avec le bois.
    for longueur in (2, 1):
        if len(mots) > longueur:
            famille = " ".join(mots[-longueur:]).lower()
            if famille in FAMILLES:
                matiere = " ".join(mots[:-longueur]).lower()
                return (grade, primes is not None, FAMILLES[famille],
                        MATIERES.get(matiere, matiere))
    return None


def lieux() -> dict:
    """Clé de région -> son nom français, d'après les libellés de nimetu."""
    with urllib.request.urlopen(SOURCE_LIEUX, timeout=180) as reponse:
        libelle = json.loads(reponse.read())
    noms = {}
    for _continent, places in libelle.items():
        for cle, valeur in places.items():
            nom = valeur.get("text", {}).get("fr") or ""
            if nom and not nom.startswith(("region_", "continent_", "place_")):
                noms[cle] = nom
    return noms


def releve(dump: dict, noms: dict) -> dict:
    """(qualité, famille, matière) -> [(x, y, lieu), …], trié."""
    table = collections.defaultdict(list)
    inconnues = set()
    for region, matieres in dump["data"].items():
        for _sheetid, points in matieres.items():
            for point in points:
                lu = analyse(point["name"])
                if lu is None:
                    continue
                grade, primes, famille, matiere = lu
                if region in ZONES_SUPREMES and grade is None:
                    qualite = "supreme"
                elif primes and grade == "Excellent":
                    qualite = "excellent"
                else:
                    continue
                if region not in noms:
                    inconnues.add(region)
                x, y = point["pos"]
                table[(qualite, famille, matiere)].append(
                    (x, y, noms.get(region, region)))
    if inconnues:
        # Un lieu sans nom s'afficherait sous sa clé technique : autant le
        # savoir maintenant que de le lire à l'écran.
        print(f"  régions sans nom français : {sorted(inconnues)}",
              file=sys.stderr)
    return {cle: sorted(set(v)) for cle, v in sorted(table.items())}


def verifie(table: dict) -> None:
    """Le dump dit-il la même chose que nos tables, établies ailleurs ?

    Nos listes de suprêmes et d'excellentes viennent de Ryzom Armory et du
    classeur de la guilde ; celles du dump, du relevé de Ballistic Mystix. Les
    deux doivent coïncider exactement. Si ce n'est plus le cas, c'est soit que le
    jeu a changé, soit qu'on lit mal le dump — dans les deux cas il faut
    regarder avant de livrer une carte fausse.
    """
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(racine), "zyroom-gtk"))
    from zyroom import armory                            # noqa: E402

    familles = {"Ambres": "amber", "Écorce": "bark", "Fibres": "fiber",
                "Huile": "oil", "Résine": "resin", "Sève": "sap",
                "Graines": "seed", "Carapace": "shell", "Bois": "wood",
                "Boucles": "wood_node"}

    def nos(source):
        vus = set()
        for saison in source.values():
            for groupes in saison.values():
                for famille, matieres in groupes.items():
                    for matiere in matieres:
                        nom = matiere.lower()
                        vus.add((familles[famille], MATIERES.get(nom, nom)))
        return vus

    for qualite, attendu in (("supreme", nos(armory.SUPREMES)),
                             ("excellent", nos(armory.EXCELLENTES))):
        trouve = {(f, m) for (q, f, m) in table if q == qualite}
        if trouve != attendu:
            print(f"{qualite} : le dump et nos tables ne disent plus la même "
                  f"chose.", file=sys.stderr)
            print(f"  chez nous seulement : {sorted(attendu - trouve)}",
                  file=sys.stderr)
            print(f"  au dump seulement   : {sorted(trouve - attendu)}",
                  file=sys.stderr)
            raise SystemExit("vérifie avant de livrer une carte fausse")
        print(f"  {qualite:9s} {len(trouve):2d} matières, "
              f"{sum(len(v) for k, v in table.items() if k[0] == qualite):3d} "
              f"points — d'accord avec nos tables")


def sur_la_carte(table: dict) -> None:
    """Chaque point tombe-t-il sur la carte embarquée ?

    Un gisement qu'on ne saurait pas placer ne servirait à rien : mieux vaut
    l'apprendre ici que de le voir manquer à l'écran.
    """
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(racine), "zyroom-gtk"))
    from zyroom import carte                             # noqa: E402
    perdus = [(cle, (x, y)) for cle, points in table.items()
              for x, y, _lieu in points if carte.pixel(x, y) is None]
    if perdus:
        for cle, point in perdus[:10]:
            print(f"  hors carte : {'/'.join(cle)} {point}", file=sys.stderr)
        raise SystemExit(f"{len(perdus)} points ne tombent sur aucune région")
    print(f"  les {sum(len(v) for v in table.values())} points tombent tous "
          f"sur la carte")


def humidites() -> dict:
    """Les fourchettes d'humidité, figées dans `donnees/`.

    Elles venaient des fiches du tracker, qui ne se consultent qu'avec le jeton
    personnel de Xiom : le relevé est donc gardé dans le dépôt plutôt que refait
    à chaque fabrication. Voir l'en-tête du fichier.
    """
    racine = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    chemin = os.path.join(racine, "donnees", "humidites-gisements.json")
    with open(chemin, encoding="utf-8") as fh:
        return json.load(fh)["humidites"]


def kotlin(table: dict, taux: dict) -> str:
    lignes = []
    for (qualite, famille, matiere), points in table.items():
        h = ", ".join(f"{bas}f to {haut}f"
                      for bas, haut in taux.get(f"{qualite}|{famille}|{matiere}", ()))
        p = ", ".join(f'Point({x}, {y}, "{lieu}")' for x, y, lieu in points)
        lignes.append(f'        Cle("{qualite}", "{famille}", "{matiere}") to '
                      f'Gisement(listOf({h}), listOf({p})),')
    return f"""package net.ryzom.zyroom.model

// Fichier produit par outils/table_gisements.py — ne pas modifier à la main.

/**
 * Où sortent les matières, en coordonnées de jeu.
 *
 * L'écran météo dit *quoi* sort ; ceci dit *où*. Les positions viennent du
 * relevé que Ballistic Mystix publie, dont l'auteur a donné son accord écrit
 * pour qu'on s'en serve et qu'on le redistribue. Les applications dessinent
 * elles-mêmes, sur la carte d'Atys embarquée : sept kilooctets de coordonnées
 * au lieu de trois mégaoctets d'images rendues ailleurs, et un zoom libre au
 * lieu d'une vue figée.
 *
 * La clé est en français, comme ce qu'affiche l'écran ; la traduction vers les
 * noms du jeu est faite à la fabrication.
 *
 * **Cette table est dans `src/main` et non dans le pack** : ce sont des faits,
 * pas des images du jeu, et leur auteur a donné son accord écrit. La variante
 * F-Droid les a donc aussi — elle n'embarque pas la carte, mais elle peut dire
 * le lieu et les coordonnées, ce qui vaut mieux que rien.
 */
object Gisements {{
    data class Cle(val qualite: String, val famille: String, val matiere: String)

    /** Un gisement : sa position de jeu, et le lieu où il se trouve. */
    data class Point(val x: Int, val y: Int, val lieu: String)

    data class Gisement(
        /** Les fourchettes d'humidité où la matière sort, en pourcentage. */
        val humidites: List<Pair<Float, Float>>,
        /** Les positions de jeu de ses gisements, avec leur lieu. */
        val points: List<Point>,
    )

    val TABLE: Map<Cle, Gisement> = mapOf(
{chr(10).join(lignes)}
    )

    /**
     * Le libellé affiché -> le couple du jeu.
     *
     * Les deux écrans ne nomment pas les matières pareil — « Colle » ici,
     * « Glue » là — et le relevé de la guilde porte les annotations de ceux qui
     * l'ont rempli. Tout est résolu à la fabrication : ici, un simple accès.
     */
    val LIBELLES: Map<Pair<String, String>, Pair<String, String>> = mapOf(
{{LIBELLES}}
    )

    /** Où sort une matière telle qu'elle s'affiche, ou rien si on ne sait pas. */
    fun points(qualite: String, famille: String, matiere: String):
        List<Point> {{
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.points ?: emptyList()
    }}

    /** Les fourchettes d'humidité, en pourcentage. */
    fun humidites(qualite: String, famille: String, matiere: String):
        List<Pair<Float, Float>> {{
        val (f, m) = LIBELLES[famille to matiere] ?: return emptyList()
        return TABLE[Cle(qualite, f, m)]?.humidites.orEmpty()
    }}
}}
"""


def python(table: dict, taux: dict) -> str:
    lignes = []
    for (qualite, famille, matiere), points in table.items():
        h = "[" + ", ".join(
            f"({bas}, {haut})"
            for bas, haut in taux.get(f"{qualite}|{famille}|{matiere}", ())) + "]"
        p = "[" + ", ".join(f'({x}, {y}, "{lieu}")' for x, y, lieu in points) + "]"
        lignes.append(f'    ("{qualite}", "{famille}", "{matiere}"): ({h}, {p}),')
    return f'''"""Où sortent les matières, en coordonnées de jeu.

Fichier produit par ../zyroom-android/outils/table_gisements.py — ne pas
modifier à la main.

L'écran météo dit *quoi* sort ; ceci dit *où*. Les positions viennent du relevé
que Ballistic Mystix publie, dont l'auteur a donné son accord écrit pour qu'on
s'en serve et qu'on le redistribue. L'application dessine elle-même, sur la
carte d'Atys embarquée.

La clé est en français, comme ce qu'affiche l'écran.
"""

#: (qualité, famille, matière) -> ([fourchettes d'humidité], [positions de jeu])
GISEMENTS = {{
{chr(10).join(lignes)}
}}

#: (famille, libellé affiché) -> (famille, matière) du jeu.
#:
#: Les deux écrans ne nomment pas les matières pareil — « Colle » ici, « Glue »
#: là — et le relevé de la guilde porte les annotations de ceux qui l'ont
#: rempli. Tout est résolu à la fabrication : ici, un simple accès.
LIBELLES = {{
{{LIBELLES}}
}}


def _trouve(qualite: str, famille: str, matiere: str):
    couple = LIBELLES.get((famille, matiere))
    return GISEMENTS.get((qualite,) + couple) if couple else None


def points(qualite: str, famille: str, matiere: str) -> list:
    """Où sort une matière, en coordonnées de jeu ; vide si on ne sait pas."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[1]) if trouve else []


def humidites(qualite: str, famille: str, matiere: str) -> list:
    """Les fourchettes d'humidité où la matière sort, en pourcentage."""
    trouve = _trouve(qualite, famille, matiere)
    return list(trouve[0]) if trouve else []
'''


def main() -> int:
    print(f"téléchargement du relevé de bmsite…")
    with urllib.request.urlopen(SOURCE, timeout=180) as reponse:
        dump = json.loads(reponse.read())
    print(f"  version {dump.get('version')}, du {dump.get('created')}")

    noms_de_lieux = lieux()
    print(f"  {len(noms_de_lieux)} lieux nommés en français")
    table = releve(dump, noms_de_lieux)
    verifie(table)
    sur_la_carte(table)
    taux = humidites()

    noms = libelles()
    orphelines = {c for c in noms.values()
                  if not any(k[1:] == c for k in table)}
    if orphelines:
        raise SystemExit("aucun gisement pour : "
                         + ", ".join("/".join(c) for c in sorted(orphelines)))
    print(f"  {len(noms)} libellés affichés, tous rattachés")

    android = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    depot = os.path.dirname(android)
    sorties = (
        (os.path.join(android,
                      "app/src/main/kotlin/net/ryzom/zyroom/model/Gisements.kt"),
         kotlin(table, taux),
         "\n".join(f'        ("{f}" to "{b}") to ("{cf}" to "{cm}"),'
                   for (f, b), (cf, cm) in sorted(noms.items()))),
        (os.path.join(depot, "zyroom-gtk/zyroom/gisements.py"),
         python(table, taux),
         "\n".join(f'    ("{f}", "{b}"): ("{cf}", "{cm}"),'
                   for (f, b), (cf, cm) in sorted(noms.items()))),
    )
    for chemin, contenu, bloc in sorties:
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write(contenu.replace("{LIBELLES}", bloc))
        print(f"→ {chemin}  ({os.path.getsize(chemin) // 1024} ko)")

    # Les images du tracker n'ont plus lieu d'être : on les retire des deux
    # portages plutôt que de les laisser grossir les paquets pour rien.
    retires = 0
    for dossier in (os.path.join(android, "app/src/packRes/drawable-nodpi"),
                    os.path.join(depot, "zyroom-gtk/zyroom/gisements")):
        if not os.path.isdir(dossier):
            continue
        for nom in sorted(os.listdir(dossier)):
            if nom.startswith("gis_"):
                os.remove(os.path.join(dossier, nom))
                retires += 1
        if not os.listdir(dossier):
            os.rmdir(dossier)
    if retires:
        print(f"  {retires} vues du tracker retirées des deux portages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
