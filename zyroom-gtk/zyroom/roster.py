"""Le registre du personnel : qui entre, qui sort, qui change de grade.

Même principe que le journal des mouvements et que celui des avant-postes, et
pour la même raison : **l'API ne rend qu'un état, jamais une histoire.** Elle
donne la liste des membres du jour, avec leur grade ; deux relevés comparés
donnent les arrivées, les départs et les promotions.

Ce qui se passe entre deux relevés ne se voit donc pas : un joueur recruté puis
parti le lendemain, si l'application n'a pas été ouverte entre-temps, ne laisse
aucune trace. C'est la limite de tout journal bâti sur des instantanés, et elle
vaut mieux que rien — l'API, elle, n'a aucune mémoire.

La date d'entrée que rend le flux — un grand entier, 6115304166 — n'est pas un
temps Unix, et rien dans l'API n'en donne la clé. On ne la lit pas : afficher
une date fausse serait pire que de n'en afficher aucune. Les dates du journal
sont donc celles de nos propres relevés.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass

#: Les grades, du plus haut au plus bas, avec leur nom français.
#:
#: L'API les rend en anglais ; le jeu les affiche en français. L'ordre sert au
#: classement du registre : on lit une liste de guilde par le haut.
GRADES = (
    ("Leader", "Chef"),
    ("HighOfficer", "Officier supérieur"),
    ("Officer", "Officier"),
    ("Member", "Membre"),
)

#: Combien de temps le journal garde ses lignes, en jours.
#:
#: Un mois : c'est la mémoire utile d'un officier. Au-delà, la liste s'allonge
#: sans que personne la lise. Les lignes plus vieilles sont écartées à la
#: lecture, et le fichier est réécrit quand il en contient trop — ainsi rien ne
#: se perd tant qu'on n'a pas relu, et rien ne s'accumule indéfiniment.
RETENTION_JOURS = 30

_RANG = {code: rang for rang, (code, _n) in enumerate(GRADES)}
_NOM = dict(GRADES)


def nom_grade(code: str) -> str:
    """« HighOfficer » → « Officier supérieur ». Un grade inconnu reste lisible."""
    return _NOM.get(code, code or "—")


def rang_grade(code: str) -> int:
    """Pour trier : le chef d'abord, les membres ensuite."""
    return _RANG.get(code, len(GRADES))


@dataclass(frozen=True)
class Change:
    """Un mouvement de personnel.

    `kind` vaut « arrivee », « depart » ou « grade ». Pour un changement de
    grade, `frm` et `to` portent les deux grades ; pour une arrivée, seul `to`,
    et pour un départ, seul `frm`."""

    at: int                 #: secondes Unix, comme les autres journaux
    member: str
    kind: str
    frm: str = ""
    to: str = ""

    @property
    def promotion(self) -> bool:
        """Vrai si le grade a monté. Un rang plus petit est un grade plus haut."""
        return self.kind == "grade" and rang_grade(self.to) < rang_grade(self.frm)


def diff(avant: dict[str, str], apres: dict[str, str]) -> list[Change]:
    """Ce qui a changé entre deux relevés : arrivées, départs, grades."""
    maintenant = int(time.time())
    changements = []
    for nom in sorted(set(avant) | set(apres)):
        ancien, nouveau = avant.get(nom), apres.get(nom)
        if ancien is None:
            changements.append(Change(maintenant, nom, "arrivee", to=nouveau or ""))
        elif nouveau is None:
            changements.append(Change(maintenant, nom, "depart", frm=ancien))
        elif ancien != nouveau:
            changements.append(Change(maintenant, nom, "grade", frm=ancien,
                                      to=nouveau))
    return changements


def decrire(changement: Change) -> str:
    """Une ligne de journal, lisible telle quelle.

    Sans le signe : l'écran le pose à part, en couleur, et le répéter dans le
    texte ferait double emploi. Cette fonction sert aussi au presse-papier et
    aux tests, où la couleur ne passe pas."""
    if changement.kind == "arrivee":
        return f"{changement.member} a rejoint la guilde ({nom_grade(changement.to)})"
    if changement.kind == "depart":
        return f"{changement.member} a quitté la guilde ({nom_grade(changement.frm)})"
    return (f"{changement.member} : {nom_grade(changement.frm)} → "
            f"{nom_grade(changement.to)}")


