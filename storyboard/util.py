#!/usr/bin/env python3

"""Supporting utilities."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import os
import re
import sys
import time

def round_up(number, ndigits=0):
    """Round a nonnegative number UPWARD to a given precision in decimal digits.

    Keyword arguments:
    number -- nonnegative floating point number
    ndigits -- number of decimal digits to round to, default is 0

    Returns: float
    """
    multiplier = 10 ** ndigits
    return math.ceil(number * multiplier) / multiplier

# patterns numerator:denominator and numerator/denominator
_NUM_COLON_DEN = re.compile(r'^([1-9][0-9]*):([1-9][0-9]*)$')
_NUM_SLASH_DEN = re.compile(r'^([1-9][0-9]*)/([1-9][0-9]*)$')
def evaluate_ratio(ratio_str):
    """Evaluate ratio in the form num:den or num/den.

    Note that numerator and denominator should both be positive integers.

    Keyword arguments:
    ratio_str: the ratio as a string (either 'num:den' or 'num/den' where num
               and den are positive integers

    Returns: the ratio as a float (or None if malformed)
    """
    match = _NUM_COLON_DEN.match(ratio_str)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        return numerator / denominator
    match = _NUM_SLASH_DEN.match(ratio_str)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        return numerator / denominator
    return None

def humansize(size):
    """Return a human readable string of the given size in bytes."""
    multiplier = 1024.0
    if size < multiplier:
        return "%dB" % size
    for unit in ['Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        size /= multiplier
        if size < multiplier:
            if size < 10:
                return "%.2f%sB" % (round_up(size, 2), unit)
            elif size < 100:
                return "%.1f%sB" % (round_up(size, 1), unit)
            else:
                return "%.0f%sB" % (round_up(size, 0), unit)
            break
    else:
        return "%.1f%sB" % (round_up(size, 1), unit)

def humantime(seconds, ndigits=2, one_hour_digit=False):
    """Return a human readable string of the given duration in seconds.

    Keyword arguments:
    ndigits - number of digits after the decimal point for the seconds part,
              default is 2
    one_hour_digit - if True, only print one hour digit; default is two hour
                     digits
    """
    # pylint: disable=invalid-name
    hh = int(seconds) // 3600 # hours
    mm = (int(seconds) // 60) % 60 # minutes
    ss = seconds - (int(seconds) // 60) * 60 # seconds
    hh_format = "%01d" if one_hour_digit else "%02d"
    mm_format = "%02d"
    ss_format = "%02d" if ndigits == 0 else \
                "%0{0}.{1}f".format(ndigits + 3, ndigits)
    format_string = "{0}:{1}:{2}".format(hh_format, mm_format, ss_format)
    return format_string % (hh, mm, ss)

# default progress bar update interval
_PROGRESS_UPDATE_INTERVAL = 1.0
# the format string for a progress bar line
#
# 0: processed size, e.g., 2.02GiB
# 1: elapsed time (7 chars), e.g., 0:00:04
# 2: current processing speed, e.g., 424MiB (/s is already hardcoded)
# 3: the bar, in the form "=====>   "
# 4: number of percent done, e.g., 99
# 5: estimated time remaining (11 chars), in the form "ETA H:MM:SS"; if
#    finished, fill with space
_FORMAT_STRING = '{0:>7s} {1} [{2:>7s}/s] [{3}] {4:>3s}% {5}\r'
class ProgressBar(object):
    """Progress bar for file processing.

    To generate a progress bar, init a ProgressBar instance, then update
    frequently with the update method, passing in the size of newly processed
    chunk. The force_update process should only be called if you want to
    overwrite the processed size which is automatically calculated
    incrementally. After you finish processing the file/stream, call the finish
    method to wrap it up.  Any further calls after the finish method has been
    called lead to undefined behavior (probably exceptions).

    Format inspired by pv(1) (pipe viewer).

    Initializer arguments:
    totalsize: total size in bytes of the file/stream to be processed
    interval: update interval in seconds of the progress bar, default is 1.0

    Public instance attributes:
    These attributes can be queried for informational purposes, but not meant
    for manual manipulation.

    During processing:
    totalsize - total size of file/stream
    processed - size of processed part
    start - starting time (absolute time returned by time.time())
    interval - update interval

    After processing (after finish is called):
    totalsize
    start
    elapsed - total elapsed time, in seconds
    """

    def __init__(self, totalsize, interval=_PROGRESS_UPDATE_INTERVAL):
        self.totalsize = totalsize
        self.processed = 0
        self.start = time.time()
        self.interval = interval
        self._last = self.start
        self._last_processed = 0
        # calculate bar length
        try:
            ncol, _ = os.get_terminal_size()
        except AttributeError:
            # python2 do not have os.get_terminal_size
            # assume a minimum of 80 columns
            ncol = 80
        self._barlen = (ncol - 47) if ncol >= 57 else 10

    def update(self, chunk_size):
        """Update the progress bar for the newly processed chunk.

        Keyword arguments:
        chunk_size: the size of the new chunk since the last update
        """
        self.processed += chunk_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def force_update(self, processed_size):
        """Force update the progress bar with a given processed size.

        Keyword arguments:
        processed_size: size of the processed part of the file, overwrites
                        existing value
        """
        self.processed = processed_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def finish(self):
        """Finish file progressing and wrap up on the progress bar."""
        # pylint: disable=attribute-defined-outside-init
        # new attribute elapsed created on the fly after processing finishes
        self.elapsed = time.time() - self.start
        del self.processed
        del self.interval
        del self._last
        del self._last_processed

        processed_s = humansize(self.totalsize)
        elapsed_s = self.humantime(self.elapsed)
        speed_s = humansize(self.totalsize / self.elapsed)
        bar_s = '=' * (self._barlen - 1) + '>'
        percent_s = '100'
        eta_s = ' ' * 11
        sys.stderr.write(_FORMAT_STRING.format(
            processed_s, elapsed_s, speed_s, bar_s, percent_s, eta_s
        ))
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _update_output(self):
        """Update the progress bar and surrounding data as appropriate."""
        if time.time() - self._last < self.interval:
            return

        # speed in the last second
        speed = (self.processed - self._last_processed) / \
                (time.time() - self._last) # bytes per second
        # update last stats for the next update
        self._last = time.time()
        self._last_processed = self.processed

        # _s suffix stands for string
        processed_s = humansize(self.processed)
        elapsed_s = self.humantime(time.time() - self.start)
        speed_s = humansize(speed)
        percentage = self.processed / self.totalsize # absolute
        percent_s = str(int(percentage * 100))
        # generate bar
        length = int(round(self._barlen * percentage))
        fill = self._barlen - length
        if length == 0:
            bar_s = " " * self._barlen
        else:
            bar_s = '=' * (length - 1) + '>' + ' ' * fill
        # calculate ETA
        remaining = self.totalsize - self.processed
        # estimate based on current speed
        eta = remaining / speed
        eta_s = "ETA %s" % self.humantime(eta)

        sys.stderr.write(_FORMAT_STRING.format(
            processed_s, elapsed_s, speed_s, bar_s, percent_s, eta_s
        ))
        sys.stderr.flush()

    def humantime(self, seconds):
        # pylint: disable=no-self-use
        """Customized humantime."""
        return humantime(seconds, ndigits=0, one_hour_digit=True)
