import math


DAY_SECONDS = 86400
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TIME_PATTERN = r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$"


def definitions(common):
    def obj(properties, required):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": required}

    timestamp = {"type": "string", "format": "date-time"}
    window = obj({"start": timestamp, "end": timestamp}, ["start", "end"])
    period = obj({
        "weekdays": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": list(WEEKDAYS)}},
        "start_time": {"type": "string", "pattern": TIME_PATTERN},
        "end_time": {"type": "string", "pattern": TIME_PATTERN},
        "end_day_offset": {"type": "integer", "enum": [0, 1]},
    }, ["weekdays", "start_time", "end_time", "end_day_offset"])
    schedule = obj({"time_reference": {"const": "UTC"},
                    "periods": {"type": "array", "minItems": 1, "items": {"$ref": common + "#/$defs/WeeklyPeriod"}},
                    "exclusions": {"type": "array", "items": window}},
                   ["time_reference", "periods"])
    scheduled = obj({"start": timestamp, "end": timestamp, "schedule": {"$ref": common + "#/$defs/WeeklySchedule"}}, ["start", "end", "schedule"])
    return {"WeeklyPeriod": period, "WeeklySchedule": schedule, "ScheduledWindow": scheduled}


def seconds(clock):
    hour, minute, second = map(int, clock.split(":"))
    return hour * 3600 + minute * 60 + second


def merge_intervals(intervals):
    result = []
    for start, end in sorted(intervals):
        if start >= end:
            continue
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def subtract(intervals, exclusions):
    for lower, upper in merge_intervals(exclusions):
        remaining = []
        for start, end in intervals:
            if upper <= start or lower >= end:
                remaining.append((start, end))
            else:
                if start < lower:
                    remaining.append((start, lower))
                if upper < end:
                    remaining.append((upper, end))
        intervals = remaining
    return intervals


def intervals(window, period, instant, clip=None):
    if window.get("continuous"):
        return [clip or (-math.inf, math.inf)]
    start, end = instant(window["start"], period), instant(window["end"], period)
    if clip:
        start, end = max(start, clip[0]), min(end, clip[1])
    if start >= end:
        return []
    schedule = window.get("schedule")
    if not schedule:
        return [(start, end)]
    result = []
    first_day = math.floor(start / DAY_SECONDS) - 1
    last_day = math.floor(end / DAY_SECONDS)
    for day in range(first_day, last_day + 1):
        midnight = day * DAY_SECONDS
        weekday = WEEKDAYS[(day + 3) % 7]
        for entry in schedule["periods"]:
            if weekday not in entry["weekdays"]:
                continue
            lower = midnight + seconds(entry["start_time"])
            upper = midnight + entry["end_day_offset"] * DAY_SECONDS + seconds(entry["end_time"])
            if lower < end and upper > start:
                result.append((max(lower, start), min(upper, end)))
    exclusions = [(instant(item["start"], None), instant(item["end"], None)) for item in schedule.get("exclusions", [])]
    return subtract(merge_intervals(result), exclusions)


def schedule_errors(window, instant):
    schedule = window.get("schedule")
    if not schedule:
        return
    for index, entry in enumerate(schedule["periods"]):
        duration = entry["end_day_offset"] * DAY_SECONDS + seconds(entry["end_time"]) - seconds(entry["start_time"])
        if not 0 < duration <= DAY_SECONDS:
            yield ("schedule", "periods", index), "weekly period must last more than zero and at most 24 hours"
    lower, upper = instant(window["start"], None), instant(window["end"], None)
    for index, exclusion in enumerate(schedule.get("exclusions", [])):
        start, end = instant(exclusion["start"], None), instant(exclusion["end"], None)
        if not lower <= start < end <= upper:
            yield ("schedule", "exclusions", index), "exclusion must be a positive interval within scheduled validity"


def contains(child, parent, period, instant):
    start, end = instant(child["start"], period), instant(child["end"], period)
    child_intervals = intervals(child, period, instant)
    parent_intervals = intervals(parent, period, instant, (start, end))
    return not subtract(child_intervals, parent_intervals)
