import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class KafkaPanelHeader(Gtk.HBox):
    def __init__(self, label, **callbacks):
        Gtk.HBox.__init__(self)

        self.callbacks = callbacks

        self.pause_button = Gtk.Button.new_from_icon_name("gtk-media-pause", Gtk.IconSize.BUTTON)
        self.pause_handler = self.pause_button.connect('clicked', self.callbacks['pause'])
        self.pack_start(self.pause_button, False, False, 0)

        self.pack_start(Gtk.Label(label), True, True, 0)

        self.close_button = Gtk.Button.new_from_icon_name("gtk-close", Gtk.IconSize.BUTTON)
        self.close_button.connect('clicked', self.callbacks['close'])
        self.pack_start(self.close_button, False, False, 0)

        self.pause_img = Gtk.Image.new_from_icon_name("gtk-media-pause", Gtk.IconSize.BUTTON)
        self.resume_img = Gtk.Image.new_from_icon_name("gtk-media-play", Gtk.IconSize.BUTTON)

        self.show_all()

        self.set_paused(False)

    def set_paused(self, paused):
        self.paused = paused
        if paused is True:
            # Swap pause button for resume button
            self.pause_button.set_image(self.resume_img)
            self.pause_button.disconnect(self.pause_handler)
            self.pause_handler = self.pause_button.connect('clicked', self.callbacks['resume'])
        else:
            self.pause_button.set_image(self.pause_img)
            self.pause_button.disconnect(self.pause_handler)
            self.pause_handler = self.pause_button.connect('clicked', self.callbacks['pause'])
