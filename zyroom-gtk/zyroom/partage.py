"""Le journal de guilde que la page publie, et que chacun relit.

L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
déduit de deux relevés successifs, et chaque installation ne connaît donc que
ce qu'elle a regardé elle-même. Un officier qui relève une fois par semaine
voit d'un bloc ce qu'un autre a vu en trois fois.

Un relevé programmé tourne donc sur GitHub, à l'heure, sans qu'aucune machine
soit allumée : il interroge la guilde, tient son journal et le versionne dans
le dépôt. Les applications le relisent au lancement et le fusionnent au leur
par `movements.fusionner`, qui garde le récit le plus fin. Personne n'a rien à
cliquer.

**Ce qui circule** : des mouvements de coffres, en fiches et en quantités. Pas
un seul nom de joueur — l'API n'associe pas les mouvements à qui les a faits,
et le journal ne l'invente pas.

**Ce qui ne circule pas** : rien ne remonte. Le dépôt se lit, il ne s'écrit
pas depuis une application — il faudrait pour cela un jeton d'écriture dans
chaque installation, et la clé de guilde livrée jadis en clair dans l'APK a
déjà montré ce que cela vaut. Le jeton du relevé, lui, est fourni par GitHub à
l'exécution et ne quitte jamais ses serveurs.
"""
from __future__ import annotations

import urllib.error
import urllib.request

from . import movements

#: La branche `journaux`, servie telle quelle par GitHub.
#:
#: Une branche **orpheline**, reconstruite et poussée en force à chaque
#: relevé — le motif de `gh-pages`, pour la même raison : un journal réécrit
#: toutes les heures laisserait sinon, dans l'historique, chacune de ses
#: versions pour toujours. Ici il n'y a jamais qu'un état, celui du dernier
#: relevé, et l'effacer l'efface vraiment.
#:
#: Ni `main`, qui garderait tout, ni `gh-pages`, que `livraison.sh` réécrit à
#: chaque livraison — ce qui effacerait le journal au premier envoi d'APK.
BASE = ("https://raw.githubusercontent.com/xiom-dev/zyroom-gtk-android"
        "/journaux/")

#: Au-delà, on renonce : ce n'est qu'un confort, il ne doit pas retarder le
#: lancement quand le réseau traîne.
_DELAI = 10


def url_du_journal(kind: str, entity_id: str) -> str:
    """L'adresse du journal publié pour cette entité."""
    return f"{BASE}{kind}-{entity_id}.jsonl"


def recuperer(kind: str, entity_id: str, chemin_local: str) -> int:
    """Relit le journal publié et le verse dans celui d'ici.

    Renvoie le nombre de mouvements ajoutés, zéro si la page n'en publie pas
    pour cette entité — le cas de toutes celles que le mainteneur ne suit pas.

    Ne lève jamais : c'est un confort de fond, appelé au lancement. Ni
    l'absence de réseau, ni une page absente, ni un fichier bancal ne doivent
    empêcher l'application de démarrer.
    """
    try:
        with urllib.request.urlopen(url_du_journal(kind, entity_id),
                                    timeout=_DELAI) as reponse:
            lignes = reponse.read().decode("utf-8", "replace").splitlines()
    except (urllib.error.URLError, OSError, ValueError):
        return 0
    try:
        return movements.importer(chemin_local, lignes)
    except OSError:
        return 0


def url_du_registre(guild_id: str) -> str:
    """L'adresse du registre du personnel publié pour cette guilde."""
    return f"{BASE}roster-{guild_id}.jsonl"


def recuperer_registre(guild_id: str, chemin_local: str) -> int:
    """Relit le registre publié et verse dans celui d'ici ce qui y manque.

    Le relevé horaire voit passer tout le monde ; une application ouverte deux
    fois par semaine ne voit qu'un membre sur trois. Sur six mois, l'écart
    devient l'essentiel du registre.

    Rend le nombre de lignes ajoutées. Ne lève jamais : c'est un confort de
    fond, appelé au lancement.
    """
    try:
        with urllib.request.urlopen(url_du_registre(guild_id),
                                    timeout=_DELAI) as reponse:
            lignes = reponse.read().decode("utf-8", "replace").splitlines()
    except (urllib.error.URLError, OSError, ValueError):
        return 0

    import json
    from . import roster
    connus, ajoutees = set(), []
    try:
        with open(chemin_local, encoding="utf-8") as fh:
            for ligne in fh:
                ligne = ligne.strip()
                if ligne:
                    d = json.loads(ligne)
                    connus.add((d["at"], d.get("member"), d.get("kind")))
    except (OSError, ValueError, KeyError):
        pass                       # journal absent ou bancal : on repart de la

    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            continue
        try:
            d = json.loads(ligne)
            cle = (d["at"], d.get("member"), d.get("kind"))
        except (ValueError, KeyError):
            continue
        if cle in connus:
            continue
        connus.add(cle)
        ajoutees.append(roster.Change(d["at"], d.get("member", ""),
                                      d.get("kind", ""), d.get("from", ""),
                                      d.get("to", "")))
    if not ajoutees:
        return 0
    try:
        with open(chemin_local, "a", encoding="utf-8") as fh:
            for c in ajoutees:
                fh.write(json.dumps({"at": c.at, "member": c.member,
                                     "kind": c.kind, "from": c.frm,
                                     "to": c.to}, ensure_ascii=False) + "\n")
    except OSError:
        return 0
    return len(ajoutees)
