#!/usr/bin/env python3

"""Extract video frames."""

from __future__ import absolute_import
from __future__ import print_function

import io
import os
import subprocess
import sys

from PIL import Image

class Frame(object):
    """Video frame object containing a timestamp and an image."""
    def __init__(self, timestamp, image):
        assert isinstance(timestamp, int) or isinstance(timestamp, float),\
            "timestamp is not an int or float"
        assert isinstance(image, Image.Image),\
            "image is not a PIL.Image.Image instance"
        self.timestamp = timestamp
        self.image = image

def extract_frame(video, timestamp, ffmpeg_bin='ffmpeg', codec='png'):
    """Seek to a specified timestamp in the given video file and return the
    corresponding frame.

    Positional arguments:
    video      -- path to the video file
    timestamp  -- an int or float in seconds specifying the timestamp to seek to

    Keyword arguments:
    ffmpeg_bin -- name or path of the FFmpeg binary, e.g., \"ffmpeg.exe\" on
                  Windows (default \"ffmpeg\")
    codec      -- codec of FFmpeg output image, which will be opened by
                  PIL.Image.open (default \"rawvideo\")

    Return value:
    A Frame object with the timestamp and the frame image as a PIL.Image.Image
    instance.
    """
    command = [ffmpeg_bin,
               '-ss', str(timestamp),
               '-i', video,
               '-f', 'image2',
               '-vcodec', codec,
               '-vframes', '1',
               '-']

    if not os.path.exists(video):
        raise IOError("video file '" + video + "' does not exist")

    # pylint: disable=unused-variable
    # the exception object err might be useful in the future
    try:
        frame_bytes = subprocess.check_output(command,
                                              stderr=open(os.devnull, "w"))
    except subprocess.CalledProcessError as err:
        msg = "error: failed to extract frame at time %.2f from video '%s'\n" %\
              (timestamp, video)
        sys.stderr.write(msg)

    if not frame_bytes:
        msg = "ffmpeg generated no output (timestamp might be out of range)"
        raise ValueError(msg)

    try:
        frame_image = Image.open(io.BytesIO(frame_bytes))
    except IOError as err:
        sys.exit("error: failed to open ffmpeg output with PIL.Image.open")

    return Frame(timestamp, frame_image)
