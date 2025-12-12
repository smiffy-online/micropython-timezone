# micropython-timezone
# Provides Python zoneinfo-style timezone support for MicroPython
# 
# MIT License
# Copyright (c) 2025 Matthew S. Smith

from datetime import timezone, timedelta, datetime

# Zone definitions: (std_offset_minutes, dst_offset_minutes, has_dst)
# DST rules are Australian: First Sunday October → First Sunday April
_ZONES = {
    "UTC": (0, 0, False),
    "Australia/Adelaide": (570, 630, True),   # +09:30 / +10:30
    "Australia/Sydney": (600, 660, True),      # +10:00 / +11:00
    "Australia/Melbourne": (600, 660, True),   # +10:00 / +11:00
    "Australia/Hobart": (600, 660, True),      # +10:00 / +11:00
    "Australia/Brisbane": (600, 600, False),   # +10:00, no DST
    "Australia/Perth": (480, 480, False),      # +08:00, no DST
    "Australia/Darwin": (570, 570, False),     # +09:30, no DST
}

# Cache for ZoneInfo objects
_zone_cache = {}


def _first_sunday(year, month):
    """Find day-of-month for first Sunday of given month."""
    # Calculate weekday of 1st of month
    # Using Zeller-like calculation for day of week
    # January/February treated as months 13/14 of previous year
    y = year
    m = month
    if m < 3:
        m += 12
        y -= 1
    
    # Day of week for 1st of month (0=Saturday, 1=Sunday, ... 6=Friday)
    q = 1  # day of month
    k = y % 100
    j = y // 100
    h = (q + ((13 * (m + 1)) // 5) + k + (k // 4) + (j // 4) - 2 * j) % 7
    
    # Convert to Python weekday (0=Monday, 6=Sunday)
    weekday = (h + 5) % 7
    
    # Days until Sunday (weekday 6)
    days_until_sunday = (6 - weekday) % 7
    if days_until_sunday == 0 and weekday != 6:
        days_until_sunday = 7
    
    return 1 + days_until_sunday


def _is_dst_active(dt, has_dst):
    """
    Check if DST is active for given datetime.
    Uses Australian rules: First Sunday October 02:00 → First Sunday April 03:00
    
    Note: dt should be in local standard time for accurate boundary detection.
    """
    if not has_dst:
        return False
    
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    
    # DST starts: First Sunday October at 02:00 (becomes 03:00)
    oct_sunday = _first_sunday(year, 10)
    
    # DST ends: First Sunday April at 03:00 (becomes 02:00)
    apr_sunday = _first_sunday(year, 4)
    
    # Southern hemisphere: DST spans year boundary
    # Active from October → December AND January → April
    
    if month > 10:
        # November/December: DST active
        return True
    elif month == 10:
        # October: check if past transition
        if day > oct_sunday:
            return True
        elif day == oct_sunday and hour >= 2:
            return True
        return False
    elif month < 4:
        # January/February/March: DST active
        return True
    elif month == 4:
        # April: check if before transition
        if day < apr_sunday:
            return True
        elif day == apr_sunday and hour < 3:
            return True
        return False
    else:
        # May-September: DST not active
        return False


class ZoneInfo:
    """
    Timezone implementation compatible with datetime.tzinfo.
    Provides named timezone lookup with automatic DST handling.
    """
    
    def __init__(self, key):
        """
        Create a ZoneInfo for the given timezone name.
        
        Args:
            key: Timezone name (e.g., "Australia/Adelaide", "UTC")
        
        Raises:
            KeyError: If timezone not found
        """
        if key not in _ZONES:
            raise KeyError(f"Unknown timezone: {key}")
        
        self._key = key
        self._std_offset, self._dst_offset, self._has_dst = _ZONES[key]
    
    @property
    def key(self):
        """Return the timezone name."""
        return self._key
    
    def utcoffset(self, dt):
        """
        Return the UTC offset for the given datetime.
        
        Args:
            dt: datetime object (naive or aware)
        
        Returns:
            timedelta representing offset from UTC
        """
        if self._has_dst and _is_dst_active(dt, self._has_dst):
            return timedelta(minutes=self._dst_offset)
        return timedelta(minutes=self._std_offset)
    
    def dst(self, dt):
        """
        Return the DST offset for the given datetime.
        
        Args:
            dt: datetime object
        
        Returns:
            timedelta if DST is active, timedelta(0) otherwise
        """
        if self._has_dst and _is_dst_active(dt, self._has_dst):
            return timedelta(minutes=self._dst_offset - self._std_offset)
        return timedelta(0)
    
    def tzname(self, dt):
        """
        Return the timezone abbreviation.
        
        Args:
            dt: datetime object
        
        Returns:
            String timezone abbreviation
        """
        # Generate abbreviation from offset
        offset = self.utcoffset(dt)
        total_minutes = int(offset.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
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


def get_localzone():
    """
    Attempt to determine local timezone.
    
    Returns:
        ZoneInfo for detected timezone, or UTC if detection fails.
    
    Note: On most MicroPython platforms, there's no reliable way to detect
    the system timezone. This returns UTC as a safe default.
    """
    # MicroPython doesn't have reliable timezone detection
    # Return UTC as safe default
    return ZoneInfo("UTC")
