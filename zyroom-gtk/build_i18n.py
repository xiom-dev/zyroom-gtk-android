#!/usr/bin/env python3
"""Génère les catalogues gettext (.mo) EN et DE pour ZyRoom GTK.

Les chaînes source sont en français (msgid). msgfmt n'étant pas requis, on écrit
directement le format .mo (binaire standard, lu par gettext).

Usage : python3 build_i18n.py
"""
import array
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALE = os.path.join(HERE, "zyroom", "locale")

# --- Traductions français -> anglais ---------------------------------------
EN = {
    # Chrome fenêtre principale
    "Ajouter un personnage ou une guilde (clé API)": "Add a character or guild (API key)",
    "Retirer l'entité sélectionnée": "Remove the selected entity",
    "Resynchroniser depuis l'API": "Resynchronize from the API",
    "Données calculées par l'API": "Data computed by the API",
    "Charger string_client.pack (noms d'items lisibles)": "Load string_client.pack (readable item names)",
    "Options…": "Options…", "Analyser un chatlog…": "Analyze a chat log…",
    "Sauvegarder maintenant": "Back up now", "Menu": "Menu", "Alertes": "Alerts",
    "Cliquer pour agrandir": "Click to enlarge",
    "Entité :": "Entity:", "Inventaire :": "Inventory:", "Volume :": "Volume:",
    "Rechercher un item par nom…": "Search an item by name…",
    "Filtres": "Filters", "Trier :": "Sort:", "Ordre d'origine": "Original order",
    "Ordre croissant/décroissant": "Ascending/descending order", "Réinit.": "Reset",
    "à": "to", "Qualité": "Quality", "Cadenas": "Padlock",
    "Avec bonus": "With bonus", "En vente": "For sale",
    # Types / classes / écosystèmes / équipement
    "Type d'objet": "Item type", "Classe": "Class", "Écosystème": "Ecosystem",
    "Équipement": "Equipment", "Type": "Type", "Volume": "Volume",
    "Quantité": "Quantity", "Prix": "Price", "Nom": "Name",
    "Matière animale": "Animal material", "Matière naturelle": "Natural material",
    "Matière système": "System material", "Catalyseur": "Catalyst",
    "Téléporteur": "Teleporter", "Autre": "Other",
    "Basique": "Basic", "Fine": "Fine", "Choix": "Choice", "Excellente": "Excellent",
    "Suprême": "Supreme", "—": "—",
    "Commun": "Common", "Primes Racines": "Prime Roots", "Désert": "Desert",
    "Jungle": "Jungle", "Forêt": "Forest", "Lacs": "Lakes",
    "Armure légère": "Light armor", "Armure moyenne": "Medium armor",
    "Armure lourde": "Heavy armor", "Arme mêlée": "Melee weapon",
    "Arme distance": "Ranged weapon", "Amplificateur": "Amplifier", "Bijou": "Jewel",
    "Bouclier": "Buckler", "Grand bouclier": "Shield", "Outil": "Tool",
    "Munition": "Ammo",
    # Inventaires
    "Sac": "Bag", "Appartement": "Apartment", "Mektoub": "Mektoub", "Monture": "Mount",
    "Zig": "Zig", "Ventes": "Sales", "Coffre": "Chest",
    # Détails
    "Général": "General", "Combat": "Combat", "Protection": "Protection",
    "Bonus": "Bonus", "Matière": "Material", "Vente": "Sale",
    "Fiche": "Sheet", "Identifiant": "Identifier", "Poids": "Weight",
    "Durabilité": "Durability", "Protégé": "Protected", "Dégâts": "Damage",
    "Vitesse": "Speed", "Portée": "Range", "Mod. esquive": "Dodge mod.",
    "Mod. parade": "Parry mod.", "Mod. esquive adverse": "Adversary dodge mod.",
    "Mod. parade adverse": "Adversary parry mod.",
    "Facteur de protection": "Protection factor", "Prot. tranchant max.": "Max slashing prot.",
    "Prot. contondant max.": "Max blunt prot.", "Prot. perforant max.": "Max piercing prot.",
    "Vit. sort élémentaire": "Elemental cast speed", "Puiss. élémentaire": "Elemental power",
    "Vit. affliction off.": "Off. affliction cast speed", "Puiss. affliction off.": "Off. affliction power",
    "Vit. soin": "Heal cast speed", "Puiss. soin": "Heal power",
    "Vit. affliction déf.": "Def. affliction cast speed", "Puiss. affliction déf.": "Def. affliction power",
    "HP": "HP", "Sève": "Sap", "Stamina": "Stamina", "Focus": "Focus",
    # Les quatre bonus, sous les noms des jauges du jeu (filtre et infobulle)
    "Vie": "Life", "Endurance": "Stamina", "Concentration": "Focus",
    "Catégorie 1": "Category 1", "Catégorie 2": "Category 2", "Couleurs": "Colors",
    "Continent": "Continent", "Expire dans": "Expires in",
    # Caractéristiques de matière (_MAT_SPEC)
    "Toutes": "All", "Légèreté": "Lightness", "Charge de sève": "Sap Load",
    "Mod. esquive adverse": "Adversary Dodge Mod.", "Facteur de protection": "Protection Factor",
    "Prot. acide": "Acid Prot.", "Prot. froid": "Cold Prot.", "Prot. pourriture": "Rot Prot.",
    "Prot. feu": "Fire Prot.", "Prot. onde de choc": "Shockwave Prot.",
    "Prot. poison": "Poison Prot.", "Prot. électricité": "Electricity Prot.",
    "Rés. désert": "Desert Res.", "Rés. forêt": "Forest Res.", "Rés. lacs": "Lakes Res.",
    "Rés. jungle": "Jungle Res.", "Rés. Primes Racines": "Prime Roots Res.",
    # Catégories de matière (_MAT_CATEGORY)
    "Lame": "Blade", "Pointe": "Point", "Masse": "Hammer", "Contrepoids": "Counterweight",
    "Manche": "Shaft", "Munition (balle)": "Ammo Bullet", "Canon": "Barrel",
    "Coque d'armure": "Armor Shell", "Enveloppe de munition": "Ammo Jacket",
    "Doublure": "Lining", "Explosif": "Explosive", "Rembourrage": "Stuffing",
    "Percuteur": "Firing Pin", "Attache d'armure": "Armor Clip", "Détente": "Trigger",
    "Sertissage": "Jewel Settings", "Poignée": "Grip", "Vêtement": "Clothes",
    "Focus magique": "Magic Focus",
    # Couleurs
    "inconnu": "unknown", "beige": "beige", "noir": "black", "bleu": "blue",
    "vert": "green", "violet": "purple", "rouge": "red", "turquoise": "turquoise",
    "blanc": "white",
    # Options
    "Options": "Options", "Langue": "Language", "Fichier string_client.pack": "string_client.pack file",
    "Dossier « save » de Ryzom": "Ryzom “save” folder",
    "Seuil d'alerte de volume (%)": "Volume alert threshold (%)",
    "Alerte ventes (heures avant expiration)": "Sales alert (hours before expiry)",
    "Alerte saison (heures avant changement)": "Season alert (hours before change)",
    "Sauvegarder le dossier « save » à la fermeture": "Back up the “save” folder on close",
    "Utiliser un proxy HTTP": "Use an HTTP proxy", "Adresse du proxy": "Proxy address",
    "Port du proxy": "Proxy port", "Identifiant proxy": "Proxy username",
    "Mot de passe proxy": "Proxy password", "Parcourir…": "Browse…",
    "Annuler": "Cancel", "Enregistrer": "Save",
    # Chatlog
    "Analyse de chatlog": "Chat log analysis", "Filtrer les messages…": "Filter messages…",
    "Système": "System", "Tous les canaux": "All channels", "Copier HTML": "Copy HTML",
    "Copier BBCode": "Copy BBCode", "Copier texte": "Copy text",
    # Onglets et journal des mouvements
    "Inventaire": "Inventory", "Journal": "Log",
    "Rechercher dans le journal…": "Search the log…",
    "Tout": "All", "Entrées": "In", "Sorties": "Out",
    "Copier": "Copy", "Vider": "Clear",
    "Copier les lignes affichées": "Copy the displayed lines",
    "Effacer le journal de cette entité": "Clear this entity's log",
    "Vider le journal ?": "Clear the log?",
}

