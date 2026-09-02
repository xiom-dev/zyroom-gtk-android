"""Fenêtre d'options (réglages généraux)."""
from __future__ import annotations

from gi.repository import GLib, Gtk

from .i18n import LANGUAGES, _


class OptionsWindow(Gtk.Window):
    def __init__(self, parent, settings, on_saved):
        super().__init__(title=_("Options"), transient_for=parent, modal=True)
        self.set_default_size(560, -1)
        self._settings = settings
        self._on_saved = on_saved

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            setattr(box.props, m, 14)
        self.set_child(box)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        box.append(grid)
        row = 0

        def label(text):
            return Gtk.Label(label=_(text), xalign=0.0)

        # Langue de l'interface
        grid.attach(label("Langue"), 0, row, 1, 1)
        self._lang_codes = list(LANGUAGES.keys())
        self._lang_dd = Gtk.DropDown.new_from_strings(list(LANGUAGES.values()))
        try:
            self._lang_dd.set_selected(self._lang_codes.index(settings.language))
        except ValueError:
            self._lang_dd.set_selected(0)
        grid.attach(self._lang_dd, 1, row, 2, 1)
        row += 1

        # string_client.pack
        grid.attach(label("Fichier string_client.pack"), 0, row, 1, 1)
        self._pack_entry = Gtk.Entry(hexpand=True, text=settings.pack_file)
        grid.attach(self._pack_entry, 1, row, 1, 1)
        pack_btn = Gtk.Button(label=_("Parcourir…"))
        pack_btn.connect("clicked", lambda *_: self._browse(self._pack_entry, False))
        grid.attach(pack_btn, 2, row, 1, 1)
        row += 1

        # Dossier save de Ryzom
        grid.attach(label("Dossier « save » de Ryzom"), 0, row, 1, 1)
        self._save_entry = Gtk.Entry(hexpand=True, text=settings.save_folder)
        grid.attach(self._save_entry, 1, row, 1, 1)
        save_btn = Gtk.Button(label=_("Parcourir…"))
        save_btn.connect("clicked", lambda *_: self._browse(self._save_entry, True))
        grid.attach(save_btn, 2, row, 1, 1)
        row += 1

        # Corps du texte
        grid.attach(label("Taille du texte (points, 0 = celle du bureau)"),
                    0, row, 1, 1)
        self._police = Gtk.SpinButton.new_with_range(0, 30, 1)
        self._police.set_value(settings.font_size)
        self._police.set_tooltip_text(_(
            "Le corps du texte, comme dans un traitement de texte. Le bureau "
            "tourne autour de 10 ; 12 ou 14 se lisent mieux dans les "
            "tableaux. Le changement prend effet au prochain lancement."))
        grid.attach(self._police, 1, row, 1, 1)
        row += 1

        # Taille des icones
        grid.attach(label("Taille des icônes (pixels)"), 0, row, 1, 1)
        self._icones = Gtk.SpinButton.new_with_range(24, 128, 8)
        self._icones.set_value(settings.icon_size)
        self._icones.set_tooltip_text(_(
            "Le côté des icônes de l'inventaire. Les boutons + et − de la "
            "barre de titre la changent aussi, sans passer par ici."))
        grid.attach(self._icones, 1, row, 1, 1)
        row += 1

        # Seuil de volume
        grid.attach(label("Seuil d'alerte de volume (%)"), 0, row, 1, 1)
        self._vol = Gtk.SpinButton.new_with_range(0, 100, 5)
        self._vol.set_value(settings.volume_threshold)
        grid.attach(self._vol, 1, row, 1, 1)
        row += 1

        # Alerte ventes
        grid.attach(label("Alerte ventes (heures avant expiration)"), 0, row, 1, 1)
        self._sales = Gtk.SpinButton.new_with_range(0, 168, 1)
        self._sales.set_value(settings.sales_count)
        grid.attach(self._sales, 1, row, 1, 1)
        row += 1

        # Alerte saison
        grid.attach(label("Alerte saison (heures avant changement)"), 0, row, 1, 1)
        self._season = Gtk.SpinButton.new_with_range(0, 168, 1)
        self._season.set_value(settings.season_count)
        grid.attach(self._season, 1, row, 1, 1)
        row += 1

        # Notifications du bureau. Le même interrupteur se trouve en bas de la
        # fenêtre des alertes, là où on est quand elles agacent.
        self._notifications = Gtk.CheckButton(
            label=_("Afficher les alertes sur le bureau (bulles près de l'horloge)"))
        self._notifications.set_active(settings.notifications)
        self._notifications.set_tooltip_text(_(
            "Décochée, l'application n'envoie plus rien au bureau. Les alertes "
            "restent visibles dans la fenêtre de la cloche."))
        grid.attach(self._notifications, 0, row, 3, 1)
        row += 1

        # Synchronisation automatique
        grid.attach(label("Resynchroniser toutes les (minutes, 0 = jamais)"), 0, row, 1, 1)
        self._sync_interval = Gtk.SpinButton.new_with_range(0, 240, 5)
        self._sync_interval.set_value(settings.sync_interval)
        grid.attach(self._sync_interval, 1, row, 1, 1)
        row += 1

        self._sync_on_start = Gtk.CheckButton(
            label=_("Synchroniser à l'ouverture d'un personnage ou d'une guilde"))
        self._sync_on_start.set_active(settings.sync_on_start)
        grid.attach(self._sync_on_start, 0, row, 3, 1)
        row += 1

        # Sauvegarde auto
        self._backup_auto = Gtk.CheckButton(label=_("Sauvegarder le dossier « save » à la fermeture"))
        self._backup_auto.set_active(settings.backup_auto)
        grid.attach(self._backup_auto, 0, row, 3, 1)
        row += 1

        # Proxy HTTP
        self._proxy_enabled = Gtk.CheckButton(label=_("Utiliser un proxy HTTP"))
        self._proxy_enabled.set_active(settings.proxy_enabled)
        grid.attach(self._proxy_enabled, 0, row, 3, 1)
        row += 1
        grid.attach(label("Adresse du proxy"), 0, row, 1, 1)
        self._proxy_addr = Gtk.Entry(hexpand=True, text=settings.proxy_address)
        grid.attach(self._proxy_addr, 1, row, 2, 1)
        row += 1
        grid.attach(label("Port du proxy"), 0, row, 1, 1)
        self._proxy_port = Gtk.SpinButton.new_with_range(0, 65535, 1)
        self._proxy_port.set_value(settings.proxy_port)
        grid.attach(self._proxy_port, 1, row, 1, 1)
        row += 1
        grid.attach(label("Identifiant proxy"), 0, row, 1, 1)
        self._proxy_user = Gtk.Entry(hexpand=True, text=settings.proxy_username)
        grid.attach(self._proxy_user, 1, row, 2, 1)
        row += 1
        grid.attach(label("Mot de passe proxy"), 0, row, 1, 1)
        self._proxy_pass = Gtk.Entry(hexpand=True, text=settings.proxy_password)
        self._proxy_pass.set_visibility(False)
        grid.attach(self._proxy_pass, 1, row, 2, 1)
        row += 1

        # Boutons
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                          halign=Gtk.Align.END)
        cancel = Gtk.Button(label=_("Annuler"))
        cancel.connect("clicked", lambda *_: self.destroy())
        save = Gtk.Button(label=_("Enregistrer"))
        save.add_css_class("suggested-action")
        save.connect("clicked", self._on_save)
        buttons.append(cancel)
        buttons.append(save)
        box.append(buttons)

    def _browse(self, entry, folder: bool) -> None:
        dialog = Gtk.FileDialog()
        if folder:
            dialog.select_folder(self, None,
                                 lambda d, r: self._browse_done(d, r, entry, True))
        else:
            dialog.open(self, None,
                        lambda d, r: self._browse_done(d, r, entry, False))

    def _browse_done(self, dialog, result, entry, folder: bool) -> None:
        try:
            gfile = (dialog.select_folder_finish(result) if folder
                     else dialog.open_finish(result))
        except GLib.Error:
            return
        if gfile and gfile.get_path():
            entry.set_text(gfile.get_path())

    def _on_save(self, _btn) -> None:
        self._settings.pack_file = self._pack_entry.get_text().strip()
        self._settings.save_folder = self._save_entry.get_text().strip()
        self._settings.volume_threshold = int(self._vol.get_value())
        self._settings.sales_count = int(self._sales.get_value())
        self._settings.season_count = int(self._season.get_value())
        self._settings.sync_interval = int(self._sync_interval.get_value())
        self._settings.sync_on_start = self._sync_on_start.get_active()
        self._settings.notifications = self._notifications.get_active()
        self._settings.backup_auto = self._backup_auto.get_active()
        self._settings.proxy_enabled = self._proxy_enabled.get_active()
        self._settings.proxy_address = self._proxy_addr.get_text().strip()
        self._settings.proxy_port = int(self._proxy_port.get_value())
        self._settings.proxy_username = self._proxy_user.get_text().strip()
        self._settings.proxy_password = self._proxy_pass.get_text()
        self._settings.language = self._lang_codes[self._lang_dd.get_selected()]
        self._settings.font_size = int(self._police.get_value())
        self._settings.icon_size = int(self._icones.get_value())
        self.destroy()
        if self._on_saved:
            self._on_saved()
