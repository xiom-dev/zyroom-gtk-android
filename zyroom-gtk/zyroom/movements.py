"""Journal des mouvements d'objets : ce qui est entré et sorti des inventaires.

Reprend la partie « mouvements » de la fenêtre d'alerte du Delphi
(UnitFormAlert.pas : atAdded / atRemoved / atModified), avec la même
distinction en trois types et le même horodatage à la seconde. La différence :
l'original vidait sa liste à la fermeture, ici les lignes sont conservées d'une
session à l'autre.

Les mouvements se déduisent de deux instantanés successifs
(`{clé_inventaire: {sheet|qualité: quantité}}`, cf. alerts.build_snapshot) :
l'API ne fournit aucun historique, seulement un état. On ne voit donc que ce
qui a changé entre deux relevés — deux mouvements qui s'annulent entre eux
passent inaperçus, exactement comme dans l'original.

C'est aussi ce qui décide de leur **date** : celle du relevé d'où ils sortent,
que le serveur inscrit dans le flux (`date_releve`), et non celle de la
synchronisation. Voir cette fonction pour le pourquoi — c'est la moitié
délicate de ce module.

Le fichier est en JSON Lines : une ligne = un mouvement, ajout par simple
append, et une ligne corrompue ne coûte que sa propre perte.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

ADDED = "added"        # l'objet n'était pas là
REMOVED = "removed"    # l'objet n'y est plus
MODIFIED = "modified"  # la quantité a changé

#: Le trésor, rangé dans l'instantané comme s'il était un contenant.
#:
#: L'argent n'est pas un objet : il ne vit dans aucun coffre, l'API le rend à
#: part (`<money>`), et il n'a ni fiche, ni qualité, ni icône. Mais il entre et
#: il sort, et c'est tout ce que le journal demande — lui donner une clé
#: d'inventaire réservée le fait suivre le même chemin que le reste, de
#: l'instantané au disque, sans une seule structure de plus.
MONEY_KEY = "money"
MONEY_SHEET = "dappers"
MONEY_SIG = f"{MONEY_SHEET}|0"
MONEY_LABEL = "Trésor"


def montant(nombre: int) -> str:
    """Un nombre de dappers, groupé par milliers — 79000000 → 79 000 000."""
    return f"{nombre:,}".replace(",", " ")

#: Au-delà de cette taille, le journal est ramené à `_TRIM_TO` lignes.
_MAX_LINES = 20000
_TRIM_TO = 10000


@dataclass
class Movement:
    ts: float = 0.0          # date du releve d'ou il sort (cf. date_releve)
    inv_key: str = ""        # clé de l'inventaire, ex "chest4"
    inv_label: str = ""      # libellé au moment du mouvement, ex "Coffre 4 — ..."
    sheet: str = ""          # fiche de l'objet (le nom lisible est résolu à l'affichage)
    quality: int = 0
    kind: str = MODIFIED
    delta: int = 0           # quantité entrée (>0) ou sortie (<0)
    old: int = 0
    new: int = 0

    @property
    def when(self) -> str:
        """Date et heure lisibles, au format de l'original."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ts))

    def as_dict(self) -> dict:
        return {"ts": self.ts, "inv": self.inv_key, "label": self.inv_label,
                "sheet": self.sheet, "q": self.quality, "kind": self.kind,
                "delta": self.delta, "old": self.old, "new": self.new}

    @classmethod
    def from_dict(cls, data: dict) -> "Movement":
        return cls(ts=float(data.get("ts", 0)), inv_key=data.get("inv", ""),
                   inv_label=data.get("label", ""), sheet=data.get("sheet", ""),
                   quality=int(data.get("q", 0)), kind=data.get("kind", MODIFIED),
                   delta=int(data.get("delta", 0)), old=int(data.get("old", 0)),
                   new=int(data.get("new", 0)))


def _labels(entity) -> dict[str, str]:
    return {inv.key: inv.label for inv in entity.inventories}


#: Avant l'ouverture de Ryzom, aucune date n'est croyable.
_OUVERTURE_DU_JEU = 1_095_638_400          # 20 septembre 2004


def date_releve(entity) -> float:
    """Quand le serveur a calculé le flux d'où sortent ces mouvements.

    **Ce n'est pas l'heure du mouvement, et rien ne peut l'être** : l'API rend
    un état, jamais un historique — pas un `<item>`, pas le `<money>`, ne porte
    de date. Tout ce qu'on sait d'un mouvement, c'est qu'il a eu lieu entre
    deux relevés. La date du relevé est la meilleure des deux bornes, et la
    seule que le flux fournisse.

    Ce qu'elle corrige, en revanche, est réel. L'API ne recalcule pas un flux à
    la demande : elle sert le dernier mis en cache, et l'écart se compte en
    heures — un flux de personnage relevé le 22 août 2026 à 01h32 portait
    `created` au 21 à 14h48. Dater les mouvements de `time.time()` revenait
    donc à les dater de l'heure d'ouverture de l'application : ouvrir tous les
    soirs vers la même heure donnait un journal où chaque jour portait la même
    heure, et trois jours d'absence s'écrasaient sur l'instant du retour.

    Une date absente, illisible, ou hors du temps du jeu vaut l'horloge
    locale : moins juste, mais jamais absurde. Même garde que
    `roster.date_entree`, et pour la même raison — mieux vaut une date
    approximative qu'une date folle.
    """
    maintenant = time.time()
    try:
        quand = int(getattr(entity, "created", 0) or 0)
    except (TypeError, ValueError):
        return maintenant
    # Une date dans l'avenir trahit une horloge locale en retard, pas un flux
    # venu de demain : on ne la laisse pas passer devant le reste du journal.
    if quand < _OUVERTURE_DU_JEU or quand > maintenant + 3600:
        return maintenant
    return float(quand)


