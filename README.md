# kafka-dashboard
Gtk dashboard for viewing Kafka topics


Before First Use
================

Dependencies
------------

    $ sudo apt install python3-pip python3-gi gir1.2-gtk-3.0 gir1.2-gtksource-3.0
    $ pip3 install --user -r requirements.txt

(Note: Pip packages are installed globally in the above example. If you want to install in a
virtualenv, you'll need to make sure that your site-packages are included in the virtualenv's
path for GTK.)


Usage
=====

Run '$ python3 main.py'

You will be prompted for the settings the app needs in order to connect.
Specifically:
- Kafka servers: a comma-separated list of bootstrap servers for your Kafka cluster
- Polling frequency: how often to poll for new messages
- Max history: the number of records to keep in memory for display/searching (per topic)
- Layout: If the layout is set to 'tabs', a tab bar will appear down the left side of the 
          window with a tab for each topic. If the view mode is set to 'tiles', one panel
          will appear for each topic.

New topics can be added using the "Add Topic" button in the header bar.



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
