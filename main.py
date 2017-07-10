#!/usr/bin/env python3

import configparser
import gi
import json
import kafka
import os
import time
import uuid
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GObject, Gdk

KAFKA_GROUP = "kafka-dashboard-" + str(uuid.uuid4())


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        buttons = (Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, "Settings", parent, 0, buttons)

        # Load defaults from file for persistence
        self.load_initial_values()

        self.set_size_request(350, 0)

        box = self.get_content_area()

        row = Gtk.HBox()
        _ = Gtk.Label("Kafka Servers")
        row.pack_start(_, False, False, 0)
        self.servers = Gtk.Entry()
        self.servers.get_buffer().set_text(self.initial_values['kafka_servers'], -1)
        row.pack_end(self.servers, False, False, 0)
        box.pack_start(row, False, False, 0)

        # TODO: Gtk.Adjustment seems to default to the min half the time
        row = Gtk.HBox()
        _ = Gtk.Label("Polling Frequency")
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

    def load_initial_values(self):
        DEFAULTS = configparser.SafeConfigParser({
            'kafka_servers': "",
            'polling_freq': "100",
            'max_history': "1000",
            'view_mode': "tabs"
        })
        DEFAULTS.read(os.path.expanduser("~/.samsa.ini"))
        self.initial_values = {
            "kafka_servers": DEFAULTS.get('samsa', 'kafka_servers'),
            "polling_freq": DEFAULTS.getint('samsa', 'polling_freq'),
            "max_history": DEFAULTS.getint('samsa', 'max_history'),
            "view_mode": DEFAULTS.get('samsa', 'view_mode')
        }

    def get_value(self):
        return {
            'kafka_servers': self.servers.get_buffer().get_text(),
            'polling_freq': self.freq.get_value_as_int(),
            'max_history': self.history.get_value_as_int(),
            'view_mode': 'tabs' if self.tab_button.get_active() else 'tiles'
        }


class FilterableStringList(Gtk.TreeView):
    def __init__(self, label="Item", filter_by=None):
        self.model = Gtk.ListStore(str)
        self.filter = self.model.filter_new()
        if filter_by:
            self.filter_by = filter_by
            self.filter.set_visible_func(self._filter_func)
            self.filter_by.connect('changed', self._refresh_filter)
        Gtk.TreeView.__init__(self, self.filter)
        column = Gtk.TreeViewColumn(label, Gtk.CellRendererText(), text=0)
        self.append_column(column)

    def add_item(self, message, limit):
        """
        Append message to list, limited to a specified value.
        """
        self.model.append([message])
        # Clean up old messages if needed
        if len(self.model) > limit:
            self.model.remove(self.model.get_iter_first())

    def _refresh_filter(self, *args, **kwargs):
        self.filter.refilter()

    def _filter_func(self, model, iter, data):
        """
        Search messages for those which contain the text in the filter widget.
        """
        search_text = self.filter_by.get_buffer().get_text()
        if not search_text:
            return True
        return search_text in model[iter][0]


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


class PickTopicDialog(Gtk.Dialog):
    def __init__(self, parent):
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                   Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, "Topic", parent, 0, buttons)

        self.set_default_size(150, 100)
        self.combo = Gtk.ComboBoxText.new_with_entry()
        for topic in sorted(parent.kafka_consumer.topics()):
            self.combo.append_text(topic)
        box = self.get_content_area()
        box.add(self.combo)
        self.show_all()

    def get_value(self):
        return self.combo.get_active_text()