def diff(old: dict, new: dict, entity, ts: float | None = None) -> list[Movement]:
    """Mouvements entre deux instantanés, du plus récent inventaire au dernier.

    Seuls les inventaires présents dans le nouvel instantané sont examinés : un
    inventaire disparu (coffre masqué, animal vendu) ne doit pas faire croire
    que tout son contenu vient d'être retiré.
    """
    if ts is None:
        ts = date_releve(entity)
    labels = _labels(entity)
    out: list[Movement] = []

    for inv_key, new_counts in new.items():
        if inv_key == MONEY_KEY:
            continue                      # le trésor a sa propre comparaison
        old_counts = old.get(inv_key, {})
        for sig in set(new_counts) | set(old_counts):
            before = old_counts.get(sig, 0)
            after = new_counts.get(sig, 0)
            if before == after:
                continue
            sheet, _, quality = sig.rpartition("|")
            if not sheet:                     # signature d'un format antérieur
                sheet, quality = sig, "0"
            if before == 0:
                kind = ADDED
            elif after == 0:
                kind = REMOVED
            else:
                kind = MODIFIED
            out.append(Movement(
                ts=ts, inv_key=inv_key, inv_label=labels.get(inv_key, inv_key),
                sheet=sheet, quality=int(quality) if quality.isdigit() else 0,
                kind=kind, delta=after - before, old=before, new=after,
            ))

    # Entrées d'abord, puis sorties, et par inventaire — ordre de lecture le
    # plus utile quand une synchronisation en rapporte beaucoup d'un coup. Le
    # trésor passe devant : une synchro qui rapporte trente rangements de
    # matières rapporte au plus un mouvement d'argent, et c'est celui-là qu'on
    # cherche des yeux.
    out.sort(key=lambda m: (m.inv_key, -m.delta))
    return _diff_money(old, new, ts) + out


def _diff_money(old: dict, new: dict, ts: float) -> list[Movement]:
    """Le mouvement du trésor entre deux instantanés, s'il y en a un.

    Rien tant que l'instantané **précédent** n'en portait pas : sans cette
    garde, la première synchronisation qui suit la mise à jour journaliserait
    le trésor entier comme une entrée de soixante-dix-neuf millions.
    """
    try:
        if MONEY_KEY not in old or MONEY_KEY not in new:
            return []
        avant = int(old[MONEY_KEY].get(MONEY_SIG, 0))
        apres = int(new[MONEY_KEY].get(MONEY_SIG, 0))
    except (AttributeError, TypeError, ValueError):
        return []                         # instantané d'un format antérieur
    if avant == apres:
        return []
    return [Movement(ts=ts, inv_key=MONEY_KEY, inv_label=MONEY_LABEL,
                     sheet=MONEY_SHEET, quality=0, kind=MODIFIED,
                     delta=apres - avant, old=avant, new=apres)]


def append(path: str, movements: list[Movement]) -> None:
    """Ajoute des mouvements au journal, en élaguant s'il a trop grossi."""
    if not movements:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            for mv in movements:
                fh.write(json.dumps(mv.as_dict(), ensure_ascii=False) + "\n")
        _trim(path)
    except OSError:
        pass          # un journal est un confort : ne jamais casser une synchro


def _trim(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) <= _MAX_LINES:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines[-_TRIM_TO:])
    except OSError:
        pass


def load(path: str, limit: int | None = None) -> list[Movement]:
    """Relit le journal, du plus récent au plus ancien."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []
    if limit:
        lines = lines[-limit:]
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Movement.from_dict(json.loads(line)))
        except (ValueError, TypeError):
            continue      # ligne tronquée par un arrêt brutal : on la saute
    # Tri stable sur l'horodatage seul : les synchros ressortent de la plus
    # récente à la plus ancienne, mais à l'intérieur de l'une d'elles l'ordre
    # d'écriture est conservé (entrées avant sorties, groupées par coffre).
    # Inverser les lignes du fichier retournerait aussi cet ordre-là.
    out.sort(key=lambda m: -m.ts)
    return out


def clear(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def describe(mv: Movement, name_fn=None) -> str:
    """Ligne lisible, sur le modèle de l'original (RS_ALERT_ADDED/REMOVED/MODIFIED)."""
    if mv.inv_key == MONEY_KEY:
        sens = "entrés" if mv.delta > 0 else "sortis"
        return (f"{mv.when} | {mv.inv_label} : {montant(abs(mv.delta))} "
                f"dappers {sens} ({montant(mv.old)} > {montant(mv.new)})")
    name = name_fn(mv.sheet) if name_fn else mv.sheet
    quality = f" Q{mv.quality}" if mv.quality else ""
    if mv.kind == ADDED:
        what = f"l'objet {name}{quality} a été ajouté ({mv.new})"
    elif mv.kind == REMOVED:
        what = f"l'objet {name}{quality} a été retiré ({mv.old})"
    else:
        what = f"la quantité de l'objet {name}{quality} a changé ({mv.old} > {mv.new})"
    return f"{mv.when} | {mv.inv_label} : {what}"
