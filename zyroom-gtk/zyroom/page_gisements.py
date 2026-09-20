"""La carte des gisements d'une matière.

Dans l'écran Météo, cliquer une matière ouvre la carte de ses points connus,
cadrée automatiquement dessus, avec le nom de chaque lieu. Une matière qu'on
ne sait pas situer reste du texte ordinaire — rien n'invite à cliquer sur ce
qui ne répondrait pas.

Le code vient de `window.py`, déplacé sans une ligne de changement. Les
réglages que cette carte partage avec celle des bêtes — zoom, seuil de
regroupement, rouge du point — sont dans `page_cartes.py`.
"""
from __future__ import annotations

from gi.repository import GLib, Gtk

from . import carte, gisements
from .i18n import _


class PageGisements:
    """La carte qu'ouvre le nom d'une matière."""
    def _on_gisement(self, _label, adresse: str) -> bool:
        self._montre_gisement(*adresse.split("|", 2))
        return True         # sinon GTK tente d'ouvrir l'adresse dans un navigateur

    def _montre_gisement(self, qualite: str, famille: str, matiere: str) -> None:
        """Où sort cette matière : nos propres marqueurs sur la carte d'Atys.

        On embarquait les vues rendues par le tracker — trois mégaoctets
        d'images figées. Ballistic Mystix a donné les coordonnées : sept
        kilooctets, notre carte, et un zoom libre. Le nom du lieu est écrit
        aussi, parce qu'un point ne dit pas où aller.
        """
        points = gisements.points(qualite, famille, matiere)
        if not points:
            return
        win = Gtk.Window(title=f"{matiere} — {famille}", transient_for=self)
        win.set_default_size(720, 640)
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._pad(boite)

        mot = _("Suprême") if qualite == "supreme" else _("Excellente")
        fourchettes = gisements.humidites(qualite, famille, matiere)
        # Sans espace autour du tiret, et la virgule décimale du français : deux
        # fourchettes doivent tenir sur la ligne du titre.
        humidite = ", ".join(f"{bas:g}–{haut:g} %".replace(".", ",")
                             for bas, haut in fourchettes)
        entete = Gtk.Label(xalign=0.0, wrap=True)
        entete.set_markup(
            f"<b>{GLib.markup_escape_text(mot)}</b>"
            + (f"  ·  {_('humidité')} {GLib.markup_escape_text(humidite)}"
               if humidite else "")
            + f"  ·  {len(points)} "
            + (_("gisements") if len(points) > 1 else _("gisement")))
        boite.append(entete)

        # L'état du zoom vit sur la fenêtre : deux gisements ouverts en même
        # temps ne doivent pas se déplacer ensemble.
        etat = {"zoom": 1.0, "glissement": [0.0, 0.0], "depart": [0.0, 0.0]}
        zone = Gtk.DrawingArea(vexpand=True)
        zone.set_content_height(340)
        zone.set_draw_func(
            lambda _a, cr, l, h: self._dessiner_gisement(cr, l, h, points, etat))

        pincement = Gtk.GestureZoom()
        pincement.connect("scale-changed",
                          lambda g, e: self._gisement_zoom(zone, etat, e,
                                                           pincement=True))
        pincement.connect("end", lambda g, s: self._gisement_pince_fin(etat))
        zone.add_controller(pincement)
        molette = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL)
        molette.connect(
            "scroll",
            lambda c, dx, dy: self._gisement_zoom(
                zone, etat,
                1 / self.PAS_ZOOM if dy > 0 else self.PAS_ZOOM))
        zone.add_controller(molette)
        glisse = Gtk.GestureDrag()
        glisse.connect("drag-update",
                       lambda g, dx, dy: self._gisement_glisse(zone, etat, dx, dy))
        glisse.connect("drag-end",
                       lambda g, dx, dy: etat["depart"].__setitem__(
                           slice(None), list(etat["glissement"])))
        zone.add_controller(glisse)
        boite.append(zone)

        # Les lieux, sans leurs coordonnées : le jeu ne permet pas de taper une
        # position pour y poser un repère — je l'avais cru, Ludo l'a corrigé —
        # et deux nombres qu'on ne peut ni saisir ni recopier nulle part
        # n'apprennent rien. Le nom du lieu, lui, dit où aller.
        # Sur deux colonnes : les gisements vont jusqu'à cinq lieux, et une
        # colonne unique repoussait la ligne d'attribution hors de la fenêtre.
        lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
        grille = Gtk.Grid(column_spacing=24, row_spacing=2)
        grille.set_column_homogeneous(True)
        rangs = (len(lieux) + 1) // 2
        for rang, lieu in enumerate(lieux):
            ligne = Gtk.Label(xalign=0.0)
            ligne.add_css_class("compact")
            ligne.set_text(lieu)
            grille.attach(ligne, rang // rangs, rang % rangs, 1, 1)
        boite.append(grille)

        credit = Gtk.Label(xalign=0.0, wrap=True)
        credit.add_css_class("dim-label")
        credit.add_css_class("caption")
        credit.set_text(_("Positions : relevé de ballisticmystix.net, avec "
                          "l'accord de son auteur"))
        boite.append(credit)

        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_child(boite)
        win.set_child(scroll)
        win.present()

    def _gisement_zoom(self, zone, etat: dict, facteur: float,
                       pincement: bool = False) -> None:
        """Agrandit **autour du centre de la vue**, pas du centre de l'image.

        C'était le défaut : le déplacement restait tel quel pendant que l'image
        grandissait autour de son propre milieu, et la vue partait sur le côté.
        Le déplacement suit maintenant l'agrandissement — ce qui est au centre y
        reste, en agrandissant comme en rapetissant.

        Le pincement rend une échelle absolue depuis le début du geste : on la
        compose avec l'agrandissement qu'on avait alors, sinon le premier
        frémissement des doigts ramenait brutalement à l'échelle 1.
        """
        avant = etat["zoom"]
        if pincement:
            if etat.get("pince_depart") is None:
                etat["pince_depart"] = avant
            apres = etat["pince_depart"] * facteur
        else:
            apres = avant * facteur
        etat["zoom"] = min(self.ZOOM_MAX, max(1.0, apres))
        if etat["zoom"] == avant:
            return
        rapport = etat["zoom"] / avant
        etat["glissement"][0] *= rapport
        etat["glissement"][1] *= rapport
        self._borner_carte(zone, etat["zoom"], etat["glissement"])
        etat["depart"][:] = list(etat["glissement"])
        zone.queue_draw()

    def _gisement_pince_fin(self, etat: dict) -> None:
        """Le geste fini, le prochain repartira de l'agrandissement courant."""
        etat["pince_depart"] = None

    def _borner_carte(self, zone, zoom: float, glissement: list) -> None:
        """Empêche la carte de s'échapper de son cadre.

        Le débord se mesure sur l'image telle qu'elle est dessinée, et non sur
        la largeur du cadre : la carte y tient en boîte aux lettres, et un
        débord calculé sur le cadre laissait la pousser dans le vide.
        """
        if self._betes_pixbuf is None:
            return
        pb = self._betes_pixbuf
        largeur, hauteur = zone.get_width(), zone.get_height()
        if largeur <= 0 or hauteur <= 0:
            return
        echelle = min(largeur / pb.get_width(), hauteur / pb.get_height()) * zoom
        debord_x = max(0.0, (pb.get_width() * echelle - largeur) / 2)
        debord_y = max(0.0, (pb.get_height() * echelle - hauteur) / 2)
        glissement[0] = max(-debord_x, min(debord_x, glissement[0]))
        glissement[1] = max(-debord_y, min(debord_y, glissement[1]))


    def _gisement_glisse(self, zone, etat: dict, dx: float, dy: float) -> None:
        # Agrandie seulement : à l'échelle 1 la carte tient entière dans son
        # cadre, et la déplacer ne montrerait que du vide.
        if etat["zoom"] <= 1.0:
            return
        etat["glissement"][:] = [etat["depart"][0] + dx, etat["depart"][1] + dy]
        self._borner_carte(zone, etat["zoom"], etat["glissement"])
        zone.queue_draw()

    #: Part du cadre que les gisements doivent occuper au premier affichage.
    #:
    #: Les quatre zones des Primes tiennent dans un dixième de la carte du
    #: monde : sans cadrage, on voyait quatre points collés au milieu d'Atys et
    #: leurs noms se chevauchaient. On garde de la marge autour, pour situer la
    #: zone dans le continent plutôt que de la montrer hors contexte.
    CADRAGE_GISEMENT = 0.55

    def _cadre_gisement(self, largeur, hauteur, points, etat) -> None:
        """Cadre la vue sur les gisements, une fois, au premier dessin.

        On ne peut pas le faire à la construction : il faut connaître la taille
        du cadre, et elle n'existe qu'à la mesure."""
        etat["cadre"] = True
        pixels = [carte.pixel(x, y) for x, y, _l in points]
        pixels = [p for p in pixels if p is not None]
        if not pixels:
            return
        xs = [p[0] for p in pixels]
        ys = [p[1] for p in pixels]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        # Un seul gisement n'a pas d'étendue : on lui en donne une, sinon le
        # zoom partirait au maximum sur un point.
        large = max(max(xs) - min(xs), 300.0)
        haute = max(max(ys) - min(ys), 260.0)
        base = min(largeur / carte.LARGEUR, hauteur / carte.HAUTEUR)
        if base <= 0:
            return
        voulue = min(self.CADRAGE_GISEMENT * largeur / large,
                     self.CADRAGE_GISEMENT * hauteur / haute)
        etat["zoom"] = min(self.ZOOM_MAX, max(1.0, voulue / base))
        echelle = base * etat["zoom"]
        debord_x = max(0.0, (carte.LARGEUR * echelle - largeur) / 2)
        debord_y = max(0.0, (carte.HAUTEUR * echelle - hauteur) / 2)
        etat["glissement"][:] = [
            max(-debord_x, min(debord_x, echelle * (carte.LARGEUR / 2 - cx))),
            max(-debord_y, min(debord_y, echelle * (carte.HAUTEUR / 2 - cy))),
        ]
        etat["pince_depart"] = None
        etat["depart"][:] = list(etat["glissement"])

    def _dessiner_gisement(self, cr, largeur, hauteur, points, etat) -> None:
        """La carte d'Atys, et les gisements d'une matière."""
        if not etat.get("cadre"):
            self._cadre_gisement(largeur, hauteur, points, etat)
        pose = self._peindre_carte(cr, largeur, hauteur, etat["zoom"],
                                   etat["glissement"])
        if pose is None:
            return
        echelle, marge_x, marge_y = pose
        cr.save()
        cr.rectangle(0, 0, largeur, hauteur)
        cr.clip()
        # Les points trop proches n'en font qu'un : deux gisements d'une même
        # zone tombent sur le même pixel à l'échelle 1, et deux noms superposés
        # ne se lisent plus.
        vus = {}
        for x, y, lieu in points:
            p = carte.pixel(x, y)
            if p is None:
                continue
            px, py = marge_x + p[0] * echelle, marge_y + p[1] * echelle
            cle = (int(px / self.SEUIL_GROUPE), int(py / self.SEUIL_GROUPE))
            vus.setdefault(cle, (px, py, lieu, 0))
            ex, ey, elieu, n = vus[cle]
            vus[cle] = (ex, ey, elieu, n + 1)
        for px, py, lieu, n in vus.values():
            if not (-40 <= px <= largeur + 40 and -40 <= py <= hauteur + 40):
                continue
            self._marqueur(cr, px, py, lieu if n == 1 else f"{lieu} ×{n}",
                           self.POINT)
        cr.restore()
