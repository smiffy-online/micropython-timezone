"""
Basic usage example for micropython-timezone

Demonstrates:
- Getting current time in a specific timezone
- Checking DST status
- Comparing times across timezones

Note: This example assumes you've generated timezone.py with at least
Australia/Adelaide and UTC zones. Adjust zone names as needed.
"""

from timezone import ZoneInfo, available_timezones
from datetime import datetime, timedelta

# List available timezones (only those you generated)
print("Available timezones:")
for tz in sorted(available_timezones()):
    print(f"  {tz}")
print()

# Get Adelaide timezone
adelaide = ZoneInfo("Australia/Adelaide")
print(f"Timezone: {adelaide}")

# Current time (requires RTC to be set, e.g., via ntptime)
try:
    now = datetime.now(adelaide)
    print(f"Current time in Adelaide: {now}")
    
    # Check offset
    offset = adelaide.utcoffset(now)
    hours = offset.total_seconds() / 3600
    print(f"UTC offset: {hours:+.1f} hours")
    
    # Check if DST is active
    dst = adelaide.dst(now)
    if dst.total_seconds() > 0:
        print("Daylight saving time is ACTIVE")
    else:
        print("Standard time (no DST)")
        
except Exception as e:
    print(f"Note: datetime.now() requires RTC to be set")
    print(f"Error: {e}")

# Compare offsets at different times of year
print("\n--- Seasonal offset comparison ---")

# Winter (July - no DST in southern hemisphere)
winter = datetime(2024, 7, 15, 12, 0)
winter_offset = adelaide.utcoffset(winter)
print(f"July 15 offset: {winter_offset} (standard time)")

# Summer (January - DST active in southern hemisphere)
summer = datetime(2024, 1, 15, 12, 0)
summer_offset = adelaide.utcoffset(summer)
print(f"January 15 offset: {summer_offset} (daylight saving)")

# DST transition boundary (first Sunday October 2024)
# October 6, 2024 is the first Sunday
pre_dst = datetime(2024, 10, 6, 1, 59)
post_dst = datetime(2024, 10, 6, 3, 1)
print(f"\nDST transition (October 6, 2024):")
print(f"  01:59 offset: {adelaide.utcoffset(pre_dst)} (just before)")
print(f"  03:01 offset: {adelaide.utcoffset(post_dst)} (just after)")

# tzname() method
print(f"\nTimezone name: {adelaide.tzname(winter)} (winter)")
print(f"Timezone name: {adelaide.tzname(summer)} (summer)")
