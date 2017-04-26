# kafka-dashboard
Gtk dashboard for viewing Kafka topics


Before First Use
================

Dependencies
------------

    $ sudo apt install python3-pip python3-gi gir1.2-gtk-3.0


Before using Samsa for the first time, you will need to create a config file.
TODO: Configuration will be done through the UI in the next release. (High priority)

On Linux, the config file location is ~/.samsa.ini
On Windows, the config file location is (TBD).

Put the following contents in .samsa.ini:

    [samsa]
    kafka=host1,host2 (comma-separated list of kafka hosts)
    polling_freq=100 (how often in milliseconds to poll for new data)
    history=500 (how many records per topic to keep in memory)
    view=tiles (UI layout, 'tiles' or 'tabs')

configured appropriately for your use.


Usage
=====

Run '$ python3 samsa.py'

You will be prompted for a topic to subscribe to (a combo box will contain all
topics that currently exist and also allow free text entry).

If the view mode is set to 'tabs', a tab bar will appear down the left side of
the window with a tab for each topic. If the view mode is set to 'tiles', one
panel will appear for each topic.

New topics can be added using the "Add Topic" button in the header bar.

TODO: Removing topics is planned for the next release. (Medium priority)


Topic Panels
------------

Each topic is represented by a panel. The panel consists of three pieces:
- A 'Search' bar at the top which allows filtering of the stream. Messages are
  treated as one single string and the text is matched exactly.
- A list of messages. If the message content is valid JSON, it will be prettified.
  Right clicking on a message will allow you to copy it to the clipboard.
- A text input and "Send" button for putting messages on the stream. If a message
  is valid JSON (including double quotes on all keys) it will be normalized (extra
  whitespace and non-printing characters will be removed, etc.). Clicking on "Send"
  publishes the message to the stream.