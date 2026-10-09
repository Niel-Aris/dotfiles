#!/usr/bin/env python3
"""Pomodoro daemon + popup window (GTK4 / libadwaita).

Runs as a single instance. `pomodoro toggle` (SUPER + P) shows/hides the window;
closing the window only hides it, the timer keeps running in the background.
"""
import math
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

import store  # noqa: E402

APP_ID = "org.lynx.Pomodoro"
SOUND = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"

CSS = b"""
.time-label { font-size: 54px; font-weight: 200; font-feature-settings: "tnum"; }
.phase-label { font-size: 11px; font-weight: 700; letter-spacing: 2px; opacity: .65; }
.dots { letter-spacing: 5px; opacity: .85; }
.msg { opacity: .8; }
.stat-value { font-size: 15px; font-weight: 700; }
.stat-cap { font-size: 9px; font-weight: 700; letter-spacing: 1.5px; opacity: .55; }
.stat-card { padding: 10px 4px; }
"""


# --------------------------------------------------------------------------- engine
class Engine:
    """Timer state machine. No GUI code in here."""

    def __init__(self, cfg, on_change, on_finish):
        self.cfg = cfg
        self.on_change = on_change
        self.on_finish = on_finish
        self.phase = "idle"  # idle | work | break
        self.running = False
        self.finished = False
        self.planned = 0.0
        self.remaining = 0.0
        self.end = 0.0
        self.seg_start = None
        self.is_ext = False
        self.break_kind = "short"
        self.tag = None
        self.done = 0  # focus sessions completed in the current cycle

    # -- helpers
    def left(self):
        return max(0.0, self.end - time.monotonic()) if self.running else self.remaining

    def _begin(self, phase, seconds):
        self.phase = phase
        self.planned = self.remaining = float(seconds)
        self.finished = False
        self.seg_start = datetime.now()
        self.resume(notify=False)
        self.on_change()

    def _log(self):
        if self.phase == "work" and self.seg_start:
            elapsed = self.planned - self.left()
            if elapsed >= 5:
                store.log_session(self.tag, self.seg_start, datetime.now(), elapsed, self.is_ext)
        self.seg_start = None

    def _finish(self):
        self.remaining = 0.0
        self.running = False
        self.finished = True
        if self.phase == "work":
            self._log()
            if not self.is_ext:
                self.done += 1
        self.on_finish()
        self.on_change()

    # -- actions
    def start_work(self, tag):
        self.tag, self.is_ext = tag, False
        self._begin("work", self.cfg["work_min"] * 60)

    def start_break(self):
        long = self.done >= self.cfg["sessions_before_long"]
        self.break_kind = "long" if long else "short"
        if long:
            self.done = 0
        self._begin("break", self.cfg["long_break_min" if long else "short_break_min"] * 60)

    def extend(self):
        self.is_ext = self.phase == "work"
        self._begin(self.phase, self.cfg["extend_min"] * 60)

    def pause(self):
        self.remaining = self.left()
        self.running = False
        self.on_change()

    def resume(self, notify=True):
        self.end = time.monotonic() + self.remaining
        self.running = True
        if notify:
            self.on_change()

    def stop(self):
        """Abort / dismiss. Partial focus time is still recorded."""
        if self.phase == "work" and not self.finished:
            self.pause()
            self._log()
        self.phase, self.running, self.finished = "idle", False, False
        self.remaining = self.planned = 0.0
        self.on_change()

    def tick(self):
        if self.running and self.left() <= 0:
            self._finish()


