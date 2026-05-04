"""
BaseScreen — common Screen base for all 6 Bedrock pages.

Owns:
- the per-screen overlay Image (via the <BaseScreen> KV rule in widgets.kv)
- a registry of Clock intervals scheduled in do_on_pre_enter, auto-cancelled
  in on_leave so navigating between screens doesn't leak timers
- a `page_key` property used by KV to look up the overlay image and theme
  bits

Subclasses override do_on_pre_enter / do_on_leave (not on_pre_enter / on_leave)
so the lifecycle bookkeeping always runs.
"""
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty


class BaseScreen(Screen):
    page_key = StringProperty("")
    _intervals = ListProperty([])

    def add_interval(self, fn, period):
        """Schedule a periodic callback that gets auto-cancelled on leave."""
        ev = Clock.schedule_interval(lambda dt: fn(), period)
        self._intervals.append(ev)
        return ev

    def schedule_once(self, fn, delay=0):
        """One-shot scheduled callback (not tracked — use Clock directly)."""
        return Clock.schedule_once(lambda dt: fn(), delay)

    def on_pre_enter(self, *args):
        # Defensive: cancel anything left over so a double on_pre_enter
        # without on_leave (rare but observed on Home) doesn't leak.
        self._cancel_all()
        self.do_on_pre_enter()

    def on_leave(self, *args):
        self._cancel_all()
        self.do_on_leave()

    # Subclass hooks — override these, not on_pre_enter / on_leave.
    def do_on_pre_enter(self):
        pass

    def do_on_leave(self):
        pass

    def _cancel_all(self):
        for ev in self._intervals:
            try:
                ev.cancel()
            except Exception:
                pass
        self._intervals = []

    def get_app(self):
        return App.get_running_app()
