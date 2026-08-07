"""Fenêtre d'information détaillée d'un item (caractéristiques de craft)."""
from __future__ import annotations

import time

from gi.repository import GLib, Gtk

from .i18n import _
from .models import (CLASS_NAMES, COLOR_NAMES, ECOSYSTEM_NAMES, MAT_CATEGORY,
                     MAT_SPEC, ItemInfo, ItemType)


class _Section:
    """Aide à construire une section (titre + lignes clé/valeur)."""
    def __init__(self, title: str):
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header = Gtk.Label(xalign=0.0)
        header.set_markup(f"<b>{GLib.markup_escape_text(_(title))}</b>")
        header.props.margin_top = 8
        self.box.append(header)
        self.grid = Gtk.Grid(column_spacing=14, row_spacing=2)
        self.grid.props.margin_start = 8
        self.box.append(self.grid)
        self._row = 0
        self.count = 0

    def add(self, key: str, value) -> None:
        if value is None or value == "":
            return
        k = Gtk.Label(label=_(key), xalign=0.0)
        k.add_css_class("dim-label")
        v = Gtk.Label(label=str(value), xalign=0.0, selectable=True, wrap=True)
        self.grid.attach(k, 0, self._row, 1, 1)
        self.grid.attach(v, 1, self._row, 1, 1)
        self._row += 1
        self.count += 1


def _time_left(expires: int) -> str:
    remaining = expires - time.time()
    if remaining <= 0:
        return "expiré"
    h = int(remaining // 3600)
    m = int((remaining % 3600) // 60)
    return f"{h} h {m} min"


def build_detail(item: ItemInfo, name_fn, category_db) -> Gtk.Widget:
    """Construit le contenu détaillé d'un item (widget défilable)."""
    if item.item_type in (ItemType.NATURAL_MAT, ItemType.ANIMAL_MAT) and category_db:
        category_db.fill(item)

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
        setattr(root.props, m, 12)

    # Général
    g = _Section("Général")
    friendly = name_fn(item.sheet) if name_fn else item.sheet
    g.add("Nom", friendly if friendly != item.sheet else "")
    g.add("Fiche", item.sheet)
    g.add("Identifiant", item.item_id)
    g.add("Qualité", item.quality or "")
    g.add("Quantité", item.stack or "")
    if item.item_class != item.item_class.UNKNOWN:
        g.add("Classe", _(CLASS_NAMES[int(item.item_class)]))
    if item.ecosystem != item.ecosystem.UNKNOWN:
        g.add("Écosystème", _(ECOSYSTEM_NAMES[int(item.ecosystem)]))
    g.add("Volume", f"{item.volume:.2f}" if item.volume else "")
    g.add("Poids", f"{item.weight:.2f}" if item.weight else "")
    if item.item_type == ItemType.EQUIPMENT and item.hp:
        g.add("Durabilité", item.hp)
    if item.locked:
        g.add("Protégé", "oui")
    root.append(g.box)

    # Combat
    c = _Section("Combat")
    c.add("Dégâts", item.c_dmg or "")
    c.add("Vitesse", item.c_speed or "")
    c.add("Portée", item.c_range or "")
    c.add("Mod. esquive", item.c_dodge or "")
    c.add("Mod. parade", item.c_parry or "")
    c.add("Mod. esquive adverse", item.c_adv_dodge or "")
    c.add("Mod. parade adverse", item.c_adv_parry or "")
    if c.count:
        root.append(c.box)

    # Protection (armure)
    p = _Section("Protection")
    if item.c_factor_prot:
        p.add("Facteur de protection", f"{item.c_factor_prot:.2f}")
    p.add("Prot. tranchant max.", item.c_slash or "")
    p.add("Prot. contondant max.", item.c_blunt or "")
    p.add("Prot. perforant max.", item.c_pierce or "")
    if p.count:
        root.append(p.box)

    # Bijou : protections + résistances
    if item.protections or item.resistances:
        j = _Section("Bijou")
        for name, value in item.protections:
            j.add(f"Protection {name}", value)
        for name, value in item.resistances:
            j.add(f"Résistance {name}", f"{value:.2f}")
        root.append(j.box)

    # Amplificateur magique
    a = _Section("Amplificateur")
    a.add("Vit. sort élémentaire", item.a_elem_speed or "")
    a.add("Puiss. élémentaire", item.a_elem_power or "")
    a.add("Vit. affliction off.", item.a_off_speed or "")
    a.add("Puiss. affliction off.", item.a_off_power or "")
    a.add("Vit. soin", item.a_heal_speed or "")
    a.add("Puiss. soin", item.a_heal_power or "")
    a.add("Vit. affliction déf.", item.a_def_speed or "")
    a.add("Puiss. affliction déf.", item.a_def_power or "")
    if a.count:
        root.append(a.box)

    # Bonus
    b = _Section("Bonus")
    b.add("HP", item.hp_buff or "")
    b.add("Sève", item.sap_buff or "")
    b.add("Stamina", item.sta_buff or "")
    b.add("Focus", item.focus_buff or "")
    if b.count:
        root.append(b.box)

    # Matière
    if item.mat_category1 or item.mat_specs1:
        mat = _Section("Matière")
        if 0 <= item.mat_category1 < len(MAT_CATEGORY):
            mat.add("Catégorie 1", _(MAT_CATEGORY[item.mat_category1]))
        for idx, level in item.mat_specs1:
            if 0 < idx < len(MAT_SPEC):
                mat.add(MAT_SPEC[idx], "★" * level)
        if 0 < item.mat_category2 < len(MAT_CATEGORY):
            mat.add("Catégorie 2", _(MAT_CATEGORY[item.mat_category2]))
        for idx, level in item.mat_specs2:
            if 0 < idx < len(MAT_SPEC):
                mat.add(MAT_SPEC[idx], "★" * level)
        if item.mat_colors:
            cols = ", ".join(_(COLOR_NAMES[c]) for c in item.mat_colors
                             if 0 <= c < len(COLOR_NAMES))
            mat.add("Couleurs", cols)
        root.append(mat.box)

    # Vente
    if item.price or item.expires:
        s = _Section("Vente")
        if item.price:
            s.add("Prix", f"{item.price:,.0f} dappers".replace(",", " "))
        s.add("Continent", item.continent)
        if item.expires:
            s.add("Expire dans", _time_left(item.expires))
        root.append(s.box)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_child(root)
    return scroll


def show_detail(parent, item: ItemInfo, name_fn, category_db) -> None:
    friendly = name_fn(item.sheet) if name_fn else item.sheet
    win = Gtk.Window(title=friendly, transient_for=parent)
    win.set_default_size(380, 520)
    win.set_child(build_detail(item, name_fn, category_db))
    win.present()
