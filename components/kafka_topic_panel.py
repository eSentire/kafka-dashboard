import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, Gdk
import kafka
import json
import time

from components import FilterableStringList


class KafkaTopicPanel(Gtk.Grid):
    def __init__(self, parent, topic):
        Gtk.Grid.__init__(self)

        self.parent = parent

        self.topic = topic
        self.kafka_producer = kafka.KafkaProducer(bootstrap_servers=self.parent.kafka_servers)

        self.searchbar = Gtk.Entry()
        self.searchbar.set_placeholder_text("Search")
        self.searchbar.set_icon_from_gicon(Gtk.EntryIconPosition.PRIMARY,
                                           Gio.ThemedIcon(name='search'))
        self.attach(self.searchbar, 0, 0, 4, 1)

        self.scrolledwindow = Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        self.attach(self.scrolledwindow, 0, 1, 4, 2)

        self.message_list = FilterableStringList(label="Messages on {}:".format(topic),
                                                 filter_by=self.searchbar)
        self.scrolledwindow.add(self.message_list)

        self.message_list.connect('size-allocate', self.on_treeview_changed)
        self.message_list.connect('button-release-event', self.on_treeview_button_press)

        self.send_input = Gtk.Entry()
        self.send_button = Gtk.Button("Send")
        self.send_input.connect('changed', self.on_input_changed)
        self.send_button.connect('clicked', self.on_send_clicked)
        self.attach(self.send_input, 0, 5, 3, 1)
        self.attach(self.send_button, 3, 5, 1, 1)
        self._lock = False
        self.popup = Gtk.Menu()
        self.copy_item = Gtk.MenuItem.new_with_label("Copy")
        self.copy_item.connect('activate', self.copy_to_clipboard)
        self.popup.add(self.copy_item)
        self.popup.show_all()

    def on_treeview_changed(self, widget, event, data=None):
        adj = self.scrolledwindow.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def append_message(self, message):
        """
        Process a new message.
        """
        try:
            # If the message is JSON, pretty-print it
            m = json.dumps(json.loads(message.value.decode('utf8')), indent=4)
        except ValueError:
            # If it's not JSON, just add it anyway
            m = message.value.decode('utf8')
        self.message_list.add_item(m, self.parent.config['max_history'])

    def on_send_clicked(self, *args, **kwargs):
        """
        Publish a message onto the queue.
        """
        texbuf = self.send_input.get_buffer()
        text = texbuf.get_text()
        resp = self.kafka_producer.send(self.topic, value=text.encode('utf8'))
        while not resp.succeeded():
            self.send_input.progress_pulse()
            time.sleep(0.1)
        self.send_input.set_progress_fraction(0)
        texbuf.set_text("", -1)

    def on_input_changed(self, widget, *args, **kwargs):
        if self._lock is False:
            # widget.props.text = text later will also trigger this
            # so we use a flag to prevent running this then.
            self._lock = True
            text = widget.props.text
            try:
                text = json.dumps(json.loads(text))
            except ValueError:
                pass
            widget.props.text = text
        self._lock = False

    def copy_to_clipboard(self, *args, **kwargs):
        model, iter = self.message_list.get_selection().get_selected()
        text = model[iter][0]
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)

    def on_treeview_button_press(self, widget, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = widget.get_path_at_pos(x, y)
            if pthinfo is not None:
                self.popup.popup(None, None, None, None, event.button, event.time)
