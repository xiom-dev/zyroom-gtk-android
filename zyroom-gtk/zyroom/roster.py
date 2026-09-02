"""Le registre du personnel : qui entre, qui sort, qui change de grade.

Même principe que le journal des mouvements et que celui des avant-postes, et
pour la même raison : **l'API ne rend qu'un état, jamais une histoire.** Elle
donne la liste des membres du jour, avec leur grade ; deux relevés comparés
donnent les arrivées, les départs et les promotions.

Ce qui se passe entre deux relevés ne se voit donc pas : un joueur recruté puis
parti le lendemain, si l'application n'a pas été ouverte entre-temps, ne laisse
aucune trace. C'est la limite de tout journal bâti sur des instantanés, et elle
vaut mieux que rien — l'API, elle, n'a aucune mémoire.

Les **arrivées** font exception depuis le 22 août 2026 : le flux porte pour
chaque membre sa date d'entrée, et l'on sait maintenant la lire (voir
`ORIGINE`). Une arrivée est donc datée du jour où elle a eu lieu, et non du
jour où l'application l'a remarquée — deux jours plus tard s'il l'a fallu.

Les **départs** et les **changements de grade** gardent la date du relevé : de
ceux-là, l'API ne dit rien du tout.
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
#: Six mois. C'était un mois — la mémoire utile d'un officier —, mais ce qui
#: se passe dans une guilde se relit sur une saison : qui est parti au
#: printemps, qui est monté officier depuis. Une ligne pèse une centaine
#: d'octets et une guilde en produit quelques dizaines par mois ; six mois
#: tiennent dans un fichier qu'on ouvre sans y penser.
#:
#: Les lignes plus vieilles sont écartées à la lecture, et le fichier est
#: réécrit quand il en contient trop — ainsi rien ne se perd tant qu'on n'a
#: pas relu, et rien ne s'accumule indéfiniment.
RETENTION_JOURS = 180

#: Les mouvements repris d'un autre journal, par guilde.
#:
#: V-RyLune et ZyRoom-GTK tiennent chacun leur registre, et chacun ne connaît
#: que ce qu'il a vu lui-même : l'API ne rend qu'un état. Ceux-ci ont été
#: **relevés le 10 août 2026 à 15 h 48** par l'exemplaire du mainteneur, sur une
#: guilde dont les autres exemplaires n'avaient pas encore de journal.
#:
#: Ils portent la date de leur constat et non celle du jour : c'est ce qui les
#: fera sortir du journal au bout de six mois, comme les autres. Rien ne les
#: remplacera ensuite, et c'est bien ainsi — une reprise sert à recoller deux
#: journaux, pas à écrire l'histoire.
REPRISE: dict[str, tuple[tuple[int, str, str, str, str], ...]] = {
    # La Lune Eternelle
    "105906237": (
        (1786369686, "Paty", "grade", "Member", "Officer"),
        (1786369686, "Thysela", "grade", "Officer", "HighOfficer"),
    ),
}

#: L'unité du compteur de dates de l'API : le dixième de seconde.
#:
#: `api.ryzom.com/time.php` — qui n'exige aucune clé — rend la même horloge et
#: avance de dix pas par seconde réelle. C'est le tic du serveur de Ryzom.
TICK = 0.1

#: L'origine de ce compteur, en secondes Unix.
#:
#: Le flux rend pour chaque membre un `<joined>` — 6402485271 pour Xiom — que
#: cette application a longtemps jeté faute d'en connaître la clé. L'unité une
#: fois trouvée, il ne manquait que l'origine, et elle se déduit de nos propres
#: relevés : chaque arrivée constatée encadre le `joined` du nouveau venu entre
#: le relevé qui ne le voyait pas encore et celui qui l'a vu. Sept arrivées de
#: La Lune Eternelle, dont une constatée trente minutes après le relevé
#: précédent, la ramènent à un quart d'heure près.
#:
#: **Le calage vaut pour les dates récentes**, celles du journal. Loin en
#: arrière il dérive — un compteur de tics ne compte sans doute pas les arrêts
#: du serveur — et une entrée de 2012 ne se lit qu'à quelques mois près. C'est
#: sans conséquence ici : le journal ne garde que six mois.
ORIGINE = 908_581_304

#: Avant l'ouverture de Ryzom, aucune date d'entrée n'est croyable.
_OUVERTURE_DU_JEU = 1_095_638_400          # 20 septembre 2004

_RANG ={code: rang for rang, (code, _n) in enumerate(GRADES)}
_NOM = dict(GRADES)


def date_entree(joined) -> int:
    """Le `<joined>` de l'API en secondes Unix, ou 0 s'il n'est pas croyable.

    Une date d'avant l'ouverture du jeu, ou dans l'avenir, trahit un champ
    absent, un compteur remis à zéro ou une horloge locale fausse. On rend
    alors zéro plutôt qu'une date inventée, et l'appelant retombe sur celle du
    relevé — la moins bonne des deux, mais jamais absurde.
    """
    try:
        quand = int(ORIGINE + int(joined) * TICK)
    except (TypeError, ValueError):
        return 0
    if quand < _OUVERTURE_DU_JEU or quand > int(time.time()) + 3600:
        return 0
    return quand


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


def diff(avant: dict[str, str], apres: dict[str, str],
         entrees: dict[str, int] | None = None,
         depuis: int = 0) -> list[Change]:
    """Ce qui a changé entre deux relevés : arrivées, départs, grades.

    `entrees` porte, par nom, la date d'entrée en guilde rendue par l'API.
    **Seules les arrivées en profitent** : de ceux qui partent ou qui changent
    de grade, l'API ne dit rien, et leur ligne garde la date du relevé.

    `depuis` est la date du relevé précédent. Elle borne les arrivées par le
    bas, comme l'instant présent les borne par le haut : **un nouveau venu est
    forcément entré entre les deux relevés**, puisque le premier ne le voyait
    pas encore. Le compteur de l'API dérive — mesuré à dix pas par seconde sur
    cinq minutes, neuf sur trente — et cette fourchette-là, elle, ne dérive
    pas : la date décodée s'y range, ou s'y fait ranger.
    """
    maintenant = int(time.time())
    entrees = entrees or {}
    changements = []
    for nom in sorted(set(avant) | set(apres)):
        ancien, nouveau = avant.get(nom), apres.get(nom)
        if ancien is None:
            quand = entrees.get(nom) or maintenant
            quand = min(max(quand, depuis), maintenant)
            changements.append(Change(quand, nom, "arrivee", to=nouveau or ""))
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

    def record(self, membres: list[tuple]) -> list[Change]:
        """Confronte le relevé au dernier état connu et journalise les mouvements.

        Chaque membre est un couple `(nom, grade)`, ou un triplet dont le
        troisième terme est le `<joined>` de l'API — la date d'entrée en
        guilde. Le couple reste accepté : les tests s'en servent, et un flux
        sans ce champ ne doit pas faire tomber le registre.

        Au tout premier relevé il n'y a rien à comparer : on enregistre sans
        rien journaliser, sinon les cent soixante-dix membres passeraient pour
        autant d'arrivées le jour de l'installation.

        Un relevé vide n'est jamais comparé : l'API rend parfois une guilde
        sans son bloc de membres — la clé n'a pas le module, ou le flux est
        tronqué — et la guilde entière semblerait alors avoir démissionné.
        """
        if not membres:
            return []
        self._reprendre()
        apres = {m[0]: m[1] for m in membres}
        entrees = {m[0]: date_entree(m[2]) for m in membres if len(m) > 2}
        self._redater(entrees)
        avant = self._lire_etat()
        precedent = self._lire_releve()
        changements = ([] if avant is None
                       else diff(avant, apres, entrees, precedent))
        if changements:
            self._ajouter(changements)
        self._ecrire_etat(apres)
        self._ecrire_releve()
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

    def _reprendre(self) -> int:
        """Verse au journal les mouvements constatés avant qu'il n'existe.

        Ce que l'autre exemplaire a vu serait perdu pour toujours — non parce
        que ce n'est pas arrivé, mais parce que personne ne le lui a dit.

        La reprise ne se fait qu'**une fois**, marquée par un fichier témoin :
        sans lui, une ligne écartée par l'élagage ou effacée à dessein
        reviendrait à chaque relevé. Les doublons sont écartés au passage — le
        journal du mainteneur, lui, les contient déjà.
        """
        temoin = os.path.join(self._dir, f"roster-{self._id}.reprise")
        if os.path.exists(temoin):
            return 0
        depuis = int(time.time()) - RETENTION_JOURS * 86400
        connus = {(c.at, c.member, c.kind) for c in self.history()}
        neufs = [Change(at, membre, genre, frm, to)
                 for at, membre, genre, frm, to in REPRISE.get(self._id, ())
                 if at >= depuis and (at, membre, genre) not in connus]
        if neufs:
            self._ajouter(neufs)
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(temoin, "w", encoding="utf-8"):
                pass
        except OSError:
            return 0
        return len(neufs)

    def _redater(self, entrees: dict[str, int]) -> int:
        """Rend aux arrivées déjà journalisées leur vraie date, une fois pour
        toutes.

        Les lignes écrites avant que l'on sache lire `<joined>` portent la date
        du relevé qui les a vues — parfois deux jours après le fait, si
        l'application est restée fermée. L'API sait encore dater ceux qui sont
        là ; ceux qui sont repartis entre-temps n'ont plus de date à donner et
        gardent la leur.

        Une seule fois, marquée par un témoin : sans lui, chaque relevé
        relirait et réécrirait le journal pour rien. Et comme l'élagage, cette
        passe **recopie telle quelle toute ligne qu'elle n'a pas comprise** :
        un journal ne se remplace pas par ce qu'on a su en relire.
        """
        if not entrees:
            return 0                      # flux sans le champ : rien à faire
        temoin = os.path.join(self._dir, f"roster-{self._id}.dates")
        if os.path.exists(temoin):
            return 0
        chemin = self._journal()
        corrigees, lignes = 0, []
        try:
            with open(chemin, encoding="utf-8") as fh:
                for ligne in fh:
                    try:
                        o = json.loads(ligne)
                        quand = (entrees.get(o["member"], 0)
                                 if o.get("kind") == "arrivee" else 0)
                    except (ValueError, AttributeError, TypeError, KeyError):
                        lignes.append(ligne)          # illisible : intacte
                        continue
                    # Le constat borne la correction par le haut : on ne peut
                    # pas avoir vu arriver quelqu'un avant qu'il n'arrive. Si
                    # la date décodée le dépasse, c'est elle qui a tort.
                    quand = min(quand, int(o.get("at", 0))) if quand else 0
                    if not quand or int(o.get("at", 0)) == quand:
                        lignes.append(ligne)
                        continue
                    o["at"] = quand
                    lignes.append(json.dumps(o) + "\n")
                    corrigees += 1
        except OSError:
            return 0                      # pas encore de journal, ou illisible
        if corrigees:
            try:
                with open(chemin, "w", encoding="utf-8") as fh:
                    fh.writelines(lignes)
            except OSError:
                return 0
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(temoin, "w", encoding="utf-8"):
                pass
        except OSError:
            pass
        return corrigees

    def _lire_releve(self) -> int:
        """La date du relevé précédent, ou 0 si on ne l'a jamais notée.

        Un fichier à part plutôt qu'une clé dans l'état : l'état est une liste
        de noms, et y glisser autre chose ferait passer cette clé pour un
        membre — le jour où l'on reviendrait à une version qui l'ignore, elle
        entrerait puis sortirait de la guilde toute seule.
        """
        try:
            with open(os.path.join(self._dir, f"roster-{self._id}.releve"),
                      encoding="utf-8") as fh:
                return int(fh.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def _ecrire_releve(self) -> None:
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(os.path.join(self._dir, f"roster-{self._id}.releve"),
                      "w", encoding="utf-8") as fh:
                fh.write(str(int(time.time())))
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
