import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')
from gi.repository import Gtk, Gio, Gdk, GtkSource
import kafka
import json
import time

from components import FilterableStringList


class KafkaTopicPanel(Gtk.VBox):
    def __init__(self, parent, topic):
        Gtk.VBox.__init__(self)

        self.parent = parent

        self.topic = topic
        self.kafka_producer = kafka.KafkaProducer(bootstrap_servers=self.parent.kafka_servers)

        self.top_bar = Gtk.HBox()
        self.searchbar = Gtk.Entry()
        self.searchbar.set_placeholder_text("Search")
        self.searchbar.set_icon_from_gicon(Gtk.EntryIconPosition.PRIMARY,
                                           Gio.ThemedIcon(name='search'))
        self.top_bar.pack_start(self.searchbar, True, True, 0)

        self.save_button = Gtk.Button("Save")
        self.save_button.connect('clicked', self.on_save_clicked)
        self.top_bar.pack_start(self.save_button, False, False, 0)

        self.pack_start(self.top_bar, False, False, 0)

        self.scrolledwindow = Gtk.ScrolledWindow()
        self.scrolledwindow.set_hexpand(True)
        self.scrolledwindow.set_vexpand(True)
        self.pack_start(self.scrolledwindow, True, True, 5)

        self.message_list = FilterableStringList(label="Messages on {}:".format(topic),
                                                 filter_by=self.searchbar)
        self.scrolledwindow.add(self.message_list)

        self.message_list.connect('size-allocate', self.on_treeview_changed)
        self.message_list.connect('button-release-event', self.on_treeview_button_press)

        self.send_bar = Gtk.HBox()
        self.send_input = GtkSource.View()
        language_manager = GtkSource.LanguageManager()
        json_lang = language_manager.get_language("json")
        self.send_input.get_buffer().set_language(json_lang)

        self.send_input.set_auto_indent(True)
        self.send_input.set_highlight_current_line(True)
        self.send_input.set_indent_on_tab(True)

        self.send_button = Gtk.Button("Send")
        self.send_button.connect('clicked', self.on_send_clicked)
        self.send_bar.pack_start(self.send_input, True, True, 0)
        self.send_bar.pack_start(self.send_button, False, False, 0)

        frame = Gtk.Frame()
        frame.add(self.send_bar)
        self.pack_end(frame, False, False, 0)

        self.popup = Gtk.Menu()
        self.copy_item = Gtk.MenuItem.new_with_label("Copy")
        self.copy_item.connect('activate', self.copy_to_clipboard)
        self.popup.add(self.copy_item)
        self.popup.show_all()

    def on_save_clicked(self, *args, **kwargs):
        _ = Gtk.Window()
        dialog = Gtk.FileChooserDialog("Destination", _,
                                       Gtk.FileChooserAction.SAVE,
                                       (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        dialog.set_current_name(self.topic)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            print("Saving file", filename)
            with open(filename, 'w') as f:
                for row in self.message_list:
                    f.write(json.dumps(json.loads(row[0])) + "\n")
        _.destroy()
        dialog.destroy()

    def on_treeview_changed(self, widget, event, data=None):
        adj = self.scrolledwindow.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def append_message(self, message):
        """
        Process a new message.
        """
        try:
            # If the message is JSON, pretty-print it
            m = json.dumps(json.loads(message.value.decode('utf8')), indent=4, sort_keys=True)
        except ValueError:
            # If it's not JSON, just add it anyway
            m = message.value.decode('utf8')
        self.message_list.add_item(m, self.parent.config['max_history'])

    def on_send_clicked(self, *args, **kwargs):
        """
        Publish a message onto the queue.
        """

        def get_text(buffer):
            start = buffer.get_start_iter()
            end = buffer.get_end_iter()
            return buffer.get_text(start, end, False)

        texbuf = self.send_input.get_buffer()
        text = get_text(texbuf)
        try:
            json.loads(text)
        except:
            print("Invalid JSON")
            return
        else:
            resp = self.kafka_producer.send(self.topic, value=text.encode('utf8'))
            while not resp.succeeded():
                time.sleep(0.1)
            texbuf.set_text("", -1)

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
