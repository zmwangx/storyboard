#!/usr/bin/env python3

import os
import subprocess
import tempfile
import unittest2

from storyboard import fflocate
from storyboard.storyboard import *


class TestStoryBoard(unittest.TestCase):

    def setUp(self):
        # create a mock srt subtitle file
        _, self.srtfile = tempfile.mkstemp(prefix='storyboard-test-',
                                           suffix='.srt')
        with open(self.srtfile, 'w') as fd:
            fd.write("1\n"
                     "00:00:01,000 --> 00:00:02,000\n"
                     "SubRip is the way to go\n")

        # create video file
        _, self.videofile = tempfile.mkstemp(prefix='storyboard-test-',
                                             suffix='.mkv')
        bins = fflocate.guess_bins()
        fflocate.check_bins(bins)  # error if bins do not exist
        self.ffmpeg_bin, self.ffprobe_bin = bins
        with open(os.devnull, 'wb') as devnull:
            command = [
                self.ffmpeg_bin,
                # video stream (320x180, pure pink)
                '-f', 'lavfi',
                '-i', 'color=c=pink:s=320x180:d=10',
                # audio stream (silent)
                '-f', 'lavfi',
                '-i', 'aevalsrc=0:d=10',
                # subtitle stream
                '-i', self.srtfile,
                # output option
                '-y', self.videofile
            ]
            subprocess.check_call(command, stdout=devnull, stderr=devnull)

    def tearDown(self):
        os.remove(self.srtfile)
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
