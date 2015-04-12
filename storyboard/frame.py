#!/usr/bin/env python3

"""Extract video frames."""

from __future__ import absolute_import
from __future__ import print_function

import io
import os
import subprocess

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
    if not os.path.exists(video):
        raise OSError("video file '" + video + "' does not exist")

    ffmpeg_args = [ffmpeg_bin,
                   '-ss', str(timestamp),
                   '-i', video,
                   '-f', 'image2',
                   '-vcodec', codec,
                   '-vframes', '1',
                   '-hide_banner',
                   '-']
    proc = subprocess.Popen(ffmpeg_args,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    frame_bytes, ffmpeg_err = proc.communicate()
    if proc.returncode != 0:
        msg = ("ffmpeg failed to extract frame at time %.2f\n" +\
               "ffmpeg error message:\n%s") %\
              (timestamp, ffmpeg_err.strip().decode('utf-8'))
        raise OSError(msg)

    if not frame_bytes:
        # empty output, no frame generated
        msg = "ffmpeg generated no output " + \
              "(timestamp %.2f might be out of range)" % timestamp
        raise OSError(msg)

    try:
        frame_image = Image.open(io.BytesIO(frame_bytes))
    except IOError:
        raise OSError("failed to open frame with PIL.Image.open")

    return Frame(timestamp, frame_image)