class RosterStore:
    """Le registre d'une guilde : son état, et l'histoire de ses mouvements.

    Un jeu de fichiers par guilde — contrairement aux avant-postes, qui sont
    ceux de tout le serveur.
    """

    def __init__(self, dossier: str, guild_id: str) -> None:
        self._dir = dossier
        self._id = guild_id or "inconnue"

    def _journal(self) -> str:
        return os.path.join(self._dir, f"roster-{self._id}.jsonl")

    def _etat(self) -> str:
        return os.path.join(self._dir, f"roster-{self._id}.json")

    def jamais_releve(self) -> bool:
        """Vrai tant qu'aucun relevé n'a été fait : le registre ne peut rien dire."""
        return not os.path.isfile(self._etat())

    def record(self, membres: list[tuple[str, str]]) -> list[Change]:
        """Confronte le relevé au dernier état connu et journalise les mouvements.

        Au tout premier relevé il n'y a rien à comparer : on enregistre sans
        rien journaliser, sinon les cent soixante-dix membres passeraient pour
        autant d'arrivées le jour de l'installation.

        Un relevé vide n'est jamais comparé : l'API rend parfois une guilde
        sans son bloc de membres — la clé n'a pas le module, ou le flux est
        tronqué — et la guilde entière semblerait alors avoir démissionné.
        """
        if not membres:
            return []
        apres = {nom: grade for nom, grade in membres}
        avant = self._lire_etat()
        changements = [] if avant is None else diff(avant, apres)
        if changements:
            self._ajouter(changements)
        self._ecrire_etat(apres)
        self.elaguer()
        return changements

    def history(self, jours: int = RETENTION_JOURS) -> list[Change]:
        """Le journal, du plus récent au plus ancien, sur `jours` jours.

        Un mois : c'est la mémoire utile d'un officier — « qui est arrivé ce
        mois-ci ? », « qui nous a quittés depuis la dernière guerre d'avant-poste
        ? ». Au-delà, la liste s'allonge sans que personne la lise, et le
        fichier grossit pour rien.
        """
        chemin = self._journal()
        if not os.path.isfile(chemin):
            return []
        depuis = int(time.time()) - jours * 86400
        lignes = []
        try:
            with open(chemin, encoding="utf-8") as fh:
                for ligne in fh:
                    if not ligne.strip():
                        continue
                    try:
                        o = json.loads(ligne)
                    except ValueError:
                        continue
                    at = int(o.get("at", 0))
                    if at < depuis:
                        continue
                    lignes.append(Change(at, o.get("member", ""),
                                         o.get("kind", ""), o.get("from", ""),
                                         o.get("to", "")))
        except OSError:
            return []
        lignes.sort(key=lambda c: c.at, reverse=True)
        return lignes

    def elaguer(self, jours: int = RETENTION_JOURS) -> int:
        """Réécrit le journal sans les lignes plus vieilles que `jours`.

        Appelé après chaque relevé : le fichier ne grossit donc jamais au-delà
        d'un mois de mouvements. Rend le nombre de lignes écartées.

        **Les lignes gardées sont recopiées telles quelles**, et jamais
        reconstruites à partir de ce qu'on a su lire. Autrement, une ligne
        illisible — fichier tronqué par une coupure de courant, écriture
        concurrente — disparaîtrait à la réécriture, et une simple erreur de
        lecture aurait vidé tout l'historique d'un coup. Ce qu'on ne comprend
        pas, on le garde : c'est un journal, il n'est pas remplaçable.
        """
        chemin = self._journal()
        if not os.path.isfile(chemin):
            return 0
        depuis = int(time.time()) - jours * 86400
        gardees, ecartees = [], 0
        try:
            with open(chemin, encoding="utf-8") as fh:
                for ligne in fh:
                    if not ligne.strip():
                        continue
                    try:
                        at = int(json.loads(ligne).get("at", 0))
                    except (ValueError, AttributeError, TypeError):
                        gardees.append(ligne)      # illisible : on n'y touche pas
                        continue
                    if at < depuis:
                        ecartees += 1
                    else:
                        gardees.append(ligne)
        except OSError:
            return 0
        if not ecartees:
            return 0
        try:
            with open(chemin, "w", encoding="utf-8") as fh:
                # Dans l'ordre où elles ont été ajoutées : le fichier reste un
                # journal, pas une pile.
                fh.writelines(gardees)
        except OSError:
            return 0
        return ecartees

    def clear(self) -> None:
        try:
            os.remove(self._journal())
        except OSError:
            pass

    def _lire_etat(self) -> dict[str, str] | None:
        try:
            with open(self._etat(), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def _ecrire_etat(self, membres: dict[str, str]) -> None:
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(self._etat(), "w", encoding="utf-8") as fh:
                json.dump(membres, fh)
        except OSError:
            pass

    def _ajouter(self, changements: list[Change]) -> None:
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(self._journal(), "a", encoding="utf-8") as fh:
                for c in changements:
                    fh.write(json.dumps({"at": c.at, "member": c.member,
                                         "kind": c.kind, "from": c.frm,
                                         "to": c.to}) + "\n")
        except OSError:
            pass
