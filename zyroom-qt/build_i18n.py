#!/usr/bin/env python3
"""Génère les catalogues gettext (.mo) EN et DE de ZyRoom-Qt.

**On ne retraduit pas ce qui l'est déjà.** Le portage GTK tient un catalogue
depuis longtemps ; les chaînes que les deux interfaces partagent — et elles
sont nombreuses, le noyau est le même — sont reprises de là. Ce fichier ne
porte que ce qui est propre à ce portage-ci, et l'écriture du `.mo` elle-même
vient aussi de là.

Les chaînes source sont en français (ce sont les msgid) ; en l'absence de
traduction, gettext retombe dessus. Une chaîne oubliée ici s'affiche donc en
français, ce qui est laid mais pas cassé.

Usage : python3 build_i18n.py
"""
from __future__ import annotations

import importlib.util
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
LOCALE = os.path.join(ICI, "zyroom", "locale")
GTK = os.path.join(ICI, "..", "zyroom-gtk", "build_i18n.py")


def _catalogue_gtk():
    """Le catalogue du portage GTK, ou des dictionnaires vides s'il manque.

    Le chemin relatif est le même que celui de `outils/sync-noyau.sh` : les
    deux portages vivent côte à côte dans le dépôt. Absent — quelqu'un qui
    n'aurait cloné que ce dossier —, on construit ce qu'on peut plutôt que
    d'échouer.
    """
    if not os.path.isfile(GTK):
        print(f"Catalogue GTK introuvable ({GTK}) : seules les chaînes "
              f"propres à Qt seront traduites.", file=sys.stderr)
        return {}, {}, None
    spec = importlib.util.spec_from_file_location("build_i18n_gtk", GTK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EN, module.DE, module.write_mo


# --- Ce que ce portage ajoute : francais -> anglais ------------------------
EN = {
    # Barre du haut, navigation, entites
    "Entité :": "Entity:", "Inventaire :": "Inventory:",
    "Clés API": "API keys", "Ajouter": "Add", "Modifier": "Edit",
    "Fermer": "Close", "Personnage": "Character", "Guilde": "Guild",
    "personnage": "character", "guilde": "guild",
    "Clé API": "API key", "Clé": "Key", "Genre": "Kind",
    "Nom affiché (optionnel)": "Display name (optional)",
    "Obtenir ma clé": "Get my key", "Coller": "Paste",
    "Coller la clé depuis le presse-papiers": "Paste the key from the clipboard",
    "Copier la clé dans le presse-papiers": "Copy the key to the clipboard",
    "Remplacer": "Replace", "Remplacer la clé": "Replace the key",
    "Retirer": "Remove", "Retirer cette entité": "Remove this entity",
    "Retirer « {} » ?": "Remove “{}”?",
    "Veuillez saisir une clé API.": "Please enter an API key.",
    "Vérification de la clé…": "Checking the key…",
    "Échec : {}": "Failed: {}",
    "Modules manquants : ": "Missing modules: ",
    "Synchronisation de {}…": "Synchronising {}…",
    "Échec de la synchro : {}": "Sync failed: {}",
    "Erreur : {}": "Error: {}",
    "Dernière synchro": "Last sync", "synchro {}": "synced {}",
    "Données calculées par l'API": "Data computed by the API",
    "Clés API : en ajouter une, relire ou remplacer celles qu'on a":
        "API keys: add one, read back or replace the ones you have",
    "Aucune clé enregistrée — l'onglet « Ajouter » est à côté.":
        "No key saved — the “Add” tab is right there.",
    "Nouvelle clé pour « {} ». Elle est vérifiée auprès de Ryzom avant "
    "d'être enregistrée.":
        "New key for “{}”. It is checked against Ryzom before "
        "being saved.",
    "Sa clé sera oubliée. Rien n'est supprimé chez Ryzom, et la remettre "
    "suffit à la retrouver.":
        "Its key will be forgotten. Nothing is deleted at Ryzom, and putting "
        "it back is enough to get it again.",
    "Une clé fait 41 signes. Celles de personnage commencent par « c », "
    "celles de guilde par « g ». Modules requis : ":
        "A key is 41 characters long. Character keys start with “c”, "
        "guild keys with “g”. Required modules: ",
    "Aucune entité — le bouton « + » ajoute un personnage ou une guilde à "
    "partir de sa clé.":
        "No entity — the “+” button adds a character or a "
        "guild from its key.",

    # Inventaire, objets
    "(capacité inconnue)": "(capacity unknown)",
    "Détails…": "Details…",
    "Copier l'identifiant": "Copy identifier",
    "Identifiant copié : {}": "Identifier copied: {}",
    "Réinitialiser l'icône": "Reset icon",
    "Enchantement : ": "Enchantment: ",
    "Charges de sève : {}": "Sap charges: {}",
    " (coût {})": " (cost {})",
    "oui": "yes", "expiré": "expired",
    "Choisir string_client.pack": "Choose string_client.pack",
    "Noms chargés depuis {}.": "Names loaded from {}.",
    "Impossible de lire ce fichier string_client.pack.":
        "Cannot read that string_client.pack file.",
    "Portrait": "Portrait",

    # Journal
    "Dappers": "Dappers",
    "{} lignes sur {} au journal": "{} lines out of {} in the log",
    "{} lignes copiées.": "{} lines copied.",
    "{} lignes affichées sur {} retenues ({} au journal) — affinez la "
    "recherche.":
        "{} lines shown out of {} kept ({} in the log) — narrow your "
        "search.",
    "Aucun mouvement enregistré. Le journal se remplit à chaque "
    "synchronisation où quelque chose a bougé.":
        "No movement recorded. The log fills up at every sync where something "
        "moved.",
    "Les {} mouvements enregistrés pour {} seront perdus. L'API ne permet "
    "pas de les reconstruire.":
        "The {} movements recorded for {} will be lost. The API cannot "
        "rebuild them.",
    "Journal de la guilde : {} mouvement(s) repris de la page.":
        "Guild log: {} movement(s) taken from the page.",

    # Effectif
    "Effectif": "Roster", "Effectif · %d": "Roster · %d",
    "Arrivées et départs": "Arrivals and departures",
    "Arrivées et départs · %d": "Arrivals and departures · %d",
    "Rechercher un membre…": "Search for a member…",
    "Aucun membre de ce nom.": "No member by that name.",
    "journal des %d derniers jours": "log of the last %d days",
    "arrivée": "arrival", "départ": "departure",
    "montée de grade": "promotion", "rétrogradation": "demotion",
    "départs et grades : date du relevé":
        "departures and ranks: date of the reading",
    "Aucune guilde consultée pour l'instant : ouvrez-en une une fois, et son "
    "effectif restera consultable d'ici.":
        "No guild looked at yet: open one once, and its roster stays "
        "readable from here.",
    "Aucun mouvement depuis le premier relevé. Le registre compare "
    "l'effectif d'une synchronisation à l'autre : l'API ne garde aucune "
    "histoire, seule l'application en tient une.":
        "No movement since the first reading. The register compares the "
        "roster from one sync to the next: the API keeps no history, only "
        "the application does.",

    # Avant-postes
    "Qui tient quoi": "Who holds what",
    "Journal des prises": "Capture log",
    "Actualiser": "Refresh",
    "Redemander l'annuaire des guildes": "Ask for the guild directory again",
    "Lecture de l'annuaire des guildes…": "Reading the guild directory…",
    "Annuaire indisponible : %s": "Directory unavailable: %s",
    "%d avant-postes tenus sur Atys": "%d outposts held on Atys",
    ", dont %d à %s": ", %d of them by %s",
    "Hors carte : ": "Off the map: ",
    "%s — pris par %s": "%s — taken by %s",
    "%s — perdu par %s": "%s — lost by %s",
    "%s — %s ▸ %s": "%s — %s ▸ %s",
    "Aucun changement de main depuis le premier relevé.":
        "No change of hands since the first reading.",
    "Premier relevé : rien à comparer. Les changements de main apparaîtront "
    "à partir du prochain.":
        "First reading: nothing to compare. Changes of hands will show from "
        "the next one on.",

    # Competences
    "Rechercher une compétence…": "Search for a skill…",
    "En cours": "In progress",
    "« En cours » ne garde que les niveaux entamés":
        "“In progress” keeps only the levels you have started",
    "Tout déplier": "Expand all", "Tout replier": "Collapse all",
    "%d compétences, %d affichées": "%d skills, %d shown",
    "%s pts · %s dépensés": "%s pts · %s spent",
    "Aucun personnage consulté pour l'instant : ouvrez-en un une fois, et "
    "son arbre restera consultable d'ici. L'API ne donne les compétences que "
    "pour un personnage, et seulement si la clé accorde ce module.":
        "No character looked at yet: open one once, and its tree stays "
        "readable from here. The API gives skills for a character only, and "
        "only if the key grants that module.",

    # Betes
    "Mektoubs": "Mektoubs", "Zigs": "Zigs", "aucune": "none",
    "dehors": "outside", "à l'écurie": "in the stable",
    "état inconnu": "state unknown", " · satiété %d": " · satiety %d",
    "%d bête dehors": "%d beast outside", "%d bêtes dehors": "%d beasts outside",
    "Aucune bête dehors : toutes sont rangées.":
        "No beast outside: they are all put away.",

    # Meteo et gisements
    "Lecture de la météo…": "Reading the weather…",
    "Météo indisponible : %s": "Weather unavailable: %s",
    "Cette saison": "This season",
    "Excellentes — %s": "Excellent — %s",
    "De jour": "By day", "De nuit": "By night",
    "  ·  en ce moment": "  ·  right now",
    "{} dans {} h": "{} in {} h",
    "Suprêmes — ce qui sort : %(condition)s, %(taux)d %%":
        "Supreme — what comes out: %(condition)s, %(taux)d %%",
    "Les Primes partagent une seule météo : celle-ci vaut pour les quatre "
    "zones.":
        "The Prime Roots share a single weather: this one holds for all four "
        "areas.",
    "humidité": "humidity", "gisement": "source", "gisements": "sources",
    "Positions : relevé de ballisticmystix.net, avec l'accord de son auteur":
        "Positions: survey by ballisticmystix.net, with its author's consent",

    # Alertes et surveillance
    "Aucune alerte": "No alert", "Aucune alerte.": "No alert.",
    "{} alerte(s)": "{} alert(s)",
    "Notifications du bureau": "Desktop notifications",
    "Notifications du bureau coupées": "Desktop notifications turned off",
    "Prévenir mouvement dappers": "Warn on dapper movement",
    "Surveiller": "Watch", "Surveiller un objet": "Watch an item",
    "Ne plus surveiller": "Stop watching",
    "Surveiller la quantité…": "Watch the quantity…",
    "Surveiller la durabilité…": "Watch the durability…",
    "Alerte si la quantité descend sous ce seuil :":
        "Alert if the quantity drops below this threshold:",
    "Alerte si la durabilité descend sous ce seuil :":
        "Alert if the durability drops below this threshold:",
    "Afficher les alertes sur le bureau (bulles près de l'horloge)":
        "Show alerts on the desktop (bubbles near the clock)",
    "Coupe les bulles qui s'affichent près de l'horloge à chaque "
    "synchronisation. Les alertes restent listées ici.":
        "Turns off the bubbles shown near the clock at every sync. The "
        "alerts stay listed here.",
    "Décochée, l'application n'envoie plus rien au bureau. Les alertes "
    "restent visibles dans la fenêtre de la cloche.":
        "Unchecked, the application sends nothing to the desktop. The alerts "
        "stay visible in the bell window.",
    "Une alerte à chaque relevé où les dappers ont bougé, dans un sens ou "
    "dans l'autre. Sans seuil à régler : un relevé rapporte au plus un "
    "mouvement d'argent, il ne peut donc pas noyer les autres.":
        "An alert at every reading where dappers moved, either way. No "
        "threshold to set: a reading brings at most one money movement, so "
        "it cannot drown the others.",

    # Presence
    "en ligne": "online", "vu à l'instant": "seen just now",
    "vu il y a {} min": "seen {} min ago", "vu il y a {} h": "seen {} h ago",
    "vu il y a {} j": "seen {} d ago", "vu le {}": "seen on {}",
    "Dernière connexion": "Last login",
    "Dernière déconnexion": "Last logout",
    "L'API ne montre que la dernière sauvegarde du personnage, écrite à la "
    "déconnexion : une connexion toute fraîche peut ne pas s'y voir encore.":
        "The API shows only the character's last save, written at logout: a "
        "brand-new login may not show in it yet.",

    # Chatlog
    "Analyse de chatlog": "Chat log analysis",
    "Choisir un fichier de chatlog": "Choose a chat log file",
    "Journaux (*.log *.txt);;Tous les fichiers (*)":
        "Logs (*.log *.txt);;All files (*)",
    "Filtrer les messages…": "Filter messages…",
    "Tous les canaux": "All channels", "Système": "System",
    "Copier HTML": "Copy HTML", "Copier BBCode": "Copy BBCode",
    "Copier texte": "Copy text",
    "{} / {} messages": "{} / {} messages",
    "{} / {} messages — {} affichés, affinez le filtre":
        "{} / {} messages — {} shown, narrow the filter",
    "{} messages copiés ({}).": "{} messages copied ({}).",
    "{} messages analysés.": "{} messages parsed.",
    "Lecture impossible : {}": "Cannot read: {}",
    "Ce fichier ne contient aucun message lisible.":
        "That file holds no readable message.",

    # Sauvegarde, options, mise a jour
    "Sauvegarde : ": "Backup: ",
    "Dossier « save » de Ryzom non configuré (voir Options).":
        "Ryzom “save” folder not configured (see Options).",
    "Options enregistrées.": "Options saved.",
    "Synchroniser à l'ouverture d'un personnage ou d'une guilde":
        "Sync when opening a character or a guild",
    "Mettre à jour": "Update",
    "Une nouvelle version est disponible": "A new version is available",
    "Une nouvelle version est disponible ({}).":
        "A new version is available ({}).",
    "Téléchargement de la mise à jour…": "Downloading the update…",
    "Téléchargement de la mise à jour… {} %": "Downloading the update… {} %",
    "Mise à jour impossible : {}": "Update failed: {}",
    "Mise à jour installée": "Update installed",
    "Elle ne prendra effet qu'au prochain lancement. Relancer maintenant ?":
        "It only takes effect at the next start. Restart now?",
    "Plus tard": "Later", "Relancer": "Restart",
    "Impossible de relancer automatiquement : fermez et rouvrez "
    "l'application pour utiliser la nouvelle version.":
        "Cannot restart automatically: close and reopen the application to "
        "use the new version.",

    # A propos
    "À propos…": "About…", "À propos de {}": "About {}",
    "Version {}": "Version {}",
    "Ce que c'est": "What it is", "Droits": "Rights", "Licence": "Licence",
    "Code source": "Source code", "Projet d'origine": "Original project",
    "Écrire à l'auteur": "Write to the author",
    "Données et images": "Data and images",
    "pour le zyRoom d'origine": "for the original zyRoom",
    "pour ce portage": "for this port",
    "Vos inventaires Ryzom et les coffres de la guilde, hors du jeu.<br>"
    "Dérivée du zyRoom de Misugi, écrit en Delphi pour Windows : {} en "
    "reprend les algorithmes et la lecture de l'API, et hérite donc de sa "
    "licence.":
        "Your Ryzom inventories and the guild chests, outside the game.<br>"
        "Derived from Misugi's zyRoom, written in Delphi for Windows: {} "
        "takes over its algorithms and its reading of the API, and so "
        "inherits its licence.",
    "GNU Affero General Public License, version 3 ou ultérieure.<br>"
    "Ce programme est fourni <b>sans aucune garantie</b>. Vous êtes libre de "
    "le redistribuer et de le modifier selon les termes de cette licence ; "
    "son texte complet accompagne l'application et se trouve aussi dans le "
    "dépôt.":
        "GNU Affero General Public License, version 3 or later.<br>"
        "This program comes with <b>absolutely no warranty</b>. You are free "
        "to redistribute it and to modify it under the terms of that "
        "licence; its full text ships with the application and is also in "
        "the repository.",
    "L'AGPL veut que l'interface dise où prendre les sources :<br>"
    "<a href=\"{0}\">{0}</a>":
        "The AGPL requires the interface to say where to get the sources:<br>"
        "<a href=\"{0}\">{0}</a>",
}


# --- Ce que ce portage ajoute : francais -> allemand ----------------------
#
# Traduction faite au mieux, sans relecture par un germanophone : le portage
# GTK a le meme defaut, et ses chaines sont reprises telles quelles. Une
# tournure qui sonnerait faux se corrige ici, sans toucher au code.
DE = {
    "Entité :": "Einheit:", "Inventaire :": "Inventar:",
    "Clés API": "API-Schlüssel", "Ajouter": "Hinzufügen",
    "Modifier": "Ändern", "Fermer": "Schließen",
    "Personnage": "Charakter", "Guilde": "Gilde",
    "personnage": "Charakter", "guilde": "Gilde",
    "Clé API": "API-Schlüssel", "Clé": "Schlüssel", "Genre": "Art",
    "Nom affiché (optionnel)": "Anzeigename (optional)",
    "Obtenir ma clé": "Schlüssel holen", "Coller": "Einfügen",
    "Coller la clé depuis le presse-papiers":
        "Schlüssel aus der Zwischenablage einfügen",
    "Copier la clé dans le presse-papiers":
        "Schlüssel in die Zwischenablage kopieren",
    "Remplacer": "Ersetzen", "Remplacer la clé": "Schlüssel ersetzen",
    "Retirer": "Entfernen", "Retirer cette entité": "Diese Einheit entfernen",
    "Retirer « {} » ?": "„{}“ entfernen?",
    "Veuillez saisir une clé API.":
        "Bitte einen API-Schlüssel eingeben.",
    "Vérification de la clé…": "Schlüssel wird geprüft…",
    "Échec : {}": "Fehlgeschlagen: {}",
    "Modules manquants : ": "Fehlende Module: ",
    "Synchronisation de {}…": "{} wird synchronisiert…",
    "Échec de la synchro : {}": "Synchronisierung fehlgeschlagen: {}",
    "Erreur : {}": "Fehler: {}",
    "Dernière synchro": "Letzte Synchronisierung",
    "Données calculées par l'API": "Von der API berechnete Daten",
    "synchro {}": "synchronisiert {}",
    "Clés API : en ajouter une, relire ou remplacer celles qu'on a":
        "API-Schlüssel: einen hinzufügen, nachlesen oder ersetzen",
    "Aucune clé enregistrée — l'onglet « Ajouter » est à côté.":
        "Kein Schlüssel gespeichert — der Reiter „Hinzufügen“ ist daneben.",
    "Aucune entité — le bouton « + » ajoute un personnage ou une guilde à "
    "partir de sa clé.":
        "Keine Einheit — die Schaltfläche „+“ fügt einen Charakter oder eine "
        "Gilde anhand ihres Schlüssels hinzu.",

    "(capacité inconnue)": "(Kapazität unbekannt)",
    "Détails…": "Einzelheiten…",
    "Copier l'identifiant": "Kennung kopieren",
    "Identifiant copié : {}": "Kennung kopiert: {}",
    "Réinitialiser l'icône": "Symbol zurücksetzen",
    "Enchantement : ": "Verzauberung: ",
    "Charges de sève : {}": "Saftladungen: {}",
    " (coût {})": " (Kosten {})",
    "oui": "ja", "expiré": "abgelaufen",
    "Choisir string_client.pack": "string_client.pack wählen",
    "Noms chargés depuis {}.": "Namen geladen aus {}.",
    "Impossible de lire ce fichier string_client.pack.":
        "Diese string_client.pack-Datei kann nicht gelesen werden.",
    "Portrait": "Porträt",

    "Dappers": "Dapper",
    "{} lignes sur {} au journal": "{} von {} Zeilen im Journal",
    "{} lignes copiées.": "{} Zeilen kopiert.",
    "Aucun mouvement enregistré. Le journal se remplit à chaque "
    "synchronisation où quelque chose a bougé.":
        "Keine Bewegung erfasst. Das Journal füllt sich bei jeder "
        "Synchronisierung, bei der sich etwas bewegt hat.",

    "Effectif": "Mitglieder", "Effectif · %d": "Mitglieder · %d",
    "Arrivées et départs": "Zugänge und Abgänge",
    "Arrivées et départs · %d": "Zugänge und Abgänge · %d",
    "Rechercher un membre…": "Mitglied suchen…",
    "Aucun membre de ce nom.": "Kein Mitglied dieses Namens.",
    "journal des %d derniers jours": "Journal der letzten %d Tage",
    "arrivée": "Zugang", "départ": "Abgang",
    "montée de grade": "Beförderung", "rétrogradation": "Rückstufung",
    "départs et grades : date du relevé":
        "Abgänge und Ränge: Datum der Erfassung",

    "Qui tient quoi": "Wer hält was",
    "Journal des prises": "Eroberungsjournal",
    "Actualiser": "Aktualisieren",
    "Redemander l'annuaire des guildes":
        "Gildenverzeichnis erneut abrufen",
    "Lecture de l'annuaire des guildes…": "Gildenverzeichnis wird gelesen…",
    "Annuaire indisponible : %s": "Verzeichnis nicht verfügbar: %s",
    "%d avant-postes tenus sur Atys": "%d Außenposten auf Atys gehalten",
    ", dont %d à %s": ", davon %d von %s",
    "Hors carte : ": "Außerhalb der Karte: ",
    "%s — pris par %s": "%s — erobert von %s",
    "%s — perdu par %s": "%s — verloren von %s",
    "Aucun changement de main depuis le premier relevé.":
        "Kein Besitzerwechsel seit der ersten Erfassung.",

    "Rechercher une compétence…": "Fähigkeit suchen…",
    "En cours": "Laufend",
    "Tout déplier": "Alles ausklappen", "Tout replier": "Alles einklappen",
    "%d compétences, %d affichées": "%d Fähigkeiten, %d angezeigt",
    "%s pts · %s dépensés": "%s Pkt. · %s ausgegeben",

    "Mektoubs": "Mektoubs", "Zigs": "Zigs", "aucune": "keine",
    "dehors": "draußen", "à l'écurie": "im Stall",
    "état inconnu": "Zustand unbekannt", " · satiété %d": " · Sättigung %d",
    "%d bête dehors": "%d Tier draußen",
    "%d bêtes dehors": "%d Tiere draußen",
    "Aucune bête dehors : toutes sont rangées.":
        "Kein Tier draußen: alle sind untergebracht.",

    "Lecture de la météo…": "Wetter wird gelesen…",
    "Météo indisponible : %s": "Wetter nicht verfügbar: %s",
    "Cette saison": "Diese Jahreszeit",
    "Excellentes — %s": "Exzellente — %s",
    "De jour": "Am Tag", "De nuit": "In der Nacht",
    "  ·  en ce moment": "  ·  gerade jetzt",
    "{} dans {} h": "{} in {} h",
    "humidité": "Feuchtigkeit",
    "gisement": "Vorkommen", "gisements": "Vorkommen",

    "Aucune alerte": "Keine Warnung", "Aucune alerte.": "Keine Warnung.",
    "{} alerte(s)": "{} Warnung(en)",
    "Notifications du bureau": "Desktop-Benachrichtigungen",
    "Notifications du bureau coupées":
        "Desktop-Benachrichtigungen abgeschaltet",
    "Prévenir mouvement dappers": "Bei Dapper-Bewegung warnen",
    "Surveiller": "Überwachen", "Surveiller un objet": "Gegenstand überwachen",
    "Ne plus surveiller": "Nicht mehr überwachen",
    "Surveiller la quantité…": "Menge überwachen…",
    "Surveiller la durabilité…": "Haltbarkeit überwachen…",
    "Alerte si la quantité descend sous ce seuil :":
        "Warnung, wenn die Menge unter diesen Schwellenwert fällt:",
    "Alerte si la durabilité descend sous ce seuil :":
        "Warnung, wenn die Haltbarkeit unter diesen Schwellenwert fällt:",

    "en ligne": "online", "vu à l'instant": "gerade eben gesehen",
    "vu il y a {} min": "vor {} Min. gesehen",
    "vu il y a {} h": "vor {} Std. gesehen",
    "vu il y a {} j": "vor {} T. gesehen", "vu le {}": "gesehen am {}",
    "Dernière connexion": "Letzte Anmeldung",
    "Dernière déconnexion": "Letzte Abmeldung",

    "Analyse de chatlog": "Chatlog-Auswertung",
    "Choisir un fichier de chatlog": "Chatlog-Datei wählen",
    "Filtrer les messages…": "Nachrichten filtern…",
    "Tous les canaux": "Alle Kanäle", "Système": "System",
    "Copier HTML": "HTML kopieren", "Copier BBCode": "BBCode kopieren",
    "Copier texte": "Text kopieren",
    "{} / {} messages": "{} / {} Nachrichten",
    "{} messages copiés ({}).": "{} Nachrichten kopiert ({}).",
    "{} messages analysés.": "{} Nachrichten ausgewertet.",
    "Lecture impossible : {}": "Lesen nicht möglich: {}",

    "Sauvegarde : ": "Sicherung: ",
    "Options enregistrées.": "Optionen gespeichert.",
    "Synchroniser à l'ouverture d'un personnage ou d'une guilde":
        "Beim Öffnen eines Charakters oder einer Gilde synchronisieren",
    "Mettre à jour": "Aktualisieren",
    "Une nouvelle version est disponible":
        "Eine neue Version ist verfügbar",
    "Une nouvelle version est disponible ({}).":
        "Eine neue Version ist verfügbar ({}).",
    "Téléchargement de la mise à jour…": "Aktualisierung wird geladen…",
    "Téléchargement de la mise à jour… {} %":
        "Aktualisierung wird geladen… {} %",
    "Mise à jour impossible : {}": "Aktualisierung fehlgeschlagen: {}",
    "Mise à jour installée": "Aktualisierung installiert",
    "Elle ne prendra effet qu'au prochain lancement. Relancer maintenant ?":
        "Sie wirkt erst beim nächsten Start. Jetzt neu starten?",
    "Plus tard": "Später", "Relancer": "Neu starten",

    "À propos…": "Über…", "À propos de {}": "Über {}",
    "Version {}": "Version {}",
    "Ce que c'est": "Was es ist", "Droits": "Rechte", "Licence": "Lizenz",
    "Code source": "Quelltext", "Projet d'origine": "Ursprungsprojekt",
    "Écrire à l'auteur": "Dem Autor schreiben",
    "Données et images": "Daten und Bilder",
    "pour le zyRoom d'origine": "für das ursprüngliche zyRoom",
    "pour ce portage": "für diese Portierung",
}


def main() -> None:
    en_gtk, de_gtk, write_mo = _catalogue_gtk()
    if write_mo is None:
        from build_i18n_secours import write_mo   # pragma: no cover
    for langue, herite, propre in (("en", en_gtk, EN), ("de", de_gtk, DE)):
        # Les notres l'emportent : si une chaine existe des deux cotes avec
        # deux traductions, celle qui a ete ecrite pour cette interface-ci
        # colle mieux a ce qu'elle affiche.
        catalogue = dict(herite)
        catalogue.update(propre)
        chemin = os.path.join(LOCALE, langue, "LC_MESSAGES", "zyroom.mo")
        write_mo(catalogue, chemin)
        print(f"{langue}: {len(catalogue)} chaînes "
              f"({len(propre)} propres à Qt) -> {chemin}")


if __name__ == "__main__":
    main()
