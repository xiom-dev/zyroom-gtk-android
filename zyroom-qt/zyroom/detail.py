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
        g.ajouter("Durabilité", f"{item.hp} / {item.hp_max}" if item.hp_max else item.hp)
    if item.locked:
        g.ajouter("Protégé", _("oui"))
    colonne.addWidget(g.boite)

    # Combat
    c = _Section("Combat")
    c.ajouter("Dégâts", item.c_dmg or "")
    c.ajouter("Vitesse", item.c_speed or "")
    # L'API donne la portee en millimetres.
    c.ajouter("Portée", f"{item.c_range / 1000:.0f} m" if item.c_range else "")
    c.ajouter("Mod. esquive", f"{item.c_dodge:+d}" if item.c_dodge else "")
    c.ajouter("Mod. parade", f"{item.c_parry:+d}" if item.c_parry else "")
    c.ajouter("Mod. esquive adverse", f"{item.c_adv_dodge:+d}" if item.c_adv_dodge else "")
    c.ajouter("Mod. parade adverse", f"{item.c_adv_parry:+d}" if item.c_adv_parry else "")
    if c.compte:
        colonne.addWidget(c.boite)

    # Protection (armure)
    p = _Section("Protection")
    if item.c_factor_prot:
        p.ajouter("Facteur de protection", f"{item.c_factor_prot:.2f} %")
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
            j.ajouter(f"Résistance {nom}", f"{valeur:.1f}")
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


def stats_infobulle(item: ItemInfo) -> str:
    """Les caractéristiques de craft, en résumé pour l'infobulle d'un objet.

    Les mêmes que la fiche détaillée, sauf les bonus vie/sève/endurance/
    concentration : l'infobulle les montre déjà, avec leur goutte. Chaîne
    vide pour une matière ou un objet sans caractéristiques. En texte simple :
    l'appelant l'échappe avant de le poser dans l'infobulle enrichie."""
    blocs = []

    combat = []
    if item.c_dmg:
        combat.append(_("Dégâts") + f" : {item.c_dmg}")
    if item.c_speed:
        combat.append(_("Vitesse") + f" : {item.c_speed}")
    if item.c_range:
        # L'API donne la portee en millimetres.
        combat.append(_("Portée") + f" : {item.c_range / 1000:.0f} m")
    for libelle, valeur in (("Esquive", item.c_dodge),
                            ("Parade", item.c_parry),
                            ("Esquive adverse", item.c_adv_dodge),
                            ("Parade adverse", item.c_adv_parry)):
        if valeur:
            combat.append(_(libelle) + f" : {valeur:+d}")
    if combat:
        blocs.append(combat)

    armure = []
    if item.c_factor_prot:
        armure.append(_("Protection") + f" : {item.c_factor_prot:.2f} %")
    for libelle, valeur in (("Max. tranchant", item.c_slash),
                            ("Max. contondant", item.c_blunt),
                            ("Max. perforant", item.c_pierce)):
        if valeur:
            armure.append(_(libelle) + f" : {valeur}")
    if armure:
        blocs.append(armure)

    bijou = [_("Protection {}").format(nom) + f" : {valeur}"
             for nom, valeur in item.protections]
    bijou += [_("Résistance {}").format(nom) + f" : {valeur:.1f}"
              for nom, valeur in item.resistances]
    if bijou:
        blocs.append(bijou)

    ampli = []
    for libelle, vitesse, puissance in (
            ("Élémentaire", item.a_elem_speed, item.a_elem_power),
            ("Affliction off.", item.a_off_speed, item.a_off_power),
            ("Soin", item.a_heal_speed, item.a_heal_power),
            ("Affliction déf.", item.a_def_speed, item.a_def_power)):
        if vitesse or puissance:
            ampli.append(_(libelle) + " : " + _("vitesse {}, puissance {}")
                         .format(vitesse, puissance))
    if ampli:
        blocs.append(ampli)

    # Une ligne vide entre les familles : armure et bijou se suivent sinon
    # sans qu'on voie ou l'une s'arrete.
    return "\n\n".join("\n".join(bloc) for bloc in blocs)


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
