"""La carte des gisements d'une matière.

Dans l'écran Météo, cliquer une matière ouvre la carte de ses points connus,
cadrée automatiquement dessus, avec le nom de chaque lieu. Une matière qu'on
ne sait pas situer reste du texte ordinaire — rien n'invite à cliquer sur ce
qui ne répondrait pas.

**Les quatre points ne se valent pas au même instant.** Une suprême sort dans
une zone des Primes et pas dans la voisine, selon le temps qu'il y fait : la
carte montrait les quatre du même rouge, et il fallait retourner au tableau
pour savoir auquel aller. Les gisements qui sortent en ce moment sont **verts**,
les autres gris — gris et non retirés, parce que « ici, mais pas maintenant »
est une réponse, et qu'une carte amputée n'en donne aucune.

**Et elle suit le temps.** Un cycle météo dure neuf minutes réelles : une carte
laissée ouverte mentait dès la bascule suivante. Elle se recalcule au battement
de l'écran météo, toutes les dix secondes — couleurs, décompte et phrases —
sans rien redemander à l'API.

Le code vient de `window.py`, déplacé sans une ligne de changement. Les
réglages que cette carte partage avec celle des bêtes — zoom, seuil de
regroupement, rouge du point — sont dans `page_cartes.py`.
"""
from __future__ import annotations

from gi.repository import GLib, Gtk

from . import carte, gisements, meteo
from .i18n import _

#: La qualité des gisements telle que la table de forage la nomme.
_QUALITE = {"supreme": meteo.SUPREME, "excellent": meteo.EXCELLENTE}


