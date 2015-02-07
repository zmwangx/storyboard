#!/usr/bin/env python3

from __future__ import print_function

import io
import os
import subprocess
import sys

from PIL import Image

def extract_frame(video, timestamp, ffmpeg_bin='ffmpeg', codec='png'):
    """Seek to a specified timestamp in the given video file and return the
    corresponding frame as a PIL image.

    Positional arguments:
    video      -- path to the video file
    timestamp  -- a real number in seconds specifying the timestamp to seek to

    Keyword arguments:
    ffmpeg_bin -- name or path of the FFmpeg binary, e.g., \"ffmpeg.exe\" on
                  Windows (default \"ffmpeg\")
    codec      -- codec of FFmpeg output image, which will be opened by
                  PIL.Image.open (default \"rawvideo\")
    """
    command = [ ffmpeg_bin,
                '-ss', str(timestamp),
                '-i', video,
                '-f', 'image2',
                '-vcodec', codec,
                '-vframes', '1',
                '-' ]

    if not os.path.exists(video):
        raise IOError("video file '" + video + "' does not exist")

    try:
        frame_bytes = subprocess.check_output(command,
                                              stderr=open(os.devnull, "w"))
    except subprocess.CalledProcessError as err:
        print("error: ffmpeg failed to extract frame at time " + str(time) +
              " from video '" + video, sys.stderr + "'")
        raise

    if not frame_bytes:
        msg = "ffmpeg generated no output (timestamp might be out of range)"
        raise ValueError(msg)

    try:
        frame_image = Image.open(io.BytesIO(frame_bytes))
    except IOError as err:
        sys.exit("error: failed to open ffmpeg output with PIL.Image.open")

    return frame_image
