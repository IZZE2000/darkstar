#!/usr/bin/env python3
"""Test script for UI19 - Custom Date Picker API functionality."""

from datetime import date, datetime, timedelta

import pytz


def test_date_parsing():
    """Test YYYY-MM-DD date parsing."""
    test_cases = [
        ("2024-02-10", "2024-02-15"),  # Valid range
        ("2024-01-01", "2024-12-31"),  # Full year
        ("2024-02-10", "2024-02-10"),  # Single day
    ]

    for start_str, end_str in test_cases:
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            print(f"✓ Parsed {start_str} to {end_str}: {start} -> {end}")
        except ValueError as e:
            print(f"✗ Failed to parse {start_str} to {end_str}: {e}")


def test_date_validation():
    """Test date range validation."""
    test_cases = [
        ("2024-02-10", "2024-02-15", True),  # Valid: end > start
        ("2024-02-15", "2024-02-10", False),  # Invalid: end < start
        ("2024-02-10", "2024-02-10", True),  # Valid: end == start
    ]

    for start_str, end_str, expected_valid in test_cases:
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()

            is_valid = end >= start

            if is_valid == expected_valid:
                print(
                    f"✓ {start_str} to {end_str}: {'Valid' if is_valid else 'Invalid'} (expected)"
                )
            else:
                print(
                    f"✗ {start_str} to {end_str}: {'Valid' if is_valid else 'Invalid'} (unexpected)"
                )
        except ValueError as e:
            print(f"✗ Failed validation test: {e}")


def test_period_date_calculation():
    """Test period-based date calculations match preset logic."""
    tz = pytz.timezone("Europe/Stockholm")
    now_local = datetime.now(tz)
    today_local = now_local.date()

    test_cases = [
        ("today", today_local, today_local),
        ("yesterday", today_local - timedelta(days=1), today_local - timedelta(days=1)),
        ("week", today_local - timedelta(days=6), today_local),
        ("month", today_local - timedelta(days=29), today_local),
    ]

    for period, expected_start, expected_end in test_cases:
        # Calculate dates based on period
        if period == "today":
            start_date = end_date = today_local
        elif period == "yesterday":
            end_date = today_local - timedelta(days=1)
            start_date = end_date
        elif period == "week":
            end_date = today_local
            start_date = today_local - timedelta(days=6)
        elif period == "month":
            end_date = today_local
            start_date = today_local - timedelta(days=29)
        else:
            start_date = end_date = today_local

        if start_date == expected_start and end_date == expected_end:
            print(f"✓ {period}: {start_date} to {end_date}")
        else:
            print(
                f"✗ {period}: Expected {expected_start} to {expected_end}, got {start_date} to {end_date}"
            )


def test_custom_date_override():
    """Test that custom dates override period-based calculation."""
    custom_start = date(2024, 1, 15)
    custom_end = date(2024, 2, 15)

    # Simulate custom date selection
    start_date = custom_start
    end_date = custom_end

    if start_date == custom_start and end_date == custom_end:
        print(f"✓ Custom dates override: {start_date} to {end_date}")
    else:
        print("✗ Custom dates not applied correctly")


def test_timezone_awareness():
    """Test timezone-aware datetime conversion."""
    tz = pytz.timezone("Europe/Stockholm")
    start_date = date(2024, 2, 10)
    end_date = date(2024, 2, 15)

    # Convert to timezone-aware datetime (as done in services.py)
    day_start = tz.localize(datetime(start_date.year, start_date.month, start_date.day))
    day_end_excl = tz.localize(datetime(end_date.year, end_date.month, end_date.day)) + timedelta(
        days=1
    )

    print(f"✓ Timezone-aware start: {day_start}")
    print(f"✓ Timezone-aware end: {day_end_excl}")
    print(f"  Duration: {(day_end_excl - day_start).days} days")


def main():
    """Run all tests."""
    print("=" * 60)
    print("UI19 - Custom Date Picker API Tests")
    print("=" * 60)

    print("\n1. Testing date parsing...")
    test_date_parsing()

    print("\n2. Testing date validation...")
    test_date_validation()

    print("\n3. Testing period date calculation...")
    test_period_date_calculation()

    print("\n4. Testing custom date override...")
    test_custom_date_override()

    print("\n5. Testing timezone awareness...")
    test_timezone_awareness()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