class SamsaWindow(Gtk.Window):
    def __init__(self, config):
        Gtk.Window.__init__(self)
        self.connect('destroy', self.on_destroy)
        self.config = config

        self.kafka_servers = [
            k.strip()
            for k in self.config['kafka_servers'].split(',')
        ]

        self.kafka_consumer = kafka.KafkaConsumer(bootstrap_servers=self.kafka_servers,
                                                  group_id=KAFKA_GROUP,
                                                  enable_auto_commit=True)

        self.pages = {}
        self.tabs = {}

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "Kafka Dashboard"
        self.set_titlebar(hb)

        newButton = Gtk.Button()
        image = Gtk.Image.new_from_gicon(Gio.ThemedIcon(name="gtk-add"),
                                         Gtk.IconSize.BUTTON)
        box = Gtk.HBox()
        box.add(image)
        box.add(Gtk.Label("Add Topic"))
        newButton.add(box)
        newButton.connect('clicked', self.on_add_clicked)
        hb.pack_end(newButton)

        self.set_default_size(800, 600)
        if self.config['view_mode'] == 'tabs':
            self.topic_panel_container = Gtk.Notebook()
            self.topic_panel_container.set_tab_pos(Gtk.PositionType.LEFT)
            self.topic_panel_container.connect('switch-page', self.on_switch_page)
        elif self.config['view_mode'] == 'tiles':
            self.topic_panel_container = Gtk.HBox()

        self.add(self.topic_panel_container)

        GObject.timeout_add(self.config['polling_freq'], self.update)
        self.show_all()

    def add_page(self, topic):
        """
        Create a new page.
        """
        page = KafkaTopicPanel(self, topic)
        label_box = Gtk.HBox()
        label = Gtk.Label(topic)
        close_button = Gtk.Button.new_with_label("x")
        close_button.connect('clicked', lambda b: self.remove_page(topic))
        label_box.pack_start(label, False, False, 0)
        label_box.pack_end(close_button, False, False, 0)
        if self.config['view_mode'] == 'tabs':
            self.topic_panel_container.append_page(page, label_box)
            self.topic_panel_container.set_current_page(-1)
            self.pages[topic] = page
        elif self.config['view_mode'] == 'tiles':
            vbox = Gtk.VBox()
            vbox.pack_start(label_box, False, False, 0)
            vbox.pack_start(page, True, True, 0)
            vbox.show_all()
            self.topic_panel_container.pack_start(vbox, True, True, 5)
            self.pages[topic] = vbox
        page.show_all()
        self.tabs[topic] = label_box
        label_box.show_all()
        self.kafka_consumer.subscribe(self.pages.keys())

    def remove_page(self, topic):
        print("Removing page for", topic)
        self.topic_panel_container.remove(self.pages[topic])
        del self.pages[topic]
        if self.pages.keys():
            self.kafka_consumer.subscribe(self.pages.keys())
        else:
            self.kafka_consumer.unsubscribe()

    def on_switch_page(self, notebook, page, page_num, *args, **kwargs):
        """
        Clear the bold markup if present when switching to a tab.
        """
        tab_box = notebook.get_tab_label(page)
        label = tab_box.get_children()[0]
        label.set_markup(label.get_text())

    def on_add_clicked(self, *args, **kwargs):
        """
        Prompt the user for a new topic and add a page for it.
        """
        dialog = PickTopicDialog(self)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            topic = dialog.get_value()
            if topic:
                self.add_page(topic)
        dialog.destroy()

    def on_destroy(self, *args, **kwargs):
        """
        Close and clean up.
        """
        print("Closing")
        self.kafka_consumer.close()
        Gtk.main_quit()

    def update(self):
        """
        Check for new messages and distribute them to their
        appropriate pages.
        """
        response = self.kafka_consumer.poll()
        updated_topics = set(map(lambda x: x.topic, response.keys()))
        for topic in self.tabs.keys():
            self.set_urgency_hint(True)
            if topic in updated_topics:
                self.tabs[topic].get_children()[0].set_markup("<b>{}</b>".format(topic))
        for messages in response.values():
            for message in messages:
                self.pages[message.topic].append_message(message)
        return True


if __name__ == '__main__':
    dialog = SettingsDialog(None)
    response = dialog.run()
    config = {}
    if response == Gtk.ResponseType.OK:
        config = dialog.get_value()
        DEFAULTS = configparser.ConfigParser()
        DEFAULTS.add_section("samsa")
        for k, v in config.items():
            DEFAULTS.set('samsa', k, str(v))
        print("Writing config")
        with open(os.path.expanduser("~/.samsa.ini"), 'w') as f:
            DEFAULTS.write(f)
        print("Written")
    else:
        Gtk.main_quit()
    dialog.destroy()
    if config.get('kafka_servers'):
        win = SamsaWindow(config)
        Gtk.main()