# --------------------------------------------------------------------------- window
class PomodoroWindow(Adw.ApplicationWindow):
    def __init__(self, app, engine):
        super().__init__(application=app, title="Pomodoro", resizable=False)
        self.set_default_size(360, 600)
        self.engine = engine
        self.cfg = engine.cfg
        self.tick_id = 0
        self.connect("close-request", lambda w: (w.set_visible(False), True)[1])

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.settings_btn = Gtk.ToggleButton(icon_name="emblem-system-symbolic", tooltip_text="Settings")
        self.settings_btn.connect("toggled", self._on_settings_toggled)
        header.pack_end(self.settings_btn)
        self.title_widget = Adw.WindowTitle(title="Pomodoro", subtitle="")
        header.set_title_widget(self.title_widget)
        view.add_top_bar(header)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(self._build_timer_page(), "timer")
        self.stack.add_named(self._build_settings_page(), "settings")
        view.set_content(self.stack)
        self.set_content(view)
        self.refresh()

    # -- timer page
    def _build_timer_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        for side in ("start", "end"):
            getattr(page, f"set_margin_{side}")(22)
        page.set_margin_top(8)
        page.set_margin_bottom(20)

        # tag selector
        row = Gtk.Box(spacing=8)
        self.tag_model = Gtk.StringList.new(store.list_tags())
        self.dropdown = Gtk.DropDown(model=self.tag_model, hexpand=True, tooltip_text="Type of work")
        last = self.cfg.get("last_tag")
        for i, t in enumerate(self.tag_model):
            if t.get_string() == last:
                self.dropdown.set_selected(i)
        self.dropdown.connect("notify::selected", self._on_tag_changed)
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="New type of work")
        add.add_css_class("circular")
        add.connect("clicked", self._on_add_tag)
        self.add_btn = add
        row.append(self.dropdown)
        row.append(add)
        page.append(row)

        # ring + time
        overlay = Gtk.Overlay(vexpand=True)
        self.ring = Gtk.DrawingArea(content_width=250, content_height=250, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.ring.set_draw_func(self._draw_ring)
        overlay.set_child(self.ring)
        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, spacing=2)
        self.time_label = Gtk.Label(css_classes=["time-label"])
        self.phase_label = Gtk.Label(css_classes=["phase-label"])
        self.dots_label = Gtk.Label(css_classes=["dots"], margin_top=6)
        for w in (self.time_label, self.phase_label, self.dots_label):
            center.append(w)
        overlay.add_overlay(center)
        page.append(overlay)

        self.msg_label = Gtk.Label(css_classes=["msg"], wrap=True, justify=Gtk.Justification.CENTER)
        page.append(self.msg_label)

        self.buttons = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER, homogeneous=False)
        page.append(self.buttons)

        # stats for the selected tag
        stats = Gtk.Box(spacing=8, homogeneous=True, margin_top=6)
        self.stat_values = {}
        for key, cap in (("week", "THIS WEEK"), ("month", "THIS MONTH"), ("year", "THIS YEAR")):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, css_classes=["card", "stat-card"])
            val = Gtk.Label(label="0h 00m", css_classes=["stat-value"])
            card.append(val)
            card.append(Gtk.Label(label=cap, css_classes=["stat-cap"]))
            self.stat_values[key] = val
            stats.append(card)
        page.append(stats)
        return page

    # -- settings page
    def _build_settings_page(self):
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title="Timer", description="Applies to the next session you start.")
        spins = (
            ("work_min", "Focus (minutes)", 1, 180),
            ("short_break_min", "Short break (minutes)", 1, 60),
            ("long_break_min", "Long break (minutes)", 1, 120),
            ("sessions_before_long", "Sessions before long break", 1, 12),
            ("extend_min", "Extend by (minutes)", 1, 60),
        )
        for key, title, lo, hi in spins:
            r = Adw.SpinRow.new_with_range(lo, hi, 1)
            r.set_title(title)
            r.set_value(self.cfg[key])
            r.connect("notify::value", self._on_spin, key)
            group.add(r)
        sound = Adw.SwitchRow(title="Play sound when a timer ends", active=self.cfg["sound"])
        sound.connect("notify::active", lambda r, _p: self._set_cfg("sound", r.get_active()))
        group.add(sound)
        page.add(group)

        data = Adw.PreferencesGroup(title="History")
        folder = Adw.ActionRow(title="Open history folder", subtitle=str(store.DATA_DIR), activatable=True)
        folder.add_suffix(Gtk.Image(icon_name="folder-open-symbolic"))
        folder.connect("activated", lambda _r: subprocess.Popen(["xdg-open", str(store.DATA_DIR)]))
        data.add(folder)
        page.add(data)
        return page

    # -- callbacks
    def _on_key(self, _ctl, keyval, _code, _state):
        if keyval == Gdk.KEY_Escape:
            if self.settings_btn.get_active():
                self.settings_btn.set_active(False)
            else:
                self.set_visible(False)
            return True
        return False

    def _set_cfg(self, key, value):
        self.cfg[key] = value
        store.save_config(self.cfg)
        self.refresh()

    def _on_spin(self, row, _p, key):
        self._set_cfg(key, int(row.get_value()))

    def _on_settings_toggled(self, btn):
        self.stack.set_visible_child_name("settings" if btn.get_active() else "timer")
        self.title_widget.set_title("Settings" if btn.get_active() else "Pomodoro")

    def current_tag(self):
        item = self.dropdown.get_selected_item()
        return item.get_string() if item else "General"

    def _on_tag_changed(self, *_):
        self._set_cfg("last_tag", self.current_tag())
        self.refresh_stats()

    def _on_add_tag(self, _btn):
        entry = Gtk.Entry(placeholder_text="e.g. Coding, Reading, Design", activates_default=True)
        dialog = Adw.AlertDialog(heading="New type of work", body="A folder with this name is created in your Pomodoro history.")
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("add")
        dialog.set_close_response("cancel")

        def done(_d, response):
            if response != "add":
                return
            name = store.add_tag(entry.get_text())
            if not name:
                return
            tags = store.list_tags()
            self.tag_model.splice(0, self.tag_model.get_n_items(), tags)
            self.dropdown.set_selected(tags.index(name))

        dialog.connect("response", done)
        dialog.present(self)
        entry.grab_focus()

    # -- drawing
    def _draw_ring(self, _area, cr, w, h):
        e = self.engine
        fg = self.get_color()
        accent = Adw.StyleManager.get_default().get_accent_color_rgba()
        color = (0.35, 0.78, 0.52) if e.phase == "break" else (accent.red, accent.green, accent.blue)
        cx, cy, r, lw = w / 2, h / 2, min(w, h) / 2 - 12, 12
        cr.set_line_width(lw)
        cr.set_line_cap(1)  # round
        cr.set_source_rgba(fg.red, fg.green, fg.blue, 0.12)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        if e.phase != "idle" and e.planned > 0:
            frac = e.left() / e.planned
            if frac > 0:
                a = 0.45 if (e.phase != "idle" and not e.running and not e.finished) else 1.0
                cr.set_source_rgba(*color, a)
                start = -math.pi / 2
                cr.arc(cx, cy, r, start, start + 2 * math.pi * frac)
                cr.stroke()

    # -- state -> widgets
    def refresh_stats(self):
        t = store.totals(self.current_tag())
        for key, lbl in self.stat_values.items():
            lbl.set_label(store.fmt_hm(t[key][0]))

    def update_time(self):
        e = self.engine
        secs = e.left() if e.phase != "idle" else self.cfg["work_min"] * 60
        text = f"{int(math.ceil(secs)) // 60:02d}:{int(math.ceil(secs)) % 60:02d}"
        self.time_label.set_label(text)
        self.ring.queue_draw()
        if e.phase == "idle":
            self.set_title("Pomodoro")
        else:
            self.set_title(f"{text} · Pomodoro")
        self.title_widget.set_subtitle("" if self.settings_btn.get_active() else (e.tag if e.phase == "work" else ""))

    def _button(self, label, cb, kind=None):
        b = Gtk.Button(label=label)
        b.add_css_class("pill")
        if kind:
            b.add_css_class(kind)
        b.connect("clicked", lambda _b: cb())
        self.buttons.append(b)

    def refresh(self):
        e = self.engine
        cfg = self.cfg
        while (child := self.buttons.get_first_child()) is not None:
            self.buttons.remove(child)

        self.dropdown.set_sensitive(e.phase == "idle")
        self.add_btn.set_sensitive(e.phase == "idle")

        ext = f"+{cfg['extend_min']} min"
        if e.phase == "idle":
            phase, msg = "READY", ""
            self._button("Start", lambda: e.start_work(self.current_tag()), "suggested-action")
        elif e.finished and e.phase == "work":
            phase, msg = "TIME'S UP", "Nice work! Take a break, or keep going."
            nxt = "long" if e.done >= cfg["sessions_before_long"] else "short"
            self._button(f"Start {nxt} break", e.start_break, "suggested-action")
            self._button(ext, e.extend)
            self._button("Done", e.stop)
        elif e.finished:
            phase, msg = "BREAK OVER", "Ready for the next round?"
            self._button("Start focus", lambda: e.start_work(self.current_tag()), "suggested-action")
            self._button(ext, e.extend)
            self._button("Done", e.stop)
        else:
            if e.phase == "work":
                phase, msg = "FOCUS", ""
            else:
                phase, msg = f"{e.break_kind.upper()} BREAK", "Step away from the screen."
            if not e.running:
                phase += " · PAUSED"
            self._button("Pause" if e.running else "Resume", e.pause if e.running else e.resume, "suggested-action")
            self._button("Stop" if e.phase == "work" else "Skip", e.stop)

        self.phase_label.set_label(phase)
        self.msg_label.set_label(msg)
        n = cfg["sessions_before_long"]
        filled = min(e.done, n)
        self.dots_label.set_label("●" * filled + "○" * (n - filled))
        self.update_time()
        self.refresh_stats()

        if e.running and not self.tick_id:
            self.tick_id = GLib.timeout_add(250, self._on_tick)

    def _on_tick(self):
        self.engine.tick()
        self.update_time()
        if not self.engine.running:
            self.tick_id = 0
            return False
        return True