class PageGisements:
    """La carte qu'ouvre le nom d'une matière."""

    def _gisements_actifs(self, qualite: str, famille: str, matiere: str,
                          lieux: list):
        """Les lieux où cette matière sort en ce moment, et la météo du moment.

        Rend `(None, None)` quand on ne peut pas trancher — pas de relevé
        météo, ou des gisements hors des Primes, les seules zones dont la table
        de forage parle. Mieux vaut tout laisser en rouge que griser au hasard.
        """
        releve = self._meteo_affiche or self._meteo_releve
        actuelle = releve.maintenant() if releve is not None else None
        connus = [lieu for lieu in lieux if lieu in meteo.ZONES]
        if actuelle is None or not connus:
            return None, None
        attendue = _QUALITE.get(qualite)
        actifs = {lieu for lieu in lieux
                  if lieu not in meteo.ZONES
                  or meteo.qualite_de(lieu, famille, matiere,
                                      releve.saison, actuelle.condition)
                  == attendue}
        return actifs, actuelle

    def _prochaine_sortie(self, qualite: str, famille: str, matiere: str,
                          lieux: list):
        """Le premier cycle à venir où cette matière sortira quelque part.

        Chaque matière a son propre seuil : Zun suprême sort dès cinquante pour
        cent d'humidité, là où la grande fenêtre du suprême en demande
        quatre-vingt-trois. Dire « ça ne sort pas » sans dire quand, c'était
        obliger à retourner lire la courbe et à poser l'addition.

        On interroge la même table que pour le rouge et le gris, cycle par
        cycle : une carte qui annoncerait une sortie que le tableau ne montre
        pas serait pire que le silence.
        """
        releve = self._meteo_affiche or self._meteo_releve
        if releve is None:
            return None
        attendue = _QUALITE.get(qualite)
        zones = [lieu for lieu in lieux if lieu in meteo.ZONES]
        for cycle in releve.cycles_des_primes():
            if cycle.cycle <= releve.cycle_courant:
                continue
            if any(meteo.qualite_de(lieu, famille, matiere, releve.saison,
                                    cycle.condition) == attendue
                   for lieu in zones):
                return releve.minutes_avant(cycle.cycle)
        return None

    def _textes_carte(self, qualite: str, famille: str, matiere: str,
                      lieux: list):
        """Les lieux qui sortent, et les deux phrases qui l'expliquent.

        Un seul endroit pour les deux : l'ouverture de la fenêtre et le
        battement qui la rafraîchit doivent dire mot pour mot la même chose,
        sans quoi l'une des deux dériverait sans qu'on s'en aperçoive.
        """
        actifs, actuelle = self._gisements_actifs(qualite, famille, matiere,
                                                  lieux)
        if actifs is None:
            return None, "", ""
        dehors = [lieu for lieu in lieux if lieu not in actifs]
        sortent = len(lieux) - len(dehors)
        maintenant = (
            (_("En ce moment — %(condition)s, %(taux)d %% : aucun des "
               "%(total)d gisements ne sort.") if not sortent
             else _("En ce moment — %(condition)s, %(taux)d %% : "
                    "un gisement sur %(total)d.") if sortent == 1
             else _("En ce moment — %(condition)s, %(taux)d %% : "
                    "%(sortent)d gisements sur %(total)d."))
            % {"condition": meteo.texte_condition(actuelle.condition),
               "taux": round(actuelle.value * 100),
               "sortent": sortent, "total": len(lieux)}
            + (_("  Les autres sont en gris.") if dehors and sortent else ""))
        apres = ""
        if not sortent:
            minutes = self._prochaine_sortie(qualite, famille, matiere, lieux)
            apres = (_("Prochaine fois dans %(delai)s — %(quand)s.")
                     % {"delai": meteo.duree(minutes),
                        "quand": meteo.moment_du_changement(minutes)}
                     if minutes is not None
                     else _("Pas avant six heures — au-delà, le jeu ne dit "
                            "plus le temps qu'il fera."))
        return actifs, maintenant, apres

    def _rafraichir_cartes_gisements(self) -> None:
        """Remet les cartes ouvertes à l'heure, au battement de l'écran météo.

        Un cycle dure neuf minutes réelles : une carte laissée ouverte mentait
        dès la bascule suivante, et elle mentait en silence — rien ne distingue
        un point vert juste qu'un point vert périmé. Rien n'est redemandé à
        l'API : l'écran météo fait déjà avancer son relevé tout seul.
        """
        for ouverte in list(getattr(self, "_cartes_gisements", [])):
            actifs, maintenant, apres = self._textes_carte(
                ouverte["qualite"], ouverte["famille"], ouverte["matiere"],
                ouverte["lieux"])
            ouverte["etat"]["actifs"] = actifs
            for label, texte in ((ouverte["maintenant"], maintenant),
                                 (ouverte["apres"], apres)):
                label.set_text(texte)
                label.set_visible(bool(texte))
            for lieu, label in ouverte["noms"].items():
                if actifs is not None and lieu not in actifs:
                    label.add_css_class("dim-label")
                else:
                    label.remove_css_class("dim-label")
            ouverte["zone"].queue_draw()

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
        # Les positions des Primes, et elles seules : le releve place ses
        # excellentes sur les continents, et la carte s'ouvrait sur la Porte
        # des Vents pour une XL des Sources Interdites.
        points = meteo.positions_des_primes(_QUALITE.get(qualite), famille,
                                            matiere)
        if not points:
            return
        # Les lieux d'abord : l'en-tête en parle, et le tracé les colore.
        lieux = list(dict.fromkeys(lieu for _x, _y, lieu in points))
        actifs, texte_maintenant, texte_apres = self._textes_carte(
            qualite, famille, matiere, lieux)
        win = Gtk.Window(title=f"{matiere} — {famille}", transient_for=self)
        # Quarante points de plus qu'avant : la ligne « en ce moment » s'ajoute
        # sous l'en-tete, et elle se replie sur deux lignes quand rien ne sort.
        win.set_default_size(720, 680)
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

        # Ce que le vert et le gris veulent dire, écrit une fois : un code de
        # couleur qu'il faut deviner ne vaut pas mieux que pas de code du tout.
        # Les deux étiquettes existent toujours, même vides : le battement les
        # remplit et les vide, et une étiquette créée à la volée obligerait à
        # reconstruire la fenêtre pour rien.
        etiquettes = []
        for texte in (texte_maintenant, texte_apres):
            label = Gtk.Label(xalign=0.0, wrap=True)
            label.add_css_class("caption")
            label.set_text(texte)
            label.set_visible(bool(texte))
            boite.append(label)
            etiquettes.append(label)

        # L'état du zoom vit sur la fenêtre : deux gisements ouverts en même
        # temps ne doivent pas se déplacer ensemble.
        etat = {"zoom": 1.0, "glissement": [0.0, 0.0], "depart": [0.0, 0.0],
                "actifs": actifs}
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
        grille = Gtk.Grid(column_spacing=24, row_spacing=2)
        grille.set_column_homogeneous(True)
        rangs = (len(lieux) + 1) // 2
        noms = {}
        for rang, lieu in enumerate(lieux):
            ligne = Gtk.Label(xalign=0.0)
            ligne.add_css_class("compact")
            noms[lieu] = ligne
            # Le nom suit le point : terni quand le gisement ne sort pas, pour
            # qu'on puisse lire la reponse dans la liste sans viser un pixel.
            if actifs is not None and lieu not in actifs:
                ligne.add_css_class("dim-label")
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

        # La fenetre s'inscrit au battement de l'ecran meteo, et s'en retire
        # en se fermant : une carte fermee qu'on continuerait de redessiner
        # leverait une erreur GTK a la premiere bascule de cycle.
        ouverte = {"qualite": qualite, "famille": famille, "matiere": matiere,
                   "lieux": lieux, "etat": etat, "zone": zone,
                   "maintenant": etiquettes[0], "apres": etiquettes[1],
                   "noms": noms}
        if not hasattr(self, "_cartes_gisements"):
            self._cartes_gisements = []
        self._cartes_gisements.append(ouverte)
        win.connect("close-request",
                    lambda *_a: (self._cartes_gisements.remove(ouverte),
                                 False)[1])
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
        actifs = etat.get("actifs")
        # Les gris d'abord, les verts par-dessus : deux gisements voisins se
        # recouvrent parfois d'un pixel, et c'est celui qui sort qu'on veut voir.
        for vert in (False, True):
            for px, py, lieu, n in vus.values():
                if not (-40 <= px <= largeur + 40
                        and -40 <= py <= hauteur + 40):
                    continue
                sort = actifs is None or lieu in actifs
                if sort != vert:
                    continue
                self._marqueur(cr, px, py, lieu if n == 1 else f"{lieu} ×{n}",
                               self.POINT_ACTIF if sort
                               else self.POINT_INACTIF)
        cr.restore()
