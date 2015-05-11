#!/usr/bin/env python3

"""Extract video frames.

Classes
-------
.. autosummary::
    Frame

Routines
--------
.. autosummary::
    extract_frame

----

"""

from __future__ import absolute_import
from __future__ import print_function

import io
import os
import subprocess

from PIL import Image

from storyboard import fflocate
from storyboard.util import read_param as _read_param


class Frame(object):
    """Video frame object containing a timestamp and an image.

    Parameters
    ----------
    timestamp : float
        Timestamp of the frame, in seconds.
    image : PIL.Image.Image
        Image of the frame.

    Attributes
    ----------
    timestamp : float
    image : PIL.Image.Image

    """

    # pylint: disable=too-few-public-methods

    def __init__(self, timestamp, image):
        assert isinstance(timestamp, int) or isinstance(timestamp, float),\
            "timestamp is not an int or float"
        assert isinstance(image, Image.Image),\
            "image is not a PIL.Image.Image instance"
        self.timestamp = timestamp
        self.image = image


def extract_frame(video_path, timestamp, params=None):
    """Extract a video frame from a given timestamp.

    Use FFmpeg to seek to the specified timestamp and decode the
    corresponding frame.

    Parameters
    ----------
    video_path : str
        Path to the video file.
    timestamp : float
        Timestamp in seconds (as a nonnegative float).
    params : dict, optional
        Optional parameters enclosed in a dict. Default is ``None``.
        See the "Other Parameters" section for understood key/value
        pairs.

    Returns
    -------
    frame : Frame

    Raises
    ------
    OSError
        If video file doesn't exist, ffmpeg binary doesn't exist or
        fails to run, or ffmpeg runs but generates no output (possibly
        due to an out of range timestamp).

    Other Parameters
    ----------------
    ffmpeg_bin : str, optional
        Name or path of FFmpeg binary. If ``None``, make educated guess
        using ``storyboard.fflocate.guess_bins``. Default is ``None``.
    codec : str, optional
        Image codec used by FFmpeg when outputing the frame. Default is
        ``'png'``. There is no need to touch this option unless your
        FFmpeg cannot encode PNG, which is very unlikely.
    frame_by_frame : bool, optional
        Whether to seek frame by frame, i.e., whether to use output
        seeking (see https://trac.ffmpeg.org/wiki/Seeking). Default is
        ``False``. Note that seeking frame by frame is *extremely* slow,
        but accurate. Only use this when the container metadata is wrong
        or missing, so that input seeking produces wrong image.

    """

    if params is None:
        params = {}
    if 'ffmpeg_bin' in params and params['ffmpeg_bin'] is not None:
        ffmpeg_bin = params['ffmpeg_bin']
    else:
        ffmpeg_bin, _ = fflocate.guess_bins()
    codec = _read_param(params, 'codec', 'png')
    frame_by_frame = (params['frame_by_frame'] if 'frame_by_frame' in params
                      else False)

    if not os.path.exists(video_path):
        raise OSError("video file '%s' does not exist" % video_path)

    ffmpeg_args = [ffmpeg_bin]
    if frame_by_frame:
        # output seeking
        ffmpeg_args += [
            '-i', video_path,
            '-ss', str(timestamp),
        ]
    else:
        # input seeking
        ffmpeg_args += [
            '-ss', str(timestamp),
            '-i', video_path,
        ]
    ffmpeg_args += [
        '-f', 'image2',
        '-vcodec', codec,
        '-vframes', '1',
        '-hide_banner',
        '-',
    ]
    proc = subprocess.Popen(ffmpeg_args,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_bytes, ffmpeg_err = proc.communicate()
    if proc.returncode != 0:
        msg = (("ffmpeg failed to extract frame at time %.2f\n"
                "ffmpeg error message:\n%s") %
               (timestamp, ffmpeg_err.strip().decode('utf-8')))
        raise OSError(msg)

    if not frame_bytes:
        # empty output, no frame generated
        msg = ("ffmpeg generated no output "
               "(timestamp %.2f might be out of range)"
               "ffmpeg error message:\n%s" %
               (timestamp, ffmpeg_err.strip().decode('utf-8')))
        raise OSError(msg)

    try:
        frame_image = Image.open(io.BytesIO(frame_bytes))
    except IOError:
        raise OSError("failed to open frame with PIL.Image.open")

    return Frame(timestamp, frame_image)
