# -*- coding: utf-8 -*-
#
# Copyright 2009-2010 Zuza Software Foundation
# Copyright 2016 F Wolff
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk
from gi.repository.GObject import SIGNAL_RUN_FIRST, TYPE_PYOBJECT

from virtaal.common import GObjectWrapper
from virtaal.views.widgets.cellrendererwidget import CellRendererWidget

__all__ = ['COL_ENABLED', 'COL_NAME', 'COL_DESC', 'COL_DATA', 'COL_WIDGET', 'SelectView']

COL_ENABLED, COL_NAME, COL_DESC, COL_DATA, COL_WIDGET = range(5)


# Coordinate and test this value with the size of PreferencesDlg in the glade
# file as well as the size of SelectDialog all over (e.g. TMView)
DEFAULT_WIDTH = 450


class SelectView(Gtk.TreeView, GObjectWrapper):
    """
    A tree view that enables the user to select items from a list.
    """

    __gtype_name__ = 'SelectView'
    __gsignals__ = {
        'item-enabled':  (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-disabled': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
        'item-selected': (SIGNAL_RUN_FIRST, None, (TYPE_PYOBJECT,)),
    }

    CONTENT_VBOX = 'vb_content'
    """The name of the C{Gtk.VBox} containing the selection items."""

    # INITIALIZERS #
    def __init__(self, items=None, bold_name=True):
        Gtk.TreeView.__init__(self)
        GObjectWrapper.__init__(self)

        self.bold_name = bold_name
        self.selected_item = None
        if not items:
            items = Gtk.ListStore(bool, str, str, TYPE_PYOBJECT, TYPE_PYOBJECT)
        self.set_model(items)

        self._add_columns()
        self._set_defaults()
        self._connect_events()

    def _add_columns(self):
        cell = Gtk.CellRendererToggle()
        cell.connect('toggled', self._on_item_toggled)
        self.select_col = Gtk.TreeViewColumn(_('Enabled'), cell, active=COL_ENABLED)
        self.append_column(self.select_col)

        width = self.get_allocation().width
        if width <= 1:
            width = DEFAULT_WIDTH

        cell = CellRendererWidget(
            strfunc=self._get_widget_string,
            default_width=width,
            widget_func=self._create_widget_for_item,
        )
        self.namedesc_col = Gtk.TreeViewColumn(_('Name'), cell, widget=4)
        self.append_column(self.namedesc_col)

    def _connect_events(self):
        self.get_selection().connect('changed', self._on_selection_change)

    def _set_defaults(self):
        self.set_rules_hint(True)
        self.props.activate_on_single_click = True
        self.props.enable_search = False


    # METHODS #
    def _create_widget_for_item(self, item):
        hbox = Gtk.HBox()
        vbox = Gtk.VBox()
        vbox.min_height = 60

        vbox.lbl_name = None
        if 'name' in item and item['name']:
            name = (self.bold_name and '<b>%s</b>' or '%s') % (item['name'])
            lbl = Gtk.Label()
            lbl.set_alignment(0, 0)
            lbl.set_text(name)
            lbl.set_use_markup(self.bold_name)
            lbl.set_property('xpad', 2)
            vbox.pack_start(lbl, True, True, 0)
            vbox.lbl_name = lbl

        vbox.lbl_desc = None
        if 'desc' in item and item['desc']:
            lbl = Gtk.Label()
            lbl.set_alignment(0, 0)
            lbl.set_line_wrap(True)
            lbl.set_text(item['desc'])
            lbl.set_use_markup(False)
            lbl.set_property('xpad', 2)
            if self.get_direction() == Gtk.TextDirection.LTR:
                # in RTL this code causes the label to be left aligned in the
                # column for some reason
                lbl.set_size_request(DEFAULT_WIDTH, -1)
            vbox.pack_start(lbl, True, True, 0)
            vbox.lbl_desc = lbl
        hbox.pack_start(vbox, True, True, 0)

        #TODO: ideally we need an accesskey, but it is not currently working
        if 'config' in item and callable(item['config']):
            btnconf = Gtk.Button(_('Configure...'))
            def clicked(button, event):
                item['config'](self.get_toplevel())
            btnconf.connect('button-release-event', clicked)
            btnconf.config_func = item['config']
            hbox.pack_start(btnconf, False, True, 0)

        return hbox

    def _get_widget_string(self, widget):
        s = ''
        widget = widget.get_children()[0]
        if widget.lbl_name:
            s = widget.lbl_name.get_label()
        if widget.lbl_desc:
            # avoid the import of xml.sax.saxutils.escape
            escaped = widget.lbl_desc.get_text().replace(u"&", u"&amp;").replace(u"<", u"&lt;") # & must be first
            s += '\n' + escaped
        return s

    def get_all_items(self):
        if not self._model:
            return None
        return [
            {
                'enabled': row[COL_ENABLED],
                'name':    row[COL_NAME],
                'desc':    row[COL_DESC],
                'data':    row[COL_DATA]
            } for row in self._model
        ]

    def get_item(self, iter):
        if not self._model:
            return None
        if not self._model.iter_is_valid(iter):
            return None

        config = None
        widget = self._model.get_value(iter, COL_WIDGET)
        try:
            if widget:
                widget = widget.get_children()[1]
                config = widget.config_func
        except IndexError:
            pass

        item = {
            'enabled': self._model.get_value(iter, COL_ENABLED),
            'name':    self._model.get_value(iter, COL_NAME),
            'desc':    self._model.get_value(iter, COL_DESC),
            'data':    self._model.get_value(iter, COL_DATA),
        }
        if config:
            item['config'] = config

        return item

    def get_selected_item(self):
        return self.selected_item

    def select_item(self, item):
        if item is None:
            self.get_selection().unselect_all()
            return
        found = False
        itr = self._model.get_iter_first()
        while itr is not None and self._model.iter_is_valid(itr):
            if self.get_item(itr) == item:
                found = True
                break
        if found and itr and self._model.iter_is_valid(itr):
            self.get_selection().select_iter(itr)
            self.selected_item = item
        else:
            self.selected_item = None

    def set_model(self, items):
        if isinstance(items, Gtk.ListStore):
            self._model = items
        else:
            self._model = Gtk.ListStore(bool, str, str, TYPE_PYOBJECT, TYPE_PYOBJECT)
            items = list(items)
            items.sort(key=lambda x: x.get('name', ''))
            for row in items:
                self._model.append([
                    row.get('enabled', False),
                    row.get('name', ''),
                    row.get('desc', ''),
                    row.get('data', None),
                    self._create_widget_for_item(row)
                ])

        super(SelectView, self).set_model(self._model)


    # EVENT HANDLERS #
    def _on_item_toggled(self, cellr, path):
        iter = self._model.get_iter(path)
        if not iter:
            return
        item_info = self.get_item(iter)
        item_info['enabled'] = not item_info['enabled']
        self._model.set_value(iter, COL_ENABLED, item_info['enabled'])

        if item_info['enabled']:
            self.emit('item-enabled', item_info)
        else:
            self.emit('item-disabled', item_info)

    def _on_selection_change(self, selection):
        model, iter = selection.get_selected()
        if iter and self._model.iter_is_valid(iter):
            self.selected_item = self.get_item(iter)
            path = model.get_path(iter)
            self.set_cursor(path, self.namedesc_col, start_editing=True)
            self.emit('item-selected', self.selected_item)

    def do_row_activated(self, path, column):
        self.set_cursor(path, self.namedesc_col, start_editing=True)
