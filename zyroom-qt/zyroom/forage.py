"""Ce que rend un gisement des Primes, selon la zone, la saison et le temps.

Fichier produit par ../zyroom-android/outils/table_forage.py — ne pas
modifier à la main.

**Tout vient du relevé de terrain des foreuses de la guilde**, saisi
case par case sur https://xiom.be/forage/ : quatre cent vingt-six
créneaux pour le suprême, deux cent quarante-quatre pour l'excellente.
C'est la seule source qui ait été mesurée dans les Primes ; le reste —
le tracker d'atys.us, Ballistic Mystix, les classeurs de 2009 — en
était déduit, et se trompe une fois sur deux.

Le choix reste vide : personne ne le relève, et le déduire par
élimination ferait dire à l'écran plus que ce qu'on sait.
"""

#: {zone: {(famille, matière): {(saison, condition)}}} — le suprême.
#:
#: Une vingtaine de matières par zone dès que le temps est exécrable,
#: une poignée d'autres à un créneau précis. Rien ne peut le
#: contredire : `verifie()` refuse d'écrire une table qui s'en écarte.
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
#: Du même relevé que le suprême : cinquante-six créneaux vus en jeu
#: par les foreuses, cent quatre-vingt-huit rapportés par une autre
#: source et cochés en orange, qui restent à confirmer.
EXCELLENTES = {
    "Sources Interdites": {
        ("Ambres", "Beng"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Boucles", "Scrath"): {
            ("ETE", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "BEST"),
        },
        ("Fibres", "Dzao"): {
            ("HIVER", "BEST"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "BAD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
        },
        ("Sève", "Visc"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Oath"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Hash"): {
            ("AUTOMNE", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Eyota"): {
            ("HIVER", "BAD"),
        },
        ("Bois", "Motega"): {
            ("HIVER", "BAD"),
        },
        ("Bois", "Tama"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("ETE", "BAD"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "BAD"),
        },
        ("Huile", "Gulatch"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Huile", "Irin"): {
            ("ETE", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("HIVER", "BAD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Sève", "Dante"): {
            ("HIVER", "BAD"),
        },
        ("Sève", "Enola"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Visc"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Écorce", "Mitexi"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Hash"): {
            ("AUTOMNE", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Soo"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
            ("HIVER", "BAD"),
            ("HIVER", "WORST"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Saurona"): {
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "BAD"),
        },
        ("Huile", "Irin"): {
            ("HIVER", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Résine", "Moon"): {
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Redhot"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
        },
        ("Écorce", "Oath"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
    },
    "Profondeurs Interdites": {
        ("Ambres", "Hash"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Soo"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Bois", "Tama"): {
            ("HIVER", "BAD"),
        },
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Saurona"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Gulatch"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Fung"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Écorce", "Oath"): {
            ("ETE", "BAD"),
        },
    },
}

#: {zone: {(famille, matière): {(saison, condition)}}} — ce qui reste
#: à vérifier en jeu.
#:
#: Les croix oranges du relevé : cochées d'après une autre source, et
#: jamais vues sur place. Elles font partie d'EXCELLENTES -- l'écran
#: les affiche, une XL annoncée à tort coûte un aller-retour, une XL
#: tue coûte tout le reste -- mais on les distingue pour dire où aller
#: les confirmer, et pour qu'une croix qui ne sort jamais finisse par
#: se démasquer.
A_CONFIRMER = {
    "Sources Interdites": {
        ("Ambres", "Beng"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
        },
        ("Boucles", "Nita"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Boucles", "Scrath"): {
            ("ETE", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Carapace", "Cuty"): {
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Carapace", "Splinter"): {
            ("HIVER", "BAD"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BAD"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Koorin"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Pilan"): {
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Dung"): {
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Écorce", "Beckers"): {
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Oath"): {
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Eyota"): {
            ("HIVER", "BAD"),
        },
        ("Bois", "Motega"): {
            ("HIVER", "BAD"),
        },
        ("Bois", "Tama"): {
            ("ETE", "BEST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("ETE", "BAD"),
        },
        ("Fibres", "Anete"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Gulatch"): {
            ("ETE", "BEST"),
        },
        ("Huile", "Koorin"): {
            ("HIVER", "BAD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BAD"),
        },
        ("Sève", "Dante"): {
            ("HIVER", "BAD"),
        },
        ("Sève", "Enola"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "BAD"),
        },
        ("Écorce", "Mitexi"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Soo"): {
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("ETE", "GOOD"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Redhot"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
        },
        ("Écorce", "Oath"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
    },
    "Profondeurs Interdites": {
        ("Ambres", "Hash"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Pha"): {
            ("ETE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Ambres", "Soo"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Abhaya"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Saurona"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Gulatch"): {
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Dung"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Fung"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BAD"),
            ("PRINTEMPS", "BAD"),
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
