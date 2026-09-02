"""Fenêtre d'information détaillée d'un objet (caractéristiques de craft).

Les mêmes sections que la version GTK, dans le même ordre, avec les mêmes
libellés : Général, Combat, Protection, Bijou, Amplificateur, Bonus, Matière,
Vente. Une section vide ne s'affiche pas — un catalyseur n'a rien à dire d'une
protection au tranchant.

**Ce qui change avec Qt.** GTK empile des `Gtk.Grid` dans une boîte ; ici
chaque section est une grille à deux colonnes, la clé en gris à gauche, la
valeur à droite, sélectionnable pour qu'on puisse la recopier. Le tout dans
une zone défilante, comme là-bas.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QGridLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

from .i18n import _
from .models import (CLASS_NAMES, COLOR_NAMES, ECOSYSTEM_NAMES, MAT_CATEGORY,
                     MAT_SPEC, ItemInfo, ItemType)


class _Section:
    """Aide à construire une section : un titre, puis des lignes clé/valeur."""

    def __init__(self, titre: str) -> None:
        self.boite = QWidget()
        colonne = QVBoxLayout(self.boite)
        colonne.setContentsMargins(0, 8, 0, 0)
        colonne.setSpacing(2)

        entete = QLabel(f"<b>{_(titre)}</b>")
        colonne.addWidget(entete)

        porteur = QWidget()
        self.grille = QGridLayout(porteur)
        self.grille.setContentsMargins(8, 0, 0, 0)
        self.grille.setHorizontalSpacing(14)
        self.grille.setVerticalSpacing(2)
        # La colonne des valeurs prend la place restante : sans cela, une
        # valeur courte laisserait la cle flotter loin d'elle.
        self.grille.setColumnStretch(1, 1)
        colonne.addWidget(porteur)

        self._rang = 0
        self.compte = 0

    def ajouter(self, cle: str, valeur) -> None:
        """Une ligne. Rien ne s'affiche si la valeur est vide."""
        if valeur is None or valeur == "":
            return
        lbl_cle = QLabel(_(cle))
        lbl_cle.setObjectName("discret")
        lbl_valeur = QLabel(str(valeur))
        lbl_valeur.setWordWrap(True)
        # Selectionnable : un identifiant d'objet se recopie, et c'est la
        # seule facon de le sortir d'ici.
        lbl_valeur.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.grille.addWidget(lbl_cle, self._rang, 0,
                              Qt.AlignmentFlag.AlignTop)
        self.grille.addWidget(lbl_valeur, self._rang, 1)
        self._rang += 1
        self.compte += 1


