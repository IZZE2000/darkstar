"""
Tests for REV K25 Phase 3: EV Departure Deadline Calculation
"""

from datetime import datetime

from pytz import timezone as pytz_timezone

from planner.pipeline import calculate_ev_deadline


class TestEVDeadlineCalculation:
    """Test the calculate_ev_deadline function."""

    def test_departure_tomorrow_when_current_time_after(self):
        """Test: now=15:00, departure=07:00 -> deadline is tomorrow 07:00"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 15, 0, 0))  # 15:00 today

        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.hour == 7
        assert deadline.minute == 0
        assert deadline.day == 16  # Tomorrow

    def test_departure_today_when_current_time_before(self):
        """Test: now=06:00, departure=07:00 -> deadline is today 07:00"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 6, 0, 0))  # 06:00 today

        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.hour == 7
        assert deadline.minute == 0
        assert deadline.day == 15  # Today

    def test_departure_tomorrow_for_next_day_when_passed(self):
        """Test: now=09:00, departure=07:00 -> deadline is tomorrow 07:00"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 9, 0, 0))  # 09:00 today (after 07:00)

        deadline = calculate_ev_deadline("07:00", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.hour == 7
        assert deadline.minute == 0
        assert deadline.day == 16  # Tomorrow (for next day's departure)

    def test_late_night_departure_same_day(self):
        """Test: now=20:00, departure=23:30 -> deadline is today 23:30"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 20, 0, 0))  # 20:00

        deadline = calculate_ev_deadline("23:30", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.hour == 23
        assert deadline.minute == 30
        assert deadline.day == 15  # Today

    def test_midnight_departure(self):
        """Test: now=23:00, departure=00:00 -> deadline is tomorrow 00:00"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 23, 0, 0))  # 23:00

        deadline = calculate_ev_deadline("00:00", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.hour == 0
        assert deadline.minute == 0
        assert deadline.day == 16  # Tomorrow

    def test_empty_departure_time_returns_none(self):
        """Test: empty string returns None"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline = calculate_ev_deadline("", now, "Europe/Stockholm")

        assert deadline is None

    def test_invalid_departure_time_returns_none(self):
        """Test: invalid time format returns None"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline = calculate_ev_deadline("invalid", now, "Europe/Stockholm")

        assert deadline is None

    def test_invalid_hour_returns_none(self):
        """Test: hour > 23 returns None"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline = calculate_ev_deadline("25:00", now, "Europe/Stockholm")

        assert deadline is None

    def test_invalid_minute_returns_none(self):
        """Test: minute > 59 returns None"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline = calculate_ev_deadline("12:60", now, "Europe/Stockholm")

        assert deadline is None

    def test_naive_datetime_gets_localized(self):
        """Test: naive datetime gets localized to timezone"""
        now = datetime(2024, 1, 15, 12, 0, 0)  # Naive

        deadline = calculate_ev_deadline("15:00", now, "Europe/Stockholm")

        assert deadline is not None
        assert deadline.tzinfo is not None

    def test_different_timezone(self):
        """Test: works with different timezones"""
        tz = pytz_timezone("America/New_York")
        now = tz.localize(datetime(2024, 1, 15, 15, 0, 0))

        deadline = calculate_ev_deadline("07:00", now, "America/New_York")

        assert deadline is not None
        assert deadline.hour == 7
        assert deadline.minute == 0
        assert deadline.day == 16  # Tomorrow

    def test_integer_960_equals_16_00(self):
        """Test: integer 960 (16*60) equals string '16:00' (YAML 1.1 sexagesimal fallback)"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline_int = calculate_ev_deadline(960, now, "Europe/Stockholm")
        deadline_str = calculate_ev_deadline("16:00", now, "Europe/Stockholm")

        assert deadline_int is not None
        assert deadline_str is not None
        assert deadline_int == deadline_str
        assert deadline_int.hour == 16
        assert deadline_int.minute == 0

    def test_integer_1020_equals_17_00(self):
        """Test: integer 1020 (17*60) equals string '17:00'"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline_int = calculate_ev_deadline(1020, now, "Europe/Stockholm")
        deadline_str = calculate_ev_deadline("17:00", now, "Europe/Stockholm")

        assert deadline_int is not None
        assert deadline_str is not None
        assert deadline_int == deadline_str
        assert deadline_int.hour == 17
        assert deadline_int.minute == 0

    def test_integer_out_of_range_returns_none(self):
        """Test: integer out of range (9999) returns None"""
        tz = pytz_timezone("Europe/Stockholm")
        now = tz.localize(datetime(2024, 1, 15, 12, 0, 0))

        deadline = calculate_ev_deadline(9999, now, "Europe/Stockholm")

        assert deadline is None
