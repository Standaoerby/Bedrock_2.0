import pytest
import os
import json

from services.alarm_service import AlarmService
from services.schedule_service import ScheduleService
from services.notifications_service import NotificationService

def test_alarm_service(tmp_path):
    path = tmp_path / "alarm.json"
    service = AlarmService(str(path))
    assert service.alarms == []
    service.add_alarm({
        "time": "06:00",
        "enabled": True,
        "repeat": [1,2,3],
        "label": "Test"
    })
    assert len(service.alarms) == 1
    assert service.alarms[0]["time"] == "06:00"
    service.remove_alarm(0)
    assert service.alarms == []

def test_schedule_service(tmp_path):
    path = tmp_path / "schedule.json"
    service = ScheduleService(str(path))
    assert isinstance(service.schedule, dict)
    service.add_lesson(1, {"start": "08:00", "subject": "Math", "type": "0"})
    assert service.schedule["1"][0]["subject"] == "Math"

def test_notifications_service(tmp_path):
    path = tmp_path / "notifications.json"
    service = NotificationService(str(path))
    service.add("Test message", "школьный")
    assert len(service.notifications) == 1
    assert service.notifications[0]["text"] == "Test message"
    service.mark_as_read(0)
    assert service.notifications[0]["read"]

# Для запуска UI автотеста лучше использовать инструменты типа Selenium/Appium,
# но базовый тест работы сервисов для CI/CD выглядит вот так.

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))