def _temps_restant(expire: int) -> str:
    reste = expire - time.time()
    if reste <= 0:
        return _("expiré")
    heures = int(reste // 3600)
    minutes = int((reste % 3600) // 60)
    return f"{heures} h {minutes} min"


def construire(item: ItemInfo, nom_fn, category_db) -> QWidget:
    """Le contenu détaillé d'un objet, dans une zone défilante."""
    if item.item_type in (ItemType.NATURAL_MAT, ItemType.ANIMAL_MAT) and category_db:
        category_db.fill(item)

    racine = QWidget()
    colonne = QVBoxLayout(racine)
    colonne.setContentsMargins(12, 12, 12, 12)
    colonne.setSpacing(4)

    # General
    g = _Section("Général")
    lisible = nom_fn(item.sheet) if nom_fn else item.sheet
    g.ajouter("Nom", lisible if lisible != item.sheet else "")
    g.ajouter("Fiche", item.sheet)
    g.ajouter("Identifiant", item.item_id)
    g.ajouter("Qualité", item.quality or "")
    g.ajouter("Quantité", item.stack or "")
    if item.item_class != item.item_class.UNKNOWN:
        g.ajouter("Classe", _(CLASS_NAMES[int(item.item_class)]))
    if item.ecosystem != item.ecosystem.UNKNOWN:
        g.ajouter("Écosystème", _(ECOSYSTEM_NAMES[int(item.ecosystem)]))
    g.ajouter("Volume", f"{item.volume:.2f}" if item.volume else "")
    g.ajouter("Poids", f"{item.weight:.2f}" if item.weight else "")
    if item.item_type == ItemType.EQUIPMENT and item.hp:
        g.ajouter("Durabilité", item.hp)
    if item.locked:
        g.ajouter("Protégé", _("oui"))
    colonne.addWidget(g.boite)

    # Combat
    c = _Section("Combat")
    c.ajouter("Dégâts", item.c_dmg or "")
    c.ajouter("Vitesse", item.c_speed or "")
    c.ajouter("Portée", item.c_range or "")
    c.ajouter("Mod. esquive", item.c_dodge or "")
    c.ajouter("Mod. parade", item.c_parry or "")
    c.ajouter("Mod. esquive adverse", item.c_adv_dodge or "")
    c.ajouter("Mod. parade adverse", item.c_adv_parry or "")
    if c.compte:
        colonne.addWidget(c.boite)

    # Protection (armure)
    p = _Section("Protection")
    if item.c_factor_prot:
        p.ajouter("Facteur de protection", f"{item.c_factor_prot:.2f}")
    p.ajouter("Prot. tranchant max.", item.c_slash or "")
    p.ajouter("Prot. contondant max.", item.c_blunt or "")
    p.ajouter("Prot. perforant max.", item.c_pierce or "")
    if p.compte:
        colonne.addWidget(p.boite)

    # Bijou : protections + resistances
    if item.protections or item.resistances:
        j = _Section("Bijou")
        for nom, valeur in item.protections:
            j.ajouter(f"Protection {nom}", valeur)
        for nom, valeur in item.resistances:
            j.ajouter(f"Résistance {nom}", f"{valeur:.2f}")
        colonne.addWidget(j.boite)

    # Amplificateur magique
    a = _Section("Amplificateur")
    a.ajouter("Vit. sort élémentaire", item.a_elem_speed or "")
    a.ajouter("Puiss. élémentaire", item.a_elem_power or "")
    a.ajouter("Vit. affliction off.", item.a_off_speed or "")
    a.ajouter("Puiss. affliction off.", item.a_off_power or "")
    a.ajouter("Vit. soin", item.a_heal_speed or "")
    a.ajouter("Puiss. soin", item.a_heal_power or "")
    a.ajouter("Vit. affliction déf.", item.a_def_speed or "")
    a.ajouter("Puiss. affliction déf.", item.a_def_power or "")
    if a.compte:
        colonne.addWidget(a.boite)

    # Bonus
    b = _Section("Bonus")
    b.ajouter("Vie", item.hp_buff or "")
    b.ajouter("Sève", item.sap_buff or "")
    b.ajouter("Endurance", item.sta_buff or "")
    b.ajouter("Concentration", item.focus_buff or "")
    if b.compte:
        colonne.addWidget(b.boite)

    # Matiere
    if item.mat_category1 or item.mat_specs1:
        mat = _Section("Matière")
        if 0 <= item.mat_category1 < len(MAT_CATEGORY):
            mat.ajouter("Catégorie 1", _(MAT_CATEGORY[item.mat_category1]))
        for idx, niveau in item.mat_specs1:
            if 0 < idx < len(MAT_SPEC):
                mat.ajouter(MAT_SPEC[idx], "★" * niveau)
        if 0 < item.mat_category2 < len(MAT_CATEGORY):
            mat.ajouter("Catégorie 2", _(MAT_CATEGORY[item.mat_category2]))
        for idx, niveau in item.mat_specs2:
            if 0 < idx < len(MAT_SPEC):
                mat.ajouter(MAT_SPEC[idx], "★" * niveau)
        if item.mat_colors:
            couleurs = ", ".join(_(COLOR_NAMES[c]) for c in item.mat_colors
                                 if 0 <= c < len(COLOR_NAMES))
            mat.ajouter("Couleurs", couleurs)
        colonne.addWidget(mat.boite)

    # Vente
    if item.price or item.expires:
        v = _Section("Vente")
        if item.price:
            v.ajouter("Prix", f"{item.price:,.0f}".replace(",", " ")
                      + " dappers")
        v.ajouter("Continent", item.continent)
        if item.expires:
            v.ajouter("Expire dans", _temps_restant(item.expires))
        colonne.addWidget(v.boite)

    colonne.addStretch(1)

    defilant = QScrollArea()
    defilant.setWidget(racine)
    defilant.setWidgetResizable(True)
    defilant.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return defilant


def montrer(parent, item: ItemInfo, nom_fn, category_db) -> None:
    """Ouvre la fiche d'un objet dans sa propre fenêtre."""
    lisible = nom_fn(item.sheet) if nom_fn else item.sheet
    fen = QDialog(parent)
    fen.setWindowTitle(lisible)
    fen.resize(380, 520)
    colonne = QVBoxLayout(fen)
    colonne.setContentsMargins(0, 0, 0, 0)
    colonne.addWidget(construire(item, nom_fn, category_db))
    # Non modale : on compare volontiers deux objets cote a cote, et la
    # version GTK ouvre elle aussi une fenetre a part entiere.
    fen.setModal(False)
    fen.show()
