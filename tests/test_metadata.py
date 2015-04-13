#!/usr/bin/env python3

import os
import subprocess
import tempfile
import unittest

from storyboard import fflocate
from storyboard.metadata import *

class TestMetadata(unittest.TestCase):

    def setUp(self):
        _, self.videofile = tempfile.mkstemp(prefix='storyboard-test-',
                                             suffix='.mp4')
        bins = fflocate.guess_bins()
        fflocate.check_bins(bins) # error if bins do not exist
        self.ffmpeg_bin, self.ffprobe_bin = bins
        with open(os.devnull, 'wb') as devnull:
            command = [
                self.ffmpeg_bin,
                '-f', 'lavfi',
                '-i', 'color=c=pink:s=320x180:d=10',
                '-y', self.videofile
            ]
            subprocess.check_call(command, stdout=devnull, stderr=devnull)

    def tearDown(self):
        os.remove(self.videofile)

    def test_metadata(self):
        vid = Video(
            self.videofile,
            ffprobe_bin=self.ffprobe_bin,
            print_progress=False
        )

        output = vid.pretty_print_metadata()
        expected_output = """Filename:               {0}
File size:              8511 (8.32KiB)
Container format:       MPEG-4 Part 14 (MP4)
Duration:               00:00:10.00
Pixel dimensions:       320x180
Display aspect ratio:   16:9
Scan type:              Progressive scan
Frame rate:             25 fps
Streams:
    #0: Video, H.264 (High Profile level 1.2), 320x180 (DAR 16:9), 25 fps, 4 kb/s""" \
        .format(os.path.basename(self.videofile))

        self.assertEqual(output, expected_output)

if __name__ == '__main__':
    unittest.main()
