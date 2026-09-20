"""L'écran « Perdu ? » : où sont les bêtes du joueur, sur la carte d'Atys.

Un mektoub de bât laissé en pleine terre y reste, et son propriétaire finit
par oublier où. L'API donne sa position à chaque relevé ; c'est la seule chose
qu'elle sache dire d'un animal qu'on ne retrouve plus.

Ce module ne contient que cet écran. Il vivait dans `window.py`, au milieu des
six autres ; le sortir n'a rien changé à son code — les méthodes sont les
mêmes, dans le même ordre. `MainWindow` hérite de ce mixin, et `self._…`
continue de désigner la fenêtre entière.

Les réglages communs aux deux cartes — zoom, seuil de regroupement — sont dans
`page_cartes.py`.
"""
from __future__ import annotations

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from . import carte
from .i18n import _


class PageBetes:
    """L'écran des montures, et la carte qu'il dessine."""
    #: Le noir des cernes et des liserés, jamais tout à fait noir pour l'œil.
    CERNE = (0.06, 0.08, 0.09)

    #: Le bleu du repère du joueur, distinct du rouge des bêtes.
    POINT_JOUEUR = (0.23, 0.61, 1.0)

    def _build_betes_page(self) -> Gtk.Widget:
        """Où sont les bêtes du joueur.

        Un mektoub de bât laissé en pleine terre y reste, et son propriétaire
        finit par oublier où. L'API donne sa position à chaque relevé ; c'est la
        seule chose qu'elle sache dire d'un animal qu'on ne retrouve plus.

        Seule la carte dit où : les coordonnées ne sont pas affichées. Le jeu ne
        permet pas d'en saisir pour poser un repère, donc deux nombres de plus
        n'auraient servi à rien.
        """
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self._betes_carte = Gtk.DrawingArea()
        self._betes_carte.set_content_height(300)
        self._betes_carte.set_draw_func(self._dessiner_carte_betes)
        self._betes_zoom = 1.0
        self._betes_glissement = [0.0, 0.0]

        # Trois façons d'agrandir, parce que trois matériels : le pincement du
        # pavé tactile, la molette de la souris, et le glissement au bouton pour
        # se déplacer une fois agrandi. Le monde entier tient dans la hauteur
        # d'une carte de visite : sans agrandissement, deux bêtes séparées de
        # cinq cents mètres sont au même endroit.
        pincement = Gtk.GestureZoom()
        pincement.connect("scale-changed", self._on_betes_pincement)
        self._betes_carte.add_controller(pincement)

        molette = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL)
        molette.connect("scroll", self._on_betes_molette)
        self._betes_carte.add_controller(molette)

        glisse = Gtk.GestureDrag()
        glisse.connect("drag-update", self._on_betes_glisse)
        glisse.connect("drag-end", self._on_betes_glisse_fin)
        self._betes_carte.add_controller(glisse)
        self._betes_glisse_depart = [0.0, 0.0]

        page.append(self._betes_carte)

        self._betes_entete = Gtk.Label(xalign=0.0)
        self._betes_entete.add_css_class("dim-label")
        self._pad(self._betes_entete)
        page.append(self._betes_entete)

        # Deux colonnes : les mektoubs à gauche — de monte comme de bât —, les
        # zigs à droite. On cherche rarement les uns en pensant aux autres, et
        # les zigs sont souvent nombreux.
        defilement = Gtk.ScrolledWindow(vexpand=True)
        colonnes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                           homogeneous=True)
        self._pad(colonnes)
        self._betes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._betes_zigs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        colonnes.append(self._betes_box)
        colonnes.append(self._betes_zigs)
        defilement.set_child(colonnes)
        page.append(defilement)

        self._betes_pixbuf = None
        return page

    def _rafraichir_betes_si_visible(self) -> None:
        """Recharge la liste si on la regarde : changer d'entité change de bêtes."""
        if (self._stack.get_visible_child_name() == "plus"
                and self._plus_stack.get_visible_child_name() == "betes"):
            self._remplir_betes(self._entity)

    def _borner_glissement(self) -> None:
        """Empêche la carte des bêtes de s'échapper de son cadre.

        Le débord se mesurait sur la largeur du cadre — `largeur × (zoom − 1)`
        — alors que la carte y tient en boîte aux lettres : on pouvait donc la
        pousser dans le vide. `_borner_carte` le mesure sur l'image telle
        qu'elle est dessinée."""
        self._borner_carte(self._betes_carte, self._betes_zoom,
                           self._betes_glissement)

    def _regler_zoom_betes(self, facteur: float) -> None:
        avant = self._betes_zoom
        self._betes_zoom = max(1.0, min(self.ZOOM_MAX, self._betes_zoom * facteur))
        if self._betes_zoom == avant:
            return
        rapport = self._betes_zoom / avant
        self._betes_glissement[0] *= rapport
        self._betes_glissement[1] *= rapport
        self._borner_glissement()
        self._betes_carte.queue_draw()

    def _on_betes_pincement(self, gesture, echelle) -> None:
        # Le geste rend une échelle absolue depuis son début ; on la ramène à un
        # facteur relatif pour la composer avec l'agrandissement en cours.
        depart = getattr(self, "_betes_pince_depart", None)
        if depart is None or not gesture.is_active():
            self._betes_pince_depart = self._betes_zoom
            depart = self._betes_zoom
        avant = self._betes_zoom
        self._betes_zoom = max(1.0, min(self.ZOOM_MAX, depart * echelle))
        # Le déplacement suit l'agrandissement, sinon la vue part sur le côté :
        # l'image grandit autour de son propre milieu, pas autour du nôtre.
        if avant > 0:
            rapport = self._betes_zoom / avant
            self._betes_glissement[0] *= rapport
            self._betes_glissement[1] *= rapport
        self._borner_glissement()
        self._betes_glisse_depart = list(self._betes_glissement)
        self._betes_carte.queue_draw()

    def _on_betes_molette(self, _controller, _dx, dy) -> bool:
        self._regler_zoom_betes(
            1 / self.PAS_ZOOM if dy > 0 else self.PAS_ZOOM)
        return True

    def _on_betes_glisse(self, _gesture, dx, dy) -> None:
        self._betes_glissement[0] = self._betes_glisse_depart[0] + dx
        self._betes_glissement[1] = self._betes_glisse_depart[1] + dy
        self._borner_glissement()
        self._betes_carte.queue_draw()

    def _on_betes_glisse_fin(self, _gesture, _dx, _dy) -> None:
        self._betes_glisse_depart = list(self._betes_glissement)

    def _remplir_betes(self, ent) -> None:
        for boite in (self._betes_box, self._betes_zigs):
            while (child := boite.get_first_child()) is not None:
                boite.remove(child)
        betes = list(getattr(ent, "betes", []))
        dehors = [b for b in betes if b.dehors]
        self._betes_entete.set_text(
            _("Aucune bête dehors : toutes sont rangées.") if not dehors
            else _("%d bête dehors") % len(dehors) if len(dehors) == 1
            else _("%d bêtes dehors") % len(dehors))
        self._remplir_colonne_betes(self._betes_box, _("Mektoubs"),
                                    [b for b in betes if not b.zig])
        self._remplir_colonne_betes(self._betes_zigs, _("Zigs"),
                                    [b for b in betes if b.zig])
        self._betes_carte.queue_draw()

    def _remplir_colonne_betes(self, boite, titre: str, betes: list) -> None:
        """Une colonne de bêtes, avec son titre. Vide, elle le dit."""
        entete = Gtk.Label(label=f"{titre} · {len(betes)}", xalign=0.0)
        entete.add_css_class("title-4")
        entete.add_css_class("peuple")
        entete.props.margin_bottom = 4
        boite.append(entete)
        for rang, bete in enumerate(betes):
            ligne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            if rang % 2 == 0:
                ligne.add_css_class("zebre")
            self._pad(ligne)
            nom = Gtk.Label(label=bete.nom or bete.etiquette, xalign=0.0)
            nom.add_css_class("heading")
            ligne.append(nom)
            detail = Gtk.Label(label=self._etat_bete(bete), xalign=0.0, wrap=True)
            detail.add_css_class("dim-label")
            ligne.append(detail)
            boite.append(ligne)
        if not betes:
            vide = Gtk.Label(label=_("aucune"), xalign=0.0)
            vide.add_css_class("dim-label")
            self._pad(vide)
            boite.append(vide)

    @staticmethod
    def _etat_bete(bete) -> str:
        """L'état d'une bête, en français.

        La satiété n'a pas d'échelle documentée — les valeurs relevées vont de
        54 à 933 — donc on la donne telle quelle plutôt que d'inventer un
        pourcentage qui serait faux."""
        lieux = {"landscape": _("dehors"), "stable": _("à l'écurie"),
                 "": _("état inconnu")}
        lieu = lieux.get(bete.statut, bete.statut)
        detail = f"{bete.etiquette} · {lieu}" if bete.nom else lieu
        if bete.satiete > 0:
            detail += _(" · satiété %d") % int(bete.satiete)
        return detail

    def _peindre_carte(self, cr, largeur: float, hauteur: float, zoom: float,
                       glissement: list):
        """Peint la carte d'Atys, agrandie et déplacée, et rend sa pose.

        Rend `(échelle, marge_x, marge_y)` — de quoi placer un point de la carte
        à l'écran — ou None si l'image manque. Partagé par l'écran des bêtes et
        par les cartes de gisements : c'est la même image, la même mise à
        l'échelle et le même découpage.
        """
        if self._betes_pixbuf is None:
            try:
                self._betes_pixbuf = GdkPixbuf.Pixbuf.new_from_file(carte.CHEMIN)
            except GLib.Error:
                return None
        pb = self._betes_pixbuf
        echelle = min(largeur / pb.get_width(),
                      hauteur / pb.get_height()) * zoom
        marge_x = (largeur - pb.get_width() * echelle) / 2 + glissement[0]
        marge_y = (hauteur - pb.get_height() * echelle) / 2 + glissement[1]
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        cr.translate(marge_x, marge_y)
        cr.scale(echelle, echelle)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.paint()
        cr.restore()
        return (echelle, marge_x, marge_y)

    def _marqueur(self, cr, x: float, y: float, texte: str, couleur) -> None:
        """Un point cerné et son nom, lisible sur n'importe quel fond.

        Le blanc cerné de noir sur ses huit côtés : l'or du thème se perd sur
        les zones sableuses, c'est la solution des cartes de toujours.
        """
        for rayon, teinte in ((6.5, self.CERNE), (4.0, couleur)):
            cr.set_source_rgb(*teinte)
            cr.arc(x, y, rayon, 0, 6.2832)
            cr.fill()
        if not texte:
            return
        cr.select_font_face("Sans")
        cr.set_font_size(13 * self._settings.zoom)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    cr.set_source_rgb(*self.CERNE)
                    cr.move_to(x + 10 + dx * 1.2, y - 6 + dy * 1.2)
                    cr.show_text(texte)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.move_to(x + 10, y - 6)
        cr.show_text(texte)

    def _dessiner_carte_betes(self, _area, cr, largeur, hauteur) -> None:
        """La carte d'Atys, et les bêtes qui y sont.

        Ce n'est pas une carte de navigation : elle sert à comprendre d'un coup
        d'œil dans quelle région une bête a été laissée."""
        ent = self._entity
        betes = [b for b in getattr(ent, "betes", [])
                 if b.dehors and carte.contient(b.x, b.y)] if ent else []
        # La carte s'affiche aussi quand seul le joueur est plaçable : savoir où
        # l'on est vaut d'être montré, même sans bête dehors.
        if ent is None or (not betes and not carte.contient(ent.x, ent.y)):
            return
        pose = self._peindre_carte(cr, largeur, hauteur, self._betes_zoom,
                                   self._betes_glissement)
        if pose is None:
            return
        echelle, marge_x, marge_y = pose

        # Le joueur d'abord, sous les bêtes : c'est un repère, pas ce qu'on
        # cherche. Sa position est celle de sa dernière déconnexion.
        p = carte.pixel(ent.x, ent.y) if (ent.x or ent.y) else None
        if p is not None:
            jx, jy = marge_x + p[0] * echelle, marge_y + p[1] * echelle
            if 0 <= jx <= largeur and 0 <= jy <= hauteur:
                for rayon, couleur in ((7.0, self.CERNE), (5.5, (1.0, 1.0, 1.0)),
                                       (3.0, self.POINT_JOUEUR)):
                    cr.set_source_rgb(*couleur)
                    cr.arc(jx, jy, rayon, 0, 6.2832)
                    cr.fill()
                cr.select_font_face("Sans")
                cr.set_font_size(13 * self._settings.zoom)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx or dy:
                            cr.set_source_rgb(*self.CERNE)
                            cr.move_to(jx + 11 + dx * 1.2, jy - 7 + dy * 1.2)
                            cr.show_text(ent.name)
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.move_to(jx + 11, jy - 7)
                cr.show_text(ent.name)

        # Les bêtes trop proches n'en font qu'une : quatre mektoubs attachés
        # ensemble tombent sur le même pixel, et quatre noms superposés ne se
        # lisent plus.
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        groupes: dict[tuple[int, int], list] = {}
        for b in betes:
            p = carte.pixel(b.x, b.y)
            if p is None:
                continue
            px, py = p
            cle = (int((marge_x + px * echelle) / self.SEUIL_GROUPE),
                   int((marge_y + py * echelle) / self.SEUIL_GROUPE))
            groupes.setdefault(cle, []).append(b)
        cr.select_font_face("Sans")
        cr.set_font_size(13 * self._settings.zoom)
        for groupe in groupes.values():
            px, py = carte.pixel(groupe[0].x, groupe[0].y)
            x, y = marge_x + px * echelle, marge_y + py * echelle
            # Une cible, pas un anneau : cerne noir, disque blanc, cœur rouge.
            # La carte passe du vert sombre des forêts au sable clair, au rouge
            # du désert et au violet des zones corrompues — aucune teinte unique
            # ne s'y détache partout, mais le contraste noir sur blanc, lui,
            # tient sur tout.
            for rayon, couleur in ((7.0, self.CERNE), (5.5, (1.0, 1.0, 1.0)),
                                   (3.0, self.POINT)):
                cr.set_source_rgb(*couleur)
                cr.arc(x, y, rayon, 0, 6.2832)
                cr.fill()
            nom = groupe[0].nom or groupe[0].etiquette
            if len(groupe) > 1:
                nom += f" +{len(groupe) - 1}"
            # Le nom en blanc, cerné de noir sur ses huit côtés : c'est la
            # solution des cartes de toujours, et la seule qui tienne ici. L'or
            # du thème se perdait sur le sable ; deux décalages en diagonale
            # laissaient le liseré manquant au-dessus et sur les côtés.
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        cr.set_source_rgb(*self.CERNE)
                        cr.move_to(x + 11 + dx * 1.2, y - 7 + dy * 1.2)
                        cr.show_text(nom)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.move_to(x + 11, y - 7)
            cr.show_text(nom)
        cr.restore()
