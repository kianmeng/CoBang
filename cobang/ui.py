
from urllib.parse import urlunsplit
from urllib.parse import SplitResult as UrlSplitResult
from typing import Optional

import gi
from logbook import Logger
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('NM', '1.0')
gi.require_version('Gio', '2.0')

from gi.repository import Gtk, Gdk, NM, Gio

from .common import _
from .resources import get_ui_filepath
from .messages import WifiInfoMessage
from .net import is_connected_same_wifi, add_wifi_connection


logger = Logger(__name__)

BEST_HORIZONTAL_WIDTH = 914
BEST_VERTICAL_HEIGHT = 654


def build_app_menu_model() -> Gio.Menu:
    menu = Gio.Menu()
    menu.append('About', 'app.about')
    menu.append('Quit', 'app.quit')
    return menu


def update_progress(bar: Gtk.ProgressBar, jump: Optional[float] = None):
    # FIXME: Due to async operation, this function may be called after bar has been destroyed.
    if jump is None:
        f = bar.get_fraction()
        bar.set_fraction(f + 0.05)
    else:
        bar.set_fraction(jump)
    f = bar.get_fraction()
    if f >= 1:
        bar.set_visible(False)
        return False
    return True


def build_wifi_info_display(wifi: WifiInfoMessage, nm_client: Optional[NM.Client]) -> Gtk.Box:
    filepath = str(get_ui_filepath('wifi-display.glade'))
    builder = Gtk.Builder.new_from_file(filepath)
    box = builder.get_object('wifi-form')
    builder.get_object('ssid-value').set_text(wifi.ssid)
    if wifi.password:
        builder.get_object('password-value').set_text(wifi.password)
    btn: Gtk.Button = builder.get_object('btn-connect')
    if nm_client and is_connected_same_wifi(wifi, nm_client):
        logger.debug('Set sensitive for {}', btn)
        btn.set_sensitive(False)
        btn.set_label(_('Connected'))
    logger.debug('Connect handlers for Wifi UI')
    builder.get_object('password-value').connect('icon-press', on_secondary_icon_pressed)
    btn.connect_after('clicked', on_btn_connect_clicked, wifi, nm_client)
    return box


def on_secondary_icon_pressed(entry: Gtk.Entry, pos: Gtk.EntryIconPosition, event: Gdk.EventButton):
    visible = entry.get_visibility()
    entry.set_visibility(not visible)


def on_btn_connect_clicked(btn: Gtk.Button, wifi: WifiInfoMessage, nm_client: Optional[NM.Client]):
    add_wifi_connection(wifi, wifi_connect_done, btn, nm_client)


def build_url_display(url: UrlSplitResult):
    filepath = str(get_ui_filepath('url-display.glade'))
    builder = Gtk.Builder.new_from_file(filepath)
    box = builder.get_object('box')
    btn: Gtk.LinkButton = builder.get_object('btn-link')
    btn.set_label(url.netloc)
    btn.set_uri(urlunsplit(url))
    return box


def wifi_connect_done(client: NM.Client, res: Gio.AsyncResult, button: Gtk.Button):
    created = client.add_connection_finish(res)
    logger.debug('NetworkManager created connection: {}', created)
    if created:
        button.set_label(_('Saved'))
        button.set_sensitive(False)


def get_monitor_screen(window: Gtk.Window):
    display = window.get_display()
    logger.debug('Display: {}, {}', display, display.get_name())
    # FIXME: It returns wrong monitor
    monitor = display.get_monitor_at_window(window.get_window())
    geo = monitor.get_geometry()
    w, h = geo.width, geo.height
    logger.debug('Monitor size: {}', (w, h))
    return (w, h)


def resize_to_match_screen(window: Gtk.Window):
    '''Try to detect desktop or mobile screen, and resize to promote the horizontal or vertical layout.'''
    scale = window.get_scale_factor()
    best_horizontal_width = BEST_HORIZONTAL_WIDTH / scale
    best_vertical_height = BEST_VERTICAL_HEIGHT / scale
    sw, sh = get_monitor_screen(window)
    w, h = window.get_size()
    logger.debug('Current window size: {}', (w, h))
    if sw > best_horizontal_width:
        window.resize(best_horizontal_width, h)
    elif sh > best_vertical_height:
        window.resize(w, best_vertical_height)
