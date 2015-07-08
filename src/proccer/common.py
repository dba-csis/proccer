from __future__ import division, print_function

from datetime import timedelta


def parse_interval(s):
    if s is None:
        return None
    try:
        return timedelta(seconds=int(s))
    except ValueError:
        pass  # not an intable thing

    try:
        count, interval = s.split()
        return timedelta(seconds=int(count) * intervals[interval])
    except (KeyError, ValueError):
        raise ValueError('Bad interval', s)

intervals = {
    'seconds': 1,
    'minutes': 60,
    'hours': 60 * 60,
    'days': 24 * 60 * 60,
}
