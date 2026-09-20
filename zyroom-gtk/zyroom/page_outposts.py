"""L'écran « Avant-postes » : qui tient quoi sur Atys.

Les avant-postes par peuple, avec les emblèmes de guilde, et le journal des
prises. L'annuaire public des guildes ne demande aucune clé mais pèse un
demi-méga-octet : il n'est donc demandé qu'à l'ouverture de l'onglet, et
rafraîchi à la main.

Le code vient de `window.py`, déplacé sans une ligne de changement.
"""
from __future__ import annotations

from datetime import datetime
from math import cos, radians, sin

from gi.repository import GLib, Gtk, Pango

from . import outposts, ryzom_api
from .config import noter_erreur
from .i18n import _
from .ryzom_api import KIND_GUILD
from .ui_commun import run_async


class PageOutposts:
    """Les avant-postes d'Atys, leur carte par peuple et leurs prises."""
    # ------------------------------------------------------- Avant-postes
    #
    # Qui tient quoi sur Atys, et le journal des prises. L'annuaire public des
    # guildes ne demande aucune clé, mais pèse un demi-méga-octet : il n'est
    # donc demandé qu'à l'ouverture de l'onglet, et rafraîchi à la main.

    #: Les quatre peuples, dans l'ordre de la carte.
    PEUPLES = (("fyros", "Fyros"), ("matis", "Matis"),
               ("tryker", "Tryker"), ("zorai", "Zoraï"))

    #: La part de la taille des icones d'inventaire qu'occupe un embleme de
    #: guilde, au debut d'une ligne d'avant-poste.
    #:
    #: **Une part, et non vingt pixels en dur.** Le zoom est le seul reglage
    #: d'apparence qui reste, et il doit grossir la page entiere -- texte et
    #: images ensemble. Fige a vingt, l'embleme restait seul a sa taille
    #: pendant que ses trois colonnes doublaient : a deux cents pour cent, une
    #: vignette qu'on devinait plus qu'on ne la reconnaissait. Zero virgule
    #: quarante-deux rend bien vingt a cent pour cent, la valeur d'avant.
    PART_EMBLEME = 0.42

    #: La part des icones d'inventaire qu'occupe la pastille de changement.
    #:
    #: La meme que l'embleme, et non la moitie : a dix pixels, les deux
    #: fleches se confondaient en un anneau et le symbole ne disait plus rien.
    #: Elle suit le zoom comme lui, pour que la ligne grossisse d'un bloc.
    PART_PASTILLE = 0.42

    #: Le symbole de la pastille -- deux fleches qui tournent -- **dessine et
    #: non ecrit**.
    #:
    #: Le caractere du recyclage existe (U+267B), mais aucune police
    #: d'interface ne le porte : ni Cantarell sous GNOME, ni Segoe UI sous
    #: Windows. Le repli tombe sur Noto Color Emoji, qui l'impose en couleur
    #: -- un vert qui n'est pas le notre, a cote d'un nom qui l'est. Dessine,
    #: le symbole a la couleur qu'on lui donne, la meme taille partout, et le
    #: meme trace dans les deux portages : `page_outposts.py` repete ces
    #: memes valeurs pour QPainter.
    #:
    #: Les deux arcs, en degres, dans le sens des aiguilles a l'ecran.
    #: Rayon et epaisseur sont tenus par une contrainte : la pointe va
    #: jusqu'a `rayon + trait * barbe`, et ce total doit rester sous la
    #: moitie du cote, sinon la zone de dessin rogne les barbes.
    PASTILLE_ARCS = ((25, 155), (205, 335))
    PASTILLE_RAYON = 0.31       #: du cote de la pastille
    PASTILLE_TRAIT = 0.15       #: epaisseur, du cote aussi
    PASTILLE_BARBE = 1.20       #: demi-hauteur de la barbe, en parts du trait
    PASTILLE_POINTE = 28        #: les degres que la pointe parcourt en plus

    def _build_outposts_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._op_vue = Gtk.DropDown.new_from_strings(
            [_("Qui tient quoi"), _("Journal des prises")])
        self._op_vue.connect("notify::selected", lambda *a: self._refresh_outposts())
        bar.append(self._op_vue)

        self._op_refresh = Gtk.Button(label=_("Actualiser"))
        self._op_refresh.set_tooltip_text(_("Redemander l'annuaire des guildes"))
        self._op_refresh.connect("clicked", lambda *a: self._load_outposts(force=True))
        bar.append(self._op_refresh)

        self._op_status = Gtk.Label(xalign=0.0)
        self._op_status.add_css_class("dim-label")
        self._op_status.set_hexpand(True)
        bar.append(self._op_status)

        # Deux colonnes : Fyros et Matis à gauche, Tryker et Zoraï à droite.
        # Les vingt-neuf avant-postes tenaient sur une colonne plus haute que
        # l'écran, et il fallait faire défiler pour comparer deux peuples.
        # Chacune défile pour son compte, les quatre listes n'ayant pas la même
        # longueur.
        colonnes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                           homogeneous=True)
        self._op_gauche = Gtk.ListBox()
        self._op_gauche.add_css_class("survol")
        self._op_droite = Gtk.ListBox()
        self._op_droite.add_css_class("survol")
        for colonne in (self._op_gauche, self._op_droite):
            colonne.set_selection_mode(Gtk.SelectionMode.NONE)
            defilement = Gtk.ScrolledWindow()
            defilement.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            defilement.set_vexpand(True)
            defilement.set_child(colonne)
            colonnes.append(defilement)
        # Le journal, lui, se lit sur toute la largeur : ses lignes sont des
        # phrases, pas un tableau.
        self._op_box = Gtk.ListBox()
        self._op_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._op_box.add_css_class("survol")
        journal = Gtk.ScrolledWindow()
        journal.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        journal.set_vexpand(True)
        journal.set_child(self._op_box)

        self._op_pile = Gtk.Stack()
        self._op_pile.set_transition_type(Gtk.StackTransitionType.NONE)
        self._op_pile.add_named(colonnes, "carte")
        self._op_pile.add_named(journal, "journal")
        self._op_pile.set_vexpand(True)
        page.append(self._op_pile)

        self._op_carte: list = []
        self._op_changements: list = []
        #: Nom de guilde -> identifiant d'embleme, pour le journal des prises.
        self._op_emblemes: dict = {}
        self._op_premier = False
        self._op_charge = False
        return page

    def _load_outposts(self, force: bool = False) -> None:
        """Va chercher l'annuaire, journalise les changements de main."""
        if self._op_charge and not force:
            # L'annuaire est deja en memoire : rien a redemander au reseau.
            # Mais l'entete et le surlignage vert disent « et nous ? », et le
            # « nous » a pu changer depuis -- sans ce rafraichissement,
            # l'affichage restait sur la guilde precedente.
            if self._op_carte:
                self._refresh_outposts()
            return
        self._op_charge = True
        self._op_refresh.set_sensitive(False)
        self._op_status.set_text(_("Lecture de l'annuaire des guildes…"))

        def work():
            xml = ryzom_api.fetch_guild_directory_xml()
            carte, emblemes = outposts.parse_annuaire(xml)
            premier = self._op_store.jamais_releve()
            self._op_store.record(carte)
            return carte, emblemes, self._op_store.history(), premier

        def done(res, err):
            self._op_refresh.set_sensitive(True)
            if err:
                self._op_status.set_text(_("Annuaire indisponible : %s") % err)
                return
            (self._op_carte, self._op_emblemes,
             self._op_changements, self._op_premier) = res
            self._op_status.set_text("")
            self._refresh_outposts()

        run_async(work, done)

    def _ma_guilde(self) -> str:
        """Le nom de la guilde qu'on regarde — la sienne, ou celle du perso."""
        ent = self._entity
        if ent is None:
            return ""
        return (ent.name if ent.kind == KIND_GUILD else ent.guild) or ""

    def _maj_compteur_prises(self) -> None:
        """Le nombre de prises qui nous concernent, sur l'entrée du journal.

        **Un nombre dans la liste déroulante, et pas une colonne de plus.** Le
        journal des prises existait déjà et ne se voyait pas : il fallait
        penser à l'ouvrir. Le compte s'efface dès qu'on l'a lu — c'est un
        rappel, pas un décompte.
        """
        modele = self._op_vue.get_model()
        if modele is None:
            return
        n = self._op_store.non_lus(self._ma_guilde())
        titre = _("Journal des prises")
        if n:
            titre += f" ({n})"
        if modele.get_string(1) != titre:
            modele.splice(1, 1, [titre])

    def _refresh_outposts(self) -> None:
        for boite in (self._op_gauche, self._op_droite, self._op_box):
            while (child := boite.get_first_child()) is not None:
                boite.remove(child)
        # Avant le retour anticipé : le compte se lit dans le journal, qui
        # existe même quand la carte n'est pas encore chargée.
        self._maj_compteur_prises()
        if not self._op_carte:
            return
        if self._op_vue.get_selected() == 1:
            self._op_pile.set_visible_child_name("journal")
            self._remplir_journal_outposts()
            # Lu : le compte tombe à zéro, et l'entrée reprend son nom nu.
            self._op_store.marquer_lu()
        else:
            self._op_pile.set_visible_child_name("carte")
            self._remplir_carte_outposts()
        self._maj_compteur_prises()   # après lecture : le compte est retombé

    def _remplir_carte_outposts(self) -> None:
        carte = self._op_carte
        # Sur une guilde, c'est son nom ; sur un personnage, celui de sa guilde.
        # Sans cela, ouvrir la carte depuis son personnage ne mettait rien en
        # vert, alors que c'est justement là qu'on se demande « et nous ? ».
        ma_guilde = self._ma_guilde()
        # Ce qui a change de main depuis le dernier coup d'oeil au journal.
        # Lu ici et non au chargement : la carte se redessine aussi quand on
        # revient du journal, et le marqueur de lecture vient d'etre pose --
        # les pastilles doivent alors avoir disparu.
        recents = self._op_store.recents()
        miens = sum(1 for o in carte if o.guild == ma_guilde)
        entete = _("%d avant-postes tenus sur Atys") % len(carte)
        # Des qu'on sait de quelle guilde on parle, on le dit -- meme quand la
        # reponse est zero. Taire le compte nul laissait croire a un affichage
        # reste en arriere : « et nous ? » merite un « aucun » explicite.
        if ma_guilde:
            entete += _(", dont %d à %s") % (miens, ma_guilde)
        self._op_status.set_text(entete + ".")

        connus = {c for c, _n in self.PEUPLES}
        # Deux peuples par colonne, dans l'ordre de la carte.
        for colonne, peuples in ((self._op_gauche, self.PEUPLES[:2]),
                                 (self._op_droite, self.PEUPLES[2:])):
            # Un jeu de groupes de taille par colonne : ils imposent à tous
            # leurs membres la largeur du plus large, ce qui aligne les trois
            # colonnes d'une ligne à l'autre. Un jeu par côté, et non un seul :
            # les deux colonnes n'ont pas les mêmes noms, et leur imposer une
            # largeur commune gâcherait la place de l'une.
            groupes = tuple(Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
                            for _ in range(3))
            rang = 0
            for code, nom in peuples:
                # Du plus haut niveau au plus bas, comme on lit une carte de
                # conquête : les enjeux d'abord.
                siens = sorted((o for o in carte if o.people == code),
                               key=lambda o: (-o.level, self._names.name(o.name_key)))
                if not siens:
                    continue
                colonne.append(self._entete_peuple(nom))
                for avant_poste in siens:
                    # **Une ligne qui casse ne doit pas emporter l'écran.**
                    # Un joueur s'est retrouvé devant un titre de peuple et du
                    # vide : la construction s'arrêtait à la première ligne
                    # fautive, et l'exception partait sur une sortie qu'un
                    # paquet lancé depuis le bureau n'affiche jamais. On note
                    # ce qui a cassé, on montre que la ligne manque, et l'on
                    # continue — vingt-huit avant-postes lisibles valent mieux
                    # qu'un écran blanc.
                    try:
                        rangee = self._ligne_outpost(
                            avant_poste, avant_poste.guild == ma_guilde,
                            rang % 2 == 0, groupes,
                            recents.get(avant_poste.code), bool(recents))
                    except Exception as souci:           # noqa: BLE001
                        noter_erreur(
                            f"avant-poste {getattr(avant_poste, 'code', '?')}",
                            souci)
                        rangee = self._ligne_simple(
                            _("(ligne illisible — voir erreurs.log)"), True)
                    colonne.append(rangee)
                    rang += 1
        orphelins = [o for o in carte if o.people not in connus]
        if orphelins:
            # L'annuaire contient parfois un code qui n'est pas un avant-poste
            # — « #15 ». Le taire ferait un total qui ne tombe pas juste.
            self._op_droite.append(self._ligne_simple(
                _("Hors carte : ") + ", ".join(f"{o.code} ({o.guild})"
                                               for o in orphelins), dim=True))

    def _remplir_journal_outposts(self) -> None:
        if self._op_premier and not self._op_changements:
            self._op_box.append(self._ligne_simple(
                _("Premier relevé : rien à comparer. Les changements de main "
                  "apparaîtront à partir du prochain."), dim=True))
            return
        if not self._op_changements:
            self._op_box.append(self._ligne_simple(
                _("Aucun changement de main depuis le premier relevé."), dim=True))
            return
        for rang, c in enumerate(self._op_changements):
            quand = datetime.fromtimestamp(c.at).strftime("%d/%m %H:%M")
            nom = self._names.name(f"{c.outpost}.outpost")
            self._op_box.append(
                self._ligne_prise(quand, nom, c, zebre=rang % 2 == 0))

    #: Les couleurs du journal des prises, celles du registre de l'effectif :
    #: ce qui arrive est vert, ce qui part est rouge, et l'or nomme la guilde
    #: qui a perdu. Ecrites ici et non en CSS : une ligne porte trois couleurs,
    #: et une classe ne s'applique qu'a l'etiquette entiere.
    PRISE_VERT = "#4caf50"
    PRISE_ROUGE = "#e2696a"
    PRISE_OR = "#e8c15a"

    def _fleche_prise(self, gagne: bool) -> str:
        """La flèche du sens : verte qui monte, rouge qui descend."""
        couleur = self.PRISE_VERT if gagne else self.PRISE_ROUGE
        return f'<span foreground="{couleur}">{"▲" if gagne else "▼"}</span>'

    def _nom_guilde(self, guilde: str, gagne: bool) -> str:
        """Le nom d'une guilde, vert si elle gagne, or si elle perd."""
        couleur = self.PRISE_VERT if gagne else self.PRISE_OR
        return (f'<span foreground="{couleur}">'
                f'{GLib.markup_escape_text(guilde)}</span>')

    def _ligne_prise(self, quand: str, nom: str, change,
                     zebre: bool = False) -> Gtk.ListBoxRow:
        """Une ligne du journal : la date, l'avant-poste, et qui l'a pris.

        **Une boîte et non une seule étiquette.** Le markup Pango ne sait pas
        porter d'image, et l'emblème d'une guilde est justement ce qui la fait
        reconnaître d'un coup d'œil dans une colonne de noms qui se
        ressemblent. La ligne se compose donc : le texte de gauche, puis pour
        chaque guilde son emblème et son nom.

        L'emblème se cherche par le nom, seule chose que le journal retienne
        d'une guilde. Une guilde absente de l'annuaire du jour — dissoute
        depuis — n'en a plus : sa ligne se lit alors comme avant.
        """
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        gauche = Gtk.Label(
            label=f"{quand}   {nom}   —", xalign=0.0)
        line.append(gauche)

        for guilde, gagne in ((change.frm, False), (change.to, True)):
            if not guilde:
                continue
            # La fleche d'abord : elle dit le sens de l'echange, et c'est
            # a ce titre qu'elle ouvre le groupe. L'embleme vient ensuite,
            # colle au nom qu'il illustre.
            fleche = Gtk.Label(xalign=0.0)
            fleche.set_markup(self._fleche_prise(gagne))
            line.append(fleche)

            # La place est reservee meme quand l'annuaire ne connait plus la
            # guilde : sans elle, une ligne sans embleme serait plus basse que
            # ses voisines, et le journal monterait et descendrait en
            # defilant.
            image = Gtk.Image()
            image.set_pixel_size(self._settings.icone(self.PART_EMBLEME))
            line.append(image)
            embleme = self._op_emblemes.get(guilde, "")
            if embleme:
                self._icons.request_emblem(
                    embleme,
                    lambda chemin, img=image: (img.set_from_file(chemin)
                                               if chemin else None))

            etiquette = Gtk.Label(xalign=0.0)
            etiquette.set_markup(self._nom_guilde(guilde, gagne))
            line.append(etiquette)

        self._pad(line)
        row.set_child(line)
        return row

    def _entete_peuple(self, nom: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        label = Gtk.Label(label=nom, xalign=0.0)
        label.add_css_class("title-4")
        label.add_css_class("peuple")
        label.props.margin_top = 10
        label.props.margin_bottom = 2
        # Aligné sur le bloc des lignes, qui est centré : un titre resté contre
        # le bord gauche n'aurait plus rien coiffé.
        label.set_halign(Gtk.Align.CENTER)
        label.set_size_request(456, -1)
        row.set_child(label)
        return row

    def _pastille_changement(self, change) -> Gtk.Widget:
        """Les deux flèches qui tournent, sur une ligne qui a changé de main.

        Toujours construite, même quand rien n'a changé : sans place réservée,
        la colonne du nom sauterait de quelques pixels d'une ligne à l'autre
        selon qu'elle porte une pastille ou non. Vide, la zone ne peint rien et
        ne fait que tenir sa largeur.
        """
        cote = self._settings.icone(self.PART_PASTILLE)
        zone = Gtk.DrawingArea()
        zone.set_content_width(cote)
        zone.set_content_height(cote)
        zone.set_valign(Gtk.Align.CENTER)
        if change is None:
            return zone
        zone.set_draw_func(self._dessiner_pastille)
        zone.set_tooltip_text(self._infobulle_changement(change))
        return zone

    def _dessiner_pastille(self, _zone, cr, largeur, hauteur) -> None:
        """Deux arcs opposés, chacun terminé par une pointe qui suit le cercle.

        La barbe de la pointe est **radiale** et sa pointe **tangente** : c'est
        ce qui fait lire une flèche qui tourne plutôt qu'un trait posé en
        travers. Le tracé est celui de `page_outposts.py`, au degré près.
        """
        cote = min(largeur, hauteur)
        cx, cy = largeur / 2.0, hauteur / 2.0
        rayon = cote * self.PASTILLE_RAYON
        trait = cote * self.PASTILLE_TRAIT
        barbe = trait * self.PASTILLE_BARBE
        # Le vert du survol des boutons : `accent_color`, deja dans la palette.
        cr.set_source_rgb(0x7f / 255, 0xb3 / 255, 0xa2 / 255)
        cr.set_line_width(trait)
        cr.set_line_cap(1)                    # cairo.LINE_CAP_ROUND
        for depart, fin in self.PASTILLE_ARCS:
            cr.new_sub_path()
            cr.arc(cx, cy, rayon, radians(depart), radians(fin))
            cr.stroke()
            # La pointe : deux points sur le rayon de la fin de l'arc, et un
            # troisieme un peu plus loin sur le cercle.
            a, b = radians(fin), radians(fin + self.PASTILLE_POINTE)
            cr.move_to(cx + (rayon + barbe) * cos(a),
                       cy + (rayon + barbe) * sin(a))
            cr.line_to(cx + (rayon - barbe) * cos(a),
                       cy + (rayon - barbe) * sin(a))
            cr.line_to(cx + rayon * cos(b), cy + rayon * sin(b))
            cr.close_path()
            cr.fill()

    def _infobulle_changement(self, change) -> str:
        """Ce que la pastille raconte quand on s'arrête dessus.

        Sans le nom de l'avant-poste : il est écrit juste à côté, sur la ligne
        que la pastille marque.
        """
        quand = datetime.fromtimestamp(change.at).strftime("%d/%m %H:%M")
        if change.taken:
            return _("Pris par %s (%s)") % (change.to, quand)
        if change.lost:
            return _("Perdu par %s (%s)") % (change.frm, quand)
        return _("%s ▸ %s (%s)") % (change.frm, change.to, quand)

    def _ligne_outpost(self, avant_poste, mien: bool, zebre: bool,
                       groupes, change=None,
                       pastilles: bool = False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        # Les trois colonnes forment un bloc centré, à largeur fixe. Le nom
        # tenait auparavant toute la largeur disponible, ce qui repoussait le
        # niveau et la guilde contre le bord droit : sur un écran large, l'œil
        # devait traverser vingt centimètres de vide pour relier un
        # avant-poste à son propriétaire.
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        line.set_halign(Gtk.Align.CENTER)
        line.props.margin_top = 3
        line.props.margin_bottom = 3

        # L'emblème de la guilde, chargé en tâche de fond et mis en cache.
        image = Gtk.Image()
        image.set_pixel_size(self._settings.icone(self.PART_EMBLEME))
        self._icons.request_emblem(
            avant_poste.icon,
            lambda chemin, img=image: img.set_from_file(chemin) if chemin else None)
        line.append(image)

        # Apres l'embleme et non en bout de ligne : ce qui a change, c'est le
        # proprietaire, et c'est son embleme qu'on vient de voir changer.
        #
        # La colonne n'existe que les jours ou quelque chose a bouge : le reste
        # du temps, reserver sa place volerait trente pixels a la colonne des
        # noms pour ne rien y mettre.
        if pastilles:
            line.append(self._pastille_changement(change))

        # `set_size_request` ne fixe qu'un **minimum** : un nom long débordait et
        # poussait le niveau et la guilde plus loin, si bien qu'aucune colonne
        # n'était alignée d'une ligne à l'autre. Les groupes de taille, eux,
        # imposent à tous leurs membres la largeur du plus large — c'est
        # exactement ce qu'on veut d'une colonne.
        # Pas de largeur maximale : le groupe prend la largeur du nom le plus
        # long, et tous s'affichent en entier tant que la fenêtre le permet.
        # L'abrègement ne sert plus que de secours, quand on la rétrécit.
        nom = Gtk.Label(label=self._names.name(avant_poste.name_key), xalign=0.0)
        nom.set_ellipsize(Pango.EllipsizeMode.END)
        nom.add_css_class("compact")
        if mien:
            nom.add_css_class("fini")     # le vert de l'application
        groupes[0].add_widget(nom)
        line.append(nom)

        niveau = Gtk.Label(label=str(avant_poste.level) if avant_poste.level else "—",
                           xalign=1.0)
        niveau.add_css_class("dim-label")
        niveau.add_css_class("compact")
        groupes[1].add_widget(niveau)
        line.append(niveau)

        guilde = Gtk.Label(label=avant_poste.guild, xalign=0.0)
        guilde.set_ellipsize(Pango.EllipsizeMode.END)
        guilde.set_max_width_chars(24)
        guilde.add_css_class("compact")
        if mien:
            guilde.add_css_class("fini")
        groupes[2].add_widget(guilde)
        line.append(guilde)

        row.set_child(line)
        return row

    def _ligne_simple(self, texte: str, dim: bool = False,
                      zebre: bool = False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        if zebre:
            row.add_css_class("zebre")
        label = Gtk.Label(xalign=0.0, wrap=True)
        # Du texte nu, jamais de markup : le seul qui en demandait etait le
        # journal des prises, et il compose desormais sa ligne lui-meme --
        # voir `_ligne_prise`.
        label.set_text(texte)
        if dim:
            label.add_css_class("dim-label")
        self._pad(label)
        row.set_child(label)
        return row
