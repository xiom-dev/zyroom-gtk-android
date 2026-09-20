"""L'écran « Effectif » : les membres de la guilde, et leurs mouvements.

Deux vues sous un même toit — les noms par grade, sur six colonnes, et le
registre des arrivées, des départs et des changements de grade. Un mouvement
n'existe pas dans l'API : il se déduit de deux relevés, et c'est `roster.py`,
dans le noyau, qui le sait faire. Cet écran ne fait que le montrer.

Le code vient de `window.py`, déplacé sans une ligne de changement.
"""
from __future__ import annotations

from datetime import datetime

from gi.repository import Gdk, GLib, Gtk, Pango

from . import roster
from .config import data_dir
from .i18n import _
from .ryzom_api import KIND_GUILD
from .ui_commun import _norm


class PageRoster:
    """L'effectif de la guilde, et le registre de ses mouvements."""
    #: Combien de noms par rangée dans l'effectif.
    #:
    #: Six : c'est ce qui tient sur une fenêtre au large, et le zébrage a besoin
    #: d'un nombre fixe — une boîte à flot n'a de rangées que le jour où elle se
    #: dessine, et on ne saurait pas laquelle teinter.
    ROSTER_COLONNES = 6
    # -------------------------------------------------- Registre du personnel

    def _build_roster_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        # Deux bascules liées plutôt qu'un menu déroulant, comme les deux
        # pastilles du téléphone. Le menu cachait la seconde vue à qui ne
        # pensait pas à le dérouler — et son premier choix s'appelant
        # « Effectif », du nom de la page elle-même, rien ne laissait deviner
        # qu'il y avait autre chose dessous. Les arrivées et les départs sont
        # tenus depuis le premier jour ; ils ne se voyaient pas.
        self._roster_vue = "effectif"
        vues = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vues.add_css_class("linked")
        self._roster_boutons = {}
        for nom, etiquette in (("effectif", _("Effectif")),
                               ("mouvements", _("Arrivées et départs"))):
            bouton = Gtk.ToggleButton(label=etiquette)
            bouton.connect("toggled", self._on_roster_vue, nom)
            self._roster_boutons[nom] = bouton
            vues.append(bouton)
        self._roster_boutons["effectif"].set_active(True)
        # **La place du compte est reservee des le depart.** Les deux libelles
        # gagnent un « · 178 » des que le registre est lu, et les boutons
        # s'elargissaient alors d'un coup sous le pointeur, poussant leur
        # voisin. On leur donne tout de suite la largeur qu'ils auront une
        # fois remplis. Repousse a la boucle d'inactivite : la mesure se fait
        # sur la police, et celle-ci n'est la bonne qu'une fois la fenetre
        # posee -- la version Qt s'est fait prendre au meme piege.
        GLib.idle_add(self._reserver_largeur_roster)
        bar.append(vues)

        # Cent soixante-douze noms sur six colonnes se cherchent encore à l'œil.
        # Le champ ne paraît que sur l'effectif : le journal se lit par sa date,
        # et un champ qui ne filtrerait rien serait pire qu'absent.
        self._roster_recherche = Gtk.SearchEntry()
        self._roster_recherche.set_placeholder_text(_("Rechercher un membre…"))
        self._roster_recherche.set_hexpand(True)
        self._roster_recherche.connect("search-changed",
                                       lambda *a: self._refresh_roster())
        bar.append(self._roster_recherche)

        self._roster_status = Gtk.Label(xalign=1.0)
        self._roster_status.add_css_class("dim-label")
        bar.append(self._roster_status)

        self._roster_box = Gtk.ListBox()
        # **Plusieurs lignes d'un coup.** Chaque etiquette se selectionnait
        # deja a la souris, mais une par une : recopier trois arrivees dans le
        # canal de guilde demandait trois passages. La ListBox sait choisir
        # plusieurs rangees -- clic, Maj+clic, Ctrl+clic -- des qu'on le lui
        # permet, et le glisse s'ajoute d'un geste. Ctrl+C et le clic droit
        # copient ensuite, comme dans le journal des mouvements.
        self._roster_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self._roster_box.add_css_class("survol")
        glisse = Gtk.GestureDrag()
        glisse.connect("drag-begin", self._on_registre_glisse_debut)
        glisse.connect("drag-update", self._on_registre_glisse)
        self._roster_box.add_controller(glisse)
        clic = Gtk.GestureClick(button=3)
        clic.connect("pressed", self._on_registre_clic_droit)
        self._roster_box.add_controller(clic)
        raccourci = Gtk.ShortcutController()
        raccourci.set_scope(Gtk.ShortcutScope.GLOBAL)
        raccourci.add_shortcut(Gtk.Shortcut(
            trigger=Gtk.ShortcutTrigger.parse_string("<Control>c"),
            action=Gtk.CallbackAction.new(
                lambda *_a: self._copier_registre_choisi())))
        self.add_controller(raccourci)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_child(self._roster_box)
        page.append(scrolled)
        return page

    def _reserver_largeur_roster(self) -> bool:
        """Fige la largeur des deux bascules sur leur libelle le plus long."""
        from gi.repository import Pango
        for nom, gabarit in (("effectif", _("Effectif · %d") % 9999),
                             ("mouvements",
                              _("Arrivées et départs · %d") % 9999)):
            bouton = self._roster_boutons.get(nom)
            if bouton is None:
                continue
            mise = Pango.Layout(bouton.get_pango_context())
            mise.set_text(gabarit)
            # La marge du theme par-dessus le texte, comme du cote Qt.
            bouton.set_size_request(mise.get_pixel_size().width + 36, -1)
        return False

    def _on_roster_vue(self, bouton, nom: str) -> None:
        """Deux bascules qui se conduisent comme un choix unique.

        Un bouton bascule se relâche quand on le reclique : recliquer la vue
        déjà affichée la laisserait donc sans aucune des deux d'active, et la
        liste se viderait. On le remet enfoncé sans rien redessiner."""
        if not bouton.get_active():
            if nom == self._roster_vue:
                bouton.set_active(True)
            return
        if nom == self._roster_vue:
            return
        self._roster_vue = nom
        autre = "mouvements" if nom == "effectif" else "effectif"
        self._roster_boutons[autre].set_active(False)
        self._refresh_roster()

    def _refresh_roster(self) -> None:
        while (child := self._roster_box.get_first_child()) is not None:
            self._roster_box.remove(child)
        self._roster_recherche.set_visible(self._roster_vue == "effectif")
        # L'effectif s'ouvre quelle que soit l'entité choisie : c'est celui de
        # la dernière guilde rencontrée, et consulter un registre ne devrait pas
        # obliger à changer d'entité. Le nom de la guilde est rappelé quand ce
        # n'est pas celle qu'on regarde.
        ent = self._entity
        if ent is None or ent.kind != KIND_GUILD or not ent.members:
            ent = self._derniere_guilde or self._entite_en_cache(KIND_GUILD)
            self._derniere_guilde = self._derniere_guilde or ent
            ailleurs = ent is not None
        else:
            ailleurs = False
        if ent is None:
            self._compter_roster(0, 0)
            self._roster_status.set_text(
                _("Aucune guilde consultée pour l'instant : ouvrez-en une une "
                  "fois, et son effectif restera consultable d'ici."))
            return

        store = (self._roster_store if not ailleurs
                 else roster.RosterStore(data_dir(), ent.entity_id))
        changements = store.history() if store else []
        # Les nombres sont sur les boutons, comme sur le téléphone : c'est là
        # qu'ils disent quelque chose — « il y a trois mouvements à voir » — au
        # lieu de compter ce qu'on a déjà sous les yeux. Reste au statut ce
        # qu'un bouton ne peut pas porter : de quelle guilde il s'agit quand ce
        # n'est pas celle qu'on regarde, et jusqu'où remonte le journal.
        self._compter_roster(len(ent.members), len(changements))
        morceaux = []
        if ailleurs:
            morceaux.append(ent.name)
        if self._roster_vue == "mouvements":
            morceaux.append(_("journal des %d derniers jours")
                            % roster.RETENTION_JOURS)
        self._roster_status.set_text(" · ".join(morceaux))

        if self._roster_vue == "mouvements":
            self._remplir_mouvements_roster(changements)
        else:
            self._remplir_effectif_roster(ent)

    def _compter_roster(self, membres: int, mouvements: int) -> None:
        """Inscrit les deux comptes sur les bascules.

        Zéro ne s'écrit pas : « Arrivées et départs · 0 » se lit comme un compte
        à vérifier, alors qu'il n'y a rien à aller voir."""
        self._roster_boutons["effectif"].set_label(
            _("Effectif · %d") % membres if membres else _("Effectif"))
        self._roster_boutons["mouvements"].set_label(
            _("Arrivées et départs · %d") % mouvements if mouvements
            else _("Arrivées et départs"))

    def _remplir_effectif_roster(self, ent) -> None:
        """L'effectif, par grade, en autant de colonnes que la fenêtre en tient.

        Cent soixante-dix noms sur une seule colonne faisaient un ruban plus
        haut que dix écrans, où l'on ne trouvait rien. Ils se rangent sur six
        colonnes, et **c'est le grade qui est teinté, non la ligne** : le
        zébrage sert ici à séparer les groupes, pas à suivre une ligne — un
        nom n'a rien à droite de lui qu'on doive relier."""
        # Le chef d'abord, les membres ensuite : on lit une liste de guilde par
        # le haut, et l'API la rend dans un ordre qui n'en est pas un.
        cherche = _norm(self._roster_recherche.get_text().strip())
        membres = sorted((nm for nm in ent.members
                          if not cherche or cherche in _norm(nm[0])),
                         key=lambda nm: (roster.rang_grade(nm[1]), nm[0].lower()))
        # Le bouton continue d'annoncer l'effectif entier : c'est ce qu'on
        # cherche à savoir d'une guilde, et un compte qui fond à mesure qu'on
        # tape ne dit plus rien de l'effectif.
        if not membres:
            self._roster_box.append(self._ligne_simple(
                _("Aucun membre de ce nom."), dim=True))
            return
        par_grade: dict[str, list[str]] = {}
        for nom, grade, *_ in membres:      # le reste, c'est la date d'entrée
            par_grade.setdefault(grade, []).append(nom)

        for rang_groupe, (grade, noms) in enumerate(par_grade.items()):
            teinte = rang_groupe % 2 == 0
            entete = Gtk.ListBoxRow()
            entete.set_activatable(False)
            if teinte:
                entete.add_css_class("zebre")
            titre = Gtk.Label(label=f"{roster.nom_grade(grade)} · {len(noms)}",
                              xalign=0.0, selectable=True)
            titre.add_css_class("title-4")
            titre.add_css_class("peuple")
            titre.props.margin_top = 10
            titre.props.margin_start = 8
            titre.props.margin_bottom = 2
            entete.set_child(titre)
            self._roster_box.append(entete)

            # Une grille et non une boîte à flot : le zébrage suppose des
            # rangées, et une boîte à flot n'en a que le jour où elle se
            # dessine. Six colonnes, comme elle en tenait au large.
            for depart in range(0, len(noms), self.ROSTER_COLONNES):
                tranche = noms[depart:depart + self.ROSTER_COLONNES]
                row = Gtk.ListBoxRow()
                row.set_activatable(False)
                if teinte:
                    row.add_css_class("zebre")
                grille = Gtk.Grid(column_spacing=4, column_homogeneous=True)
                self._pad(grille)
                grille.props.margin_top = 1
                grille.props.margin_bottom = 1
                # La rangée est toujours remplie jusqu'à six, au besoin de
                # cases vides : une grille homogène ne répartit que les colonnes
                # qui existent, et la dernière rangée d'un grade — deux noms —
                # s'étalait sur toute la largeur au lieu de s'aligner sur celles
                # du dessus.
                for colonne in range(self.ROSTER_COLONNES):
                    nom = tranche[colonne] if colonne < len(tranche) else ""
                    # **Copiable a la souris.** Un nom de joueur se recopie
                    # dans le canal de guilde ou dans un message ; le retaper
                    # de memoire est le plus sur moyen d'ecorcher un pseudo.
                    label = Gtk.Label(label=nom, xalign=0.0, selectable=True)
                    label.add_css_class("compact")
                    label.set_ellipsize(Pango.EllipsizeMode.END)
                    grille.attach(label, colonne, 0, 1, 1)
                row.set_child(grille)
                self._roster_box.append(row)

    #: Le signe de chaque mouvement : forme, classe de couleur, et sens.
    #:
    #: La couleur porte le sens — vert pour ce qui entre, rouge pour ce qui
    #: sort, blanc pour ce qui bouge à l'intérieur — et la direction du triangle
    #: le confirme, pour qui distingue mal les deux teintes.
    SIGNES = {
        ("arrivee", True): ("▲", "tri-arrivee", "arrivée"),
        ("depart", True): ("▼", "tri-depart", "départ"),
        ("grade", True): ("▲", "tri-grade", "montée de grade"),
        ("grade", False): ("▼", "tri-retro", "rétrogradation"),
    }

    def _signe_mouvement(self, c) -> tuple:
        if c.kind == "grade":
            return self.SIGNES[("grade", c.promotion)]
        return self.SIGNES[(c.kind, True)]

    def _remplir_mouvements_roster(self, changements: list) -> None:
        self._roster_box.append(self._legende_roster())
        if not changements:
            self._roster_box.append(self._ligne_simple(
                _("Aucun mouvement depuis le premier relevé. Le registre "
                  "compare l'effectif d'une synchronisation à l'autre : l'API "
                  "ne garde aucune histoire, seule l'application en tient une."),
                dim=True))
            return
        for rang, c in enumerate(changements):
            row = Gtk.ListBoxRow()
            if rang % 2 == 0:
                row.add_css_class("zebre")
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            self._pad(line)
            line.props.margin_top = 2
            line.props.margin_bottom = 2

            # **Plus de `selectable` ici.** Une etiquette selectionnable
            # avale le clic pour y poser un curseur de texte, et la rangee ne
            # se choisissait plus. Ce qu'on vient chercher -- le nom du
            # joueur -- part maintenant avec la ligne entiere.
            quand = Gtk.Label(label=datetime.fromtimestamp(c.at)
                              .strftime("%d/%m %H:%M"), xalign=0.0)
            quand.add_css_class("dim-label")
            quand.add_css_class("compact")
            line.append(quand)

            forme, classe, _sens = self._signe_mouvement(c)
            triangle = Gtk.Label(label=forme)
            triangle.add_css_class(classe)
            line.append(triangle)

            line.append(Gtk.Label(label=roster.decrire(c), xalign=0.0))
            row.set_child(line)
            self._roster_box.append(row)

    # ------------------------------------- Choisir et copier dans le registre
    @staticmethod
    def _textes_du_widget(widget) -> list:
        """Tous les libellés d'une rangée, de gauche à droite.

        Recursif : une rangée du registre est une boîte de trois étiquettes,
        celle de l'effectif une grille de six, et la légende un assemblage de
        paires. On ne sait pas d'avance laquelle on tient.
        """
        mots = []
        if isinstance(widget, Gtk.Label):
            texte = widget.get_text()
            if texte:
                mots.append(texte)
            return mots
        enfant = widget.get_first_child() if widget is not None else None
        while enfant is not None:
            mots += PageRoster._textes_du_widget(enfant)
            enfant = enfant.get_next_sibling()
        return mots

    def _lignes_registre_choisies(self) -> list:
        """Le texte des rangées choisies, de haut en bas."""
        textes = []
        for row in self._roster_box.get_selected_rows():
            mots = self._textes_du_widget(row.get_child())
            if mots:
                textes.append("  ".join(mots))
        return textes

    def _copier_registre_choisi(self) -> bool:
        """Ctrl+C : met les rangées choisies dans le presse-papiers.

        Sans effet ailleurs que sur l'écran du registre : le raccourci est
        pose sur la fenetre, et le journal des mouvements a le sien.
        """
        if self._stack.get_visible_child_name() != "plus":
            return False
        if self._plus_stack.get_visible_child_name() != "roster":
            return False
        textes = self._lignes_registre_choisies()
        if not textes:
            return False
        self.get_clipboard().set("\n".join(textes))
        self._set_status(_("%d ligne(s) copiée(s).") % len(textes))
        return True

    def _on_registre_glisse_debut(self, _geste, _x, y) -> None:
        """L'ancre du glissé : la rangée où le bouton s'est enfoncé."""
        self._registre_ancre = self._roster_box.get_row_at_y(int(y))

    def _on_registre_glisse(self, geste, dx, dy) -> None:
        """Étend le choix jusqu'à la rangée sous le pointeur.

        Maj+clic suppose qu'on sache qu'il existe ; tirer du doigt sur
        plusieurs lignes est le geste qu'on essaie d'abord.
        """
        ancre = getattr(self, "_registre_ancre", None)
        if ancre is None:
            return
        ok, _x, y = geste.get_start_point()
        if not ok:
            return
        arrivee = self._roster_box.get_row_at_y(int(y + dy))
        if arrivee is None:
            return
        debut, fin = sorted((ancre.get_index(), arrivee.get_index()))
        self._roster_box.unselect_all()
        for rang in range(debut, fin + 1):
            row = self._roster_box.get_row_at_index(rang)
            if row is not None and row.get_selectable():
                self._roster_box.select_row(row)

    def _on_registre_clic_droit(self, _geste, _n, x, y) -> None:
        """Propose de copier ce qui est choisi, ou la rangée visée."""
        row = self._roster_box.get_row_at_y(int(y))
        if row is None:
            return
        # Un clic droit hors de ce qui est choisi prend la rangee visee : sinon
        # le menu proposerait de copier des lignes qu'on ne montre pas du
        # doigt.
        if not row.is_selected():
            self._roster_box.unselect_all()
            self._roster_box.select_row(row)
        textes = self._lignes_registre_choisies()
        if not textes:
            return
        texte = "\n".join(textes)
        bouton = Gtk.Button(label=_("Copier la ligne") if len(textes) == 1
                            else _("Copier les %d lignes") % len(textes))
        bouton.add_css_class("flat")
        popover = Gtk.Popover()
        popover.add_css_class("menu")
        popover.set_child(bouton)
        # Accroche a la rangee cliquee, qui mesure ce qu'on voit : le menu
        # s'ouvre sous le pointeur quel que soit le defilement. **Le rectangle
        # se remplit champ par champ** -- `Gdk.Rectangle(x=…)` ne pose rien,
        # PyGObject ignore les arguments d'une structure boxed.
        ok, cadre = row.compute_bounds(self._roster_box)
        vise = Gdk.Rectangle()
        vise.x = int(x)
        vise.y = int(y - cadre.origin.y) if ok else 0
        vise.width = vise.height = 1
        popover.set_parent(row)
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_pointing_to(vise)
        popover.connect("closed", lambda pop: pop.unparent())

        def copier(_b):
            self.get_clipboard().set(texte)
            popover.popdown()
            self._set_status(_("%d ligne(s) copiée(s).") % len(textes))
        bouton.connect("clicked", copier)
        popover.popup()

    def _legende_roster(self) -> Gtk.ListBoxRow:
        """Quatre signes et leur sens, en tête du journal.

        Sans elle, un triangle rouge vers le bas se lit comme une alarme plutôt
        que comme un départ.

        Elle porte aussi ce que les dates ne peuvent pas dire d'elles-mêmes :
        une arrivée est datée du jour où elle a eu lieu, l'API le sait ; un
        départ ne l'est que du relevé qui l'a constaté, faute que l'API en
        garde la moindre trace."""
        row = Gtk.ListBoxRow()
        # La legende coiffe le registre, elle n'en est pas une ligne :
        # la choisir copierait le mode d'emploi des triangles.
        row.set_selectable(False)
        row.set_activatable(False)
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self._pad(line)
        for (forme, classe, sens) in (self.SIGNES[("arrivee", True)],
                                      self.SIGNES[("depart", True)],
                                      self.SIGNES[("grade", True)],
                                      self.SIGNES[("grade", False)]):
            paire = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            triangle = Gtk.Label(label=forme)
            triangle.add_css_class(classe)
            paire.append(triangle)
            texte = Gtk.Label(label=_(sens))
            texte.add_css_class("dim-label")
            texte.add_css_class("compact")
            paire.append(texte)
            line.append(paire)
        note = Gtk.Label(label=_("départs et grades : date du relevé"),
                         xalign=1.0)
        note.add_css_class("dim-label")
        note.add_css_class("compact")
        note.set_hexpand(True)
        # Une note ne doit jamais élargir la fenêtre : elle s'efface avant.
        note.set_ellipsize(Pango.EllipsizeMode.END)
        line.append(note)
        row.set_child(line)
        return row
