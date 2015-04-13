#!/usr/bin/env python3

import os
import subprocess
import tempfile
import unittest

from storyboard import fflocate
from storyboard.storyboard import *

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

    def test_storyboard(self):
        sb = StoryBoard(
            self.videofile,
            ffmpeg_bin=self.ffmpeg_bin,
            ffprobe_bin=self.ffprobe_bin,
            print_progress=False,
        )
        board = sb.storyboard(
            include_sha1sum=True,
            print_progress=False,
        )

if __name__ == '__main__':
    unittest.main()
