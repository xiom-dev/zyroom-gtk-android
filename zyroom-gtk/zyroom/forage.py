"""Ce que rend un gisement des Primes, selon la zone, la saison et le temps.

Fichier produit par ../zyroom-android/outils/table_forage.py — ne pas
modifier à la main. Il croise les deux relevés de la guilde gardés
dans `donnees/` : le classeur des saisons, complet, et la cartographie
du Tuto Forage Prime, plus récente mais inachevée.

**Les quatre zones ne se ressemblent pas.** C'était l'erreur d'avant :
une seule table pour les quatre, alors que la Terre de la Continuité
ne sort pas ce que sortent les Sources Interdites au même moment.

Le suprême est complet. L'excellente et le choix ne sont relevés que
par endroits : la guilde y travaille encore, et un silence ne veut pas
dire « rien ne sort ».
"""

#: {zone: {(famille, matière): {(saison, condition)}}} — le suprême.
#:
#: Une vingtaine de matières par zone sortent dès que le temps est
#: exécrable, aux quatre saisons ; les autres à un créneau précis.
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
            ("ETE", "BEST"),
        },
        ("Bois", "Eyota"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Kachine"): {
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
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "BAD"),
        },
        ("Boucles", "Yana"): {
            ("PRINTEMPS", "GOOD"),
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
        ("Carapace", "Horny"): {
            ("ETE", "BAD"),
        },
        ("Carapace", "Smart"): {
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
            ("HIVER", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
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
            ("AUTOMNE", "GOOD"),
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
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "GOOD"),
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
            ("HIVER", "BEST"),
        },
        ("Écorce", "Oath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Écorce", "Perfling"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Beng"): {
            ("AUTOMNE", "BEST"),
            ("HIVER", "BEST"),
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
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Bois", "Tama"): {
            ("HIVER", "GOOD"),
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
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "WORST"),
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
        ("Carapace", "Horny"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
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
            ("HIVER", "BEST"),
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
        ("Huile", "Pilan"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Résine", "Dung"): {
            ("ETE", "WORST"),
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
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Adriel"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
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
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
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
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Tansy"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Yana"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Big"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Cuty"): {
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Horny"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Smart"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
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
            ("ETE", "BEST"),
            ("HIVER", "BEST"),
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
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "BEST"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("HIVER", "WORST"),
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
        ("Boucles", "Scrath"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Boucles", "Tansy"): {
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
        ("Carapace", "Horny"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Carapace", "Smart"): {
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
        },
        ("Fibres", "Shu"): {
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
        ("Huile", "Koorin"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Pilan"): {
            ("HIVER", "BAD"),
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
            ("HIVER", "BEST"),
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
        ("Écorce", "Perfling"): {
            ("AUTOMNE", "WORST"),
            ("ETE", "WORST"),
            ("HIVER", "WORST"),
            ("PRINTEMPS", "WORST"),
        },
    },
}

#: {zone: {(famille, matière): {(saison, condition)}}} — l'excellente
#: des Primes, telle que la cartographie la donne. Clairsemée.
EXCELLENTES = {
    "Sources Interdites": {
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("ETE", "WORST"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BAD"),
        },
        ("Bois", "Motega"): {
            ("AUTOMNE", "BAD"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Boucles", "Scrath"): {
            ("ETE", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("ETE", "BAD"),
            ("HIVER", "BEST"),
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Sarina"): {
            ("AUTOMNE", "BAD"),
        },
        ("Huile", "Irin"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "WORST"),
            ("PRINTEMPS", "BAD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BAD"),
            ("PRINTEMPS", "BAD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
        },
        ("Sève", "Visc"): {
            ("AUTOMNE", "BAD"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "GOOD"),
        },
    },
    "Terre de la Continuité": {
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
        ("Carapace", "Big"): {
            ("ETE", "BAD"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Huile", "Gulatch"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("HIVER", "BAD"),
        },
        ("Résine", "Moon"): {
            ("AUTOMNE", "BAD"),
        },
        ("Sève", "Dante"): {
            ("HIVER", "BAD"),
        },
        ("Sève", "Enola"): {
            ("HIVER", "BAD"),
        },
        ("Sève", "Visc"): {
            ("HIVER", "BAD"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Sha"): {
            ("ETE", "BAD"),
        },
        ("Ambres", "Zun"): {
            ("ETE", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "BAD"),
        },
        ("Huile", "Koorin"): {
            ("ETE", "BEST"),
        },
    },
    "Profondeurs Interdites": {
        ("Bois", "Tama"): {
            ("HIVER", "BAD"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "BAD"),
            ("HIVER", "BAD"),
        },
        ("Fibres", "Dzao"): {
            ("AUTOMNE", "BAD"),
        },
        ("Sève", "Silverweed"): {
            ("AUTOMNE", "GOOD"),
        },
    },
}

#: {zone: {(famille, matière): {(saison, condition)}}} — le choix,
#: là où la guilde l'a noté. Clairsemé lui aussi.
CHOIX = {
    "Sources Interdites": {
        ("Ambres", "Pha"): {
            ("AUTOMNE", "BEST"),
        },
        ("Ambres", "Sha"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Boucles", "Nita"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Carapace", "Cuty"): {
            ("AUTOMNE", "BEST"),
        },
        ("Carapace", "Splinter"): {
            ("ETE", "GOOD"),
        },
        ("Fibres", "Anete"): {
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "GOOD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Fibres", "Shu"): {
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Huile", "Pilan"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
        },
        ("Résine", "Glue"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "WORST"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Sève", "Visc"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Écorce", "Beckers"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
    },
    "Terre de la Continuité": {
        ("Ambres", "Zun"): {
            ("PRINTEMPS", "BAD"),
        },
        ("Bois", "Kachine"): {
            ("HIVER", "BAD"),
        },
        ("Boucles", "Tansy"): {
            ("HIVER", "BAD"),
            ("HIVER", "GOOD"),
            ("HIVER", "WORST"),
        },
        ("Carapace", "Splinter"): {
            ("AUTOMNE", "BAD"),
            ("AUTOMNE", "GOOD"),
            ("AUTOMNE", "WORST"),
        },
        ("Fibres", "Anete"): {
            ("HIVER", "BAD"),
        },
        ("Fibres", "Shu"): {
            ("HIVER", "GOOD"),
        },
        ("Huile", "Gulatch"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
            ("PRINTEMPS", "BAD"),
            ("PRINTEMPS", "WORST"),
        },
        ("Huile", "Pilan"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Sève", "Dante"): {
            ("HIVER", "BEST"),
            ("HIVER", "GOOD"),
        },
        ("Sève", "Enola"): {
            ("HIVER", "GOOD"),
        },
        ("Sève", "Silverweed"): {
            ("HIVER", "WORST"),
        },
        ("Écorce", "Adriel"): {
            ("ETE", "BAD"),
            ("ETE", "GOOD"),
            ("ETE", "WORST"),
        },
    },
    "Cité Engloutie": {
        ("Ambres", "Sha"): {
            ("ETE", "BAD"),
        },
        ("Ambres", "Soo"): {
            ("ETE", "GOOD"),
        },
        ("Ambres", "Zun"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
        ("Fibres", "Shu"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
            ("PRINTEMPS", "BEST"),
            ("PRINTEMPS", "GOOD"),
        },
        ("Graines", "Silvio"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("ETE", "GOOD"),
        },
        ("Huile", "Koorin"): {
            ("ETE", "BEST"),
            ("ETE", "GOOD"),
        },
    },
    "Profondeurs Interdites": {
        ("Carapace", "Big"): {
            ("HIVER", "GOOD"),
        },
        ("Fibres", "Buo"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
            ("HIVER", "GOOD"),
        },
        ("Graines", "Caprice"): {
            ("AUTOMNE", "GOOD"),
        },
        ("Huile", "Gulatch"): {
            ("HIVER", "GOOD"),
        },
        ("Sève", "Dante"): {
            ("AUTOMNE", "BEST"),
            ("AUTOMNE", "GOOD"),
        },
        ("Écorce", "Mitexi"): {
            ("HIVER", "GOOD"),
        },
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
