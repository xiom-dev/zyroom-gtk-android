"""L'écran « Compétences » : l'arbre à quatre branches du personnage.

Il se plie à tous les échelons, et porte les niveaux, l'avancement du niveau
en cours et les points par branche.

Le code vient de `window.py`, déplacé sans une ligne de changement.
`_entite_en_cache`, qui sert aussi à l'Effectif, y est resté : ce n'est pas
d'un écran, c'est de la fenêtre.
"""
from __future__ import annotations

from gi.repository import Gtk

from . import skills as skills_mod
from .i18n import _
from .ryzom_api import KIND_CHARACTER
from .ui_commun import _norm


class PageSkills:
    """L'arbre des compétences, et ce qu'il sait replier."""
    def _refresh_skills(self) -> None:
        """Redessine l'arbre : ce qui est visible dépend des replis, sauf quand
        une recherche ou un filtre est actif — la liste est alors plate, car
        chercher « épée » et ne rien voir parce que la branche est fermée serait
        absurde."""
        while (child := self._skills_box.get_first_child()) is not None:
            self._skills_box.remove(child)

        # L'arbre s'ouvre quelle que soit l'entité choisie : c'est celui du
        # dernier personnage rencontré. Une guilde n'a pas de compétences, et
        # devoir rebasculer d'entité pour consulter un arbre n'aurait aucun sens.
        ent = self._entity
        ailleurs = False
        if not getattr(ent, "skills", None):
            ent = self._dernier_perso or self._entite_en_cache(KIND_CHARACTER)
            self._dernier_perso = self._dernier_perso or ent
            ailleurs = ent is not None
        skills = getattr(ent, "skills", []) if ent else []
        if not skills:
            self._skills_status.set_text(
                _("Aucun personnage consulté pour l'instant : ouvrez-en un une "
                  "fois, et son arbre restera consultable d'ici. L'API ne donne "
                  "les compétences que pour un personnage, et seulement si la "
                  "clé accorde ce module."))
            self._skills_toggle.set_sensitive(False)
            return
        self._skills_toggle.set_sensitive(True)
        self._skills_de = ent.name if ailleurs else ""

        self._skills_tree = skills_mod.build_tree(skills)
        # Ce qui est monté au maximum, y compris les pères dont tout ce qu'ils
        # portent est fini : c'est ce qu'on cherche en parcourant l'arbre.
        self._skills_finies = skills_mod.finished(self._skills_tree)
        needle = _norm(self._skills_search.get_text().strip())
        en_cours = self._skills_filter.get_selected() == 1
        filtering = bool(needle) or en_cours

        if filtering:
            rows = [n for n in self._skills_tree
                    if (not en_cours or n.skill.progress)
                    and (not needle or needle in _norm(self._names.name(n.skill.code)))]
        else:
            rows = skills_mod.visible(self._skills_tree, self._skills_expanded)

        self._skills_toggle.set_label(
            _("Tout replier") if self._skills_expanded else _("Tout déplier"))
        self._skills_toggle.set_visible(not filtering)

        for index, node in enumerate(rows):
            self._skills_box.append(
                self._skill_row(node, index, filtering))

        montrees = len(rows)
        # Le nom du personnage n'est rappelé que si ce n'est pas celui qu'on
        # regarde : sinon il serait déjà deux fois à l'écran.
        prefixe = f"{self._skills_de} · " if self._skills_de else ""
        self._skills_status.set_text(
            prefixe + _("%d compétences, %d affichées") % (len(skills), montrees))

    def _skill_row(self, node, index: int, filtering: bool) -> Gtk.ListBoxRow:
        racine = node.depth == 0 and not filtering
        row = Gtk.ListBoxRow()
        row._code = node.skill.code if (node.has_children and not filtering) else ""
        row.set_activatable(bool(row._code))
        # Une ligne sur deux teintée, comme les tableaux de l'application
        # Android : sur des colonnes étroites l'œil perd sa ligne.
        if index % 2 == 0:
            row.add_css_class("zebre")

        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        line.props.margin_top = 4
        line.props.margin_bottom = 4
        line.props.margin_end = 8
        # Un cran par échelon, à partir du retrait de la flèche des racines.
        line.props.margin_start = 8 + (0 if filtering else node.depth * 14)

        fleche = Gtk.Label(label=("▾" if node.skill.code in self._skills_expanded
                                  else "▸") if row._code else " ", xalign=0.0)
        fleche.set_size_request(14, -1)
        line.append(fleche)

        nom = Gtk.Label(label=self._names.name(node.skill.code), xalign=0.0)
        nom.set_hexpand(True)
        if racine:
            nom.add_css_class("heading")
        # Toute la ligne au vert quand il n'y a plus rien à monter : c'est ce
        # qui se voit de loin en faisant défiler, et le père compte autant que
        # sa feuille — il plafonne à 100 alors que tout dessous est à 250.
        finie = node.skill.code in self._skills_finies
        if finie:
            nom.add_css_class("fini")
        line.append(nom)

        if node.skill.progress:
            barre = Gtk.LevelBar()
            barre.set_min_value(0)
            barre.set_max_value(100)
            barre.set_value(node.skill.progress)
            barre.set_size_request(90, -1)
            barre.set_valign(Gtk.Align.CENTER)
            line.append(barre)

        # Le niveau atteint, et non le plafond de l'echelon : « Creer bijoux »
        # affichait 50 quand tout ce qu'elle porte est monte a 250, et il
        # fallait deplier pour le savoir.
        atteint = (skills_mod.niveau_atteint(self._skills_tree, node.skill.code)
                   if node.has_children else node.skill.level)
        niveau = Gtk.Label(
            label=(f"{atteint} · {node.skill.progress} %"
                   if node.skill.progress else str(atteint)),
            xalign=1.0)
        niveau.set_size_request(90, -1)
        if finie:
            niveau.add_css_class("fini")
        line.append(niveau)

        if racine:
            points = getattr(self._entity, "skill_points", {}).get(node.skill.code)
            if points:
                # Le niveau d'une racine plafonne bas — Combat vaut 20 : c'est
                # le plus haut de ses descendants qui dit où en est la branche.
                detail = Gtk.Label(
                    label=_("%s pts · %s dépensés") % (f"{points[0]:,}".replace(",", " "),
                                                       f"{points[1]:,}".replace(",", " ")),
                    xalign=0.0)
                detail.add_css_class("dim-label")
                detail.add_css_class("caption")
                colonne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                colonne.append(line)
                detail.props.margin_start = 8 + 14
                detail.props.margin_bottom = 4
                colonne.append(detail)
                row.set_child(colonne)
                return row

        row.set_child(line)
        return row
    def _build_skills_page(self) -> Gtk.Widget:
        """L'arbre des compétences : quatre branches qui se plient à tous les
        échelons, avec le niveau et l'avancement du niveau en cours."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._skills_search = Gtk.SearchEntry()
        self._skills_search.set_placeholder_text(_("Rechercher une compétence…"))
        self._skills_search.set_hexpand(True)
        self._skills_search.connect("search-changed", lambda *a: self._refresh_skills())
        bar.append(self._skills_search)

        self._skills_filter = Gtk.DropDown.new_from_strings([_("Tout"), _("En cours")])
        self._skills_filter.set_tooltip_text(
            _("« En cours » ne garde que les niveaux entamés"))
        self._skills_filter.connect("notify::selected", lambda *a: self._refresh_skills())
        bar.append(self._skills_filter)

        # Un seul bouton : son nom dit ce qu'il va faire, et il n'y a jamais
        # qu'une action sensée à proposer.
        self._skills_toggle = Gtk.Button(label=_("Tout déplier"))
        self._skills_toggle.connect("clicked", self._on_skills_toggle_all)
        bar.append(self._skills_toggle)

        self._skills_box = Gtk.ListBox()
        self._skills_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._skills_box.add_css_class("survol")
        self._skills_box.connect("row-activated", self._on_skill_row)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._skills_box)
        page.append(scrolled)

        self._skills_status = Gtk.Label(xalign=0.0)
        self._skills_status.add_css_class("dim-label")
        self._skills_status.props.margin_start = 8
        self._skills_status.props.margin_bottom = 6
        page.append(self._skills_status)

        self._skills_expanded: set[str] = set()
        self._skills_finies: set[str] = set()
        self._skills_tree: list = []
        return page

    def _on_skills_toggle_all(self, _btn) -> None:
        if self._skills_expanded:
            self._skills_expanded = set()
        else:
            self._skills_expanded = {n.skill.code for n in self._skills_tree
                                     if n.has_children}
        self._refresh_skills()

    def _on_skill_row(self, _box, row) -> None:
        code = getattr(row, "_code", "")
        if not code:
            return
        if code in self._skills_expanded:
            self._skills_expanded.discard(code)
        else:
            self._skills_expanded.add(code)
        self._refresh_skills()
