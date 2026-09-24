"""La cloche, ses seuils, et la surveillance d'un objet.

Quatre sources, toutes réglées par le joueur : les seuils qu'il pose lui-même
sur un objet — quantité minimale ou durabilité, par clic droit —, la
surveillance du trésor, et ce que les relevés font apparaître. Le panneau de
la cloche les rassemble, et les bulles près de l'horloge les annoncent.

Le code vient de `window.py`, déplacé sans une ligne de changement. Les deux
moitiés — la liste et les seuils — voyageaient séparées par cinq cents lignes
d'autre chose ; elles sont ici l'une sous l'autre.
"""
from __future__ import annotations

import os

from gi.repository import Gdk, Gio, GLib, Gtk

from . import alerts, movements
from .config import movements_path, outposts_path, snapshot_path
from .i18n import _
from .watch import KIND_DURABILITY, watch_kind


class PageAlertes:
    """Ce que la cloche annonce, et ce que le joueur lui demande de guetter."""
    # -------------------------------------------- Surveillance par item
    def _on_item_right_click(self, _gesture, _n, x, y, item, image) -> None:
        pop = Gtk.Popover()
        pop.set_parent(image)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            setattr(box.props, m, 4)

        def row(label, handler):
            btn = Gtk.Button(label=label)
            btn.set_has_frame(False)
            btn.set_halign(Gtk.Align.FILL)
            btn.get_child().set_xalign(0.0)
            btn.connect("clicked", handler)
            box.append(btn)

        row("Détails…", lambda *_: (pop.popdown(), self._show_details(item)))
        if item.item_id:
            row("Copier l'identifiant", lambda *_: (pop.popdown(), self._copy_id(item)))
        if self._watch is not None:
            if self._watch.is_watched(item):
                row("Ne plus surveiller", lambda *_: self._on_unwatch(None, item, pop))
            else:
                label = ("Surveiller la durabilité…"
                         if watch_kind(item) == KIND_DURABILITY
                         else "Surveiller la quantité…")
                row(label, lambda *_: self._on_watch(None, item, pop))
        row("Réinitialiser l'icône", lambda *_: (pop.popdown(), self._reset_icon(item)))

        pop.set_child(box)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        pop.set_pointing_to(rect)
        pop.popup()

    def _on_item_activate(self, _gesture, n_press, _x, _y, item) -> None:
        if n_press >= 2:
            self._show_details(item)

    def _show_details(self, item) -> None:
        detail.show_detail(self, item, self._names.name, self._categorydb)

    def _copy_id(self, item) -> None:
        self.get_clipboard().set(item.item_id)
        self._set_status(f"Identifiant copié : {item.item_id}")

    def _reset_icon(self, item) -> None:
        path = self._icons.cached_path(item)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass
        self._redisplay_current()

    def _on_watch(self, _btn, item, pop) -> None:
        pop.popdown()
        self._open_watch_dialog(item)

    def _on_unwatch(self, _btn, item, pop) -> None:
        pop.popdown()
        if self._watch is not None:
            self._watch.remove(item)
            self._recompute_alerts()
            self._redisplay_current()

    def _open_watch_dialog(self, item) -> None:
        is_dur = watch_kind(item) == KIND_DURABILITY
        dlg = Gtk.Window(title="Surveiller un objet", transient_for=self, modal=True)
        dlg.set_default_size(420, -1)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.props.margin_top = box.props.margin_bottom = 14
        box.props.margin_start = box.props.margin_end = 14
        dlg.set_child(box)

        name = self._names.name(item.sheet)
        header = Gtk.Label(xalign=0.0)
        header.set_markup(f"<b>{GLib.markup_escape_text(name)}</b> (Q{item.quality})")
        box.append(header)
        box.append(Gtk.Label(
            label=("Alerte si la durabilité descend sous ce seuil :" if is_dur
                   else "Alerte si la quantité descend sous ce seuil :"),
            xalign=0.0, wrap=True))

        spin = Gtk.SpinButton.new_with_range(0, 100000, 1)
        spin.set_value(item.hp if is_dur else item.stack)
        box.append(spin)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Annuler")
        cancel.connect("clicked", lambda *_: dlg.destroy())
        ok = Gtk.Button(label="Surveiller")
        ok.add_css_class("suggested-action")

        def do_ok(*_):
            self._watch.add(item, int(spin.get_value()))
            dlg.destroy()
            self._recompute_alerts()
            self._redisplay_current()

        ok.connect("clicked", do_ok)
        buttons.append(cancel)
        buttons.append(ok)
        box.append(buttons)
        dlg.present()

    def _update_bell(self) -> None:
        n = len(self._alerts)
        self._bell.set_label(f"🔔 {n}" if n else "🔔")
        # Toujours cliquable, meme sans alerte : c'est dans son panneau qu'on
        # pose la surveillance du tresor, et c'est la qu'elle dit ce qu'elle
        # guette. Grisee, elle ne pouvait plus rien apprendre a personne --
        # c'est le meme raisonnement qui a rendu la cloche visible sur le
        # telephone en 2.28.
        self._bell.set_sensitive(True)
        infobulle = f"{n} alerte(s)" if n else "Aucune alerte"
        if not self._settings.notifications:
            # Sans quoi la coupure ne se voit plus une fois la fenêtre fermée,
            # et on croit l'application muette alors qu'on l'a fait taire.
            infobulle += "\n" + _("Notifications du bureau coupées")
        self._bell.set_tooltip_text(infobulle)

    def _on_bell_clicked(self, _btn) -> None:
        dlg = Gtk.Window(title="Alertes", transient_for=self, modal=True)
        # Rouverte a la taille ou on l'a laissee. La bonne largeur depend des
        # noms d'objets surveilles, que nous ne connaissons pas d'avance : au
        # joueur de la poser une fois, a nous de nous en souvenir.
        dlg.set_default_size(*self._settings.alerts_window_size)
        dlg.connect("close-request", self._on_alerts_close)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._pad(box)
        dlg.set_child(box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scroll.set_child(listbox)
        box.append(scroll)

        if not self._alerts:
            listbox.append(Gtk.Label(label="Aucune alerte.", xalign=0.0))
        # Une figure par sorte d'alerte : la liste se lit d'un coup d'œil, et
        # l'on voit tout de suite laquelle des quatre surveillances a parlé.
        figures = {"quantity": "📉", "durability": "🛡", "unfound": "❓",
                   "volume": "📦", "sales": "💰", "season": "🍂", "money": "🪙",
                   "outpost": "🚩"}
        for al in self._alerts:
            icon = figures.get(al.kind, "🔔")
            title = Gtk.Label(xalign=0.0)
            title.set_markup(f"{icon} <b>{GLib.markup_escape_text(al.title)}</b>")
            listbox.append(title)
            detail = Gtk.Label(label=al.detail, xalign=0.0, wrap=True)
            detail.add_css_class("dim-label")
            detail.props.margin_start = 18
            listbox.append(detail)

        # La surveillance du tresor se pose ici, et nulle part ailleurs :
        # l'argent n'a pas d'icone dans un inventaire ou l'on ferait un clic
        # droit, comme pour les objets. La cloche etant l'endroit ou l'on vient
        # voir ce qui est guette, c'est aussi celui ou on le lui demande.
        tresor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tresor.append(Gtk.Label(label=_("Prévenir mouvement dappers"),
                                valign=Gtk.Align.CENTER, xalign=0.0,
                                hexpand=True))
        bascule = Gtk.Switch(valign=Gtk.Align.CENTER)
        bascule.set_sensitive(self._watch is not None)
        bascule.set_active(self._watch is not None
                           and self._watch.money_watched())
        bascule.set_tooltip_text(_(
            "Une alerte à chaque relevé où les dappers ont bougé, dans un sens "
            "ou dans l'autre. Sans seuil à régler : un relevé rapporte au plus "
            "un mouvement d'argent, il ne peut donc pas noyer les autres."))
        bascule.connect("state-set", self._on_money_watch_toggled)
        tresor.append(bascule)
        box.append(tresor)

        # Le pied de la fenêtre : la coupure à gauche, la sortie à droite. La
        # coupure ne touche qu'au bureau — la liste au-dessus reste pleine.
        pied = Gtk.CenterBox()
        coupure = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        coupure.append(Gtk.Label(label=_("Notifications du bureau"),
                                 valign=Gtk.Align.CENTER))
        bouton = Gtk.Switch(valign=Gtk.Align.CENTER)
        bouton.set_active(self._settings.notifications)
        bouton.set_tooltip_text(_(
            "Coupe les bulles qui s'affichent près de l'horloge à chaque "
            "synchronisation. Les alertes restent listées ici."))
        bouton.connect("state-set", self._on_notifications_toggled)
        coupure.append(bouton)
        pied.set_start_widget(coupure)

        close = Gtk.Button(label="Fermer")
        # `close` et non `destroy` : seul le premier emet `close-request`, ou
        # se retient la taille. Detruite sans passer par la, la fenetre
        # oubliait ce que le bouton venait de fermer.
        close.connect("clicked", lambda *_: dlg.close())
        pied.set_end_widget(close)
        box.append(pied)
        dlg.present()

    def _on_alerts_close(self, dlg) -> bool:
        """Retient la taille de la fenêtre des alertes avant qu'elle parte."""
        # `get_default_size` et non `get_width` : meme raison que pour la
        # fenetre principale, une fenetre agrandie doit se souvenir de la
        # taille qu'elle avait avant de l'etre.
        self._settings.alerts_window_size = dlg.get_default_size()
        return False        # laisse la fermeture suivre son cours

    def _on_money_watch_toggled(self, _switch, actif: bool) -> bool:
        """Pose ou lève la surveillance du trésor de l'entité affichée.

        Elle vit dans la liste des objets surveillés, sous la signature
        réservée du journal : une surveillance de plus, rangée avec les autres,
        et qui suit l'entité comme elles.
        """
        if self._watch is not None:
            self._watch.set_money_watched(actif)
            self._recompute_alerts()
        return False

    def _on_notifications_toggled(self, _switch, actif: bool) -> bool:
        """Coupe ou rétablit les bulles du bureau, sans toucher aux alertes."""
        self._settings.notifications = actif
        if not actif:
            # Couper le robinet ne vide pas le seau : celle qui attend déjà
            # près de l'horloge y resterait, et c'est elle qu'on voulait voir
            # partir. On la retire donc du même geste.
            self._retirer_notification()
        self._update_bell()
        return False        # laisse l'interrupteur adopter son nouvel état

    def _retirer_notification(self) -> None:
        app = self.get_application()
        if app is not None:
            app.withdraw_notification("zyroom-alerts")

    def _notify(self, result) -> None:
        if not self._settings.notifications:
            return
        try:
            app = self.get_application()
            notif = Gio.Notification.new("ZyRoom — alertes")
            notif.set_body("\n".join(a.title for a in result[:6]))
            app.send_notification("zyroom-alerts", notif)
        except Exception:
            pass
    # ------------------------------------------------------------- Alertes
    def _check_alerts(self, ent, entry: dict, from_sync: bool,
                      time_data: dict | None = None) -> None:
        """Refait la liste de la cloche : rien que ce qui a été demandé.

        Quatre sources, et toutes réglées par le joueur : les seuils qu'il pose
        lui-même sur un objet (quantité minimale, durabilité), et les trois
        réglages des options — remplissage d'un contenant, vente qui expire,
        saison qui tourne. Un objet surveillé qui a disparu s'y ajoute, puisque
        c'est bien lui qu'on avait demandé à suivre.

        Les déplacements d'objets n'y sont pas : voir plus bas.
        """
        result = alerts.volume_alerts(ent, self._settings.volume_threshold)
        if self._watch is not None:
            result += alerts.watch_alerts(ent, self._watch, self._names.name)
        result += alerts.sales_alerts(ent, self._settings.sales_count, self._names.name)
        if self._watch is not None:
            result += alerts.money_alerts(self._mouvements_argent,
                                          self._watch.money_watched())
        # Nos avant-postes, tels que la fiche de guilde les donne. Pas de
        # réglage : comme le trésor, un relevé n'en rapporte jamais douze, et
        # personne ne tient un avant-poste sans vouloir savoir qu'il lui
        # échappe. Seulement au retour d'une synchronisation : hors de là,
        # l'entité en mémoire est celle du dernier relevé, et comparer un état
        # avec lui-même ne dirait rien.
        if from_sync:
            result += alerts.outpost_alerts(
                ent, outposts_path(entry["kind"], entry["id"]),
                self._names.name)
        if from_sync:
            path = snapshot_path(entry["kind"], entry["id"])
            old = alerts.load_snapshot(path)
            new = alerts.build_snapshot(ent)
            if old:
                # Les mouvements vont au journal, et à lui seul. La cloche ne
                # doit porter que ce qu'on lui a demandé de guetter — un seuil
                # posé sur un objet, un réglage des options. Un déplacement
                # n'est demandé par personne : ranger douze matières faisait
                # sonner douze fois, et l'alerte qui comptait se perdait dans
                # le tas. Le journal, lui, garde tout, daté et consultable.
                mouvements = movements.diff(old, new, ent)
                movements.append(movements_path(entry["kind"], entry["id"]),
                                 mouvements)
                # Le tresor est le seul mouvement que la cloche ait le droit de
                # reprendre : il y en a au plus un par releve (cf. alerts).
                self._mouvements_argent = [m for m in mouvements
                                           if m.inv_key == movements.MONEY_KEY]
                if self._stack.get_visible_child_name() == "log":
                    self._load_log()
            alerts.save_snapshot(path, new)
            if time_data:
                season = alerts.season_alert(time_data, self._settings.season_count)
                if season:
                    result.append(season)
        self._alerts = result
        self._update_bell()
        if from_sync and result:
            self._notify(result)

    def _recompute_alerts(self) -> None:
        """Recalcule les alertes (hors mouvements/saison) après un changement
        de surveillance, sans appel réseau."""
        entry = self._current_entry()
        if self._entity and entry:
            self._check_alerts(self._entity, entry, from_sync=False)

    def _redisplay_current(self) -> None:
        idx = self._inv_dd.get_selected()
        if idx != Gtk.INVALID_LIST_POSITION:
            self._display_inventory(idx)
