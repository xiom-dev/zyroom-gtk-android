"""L'écran « Météo » : la courbe de l'humidité, et ce qu'elle fait sortir.

Deux sources : l'API officielle pour le temps — calculé par le jeu, donc connu
quarante cycles à l'avance — et un relevé de Ryzom Armory figé dans
`armory.py`, qui ne changera qu'avec le jeu. La courbe avance toute seule
entre deux relevés, et le trait du présent y glisse comme un sismographe.

Cliquer une matière ouvre sa carte : c'est `page_gisements.py`.

Le code vient de `window.py`, déplacé sans une ligne de changement.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from gi.repository import GLib, Gtk

from . import gisements, meteo, ryzom_api
from .i18n import _
from .ui_commun import run_async


class PageMeteo:
    """Le temps d'Atys, sa courbe et ses matières."""
    # -------------------------------------------------------------- Météo
    #
    # La météo d'Atys en courbe, et les matières qu'elle fait sortir. Deux
    # sources : l'API officielle pour le temps — calculé par le jeu, donc connu
    # quarante cycles à l'avance — et un relevé de Ryzom Armory figé dans
    # `armory.py`, qui ne changera qu'avec le jeu.

    #: Taille des symboles de familles de matières, en part des icônes.
    #:
    #: Posée, et non demandée : une taille demandée n'est qu'un plancher, et les
    #: symboles grossissaient au gré de la place laissée par le nom de leur
    #: famille.
    #:
    #: Vingt-six et non vingt, à cent pour cent : sur un écran de bureau, à côté
    #: d'un nom de famille et d'une ligne de matières, vingt points faisaient une
    #: vignette qu'on devinait plus qu'on ne la reconnaissait. Au-delà, le
    #: symbole prendrait le pas sur le texte qu'il accompagne.
    #:
    #: Exprimée en part, comme `PART_EMBLEME`, pour que le zoom grossisse la
    #: page entière — texte et images ensemble. Zéro virgule cinquante-quatre
    #: rend bien vingt-six à cent pour cent, la valeur d'avant.
    PART_SYMBOLE = 0.54

    #: Colonnes du bloc « ce qui sort » — une par zone des Primes, pour les
    #: avoir toutes les quatre sous les yeux à la fois. Sur deux colonnes, il
    #: fallait comparer une rangée avec celle du dessous alors que le geste
    #: utile est de choisir entre les quatre.
    COLONNES_POP = 4


    def _build_meteo_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._pad(bar)
        page.append(bar)

        self._meteo_entete = Gtk.Label(xalign=0.0, use_markup=True)
        self._meteo_entete.set_hexpand(True)
        bar.append(self._meteo_entete)

        self._meteo_refresh = Gtk.Button(label=_("Actualiser"))
        self._meteo_refresh.connect("clicked", lambda *a: self._load_meteo(force=True))
        bar.append(self._meteo_refresh)

        self._meteo_courbe = Gtk.DrawingArea()
        self._meteo_courbe.set_content_height(190)
        self._meteo_courbe.set_draw_func(self._dessiner_courbe)
        self._pad(self._meteo_courbe)
        page.append(self._meteo_courbe)

        # Deux colonnes, et **un seul défilement pour tout**. Chacune a d'abord
        # eu le sien, de peur que la colonne de gauche — plus longue — n'entraîne
        # la droite et ne laisse une moitié d'écran vide. À l'usage, deux barres
        # sont pires : on ne sait plus laquelle on tient, et comparer deux
        # tableaux qui glissent séparément demande de les recaler à la main.
        defilement = Gtk.ScrolledWindow()
        defilement.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        defilement.set_vexpand(True)
        dedans = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._pad(dedans)
        defilement.set_child(dedans)

        # Ce qui sort maintenant, en tête et sur toute la largeur : c'est la
        # seule chose de cet écran qui dépende de l'instant, et donc la seule
        # sur laquelle on agit tout de suite.
        self._meteo_pop_titre = Gtk.Label(xalign=0.0)
        self._meteo_pop_titre.add_css_class("title-4")
        self._meteo_pop_titre.add_css_class("peuple")
        dedans.append(self._meteo_pop_titre)
        pop = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      homogeneous=True)
        self._meteo_pop_colonnes = []
        # Surtout pas `for _ in range(...)` : `_` est la fonction de traduction,
        # et l'écraser ici la rendrait locale à la méthode — tous les `_("…")`
        # de l'écran météo lèveraient alors une UnboundLocalError au démarrage.
        for _rang in range(self.COLONNES_POP):
            colonne = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            self._meteo_pop_colonnes.append(colonne)
            pop.append(colonne)
        dedans.append(pop)

        # Le tableau des excellentes de la saison, jour et nuit cote a cote,
        # a été retiré à son tour. Il disait la saison entière quand « ce qui
        # sort » dit l'instant, et il tenait le jour et la nuit du relevé
        # d'Armory alors que le tutoriel de la guilde, lui, range les
        # excellentes par saison et par temps — comme les suprêmes. Les deux
        # listes se contredisaient sur l'écorce et la résine.
        self._meteo_note = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        dedans.append(self._meteo_note)
        page.append(defilement)

        self._meteo_releve = None      #: ce que l'API a rendu, tel quel
        self._meteo_affiche = None     #: le même, recalé sur l'instant présent
        self._meteo_charge = False
        self._meteo_en_cours = False   #: une requête est-elle en vol ?
        self._meteo_timer = None
        return page

    def _meteo_tick(self) -> bool:
        """Fait avancer l'heure d'Atys, sans rien demander à personne.

        Les cycles reçus couvrent plusieurs heures réelles : tant que le trait
        du « maintenant » reste dans la série, il n'y a aucune raison de
        redemander quoi que ce soit. Quand il approche du bout, on redemande —
        **une fois**, et sans cesser d'avancer pendant ce temps.

        Les deux tenaient dans le même `if`, et c'était le gel : arrivé près du
        bout de la prévision, chaque battement relançait une requête et rendait
        la main sans rien recaler. La courbe s'arrêtait donc net, définitivement
        si l'API ne répondait pas — et une requête partait toutes les dix
        secondes pour rien.
        """
        if self._meteo_releve is None:
            self._meteo_timer = None
            return False
        avance = self._meteo_releve.a_present()
        cycles = avance.cycles_des_primes()
        if (cycles and not self._meteo_en_cours
                and avance.cycle_courant > cycles[-1].cycle - 4):
            self._load_meteo(force=True)
        # Quoi qu'il arrive, on avance : la prévision manquante ne concerne que
        # la droite du graphique, pas le trait du présent.
        self._meteo_affiche = avance
        self._refresh_meteo()
        # Les cartes ouvertes suivent : elles lisent le meme releve.
        self._rafraichir_cartes_gisements()
        return True

    def _load_meteo(self, force: bool = False) -> None:
        if self._meteo_charge and not force:
            return
        self._meteo_charge = True
        self._meteo_en_cours = True
        self._meteo_refresh.set_sensitive(False)
        self._meteo_entete.set_text(_("Lecture de la météo…"))

        def work():
            continents = sorted(set(meteo.CONTINENT_DE_ZONE.values()))
            # Quelques cycles déjà écoulés en plus : sans eux la courbe
            # commencerait à l'instant présent, et le trait du « maintenant »
            # se collerait au bord gauche.
            brut = ryzom_api.fetch_weather_json(continents, cycles=20, passes=6)
            releve = meteo.parse_weather(brut)
            # La saison vient d'un autre appel : le flux météo ne la porte pas,
            # et c'est elle qui dit quelle page du relevé regarder.
            try:
                saison = ryzom_api.parse_time(
                    ryzom_api.fetch_time_xml())["season_index"]
            except Exception:                           # noqa: BLE001
                saison = -1
            return meteo.MeteoAtys(releve.cycle_courant, releve.heure_atys,
                                   saison, releve.continents, releve.pris_a)

        def done(res, err):
            self._meteo_en_cours = False
            self._meteo_refresh.set_sensitive(True)
            if err:
                self._meteo_entete.set_text(_("Météo indisponible : %s") % err)
                return
            self._meteo_releve = res
            self._meteo_affiche = res
            self._refresh_meteo()
            # Le temps d'Atys avance tout seul : on ne redemande rien, on
            # recale l'affichage. Toutes les dix secondes, soit un pas de trois
            # heures et vingt d'Atys — le trait glisse au lieu de sauter.
            if self._meteo_timer is None:
                self._meteo_timer = GLib.timeout_add_seconds(
                    10, self._meteo_tick)

        run_async(work, done)

    def _refresh_meteo(self) -> None:
        releve = self._meteo_affiche or self._meteo_releve
        if releve is None:
            return
        maintenant = releve.maintenant()
        if maintenant is not None:
            suite = [c for c in releve.cycles_des_primes()
                     if c.cycle > releve.cycle_courant]
            prochain = next((c for c in suite
                             if c.condition != maintenant.condition), None)
            meilleur = next((c for c in suite if c.condition == "best"), None)
            # Chaque morceau est échappé pour lui-même, et le gras posé ensuite :
            # échapper la phrase entière puis remettre les balises à la main
            # marchait, mais aurait cédé au premier nom de matière contenant un
            # « & ».
            def gras(texte: str) -> str:
                return f"<b>{GLib.markup_escape_text(texte)}</b>"

            def clair(texte: str) -> str:
                return GLib.markup_escape_text(texte)

            # La ligne se lisait « Beau · 0 % → Excellente   Mauvaise dans
            # 5 min ». Trois nombres, une flèche, et deux conditions côte à
            # côte dont l'une était la suivante : il fallait connaître le code
            # pour la décoder. Elle se lit maintenant comme une phrase, et ce
            # qui dure passe avant ce qui décrira le décor.
            # **La condition qualifie l'humidité, pas ce qui sort.** Les quatre
            # conditions de forage portent les memes mots que les qualites de
            # matiere -- Excellente en tete des deux listes -- et « sort
            # Mauvaise » affirmait donc qu'il sortait de la mauvaise matiere.
            # C'est faux : a soixante-trois pour cent d'humidite la condition
            # est mauvaise, et il sort tout de meme du supreme. Le mot passe
            # donc devant l'humidite, ou il ne peut plus qualifier que celle-ci.
            morceaux = [
                clair(_("humidité ")),
                gras(meteo.texte_condition(maintenant.condition)),
                gras(f" {int(maintenant.value * 100)} %"),
            ]
            # Et apres « sort », la qualite qu'on ramasse vraiment -- la
            # meilleure des quatre zones, celle que les colonnes detaillent.
            qualite = self._qualite_du_moment(releve, maintenant)
            if qualite is not None:
                morceaux.append(clair(_(", sort ")))
                morceaux.append(gras(meteo.mot_qualite(qualite)))
            if prochain is not None:
                # Le temps qui reste, et non le nom de la condition d'après :
                # « pendant 5 min » répond à « est-ce que j'ai le temps ? »,
                # qui est la question qu'on se pose devant cet écran.
                morceaux.append(gras(
                    _(" pendant %s")
                    % meteo.duree(releve.minutes_avant(prochain.cycle))))
            # La fenêtre excellente, sauf si elle est déjà annoncée juste
            # au-dessus : les deux mentions se vaudraient mot pour mot.
            if (maintenant.condition != "best" and meilleur is not None
                    and (prochain is None or meilleur.cycle != prochain.cycle)):
                morceaux.append(clair(
                    "   ✦ " + _("Excellente dans %s")
                    % meteo.duree(releve.minutes_avant(meilleur.cycle))))
            morceaux.append(clair(
                f"   —   {meteo.texte_meteo(maintenant.text)}, "
                f"{meteo.nom_saison(releve.saison)}, "
                f"{releve.heure_du_jour} h sur Atys, "
                f"{'nuit' if releve.nuit else 'jour'}"))
            self._meteo_entete.set_markup("".join(morceaux))
        self._meteo_courbe.queue_draw()

        for colonne in (self._meteo_note, *self._meteo_pop_colonnes):
            while (child := colonne.get_first_child()) is not None:
                colonne.remove(child)

        # Ce qui sort maintenant, une colonne par zone : l'humidité décide de la
        # condition, la condition décide de la qualité, et la qualité décide de
        # ce qu'on trouve. Le bloc change tout seul à chaque bascule de cycle —
        # sans rien redemander.
        # Les quatre zones des Primes tiennent ainsi sur une seule rangée, ce
        # qu'on demande d'un tableau qu'on lit pour choisir où aller forer.
        actuelle = releve.maintenant()
        if actuelle is None:
            self._meteo_pop_titre.set_text("")
        else:
            sorties = [(zone,) + meteo.sortie_de(releve.saison, zone,
                                                 actuelle.condition)
                       for zone in meteo.ZONES]
            # Le titre annonce la meilleure des quatre zones. Une zone qui n'a
            # pas cette qualité-là le dit sous son nom, plutôt que de laisser
            # une colonne vide sous un titre qui promet mieux : en automne par
            # temps mauvais, seules les Sources Interdites sortent du suprême,
            # et les trois autres zones de l'excellente.
            connues = [q for _z, q, _g in sorties if q is not None]
            meilleure = (min(connues, key=meteo.QUALITES.index)
                         if connues else None)
            self._meteo_pop_titre.set_text(
                self._titre_pop(releve, actuelle, meilleure))
            for rang, (zone, qualite, groupes) in enumerate(sorties):
                colonne = self._meteo_pop_colonnes[rang % self.COLONNES_POP]
                colonne.append(self._bloc_matieres(
                    zone, groupes, rang // self.COLONNES_POP % 2 == 0,
                    qualite,
                    mention=("" if qualite == meilleure
                             else meteo.mot_qualite(qualite))))

        # Deux choses qu'on ne devine pas en regardant le tableau : que les
        # quatre zones partagent une meteo mais pas leurs pops, et qu'un spot
        # vide ne repop pas parce que le temps est revenu.
        self._meteo_note.append(self._note(
            _("Les Primes partagent une seule météo, mais pas les mêmes pops : "
              "chaque zone dit la sienne. Un spot suprême vidé met quinze "
              "jours à se recharger — les bonnes conditions ne suffisent pas. "
              "Relevés de la guilde ; positions de ballisticmystix.net.")))

    @staticmethod
    @staticmethod
    def _qualite_du_moment(releve, actuelle):
        """La meilleure qualité que les quatre zones rendent en ce moment.

        C'est ce que la première ligne annonce après « sort ». Les colonnes
        disent ensuite le détail — laquelle sort où, et sous quel nom.
        """
        connues = [meteo.sortie_de(releve.saison, zone, actuelle.condition)[0]
                   for zone in meteo.ZONES]
        connues = [q for q in connues if q is not None]
        return min(connues, key=meteo.QUALITES.index) if connues else None

    @staticmethod
    def _titre_pop(releve, actuelle, _qualite: str) -> str:
        """« Suprême dans 2 h 10 — aujourd'hui à 17:09 », et rien de plus.

        La ligne en disait trois fois trop, et elle se contredisait : elle
        annonçait « ce qui sort : Suprême » — vrai, la moitié des matières
        d'une zone est toujours dans sa fourchette — juste avant « fenêtre
        suprême dans 2 h 10 ». Deux sens du même mot dans la même phrase.

        Ne reste que le seul nombre qu'on vienne y chercher : quand s'ouvre la
        grande fenêtre, l'humidité au-dessus de 83,4 %. La condition et le taux
        du moment sont déjà en tête de l'écran, le repop et la saison dans la
        barre du haut ; les répéter ici ne faisait que noyer ce nombre-là.

        Pendant la fenêtre, le compte **décroît** : « encore 9 min », puis six,
        puis trois. Une durée totale figée mentirait dès la troisième minute,
        et c'est le temps qu'il reste pour traverser les Primes qui décide si
        l'on part ou non.
        """
        if actuelle.condition.lower() == "worst":
            restantes = meteo.fin_fenetre_supreme(releve)
            if restantes is None:
                return _("Suprême maintenant")
            fin = (datetime.now()
                   + timedelta(minutes=restantes)).strftime("%H:%M")
            return (_("Suprême maintenant, encore %(delai)s — jusqu'à %(fin)s")
                    % {"delai": meteo.duree(int(restantes)), "fin": fin})
        prochaine = meteo.prochaine_fenetre_supreme(releve)
        if prochaine is None:
            return _("Suprême : pas avant six heures")
        minutes = releve.minutes_avant(prochaine.cycle)
        return (_("Suprême dans %(delai)s — %(quand)s")
                % {"delai": meteo.duree(minutes),
                   "quand": meteo.moment_du_changement(minutes)})

    def _note(self, texte: str) -> Gtk.Widget:
        label = Gtk.Label(label=texte, xalign=0.0, wrap=True)
        label.add_css_class("dim-label")
        label.props.margin_top = 10
        return label

    def _bloc_matieres(self, titre: str, groupes: dict, zebre: bool,
                       qualite: str, mention: str = "") -> Gtk.Widget:
        boite = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        if zebre:
            boite.add_css_class("zebre")
        self._pad(boite)
        entete = Gtk.Label(label=titre, xalign=0.0)
        entete.add_css_class("heading")
        boite.append(entete)
        # La qualite ne s'ecrit que si la zone dement le titre : l'ecrire sur
        # les quatre colonnes quand elles sont d'accord ne ferait que repeter
        # ce que le titre vient de dire.
        if mention:
            rappel = Gtk.Label(label=mention, xalign=0.0)
            rappel.add_css_class("dim-label")
            rappel.add_css_class("caption")
            boite.append(rappel)
        grille = Gtk.Grid(column_spacing=12, row_spacing=1)
        for ligne, (groupe, matieres) in enumerate(sorted(groupes.items())):
            # Le nom de la famille, et sous lui son symbole du jeu : une
            # coquille pour la carapace, une goutte pour la sève. Ce sont ceux
            # qu'on a sous les yeux en forant, et l'œil les reconnaît plus vite
            # qu'il ne lit « Carapace ».
            cellule = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            cellule.set_size_request(90, -1)
            g = Gtk.Label(label=groupe, xalign=0.0)
            g.add_css_class("dim-label")
            cellule.append(g)
            chemin = meteo.symbole(groupe)
            if chemin:
                # `Gtk.Image` et non `Gtk.Picture` : la seconde s'étire pour
                # remplir ce qu'on lui donne, et `set_size_request` n'est qu'un
                # **minimum** — d'où des symboles de tailles différentes d'une
                # colonne à l'autre, selon la place laissée par le nom de la
                # famille. `set_pixel_size` fixe la taille pour de bon.
                image = Gtk.Image.new_from_file(chemin)
                image.set_pixel_size(
                    self._settings.icone(self.PART_SYMBOLE))
                image.set_halign(Gtk.Align.START)
                cellule.append(image)
            grille.attach(cellule, 0, ligne, 1, 1)
            m = Gtk.Label(xalign=0.0, wrap=True)
            m.set_markup(self._matieres_markup(qualite, groupe, matieres))
            m.connect("activate-link", self._on_gisement)
            grille.attach(m, 1, ligne, 1, 1)
        boite.append(grille)
        return boite

    @staticmethod
    def _matieres_markup(qualite: str, famille: str, matieres: list) -> str:
        """La liste des matières, celles qu'on sait situer devenant des liens.

        Un lien plutôt qu'un bouton : la liste garde son allure de phrase et
        continue de se replier toute seule quand la colonne rétrécit. Une
        matière sans carte reste du texte ordinaire — rien n'invite à cliquer
        sur ce qui ne répondrait pas.
        """
        morceaux = []
        # Les gisements sont relevés par qualité, et sous un autre nom que
        # celui de l'écran. Le choix, lui, n'est relevé nulle part : ses
        # matières restent du texte.
        qualite = meteo.QUALITE_GISEMENT.get(qualite, "")
        for matiere in matieres:
            texte = GLib.markup_escape_text(matiere)
            if qualite and gisements.points(qualite, famille, matiere):
                cible = GLib.markup_escape_text(f"{qualite}|{famille}|{matiere}")
                morceaux.append(f'<a href="{cible}">{texte}</a>')
            else:
                morceaux.append(texte)
        return ", ".join(morceaux)

    #: Ce que la courbe montre, en heures d'Atys, et où s'y tient le présent.
    #:
    #: Vingt-quatre heures d'Atys valent soixante-douze minutes réelles : de
    #: quoi voir une heure d'avance et un bon quart d'heure de passé. Le trait
    #: du présent se tient à un sixième de la largeur — c'est ce qui vient qui
    #: compte, le passé ne sert qu'à comprendre d'où l'on sort. Pas contre le
    #: bord pour autant : on veut voir le palier qu'on quitte.
    #: Minutes réelles entre deux repères d'heure sous le graphique.
    #:
    #: La fenêtre ne couvre que soixante-douze minutes réelles — vingt-quatre
    #: heures d'Atys : à l'heure ronde, il n'y aurait qu'un repère, parfois
    #: zéro. Le quart d'heure en donne quatre ou cinq, assez pour situer un
    #: creux sans encombrer l'axe.
    #:
    #: **Ce sont les heures écrites.** Les tirets, eux, tombent cinq fois plus
    #: souvent : voir `MINUTES_ENTRE_TIRETS`.
    MINUTES_ENTRE_REPERES = 15

    #: Minutes réelles entre deux tirets de l'axe.
    #:
    #: **Un tiret n'est pas un repère.** Le quart d'heure suffit à écrire une
    #: heure, mais pas à lire une prévision : entre deux repères passent cinq
    #: heures d'Atys, et un joueur qui vise un creux devait interpoler à l'œil
    #: sur soixante pixels. Cinq minutes réelles — une heure et deux tiers
    #: d'Atys — donnent deux tirets entre deux heures écrites, sans texte pour
    #: encombrer.
    MINUTES_ENTRE_TIRETS = 5

    #: Longueur des tirets sous l'axe, en pixels : celui qui porte une heure,
    #: puis le muet.
    #:
    #: **Deux et trois pixels ne se voyaient pas.** Ils suffisaient tant que
    #: l'axe ne portait qu'un repère par quart d'heure, qu'on trouvait de
    #: toute façon en lisant l'heure écrite dessous ; un tiret muet, lui, n'a
    #: que sa propre encre pour exister. Doublés, et blanchis avec.
    LONGUEUR_TIRET_ECRIT = 6
    LONGUEUR_TIRET_MUET = 4

    #: Leur opacité, sur le fond bleu-nuit.
    #:
    #: Le muet reste en retrait de celui qui porte une heure : c'est ce qui
    #: laisse lire le quart d'heure d'un coup d'œil, sans compter les tirets.
    #: L'heure écrite, elle, ne bouge pas — « visible, discrète et sobre,
    #: c'est parfait », et l'on n'y touche donc pas.
    OPACITE_TIRET_ECRIT = 0.62
    OPACITE_TIRET_MUET = 0.42

    #: Hauteur de la ligne des heures au-dessus du bas du graphique, en pixels.
    #:
    #: **Quatre, et non six.** L'axe se tient à vingt pixels du bas et le tiret
    #: qui porte une heure en descend six : il finissait à un pixel du haut des
    #: chiffres, et venait mordre dessus. Deux pixels plus bas, le tiret pose
    #: l'heure sans la toucher.
    #:
    #: On descend le texte plutôt que de raccourcir le tiret : c'est le tiret
    #: qui a été allongé pour se voir, et le reprendre reviendrait à défaire ce
    #: qu'on vient de faire.
    PIED_DES_HEURES = 4

    #: Combien de tirets on essaie de poser, de part et d'autre.
    #:
    #: On part d'une heure en arrière pour attraper le passé qui reste visible,
    #: et ceux qui tombent hors de la fenêtre sont simplement écartés. Quarante-
    #: huit tirets de cinq minutes couvrent les quatre heures d'avant, ce que
    #: seize pas d'un quart d'heure couvraient.
    PAS_DE_TEMPS = 48

    FENETRE_HEURES = 24.0
    ANCRE = 0.15

    #: Durée de la bascule d'un palier au suivant, en heures d'Atys.
    #:
    #: L'API ne donne qu'une valeur par cycle : le palier, lui, est exact, et
    #: c'est lui qui décide de la condition de gisement. Le temps que met le
    #: taux à passer d'un palier au suivant, en revanche, **n'est pas mesuré**
    #: — l'API n'en dit rien. Une heure d'Atys, soit trois minutes réelles, est
    #: un choix de tracé : le trait vertical laissait croire à une bascule
    #: instantanée, alors que le taux monte et descend graduellement.
    #:
    #: Rien d'autre n'en dépend : les comptes à rebours (« Excellente dans
    #: 22 min ») se calculent sur les cycles, pas sur ce tracé. Même valeur que
    #: dans le portage Android, pour que les deux courbes se ressemblent.
    TRANSITION_HEURES = 1.0

    def _dessiner_courbe(self, _area, cr, largeur, hauteur) -> None:
        """L'humidité dans le temps, **en paliers reliés par des obliques**.

        Une valeur vaut pour tout un cycle — trois heures d'Atys, neuf minutes
        réelles : c'est le palier, et c'est lui qui décide de la condition de
        gisement. Relier simplement les points par des obliques dessinerait des
        crêtes qui n'existent pas, et déplacerait les moments intéressants : la
        fenêtre excellente n'est pas un sommet qu'on rate, c'est un palier qui
        dure.

        La bascule d'un palier au suivant, elle, n'est pas instantanée : le taux
        monte et descend graduellement, et le trait vertical laissait croire au
        contraire. Elle se dessine donc en oblique — voir `TRANSITION_HEURES`,
        qui dit ce qui est mesuré et ce qui ne l'est pas.

        **C'est le graphique qui défile, pas le trait.** Le présent se tient
        près du bord gauche et la courbe glisse dessous, comme un sismographe :
        on garde ainsi toujours la même avance sous les yeux, au lieu de voir
        le trait dériver vers le bord jusqu'à sortir de la vue.

        Les trois traits en pointillé sont les seuils du jeu, qui découpent les
        conditions de gisement ; les deux traits pleins à 30 et 70 % ne sont que
        des graduations, pour situer un taux entre deux seuils écartés de trente
        points. Les bandes sombres sont les nuits d'Atys, que le jeu compte de
        22 h à 3 h.
        """
        releve = self._meteo_affiche or self._meteo_releve
        if releve is None:
            return
        cycles = releve.cycles_des_primes()
        if len(cycles) < 2:
            return

        marge_g, marge_b = 34.0, 20.0
        large = largeur - marge_g
        haut = hauteur - marge_b
        if large <= 0 or haut <= 0:
            return

        # Tout se repère en heures d'Atys, et non en indices de cycle : c'est ce
        # qui permet à la fenêtre de glisser continûment sous un trait fixe.
        gauche = releve.heure_atys - self.ANCRE * self.FENETRE_HEURES

        def x(heure: float) -> float:
            return marge_g + large * (heure - gauche) / self.FENETRE_HEURES

        def y(valeur: float) -> float:
            return haut * (1.0 - min(1.0, max(0.0, valeur)))

        cr.save()
        cr.rectangle(marge_g, 0, large, haut)
        cr.clip()

        # Les nuits, comptées par heure et non par cycle : un cycle de trois
        # heures enjambe volontiers le lever du jour.
        cr.set_source_rgba(1, 1, 1, 0.06)
        premiere = int(gauche) - 1
        for h in range(premiere, int(gauche + self.FENETRE_HEURES) + 2):
            if meteo.est_la_nuit(h % 24):
                cr.rectangle(x(h), 0, large / self.FENETRE_HEURES, haut)
                cr.fill()

        # La courbe et son aire. Un cycle couvre trois heures ; le palier occupe
        # le milieu, et la demi-heure de part et d'autre sert à rejoindre le
        # palier voisin en oblique.
        def parcourir():
            demi = self.TRANSITION_HEURES / 2
            for m in cycles:
                debut = m.cycle * meteo.HEURES_PAR_CYCLE
                yield (x(debut + demi),
                       x(debut + meteo.HEURES_PAR_CYCLE - demi),
                       y(m.value))

        cr.set_source_rgba(0.25, 0.48, 0.41, 0.35)
        cr.move_to(x(cycles[0].cycle * meteo.HEURES_PAR_CYCLE), haut)
        for gx, dx, py in parcourir():
            cr.line_to(gx, py)
            cr.line_to(dx, py)
        cr.line_to(x((cycles[-1].cycle + 1) * meteo.HEURES_PAR_CYCLE), haut)
        cr.close_path()
        cr.fill()

        cr.set_source_rgb(0.35, 0.68, 0.58)
        cr.set_line_width(2.0)
        for gx, dx, py in parcourir():
            cr.line_to(gx, py)
            cr.line_to(dx, py)
        cr.stroke()
        cr.restore()

        cr.select_font_face("Sans")
        cr.set_font_size(10 * self._settings.zoom)

        # Deux graduations, plus discrètes que les seuils : elles ne veulent
        # rien dire pour le jeu, elles servent seulement à situer un taux à
        # l'œil entre deux seuils écartés de trente points. Traits pleins et
        # non pointillés, pour qu'on ne les confonde pas avec les seuils.
        # L'application Android les a depuis toujours ; celle-ci ne les avait
        # pas, et les deux courbes ne se lisaient pas pareil.
        cr.set_line_width(1.0)
        for graduation, etiquette in ((0.30, "30"), (0.70, "70")):
            yy = y(graduation)
            cr.set_source_rgba(1, 1, 1, 0.18)
            cr.move_to(marge_g, yy)
            cr.line_to(largeur, yy)
            cr.stroke()
            cr.set_source_rgba(1, 1, 1, 0.35)
            cr.move_to(2, yy - 3)
            cr.show_text(etiquette)

        # Les seuils, par-dessus la courbe, et leur étiquette dans la marge.
        cr.set_dash([4.0, 4.0])
        for seuil, etiquette in zip(meteo.SEUILS, ("16", "50", "83")):
            yy = y(seuil)
            cr.set_source_rgba(0.9, 0.4, 0.4, 0.55)
            cr.move_to(marge_g, yy)
            cr.line_to(largeur, yy)
            cr.stroke()
            cr.set_source_rgba(1, 1, 1, 0.55)
            cr.move_to(2, yy - 3)
            cr.show_text(etiquette)
        cr.set_dash([])

        # Le présent, immobile près du bord gauche.
        px = x(releve.heure_atys)
        cr.set_source_rgb(0.91, 0.76, 0.35)
        cr.set_line_width(2.0)
        cr.move_to(px, 0)
        cr.line_to(px, haut)
        cr.stroke()

        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.set_line_width(1.0)
        cr.move_to(marge_g, haut)
        cr.line_to(largeur, haut)
        cr.stroke()

        # L'heure réelle, tous les quarts d'heure — et un tiret toutes les cinq
        # minutes entre elles. Une heure d'Atys valant trois minutes, la
        # fenêtre ne couvre que soixante-douze minutes réelles : à l'heure
        # ronde, il n'y aurait qu'un repère, parfois zéro — et à la demie,
        # trois pour une heure entière de prévision.
        maintenant = datetime.now()
        repere = maintenant.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        for _ in range(self.PAS_DE_TEMPS):
            repere += timedelta(minutes=self.MINUTES_ENTRE_TIRETS)
            minutes = (repere - maintenant).total_seconds() / 60.0
            atys = releve.heure_atys + minutes / meteo.MINUTES_PAR_HEURE_ATYS
            if not gauche <= atys <= gauche + self.FENETRE_HEURES:
                continue
            # **Deux longueurs de tiret, une seule écriture.** Le tiret dit où
            # tombe l'instant, l'heure écrite dit lequel c'est : les mettre
            # toutes les cinq minutes empilerait quinze nombres sur une
            # largeur qui en tient cinq. Le tiret nu se lit par sa position
            # entre deux heures — la moitié, puis les deux tiers.
            ecrite = repere.minute % self.MINUTES_ENTRE_REPERES == 0
            cr.set_source_rgba(1, 1, 1, self.OPACITE_TIRET_ECRIT if ecrite
                               else self.OPACITE_TIRET_MUET)
            cr.set_line_width(1.0)
            cr.move_to(x(atys), haut)
            cr.line_to(x(atys), haut + (self.LONGUEUR_TIRET_ECRIT if ecrite
                                        else self.LONGUEUR_TIRET_MUET))
            cr.stroke()
            if not ecrite:
                continue
            cr.set_source_rgba(1, 1, 1, 0.55)
            texte = repere.strftime("%Hh") if repere.minute == 0 \
                else repere.strftime("%Hh%M")
            cr.move_to(min(largeur - 30, max(0.0, x(atys) - 14)),
                       hauteur - self.PIED_DES_HEURES)
            cr.show_text(texte)
