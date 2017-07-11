#!/usr/bin/env python3

import configparser
import gi
import kafka
import os
import uuid
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GObject

from components import SettingsDialog, KafkaTopicPanel, KafkaPanelHeader

KAFKA_GROUP = "kafka-dashboard-" + str(uuid.uuid4())

CONFIG_FILE = os.path.expanduser("~/.samsa.ini")

# Create config file if not exists
if not os.path.exists(CONFIG_FILE):
    t = configparser.ConfigParser()
    t.add_section("samsa")
    with open(CONFIG_FILE, 'w') as f:
        t.write(f)


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


class RebalanceHandler(kafka.consumer.subscription_state.ConsumerRebalanceListener):

    def __init__(self, application):
        self.application = application

    def on_partitions_revoked(self, revoked):
        pass

    def on_partitions_assigned(self, assigned):
        for topic in self.application.paused_topics:
            self.application.pause(topic)


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
        hb.props.title = "Kafka Dashboard: " + self.config['kafka_servers']
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

        if config['topics']:
            for topic in config['topics'].split(","):
                self.add_page(topic)

        self.paused_topics = set()

        GObject.timeout_add(self.config['polling_freq'], self.update)
        self.show_all()

    def add_page(self, topic):
        """
        Create a new page.
        """
        topic = topic.strip()
        page = KafkaTopicPanel(self, topic)

        header = KafkaPanelHeader(topic,
                                  close=lambda b: self.remove_page(topic),
                                  pause=lambda b: self.pause(topic),
                                  resume=lambda b: self.resume(topic))

        # TODO: This should be abstracted a little further so that
        # I'm always adding something with the same interface to self.pages
        # Currently there's some hackery in the update function

        if self.config['view_mode'] == 'tabs':
            self.topic_panel_container.append_page(page, header)
            self.topic_panel_container.set_current_page(-1)
            self.pages[topic] = page
        elif self.config['view_mode'] == 'tiles':
            vbox = Gtk.VBox()
            vbox.pack_start(header, False, False, 0)
            vbox.pack_start(page, True, True, 0)
            vbox.show_all()
            self.topic_panel_container.pack_start(vbox, True, True, 5)
            self.pages[topic] = vbox
        page.show_all()
        self.tabs[topic] = header
        self.kafka_consumer.subscribe(self.pages.keys(), listener=RebalanceHandler(self))

    def remove_page(self, topic):
        self.topic_panel_container.remove(self.pages[topic])
        del self.pages[topic]
        if self.pages.keys():
            self.kafka_consumer.subscribe(self.pages.keys(), listener=RebalanceHandler(self))
        else:
            self.kafka_consumer.unsubscribe()

    def pause(self, topic):
        self.paused_topics.add(topic)
        partitions = self.kafka_consumer.partitions_for_topic(topic)
        assigned_partitions = self.kafka_consumer.assignment()
        to_pause = [p for p in assigned_partitions if p.topic == topic and p.partition in partitions]
        self.kafka_consumer.pause(*to_pause)
        self.tabs[topic].set_paused(True)

    def resume(self, topic):
        self.paused_topics.remove(topic)
        paused = self.kafka_consumer.paused()
        to_resume = [p for p in paused if p.topic == topic]
        self.kafka_consumer.resume(*to_resume)
        self.tabs[topic].set_paused(False)

    def on_switch_page(self, notebook, page, page_num, *args, **kwargs):
        """
        Clear the bold markup if present when switching to a tab.
        """
        tab_box = notebook.get_tab_label(page)
        label = tab_box.get_children()[1]
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
                self.tabs[topic].get_children()[1].set_markup("<b>{}</b>".format(topic))
        for messages in response.values():
            for message in messages:
                page = self.pages[message.topic]
                if isinstance(page, KafkaTopicPanel):
                    self.pages[message.topic].append_message(message)
                else:
                    page.get_children()[1].append_message(message)
        return True


if __name__ == '__main__':
    _ = Gtk.Window()
    dialog = SettingsDialog(_, CONFIG_FILE)
    response = dialog.run()
    config = {}
    if response == Gtk.ResponseType.OK:
        config = dialog.get_value()
        DEFAULTS = configparser.ConfigParser()
        DEFAULTS.add_section("samsa")
        for k, v in config.items():
            DEFAULTS.set('samsa', k, str(v))
        with open(os.path.expanduser(CONFIG_FILE), 'w') as f:
            DEFAULTS.write(f)
    dialog.destroy()
    _.destroy()
    if config.get('kafka_servers'):
        win = SamsaWindow(config)
        Gtk.main()