# --------------------------------------------------------------------------- app
class PomodoroApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None
        self.engine = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.hold()  # keep running with no visible window
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.engine = Engine(store.load_config(), lambda: self.win and self.win.refresh(), self._on_finish)
        self.win = PomodoroWindow(self, self.engine)
        try:
            from gi.repository import GLibUnix
            GLibUnix.signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._sigterm)
        except ImportError:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._sigterm)

    def _sigterm(self):
        self.quit()
        return GLib.SOURCE_REMOVE

    def do_shutdown(self):
        if self.engine:
            self.engine.stop()  # records partial focus time
        Adw.Application.do_shutdown(self)

    def do_command_line(self, cmdline):
        args = cmdline.get_arguments()[1:]
        cmd = args[0] if args else "toggle"
        if cmd == "toggle":
            if self.win.is_visible() and self.win.is_active():
                self.win.set_visible(False)
            else:
                self._show()
        elif cmd == "show":
            self._show()
        elif cmd == "hide":
            self.win.set_visible(False)
        elif cmd == "quit":
            self.quit()
        return 0  # "daemon": just stay resident

    def _show(self):
        self.win.refresh()
        self.win.present()

    def _on_finish(self):
        e = self.engine
        if e.phase == "work":
            title, body = "Focus session complete", f"{e.tag}: time for a break, or extend the session."
        else:
            title, body = "Break is over", "Ready to start the next focus session?"
        subprocess.Popen(["notify-send", "-a", "Pomodoro", "-i", "alarm-symbolic", title, body])
        if e.cfg["sound"] and os.path.exists(SOUND):
            subprocess.Popen(["pw-play", SOUND], stderr=subprocess.DEVNULL)
        self._show()


if __name__ == "__main__":
    sys.exit(PomodoroApp().run(["pomodoro"] + sys.argv[1:]))
