"""Thread-safe pub/sub event bus.

Used to decouple cross-cutting concerns: services publish, screens and
other services subscribe. Compared to Kivy's Property dispatch, this is
a lighter alternative for arbitrary named events ("theme_changed",
"language_changed", "config_changed", "alarm_fired") without forcing
every consumer to be a Widget.
"""
from collections import defaultdict
from threading import RLock
from typing import Any, Callable

import logging

logger = logging.getLogger(__name__)

Callback = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callback]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event: str, callback: Callback) -> None:
        with self._lock:
            self._subs[event].append(callback)

    def unsubscribe(self, event: str, callback: Callback) -> None:
        with self._lock:
            if callback in self._subs[event]:
                self._subs[event].remove(callback)

    def publish(self, event: str, data: Any = None) -> None:
        # Snapshot under lock so callbacks can subscribe/unsubscribe safely.
        with self._lock:
            callbacks = list(self._subs[event])
        for cb in callbacks:
            try:
                cb(data)
            except Exception:
                logger.exception("EventBus callback error in '%s'", event)


event_bus = EventBus()
