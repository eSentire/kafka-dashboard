import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


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
        _ = Gtk.Label(label)
        column.set_widget(_)
        _.show_all()
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
