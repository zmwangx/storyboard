#!/usr/bin/env python3

"""Check existence of ffmpeg and ffprobe."""

import os
import subprocess

def guess_bins():
    """Guess ffmpeg and ffprobe binary names based on OS.

    Returns a tuple (ffmpeg_bin, ffprobe_bin) of two strings, where ffmpeg_bin
    is the guessed ffmpeg binary, and ffprobe_bin is the guessed ffprobe binary.
    """
    if os.name == 'nt':
        return ('ffmpeg.exe', 'ffprobe.exe')
    else:
        return ('ffmpeg', 'ffprobe')

def check_bins(bins):
    """Check existance of ffmpeg and ffprobe binaries.

    Keyboard arguments:
    bins - a tuple (ffmpeg_bin, ffprobe_bin) of the binary names/paths

    Returns:
    True if check is successful, raises OSError if check fails
    """
    with open(os.devnull, 'wb') as devnull:
        for binary in bins:
            try:
                subprocess.check_call([binary, '-version'],
                                      stdout=devnull, stderr=devnull)
            except subprocess.CalledProcessError:
                raise OSError("%s may be corrupted" % binary)
            except OSError:
                raise OSError("%s not found on PATH" % binary)
    return True
