#!/usr/bin/env python3

"""Check existence of ffmpeg and ffprobe.

Routines
--------
.. autosummary::
    guess_bins
    check_bins

----

"""

import os
import subprocess


def guess_bins():
    """Guess ffmpeg and ffprobe binary names based on OS.

    Returns
    -------
    bins : tuple
        A tuple ``(ffmpeg_bin, ffprobe_bin)`` of two strings, where
        `ffmpeg_bin` is the guessed ffmpeg binary, and `ffprobe_bin` is
        the guessed ffprobe binary.

    """

    if os.name == 'nt':
        return ('ffmpeg.exe', 'ffprobe.exe')
    else:
        return ('ffmpeg', 'ffprobe')


def check_bins(bins):
    """Check existance of ffmpeg and ffprobe binaries.

    Parameters
    ----------
    bins : tuple
        A tuple `(ffmpeg_bin, ffprobe_bin)`` of the binary
        names/paths. Either of the two can be ``None``, in which case
        the corresponding binary is not checked.

    Returns
    -------
    True
        If check is successful.

    Raises
    ------
    OSError
        If check fails.

    """

    with open(os.devnull, 'wb') as devnull:
        for binary in bins:
            if binary is None:
                continue
            try:
                subprocess.check_call([binary, '-version'],
                                      stdout=devnull, stderr=devnull)
            except subprocess.CalledProcessError:
                raise OSError("%s may be corrupted" % binary)
            except OSError:
                raise OSError("%s not found on PATH" % binary)
    return True
