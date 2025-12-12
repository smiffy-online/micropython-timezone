#!/usr/bin/env python3
"""
timezone_generator.py - Generate minimal MicroPython timezone data from IANA tz database

Parses the system's zoneinfo database and generates a compact timezone.py module
containing only the user-selected timezones. Regenerate when tz database updates.

Usage:
    python timezone_generator.py Australia/Adelaide Australia/Sydney UTC -o timezone.py
    
    # Or with a config file
    python timezone_generator.py --config zones.txt -o timezone.py

Requirements:
    - Python 3.9+ (for zoneinfo module)
    - System tzdata package installed

MIT License - Copyright (c) 2025 Matthew S. Smith
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from zoneinfo import ZoneInfo, available_timezones
except ImportError:
    print("Error: Python 3.9+ required for zoneinfo module", file=sys.stderr)
    sys.exit(1)


def get_zone_info(zone_name: str) -> dict:
    """
    Extract timezone data from system zoneinfo.
    
    Returns dict with:
        - std_offset_minutes: Standard time offset from UTC
        - dst_offset_minutes: DST offset from UTC (same as std if no DST)
        - has_dst: Whether zone observes DST
        - dst_transitions: List of (month, week, weekday, hour) for start/end
    """
    try:
        tz = ZoneInfo(zone_name)
    except KeyError:
        raise ValueError(f"Unknown timezone: {zone_name}")
    
    # Sample dates to detect DST
    # Use mid-month dates to avoid transition boundaries
    jan = datetime(2024, 1, 15, 12, 0, tzinfo=tz)
    jul = datetime(2024, 7, 15, 12, 0, tzinfo=tz)
    
    jan_offset = jan.utcoffset().total_seconds() / 60
    jul_offset = jul.utcoffset().total_seconds() / 60
    
    jan_dst = jan.dst()
    jul_dst = jul.dst()
    
    # Determine if DST is observed
    has_dst = (jan_dst and jan_dst.total_seconds() > 0) or \
              (jul_dst and jul_dst.total_seconds() > 0)
    
    if has_dst:
        # Determine which is standard vs DST
        # In southern hemisphere, January is summer (DST)
        # In northern hemisphere, July is summer (DST)
        if jan_dst and jan_dst.total_seconds() > 0:
            # Southern hemisphere - January is DST
            std_offset = int(jul_offset)
            dst_offset = int(jan_offset)
            hemisphere = 'south'
        else:
            # Northern hemisphere - July is DST
            std_offset = int(jan_offset)
            dst_offset = int(jul_offset)
            hemisphere = 'north'
    else:
        std_offset = int(jan_offset)
        dst_offset = std_offset
        hemisphere = None
    
    # Find DST transitions by scanning the year
    transitions = find_dst_transitions(tz, 2024) if has_dst else None
    
    return {
        'name': zone_name,
        'std_offset_minutes': std_offset,
        'dst_offset_minutes': dst_offset,
        'has_dst': has_dst,
        'hemisphere': hemisphere,
        'transitions': transitions,
    }


def find_dst_transitions(tz: ZoneInfo, year: int) -> dict:
    """
    Find DST transition dates for a given year.
    
    Returns dict with 'start' and 'end' transitions, each containing:
        - month: 1-12
        - week: 1-4 for specific week, 5 for "last"
        - weekday: 0-6 (0=Monday, 6=Sunday)
        - hour: transition hour (typically 2 or 3)
    """
    from datetime import date
    from calendar import monthrange
    
    transitions = {'start': None, 'end': None}
    prev_dst = None
    
    # Scan each day of the year at noon (avoids DST boundary ambiguity)
    for month in range(1, 13):
        for day in range(1, 32):
            try:
                dt = datetime(year, month, day, 12, 0, tzinfo=tz)
                dst = dt.dst()
                dst_active = dst is not None and dst.total_seconds() > 0
                
                if prev_dst is not None and dst_active != prev_dst:
                    # Transition detected on this day
                    weekday = dt.weekday()
                    
                    # Calculate which week of the month (1=first, 5=last)
                    # Find first occurrence of this weekday in the month
                    first_of_month = date(year, month, 1)
                    first_weekday = first_of_month.weekday()
                    days_until = (weekday - first_weekday) % 7
                    first_occurrence = 1 + days_until
                    week = ((day - first_occurrence) // 7) + 1
                    
                    # Check if this is the LAST occurrence of this weekday in the month
                    # If so, use week=5 to indicate "last" (works regardless of month length)
                    days_in_month = monthrange(year, month)[1]
                    next_occurrence = day + 7
                    if next_occurrence > days_in_month:
                        week = 5  # This is the last occurrence
                    
                    if dst_active:
                        # DST just started - spring forward at 02:00 -> 03:00
                        transitions['start'] = {
                            'month': month,
                            'week': week,
                            'weekday': weekday,
                            'hour': 2,
                        }
                    else:
                        # DST just ended - fall back at 03:00 -> 02:00
                        transitions['end'] = {
                            'month': month,
                            'week': week,
                            'weekday': weekday,
                            'hour': 3,
                        }
                
                prev_dst = dst_active
            except ValueError:
                # Invalid date (e.g., Feb 30)
                continue
    
    return transitions


def generate_micropython_module(zones: list[dict], output_path: Path = None) -> str:
    """
    Generate MicroPython timezone.py module content.
    """
    
    # Build zone data
    zone_lines = []
    for z in zones:
        if z['has_dst']:
            # Format: (std_offset, dst_offset, has_dst, hemisphere, start_transition, end_transition)
            start = z['transitions']['start']
            end = z['transitions']['end']
            zone_lines.append(
                f'    "{z["name"]}": ({z["std_offset_minutes"]}, {z["dst_offset_minutes"]}, True, '
                f'"{z["hemisphere"]}", ({start["month"]}, {start["week"]}, {start["weekday"]}, {start["hour"]}), '
                f'({end["month"]}, {end["week"]}, {end["weekday"]}, {end["hour"]})),'
            )
        else:
            zone_lines.append(
                f'    "{z["name"]}": ({z["std_offset_minutes"]}, {z["dst_offset_minutes"]}, False, None, None, None),'
            )
    
    zones_dict = '\n'.join(zone_lines)
    
    module_content = f'''# micropython-timezone
# Auto-generated from IANA tz database - do not edit manually
# Regenerate with: timezone_generator.py
#
# MIT License - Copyright (c) 2025 Matthew S. Smith

from datetime import timezone, timedelta, datetime

# Zone data: (std_offset_minutes, dst_offset_minutes, has_dst, hemisphere, dst_start, dst_end)
# dst_start/end: (month, week, weekday, hour) - week 1-4 or 5=last, weekday 0=Mon 6=Sun
_ZONES = {{
{zones_dict}
}}


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
            raise KeyError(f"Unknown timezone: {{key}}")
        
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
            return f"UTC{{hours:+d}}:{{minutes:02d}}"
        return f"UTC{{hours:+d}}"
    
    def __repr__(self):
        return f"ZoneInfo(key='{{self._key}}')"
    
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
'''
    
    if output_path:
        output_path.write_text(module_content)
        print(f"Generated: {output_path}")
    
    return module_content


def list_available_zones():
    """Print all available timezones from system."""
    zones = sorted(available_timezones())
    print(f"Available timezones ({len(zones)} total):\n")
    
    # Group by region
    regions = {}
    for z in zones:
        if '/' in z:
            region = z.split('/')[0]
        else:
            region = 'Other'
        regions.setdefault(region, []).append(z)
    
    for region in sorted(regions.keys()):
        print(f"{region}:")
        for z in sorted(regions[region]):
            print(f"  {z}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Generate minimal MicroPython timezone module from IANA tz database'
    )
    parser.add_argument(
        'zones',
        nargs='*',
        help='Timezone names (e.g., Australia/Adelaide UTC America/New_York)'
    )
    parser.add_argument(
        '-c', '--config',
        type=Path,
        help='File containing timezone names (one per line)'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('timezone.py'),
        help='Output file (default: timezone.py)'
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='List all available timezones'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_available_zones()
        return
    
    # Collect zones from command line and config file
    zones_to_include = set(args.zones)
    
    if args.config:
        if not args.config.exists():
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        for line in args.config.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                zones_to_include.add(line)
    
    if not zones_to_include:
        parser.print_help()
        print("\nError: No timezones specified", file=sys.stderr)
        sys.exit(1)
    
    # Always include UTC
    zones_to_include.add('UTC')
    
    print(f"Processing {len(zones_to_include)} timezone(s)...")
    
    # Extract zone data
    zone_data = []
    for zone_name in sorted(zones_to_include):
        try:
            data = get_zone_info(zone_name)
            zone_data.append(data)
            dst_status = "DST" if data['has_dst'] else "no DST"
            print(f"  {zone_name}: {data['std_offset_minutes']//60:+.1f}h ({dst_status})")
        except ValueError as e:
            print(f"  Warning: {e}", file=sys.stderr)
    
    # Generate module
    generate_micropython_module(zone_data, args.output)
    print(f"\nGenerated {args.output} with {len(zone_data)} timezone(s)")


if __name__ == '__main__':
    main()
