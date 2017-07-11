import configparser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, config_file):
        buttons = (Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, "Settings", parent, 0, buttons)

        # Load defaults from file for persistence
        self.load_initial_values(config_file)

        self.set_size_request(350, 0)

        box = self.get_content_area()

        row = Gtk.HBox()
        _ = Gtk.Label("Kafka Servers")
        row.pack_start(_, False, False, 0)
        self.servers = Gtk.Entry()
        self.servers.get_buffer().set_text(self.initial_values['kafka_servers'], -1)
        row.pack_end(self.servers, False, False, 0)
        box.pack_start(row, False, False, 0)

        row = Gtk.HBox()
        _ = Gtk.Label("Initial Topics (Optional)")
        row.pack_start(_, False, False, 0)
        self.topics = Gtk.Entry()
        self.topics.get_buffer().set_text(self.initial_values['topics'], -1)
        row.pack_end(self.topics, False, False, 0)
        box.pack_start(row, False, False, 0)

        # TODO: Gtk.Adjustment seems to default to the min half the time
        row = Gtk.HBox()
        _ = Gtk.Label("Polling Frequency (ms)")
        row.pack_start(_, False, False, 0)
        freq_adj = Gtk.Adjustment(self.initial_values['polling_freq'], 1, 1000, 1, 10, 0)
        self.freq = Gtk.SpinButton()
        self.freq.set_adjustment(freq_adj)
        row.pack_end(self.freq, False, False, 0)
        box.pack_start(row, False, False, 0)

        row = Gtk.HBox()
        _ = Gtk.Label("Max History")
        row.pack_start(_, False, False, 0)
        history_adj = Gtk.Adjustment(self.initial_values['max_history'], 1, 5000, 100, 1000, 0)
        self.history = Gtk.SpinButton()
        self.history.set_adjustment(history_adj)
        row.pack_end(self.history, False, False, 0)
        box.pack_start(row, False, False, 0)

        row = Gtk.HBox()
        _ = Gtk.Label("Layout")
        row.pack_start(_, False, False, 0)
        layout_options = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tab_button = Gtk.RadioButton.new_with_label_from_widget(None, "Tabs")
        layout_options.pack_start(self.tab_button, True, True, 0)
        self.tile_button = Gtk.RadioButton.new_with_label_from_widget(self.tab_button, "Tiles")
        layout_options.pack_start(self.tile_button, True, True, 0)
        row.pack_end(layout_options, False, False, 0)
        box.pack_start(row, False, False, 0)

        if self.initial_values['view_mode'] == "tabs":
            self.tab_button.set_active(True)
        else:
            self.tile_button.set_active(True)

        self.show_all()

    def load_initial_values(self, config_file):
        stored_settings = configparser.SafeConfigParser({
            'kafka_servers': "",
            'topics': "",
            'polling_freq': "100",
            'max_history': "1000",
            'view_mode': "tabs"
        })
        stored_settings.read(config_file)
        self.initial_values = {
            "kafka_servers": stored_settings.get('samsa', 'kafka_servers'),
            "topics": stored_settings.get('samsa', 'topics'),
            "polling_freq": stored_settings.getint('samsa', 'polling_freq'),
            "max_history": stored_settings.getint('samsa', 'max_history'),
            "view_mode": stored_settings.get('samsa', 'view_mode')
        }

    def get_value(self):
        return {
            'kafka_servers': self.servers.get_buffer().get_text(),
            'topics': self.topics.get_buffer().get_text(),
            'polling_freq': self.freq.get_value_as_int(),
            'max_history': self.history.get_value_as_int(),
            'view_mode': 'tabs' if self.tab_button.get_active() else 'tiles'
        }
