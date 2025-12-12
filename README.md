# micropython-timezone

Generate minimal MicroPython timezone modules from the IANA tz database.

## How It Works

1. **CPython generator** (`timezone_generator.py`) parses your system's real tz database
2. You select which timezones you need
3. Generator outputs a compact `timezone.py` for MicroPython
4. Regenerate when the tz database updates

This approach keeps the MicroPython module minimal — you only ship the zones you need.

## Requirements

- Python 3.9+ (for `zoneinfo` module)
- System tzdata package (`apt install tzdata` on Debian/Ubuntu)

## Usage

### Generate timezone module

```bash
# Specify zones directly
python timezone_generator.py Australia/Adelaide Australia/Sydney UTC -o timezone.py

# Or use a config file
python timezone_generator.py --config my_zones.txt -o timezone.py

# List all available timezones
python timezone_generator.py --list
```

### Config file format

```
# my_zones.txt - one timezone per line
# Comments start with #

Australia/Adelaide
Australia/Sydney
Australia/Brisbane
UTC
```

### Deploy to MicroPython

Copy the generated `timezone.py` to your device's `lib/` directory.

Requires `datetime` from micropython-lib:
```python
import mip
mip.install("datetime")
```

## MicroPython API

```python
from timezone import ZoneInfo, available_timezones
from datetime import datetime

# Get a timezone
adelaide = ZoneInfo("Australia/Adelaide")

# Current time with timezone
now = datetime.now(adelaide)
print(f"Adelaide: {now}")

# Get UTC offset (handles DST automatically)
offset = adelaide.utcoffset(now)
print(f"Offset: {offset}")

# Check if DST is active
dst = adelaide.dst(now)
if dst:
    print("Daylight saving is active")

# List available timezones (only those you generated)
print(available_timezones())
```

## Generated Module Size

Typical sizes:
- 3 zones (e.g., Adelaide, Sydney, UTC): ~3KB
- 10 zones: ~4KB
- Full Australian set (8 zones): ~3.5KB

Memory per ZoneInfo instance: ~100 bytes

## DST Handling

The generator extracts actual DST transition rules from the IANA database:
- Detects hemisphere (northern/southern)
- Records transition dates (month, week, weekday, hour)
- Week=5 means "last occurrence" (handles variable month lengths)
- Both northern and southern hemisphere rules supported

**Example extracted rules:**
- `Australia/Adelaide`: 1st Sunday October, 1st Sunday April
- `Europe/London`: Last Sunday March, Last Sunday October
- `America/New_York`: 2nd Sunday March, 1st Sunday November

## Regenerating

When the system tz database updates (e.g., after `apt upgrade tzdata`), regenerate:

```bash
python timezone_generator.py --config my_zones.txt -o timezone.py
```

Then redeploy to your devices.

## Example Output

For `python timezone_generator.py Australia/Adelaide Europe/London UTC`:

```python
_ZONES = {
    "Australia/Adelaide": (570, 630, True, "south", (10, 1, 6, 2), (4, 1, 6, 3)),
    "Europe/London": (0, 60, True, "north", (3, 5, 6, 2), (10, 5, 6, 3)),
    "UTC": (0, 0, False, None, None, None),
}
```

Format: `(std_offset_minutes, dst_offset_minutes, has_dst, hemisphere, dst_start, dst_end)`

DST transitions: `(month, week, weekday, hour)` where week 1-4 for specific week, 5 for "last"; weekday 0=Monday, 6=Sunday.

## Files

```
micropython-timezone/
├── timezone_generator.py  # CPython tool - run on your dev machine
├── timezone.py            # Generated output - deploy to MicroPython
├── README.md
├── LICENSE
└── examples/
    ├── basic_usage.py     # MicroPython usage example
    └── zones.txt          # Example config file
```

## License

MIT License — Copyright (c) 2025 Matthew S. Smith

## Contributing

This module was developed collaboratively with Claude (Anthropic). Contributions welcome via GitHub.