# --- Traductions français -> allemand (best-effort) ------------------------
DE = {
    "Ajouter un personnage ou une guilde (clé API)": "Charakter oder Gilde hinzufügen (API-Schlüssel)",
    "Retirer l'entité sélectionnée": "Ausgewählte Einheit entfernen",
    "Resynchroniser depuis l'API": "Von der API neu synchronisieren",
    "Données calculées par l'API": "Von der API berechnete Daten",
    "Charger string_client.pack (noms d'items lisibles)": "string_client.pack laden (lesbare Gegenstandsnamen)",
    "Options…": "Optionen…", "Analyser un chatlog…": "Chatprotokoll analysieren…",
    "Sauvegarder maintenant": "Jetzt sichern", "Menu": "Menü", "Alertes": "Warnungen",
    "Cliquer pour agrandir": "Zum Vergrößern klicken",
    "Entité :": "Einheit:", "Inventaire :": "Inventar:", "Volume :": "Volumen:",
    "Rechercher un item par nom…": "Gegenstand nach Namen suchen…",
    "Filtres": "Filter", "Trier :": "Sortieren:", "Ordre d'origine": "Ursprüngliche Reihenfolge",
    "Ordre croissant/décroissant": "Auf-/absteigende Reihenfolge", "Réinit.": "Zurücksetzen",
    "à": "bis", "Qualité": "Qualität", "Cadenas": "Vorhängeschloss",
    "Avec bonus": "Mit Bonus", "En vente": "Zum Verkauf",
    "Type d'objet": "Objekttyp", "Classe": "Klasse", "Écosystème": "Ökosystem",
    "Équipement": "Ausrüstung", "Type": "Typ", "Volume": "Volumen",
    "Quantité": "Menge", "Prix": "Preis", "Nom": "Name",
    "Matière animale": "Tiermaterial", "Matière naturelle": "Naturmaterial",
    "Matière système": "Systemmaterial", "Catalyseur": "Katalysator",
    "Téléporteur": "Teleporter", "Autre": "Andere",
    "Basique": "Einfach", "Fine": "Fein", "Choix": "Auswahl", "Excellente": "Exzellent",
    "Suprême": "Höchste", "—": "—",
    "Commun": "Allgemein", "Primes Racines": "Urwurzeln", "Désert": "Wüste",
    "Jungle": "Dschungel", "Forêt": "Wald", "Lacs": "Seen",
    "Armure légère": "Leichte Rüstung", "Armure moyenne": "Mittlere Rüstung",
    "Armure lourde": "Schwere Rüstung", "Arme mêlée": "Nahkampfwaffe",
    "Arme distance": "Fernkampfwaffe", "Amplificateur": "Verstärker", "Bijou": "Schmuck",
    "Bouclier": "Buckler", "Grand bouclier": "Schild", "Outil": "Werkzeug",
    "Munition": "Munition",
    "Sac": "Tasche", "Appartement": "Wohnung", "Mektoub": "Mektoub", "Monture": "Reittier",
    "Zig": "Zig", "Ventes": "Verkäufe", "Coffre": "Truhe",
    "Général": "Allgemein", "Combat": "Kampf", "Protection": "Schutz",
    "Bonus": "Bonus", "Matière": "Material", "Vente": "Verkauf",
    "Fiche": "Blatt", "Identifiant": "Kennung", "Poids": "Gewicht",
    "Durabilité": "Haltbarkeit", "Protégé": "Geschützt", "Dégâts": "Schaden",
    "Vitesse": "Geschwindigkeit", "Portée": "Reichweite",
    "HP": "LP", "Sève": "Saft", "Stamina": "Ausdauer", "Focus": "Fokus",
    "Vie": "Leben", "Endurance": "Ausdauer", "Concentration": "Fokus",
    "Catégorie 1": "Kategorie 1", "Catégorie 2": "Kategorie 2", "Couleurs": "Farben",
    "Continent": "Kontinent", "Expire dans": "Läuft ab in",
    "Toutes": "Alle", "Légèreté": "Leichtigkeit", "Charge de sève": "Saftladung",
    "Lame": "Klinge", "Pointe": "Spitze", "Masse": "Hammer", "Poignée": "Griff",
    "Vêtement": "Kleidung", "Focus magique": "Magiefokus",
    "inconnu": "unbekannt", "beige": "beige", "noir": "schwarz", "bleu": "blau",
    "vert": "grün", "violet": "violett", "rouge": "rot", "turquoise": "türkis",
    "blanc": "weiß",
    "Options": "Optionen", "Langue": "Sprache", "Fichier string_client.pack": "string_client.pack-Datei",
    "Dossier « save » de Ryzom": "Ryzom-„save“-Ordner",
    "Seuil d'alerte de volume (%)": "Volumen-Warnschwelle (%)",
    "Alerte ventes (heures avant expiration)": "Verkaufswarnung (Stunden vor Ablauf)",
    "Alerte saison (heures avant changement)": "Jahreszeitwarnung (Stunden vor Wechsel)",
    "Sauvegarder le dossier « save » à la fermeture": "„save“-Ordner beim Schließen sichern",
    "Utiliser un proxy HTTP": "HTTP-Proxy verwenden", "Adresse du proxy": "Proxy-Adresse",
    "Port du proxy": "Proxy-Port", "Identifiant proxy": "Proxy-Benutzer",
    "Mot de passe proxy": "Proxy-Passwort", "Parcourir…": "Durchsuchen…",
    "Annuler": "Abbrechen", "Enregistrer": "Speichern",
    "Analyse de chatlog": "Chatprotokoll-Analyse", "Filtrer les messages…": "Nachrichten filtern…",
    "Système": "System", "Tous les canaux": "Alle Kanäle", "Copier HTML": "HTML kopieren",
    "Copier BBCode": "BBCode kopieren", "Copier texte": "Text kopieren",
    # Reiter und Bewegungsprotokoll
    "Inventaire": "Inventar", "Journal": "Protokoll",
    "Rechercher dans le journal…": "Im Protokoll suchen…",
    "Tout": "Alle", "Entrées": "Zugänge", "Sorties": "Abgänge",
    "Copier": "Kopieren", "Vider": "Leeren",
    "Copier les lignes affichées": "Angezeigte Zeilen kopieren",
    "Effacer le journal de cette entité": "Protokoll dieser Einheit löschen",
    "Vider le journal ?": "Protokoll leeren?",
}


def write_mo(messages: dict, path: str) -> None:
    """Écrit un fichier .mo (format GNU gettext) depuis {msgid: msgstr}."""
    items = {"": "Content-Type: text/plain; charset=UTF-8\n"}
    items.update({k: v for k, v in messages.items() if v})
    keys = sorted(items.keys())
    offsets = []
    ids = strs = b""
    for k in keys:
        msgid = k.encode("utf-8")
        msgstr = items[k].encode("utf-8")
        offsets.append((len(ids), len(msgid), len(strs), len(msgstr)))
        ids += msgid + b"\x00"
        strs += msgstr + b"\x00"
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]
    output = struct.pack("Iiiiiii", 0x950412de, 0, n, 7 * 4,
                         7 * 4 + n * 8, 0, 0)
    output += array.array("i", koffsets + voffsets).tobytes()
    output += ids + strs
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(output)


def main() -> None:
    for lang, catalog in (("en", EN), ("de", DE)):
        path = os.path.join(LOCALE, lang, "LC_MESSAGES", "zyroom.mo")
        write_mo(catalog, path)
        print(f"{lang}: {len(catalog)} chaînes -> {path}")


if __name__ == "__main__":
    main()
