# micropython-timezone
# Auto-generated from IANA tz database - do not edit manually
# Regenerate with: timezone_generator.py
#
# MIT License - Copyright (c) 2025 Matthew S. Smith

from datetime import timezone, timedelta, datetime

# Zone data: (std_offset_minutes, dst_offset_minutes, has_dst, hemisphere, dst_start, dst_end)
# dst_start/end: (month, week, weekday, hour) - week 1-4 or 5=last, weekday 0=Mon 6=Sun
_ZONES = {
    "Australia/Adelaide": (570, 630, True, "south", (10, 1, 6, 2), (4, 1, 6, 3)),
    "Australia/Brisbane": (600, 600, False, None, None, None),
    "Australia/Melbourne": (600, 660, True, "south", (10, 1, 6, 2), (4, 1, 6, 3)),
    "Australia/Perth": (480, 480, False, None, None, None),
    "Australia/Sydney": (600, 660, True, "south", (10, 1, 6, 2), (4, 1, 6, 3)),
    "UTC": (0, 0, False, None, None, None),
}


def _nth_weekday(year, month, week, weekday):
    """
    Find the nth occurrence of a weekday in a month.
    week: 1-4 for 1st-4th, 5 for last
    weekday: 0=Monday, 6=Sunday
    """
    from datetime import date
    
    # First day of month
    first = date(year, month, 1)
    first_weekday = first.weekday()
    
    # Days until first occurrence of target weekday
    days_until = (weekday - first_weekday) % 7
    first_occurrence = 1 + days_until
    
    if week == 5:
        # Last occurrence - find by going to next month and back
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        
        # Work backwards from end of month
        last = date(year, month, last_day)
        last_weekday = last.weekday()
        days_back = (last_weekday - weekday) % 7
        return last_day - days_back
    else:
        # 1st through 4th occurrence
        return first_occurrence + (week - 1) * 7


def _is_dst_active(dt, zone_data):
    """Check if DST is active for given datetime and zone data."""
    std_off, dst_off, has_dst, hemisphere, dst_start, dst_end = zone_data
    
    if not has_dst:
        return False
    
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    
    # Calculate transition dates
    start_day = _nth_weekday(year, dst_start[0], dst_start[1], dst_start[2])
    end_day = _nth_weekday(year, dst_end[0], dst_end[1], dst_end[2])
    
    start_dt = (dst_start[0], start_day, dst_start[3])  # (month, day, hour)
    end_dt = (dst_end[0], end_day, dst_end[3])
    
    current = (month, day, hour)
    
    if hemisphere == 'south':
        # Southern hemisphere: DST spans year boundary (Oct-Apr typically)
        # DST is active if AFTER start OR BEFORE end
        if current >= start_dt or current < end_dt:
            return True
        return False
    else:
        # Northern hemisphere: DST within single year (Mar-Nov typically)
        # DST is active if AFTER start AND BEFORE end
        if current >= start_dt and current < end_dt:
            return True
        return False


class ZoneInfo:
    """
    Timezone implementation compatible with datetime.tzinfo.
    Provides named timezone lookup with automatic DST handling.
    """
    
    def __init__(self, key):
        if key not in _ZONES:
            raise KeyError(f"Unknown timezone: {key}")
        
        self._key = key
        self._zone_data = _ZONES[key]
    
    @property
    def key(self):
        return self._key
    
    def utcoffset(self, dt):
        if _is_dst_active(dt, self._zone_data):
            return timedelta(minutes=self._zone_data[1])
        return timedelta(minutes=self._zone_data[0])
    
    def dst(self, dt):
        if _is_dst_active(dt, self._zone_data):
            return timedelta(minutes=self._zone_data[1] - self._zone_data[0])
        return timedelta(0)
    
    def tzname(self, dt):
        offset = self.utcoffset(dt)
        total_minutes = int(offset.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = abs(total_minutes % 60)
        if minutes:
            return f"UTC{hours:+d}:{minutes:02d}"
        return f"UTC{hours:+d}"
    
    def __repr__(self):
        return f"ZoneInfo(key='{self._key}')"
    
    def __str__(self):
        return self._key
    
    def __eq__(self, other):
        if isinstance(other, ZoneInfo):
            return self._key == other._key
        return False
    
    def __hash__(self):
        return hash(self._key)


def available_timezones():
    """Return set of available timezone names."""
    return set(_ZONES.keys())
