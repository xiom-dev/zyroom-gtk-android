"""Ce que rend un gisement des Primes, selon la zone, la saison et le temps.

Fichier produit par ../zyroom-android/outils/table_forage.py — ne pas
modifier à la main. Il croise `armory.py`, qui dit quelle matière sort
dans quelle zone et à quelle saison, avec les fourchettes d'humidité
de `donnees/humidites-gisements.json`, qui disent par quel temps.

**Les deux viennent du tracker d'atys.us**, et c'est ce qui compte :
c'est lui qu'on ouvre à côté pour vérifier. Une table qui ne lui
répond pas est fausse, si cohérente soit-elle avec elle-même.

Le choix reste vide : le tracker ne le suit pas, et le déduire par
élimination ferait dire à l'écran plus que ce qu'on sait.
"""

#: {zone: {(famille, matière): {(saison, condition)}}} — le suprême.
#:
#: Chaque gisement occupe deux des quatre bandes d'humidité : à toute
#: heure, une moitié des matières de la zone sort.
SUPREMES = {
    "Sources Interdites": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Hash"): {
            ("ETE", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Soo"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "BEST"),
            ("ETE", "BEST"),
        },
        ("Bois", "Eyota"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Bois", "Tama"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
        },
        ("Boucles", "Yana"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Splinter"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Dzao"): {
            ("HIVER", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "GOOD"),
        },
        ("Graines", "Saurona"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Dung"): {
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Fung"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Moon"): {
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "BEST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BAD"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Mitexi"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Oath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BEST"),
        },
        ("Ambres", "Hash"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Soo"): {
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Bois", "Eyota"): {
            ("ETE", "BAD"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Tama"): {
            ("HIVER", "GOOD"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Scrath"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Boucles", "Tansy"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Boucles", "Yana"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("HIVER", "BAD"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Buo"): {
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Saurona"): {
            ("ETE", "BEST"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("ETE", "GOOD"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Dung"): {
            ("HIVER", "BAD"),
        },
        ("Résine", "Fung"): {
            ("ETE", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Moon"): {
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Redhot"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "BEST"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Mitexi"): {
            ("ETE", "BAD"),
        },
        ("Écorce", "Oath"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Perfling"): {
            ("PRINTEMPS", "BAD"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Beng"): {
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Hash"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Ambres", "Soo"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Ambres", "Zun"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Eyota"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Bois", "Tama"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "BAD"),
        },
        ("Graines", "Saurona"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Irin"): {
            ("HIVER", "BAD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Pilan"): {
            ("ETE", "GOOD"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Fung"): {
            ("ETE", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Sève", "Redhot"): {
            ("PRINTEMPS", "BEST"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "BEST"),
            ("ETE", "BEST"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Beckers"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Mitexi"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Oath"): {
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Perfling"): {
            ("AUTOMNE", "BEST"),
            ("HIVER", "BEST"),
        },
    },
    "Profondeurs Interdites": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Hash"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Ambres", "Soo"): {
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Bois", "Abhaya"): {
            ("HIVER", "GOOD"),
        },
        ("Bois", "Eyota"): {
            ("AUTOMNE", "BEST"),
            ("ETE", "BEST"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BAD"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Bois", "Tama"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Yana"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("HIVER", "BAD"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Splinter"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Dzao"): {
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "BEST"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Graines", "Saurona"): {
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Fung"): {
            ("ETE", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("ETE", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Redhot"): {
            ("AUTOMNE", "BEST"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Visc"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Mitexi"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Oath"): {
            ("ETE", "BAD"),
        },
    },
}

#: {zone: {(famille, matière): {(saison, condition)}}} — l'excellente.
#:
#: Armory ne range pas les excellentes par zone : elles valent pour
#: les quatre, restreintes aux matières que la zone porte.
EXCELLENTES = {
    "Sources Interdites": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Eyota"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Tama"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Boucles", "Yana"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("ETE", "BAD"),
            ("ETE", "BEST"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Carapace", "Splinter"): {
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Buo"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Graines", "Caprice"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Graines", "Silvio"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Redhot"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Écorce", "Beckers"): {
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Mitexi"): {
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Écorce", "Oath"): {
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Écorce", "Perfling"): {
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Hash"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Soo"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Scrath"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Horny"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Caprice"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
        },
        ("Graines", "Saurona"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Résine", "Dung"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Résine", "Fung"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Résine", "Glue"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Visc"): {
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Écorce", "Beckers"): {
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Perfling"): {
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Beng"): {
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Hash"): {
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Bois", "Eyota"): {
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Tama"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Horny"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Buo"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Fibres", "Dzao"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Caprice"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Graines", "Saurona"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Huile", "Irin"): {
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Fung"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Résine", "Glue"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Sève", "Redhot"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Écorce", "Beckers"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Mitexi"): {
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Perfling"): {
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
        },
    },
    "Profondeurs Interdites": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Soo"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Abhaya"): {
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Bois", "Eyota"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Bois", "Kachine"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Bois", "Tama"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("ETE", "WORST"),
        },
        ("Boucles", "Patee"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Horny"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Carapace", "Splinter"): {
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("ETE", "BAD"),
            ("ETE", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Fibres", "Buo"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Fibres", "Dzao"): {
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Caprice"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Graines", "Sarina"): {
            ("ETE", "BEST"),
            ("ETE", "WORST"),
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
        },
        ("Graines", "Saurona"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "BEST"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Fung"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Résine", "Glue"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Dante"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Enola"): {
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Écorce", "Beckers"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Mitexi"): {
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Perfling"): {
            ("HIVER", "BEST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "WORST"),
        },
    },
}

#: {zone: {(famille, matière): {(saison, condition)}}} — le choix.
#:
#: Vide, et volontairement : aucune source ne le suit.
CHOIX = {
    "Sources Interdites": {
    },
    "Terre de la Continuité": {
    },
    "Cité Engloutie": {
    },
    "Profondeurs Interdites": {
    },
}

#: {(famille, matière): {(saison, condition)}} — les excellentes des
#: **continents**, qui ne parlent pas des Primes.
#:
#: Le tutoriel écrit que ce pop est identique sur tous les continents,
#: et les gisements correspondants sont au Gouffre d'Ichor ou à la
#: Porte des Vents. Deux saisons, deux conditions par matière.
EXCELLENTES_CONTINENTS = {
    ("Ambres", "Beng"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "GOOD"),
        ("HIVER", "BAD"),
        ("HIVER", "GOOD"),
    },
    ("Ambres", "Hash"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "WORST"),
        ("HIVER", "BEST"),
        ("HIVER", "WORST"),
    },
    ("Ambres", "Pha"): {
        ("AUTOMNE", "GOOD"),
        ("AUTOMNE", "WORST"),
        ("ETE", "GOOD"),
        ("ETE", "WORST"),
    },
    ("Ambres", "Sha"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "GOOD"),
        ("HIVER", "BEST"),
        ("HIVER", "GOOD"),
    },
    ("Ambres", "Soo"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "BEST"),
        ("HIVER", "BAD"),
        ("HIVER", "BEST"),
    },
    ("Ambres", "Zun"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "WORST"),
        ("ETE", "BAD"),
        ("ETE", "WORST"),
    },
    ("Bois", "Abhaya"): {
        ("AUTOMNE", "GOOD"),
        ("AUTOMNE", "WORST"),
        ("HIVER", "GOOD"),
        ("HIVER", "WORST"),
    },
    ("Bois", "Eyota"): {
        ("ETE", "BEST"),
        ("ETE", "GOOD"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Bois", "Kachine"): {
        ("ETE", "BEST"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "WORST"),
    },
    ("Bois", "Motega"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "WORST"),
        ("HIVER", "BAD"),
        ("HIVER", "WORST"),
    },
    ("Bois", "Tama"): {
        ("ETE", "BAD"),
        ("ETE", "BEST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "BEST"),
    },
    ("Boucles", "Nita"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "WORST"),
        ("ETE", "BEST"),
        ("ETE", "WORST"),
    },
    ("Boucles", "Patee"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "GOOD"),
        ("ETE", "BEST"),
        ("ETE", "GOOD"),
    },
    ("Boucles", "Scrath"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "GOOD"),
        ("ETE", "BAD"),
        ("ETE", "GOOD"),
    },
    ("Boucles", "Tansy"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "WORST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Boucles", "Yana"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "BEST"),
        ("ETE", "BAD"),
        ("ETE", "BEST"),
    },
    ("Carapace", "Big"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "WORST"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "WORST"),
    },
    ("Carapace", "Cuty"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "GOOD"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Carapace", "Horny"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "GOOD"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Carapace", "Smart"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "BEST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "BEST"),
    },
    ("Carapace", "Splinter"): {
        ("AUTOMNE", "GOOD"),
        ("AUTOMNE", "WORST"),
        ("PRINTEMPS", "GOOD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Fibres", "Anete"): {
        ("ETE", "BAD"),
        ("ETE", "BEST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "BEST"),
    },
    ("Fibres", "Buo"): {
        ("ETE", "BAD"),
        ("ETE", "WORST"),
        ("HIVER", "BAD"),
        ("HIVER", "WORST"),
    },
    ("Fibres", "Dzao"): {
        ("ETE", "BEST"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "WORST"),
    },
    ("Fibres", "Shu"): {
        ("ETE", "BEST"),
        ("ETE", "GOOD"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Graines", "Caprice"): {
        ("ETE", "BAD"),
        ("ETE", "BEST"),
        ("HIVER", "BAD"),
        ("HIVER", "BEST"),
    },
    ("Graines", "Sarina"): {
        ("ETE", "BEST"),
        ("ETE", "WORST"),
        ("HIVER", "BEST"),
        ("HIVER", "WORST"),
    },
    ("Graines", "Saurona"): {
        ("ETE", "BAD"),
        ("ETE", "GOOD"),
        ("HIVER", "BAD"),
        ("HIVER", "GOOD"),
    },
    ("Graines", "Silvio"): {
        ("ETE", "GOOD"),
        ("ETE", "WORST"),
        ("HIVER", "GOOD"),
        ("HIVER", "WORST"),
    },
    ("Huile", "Gulatch"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "BEST"),
        ("HIVER", "BAD"),
        ("HIVER", "BEST"),
    },
    ("Huile", "Irin"): {
        ("AUTOMNE", "GOOD"),
        ("AUTOMNE", "WORST"),
        ("HIVER", "GOOD"),
        ("HIVER", "WORST"),
    },
    ("Huile", "Koorin"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "GOOD"),
        ("HIVER", "BAD"),
        ("HIVER", "GOOD"),
    },
    ("Huile", "Pilan"): {
        ("AUTOMNE", "BAD"),
        ("AUTOMNE", "WORST"),
        ("HIVER", "BAD"),
        ("HIVER", "WORST"),
    },
    ("Résine", "Dung"): {
        ("AUTOMNE", "BEST"),
        ("AUTOMNE", "GOOD"),
        ("HIVER", "BEST"),
        ("HIVER", "GOOD"),
    },
    ("Résine", "Fung"): {
        ("ETE", "BAD"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Résine", "Glue"): {
        ("ETE", "BAD"),
        ("ETE", "GOOD"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Résine", "Moon"): {
        ("ETE", "GOOD"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "GOOD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Sève", "Dante"): {
        ("ETE", "BAD"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Sève", "Enola"): {
        ("HIVER", "BEST"),
        ("HIVER", "GOOD"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Sève", "Redhot"): {
        ("ETE", "BAD"),
        ("ETE", "GOOD"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Sève", "Silverweed"): {
        ("HIVER", "BAD"),
        ("HIVER", "BEST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "BEST"),
    },
    ("Sève", "Visc"): {
        ("ETE", "GOOD"),
        ("ETE", "WORST"),
        ("PRINTEMPS", "GOOD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Écorce", "Adriel"): {
        ("HIVER", "BEST"),
        ("HIVER", "GOOD"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Écorce", "Beckers"): {
        ("HIVER", "BAD"),
        ("HIVER", "GOOD"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "GOOD"),
    },
    ("Écorce", "Mitexi"): {
        ("HIVER", "BAD"),
        ("HIVER", "WORST"),
        ("PRINTEMPS", "BAD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Écorce", "Oath"): {
        ("HIVER", "GOOD"),
        ("HIVER", "WORST"),
        ("PRINTEMPS", "GOOD"),
        ("PRINTEMPS", "WORST"),
    },
    ("Écorce", "Perfling"): {
        ("HIVER", "BEST"),
        ("HIVER", "WORST"),
        ("PRINTEMPS", "BEST"),
        ("PRINTEMPS", "WORST"),
    },
}
