#!/usr/bin/env python3

from __future__ import division

import os
import subprocess
import tempfile
import unittest

from storyboard import fflocate
from storyboard.metadata import *
from storyboard.util import humansize, humantime


class TestMetadata(unittest.TestCase):

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

    def test_metadata(self):
        vid = Video(self.videofile, params={
            'ffprobe_bin': self.ffprobe_bin,
            'print_progress': False,
        })
        self.assertEqual(vid.path, self.videofile)
        self.assertEqual(vid.filename, os.path.basename(self.videofile))
        self.assertIsNone(vid.title)
        self.assertIsInstance(vid.size, int)
        self.assertEqual(humansize(vid.size), vid.size_text)
        self.assertEqual(vid.format, 'Matroska')
        self.assertLess(abs(vid.duration - 10.0), 1.0)
        self.assertEqual(humantime(vid.duration), vid.duration_text)
        self.assertEqual(vid.dimension, (320, 180))
        self.assertEqual(vid.dimension_text, '320x180')
        self.assertAlmostEqual(vid.dar, 16/9)
        self.assertEqual(vid.dar_text, '16:9')
        self.assertEqual(vid.scan_type, 'Progressive scan')
        self.assertAlmostEqual(vid.frame_rate, 25.0)
        self.assertEqual(vid.frame_rate_text, '25 fps')
        self.assertIsInstance(vid.streams, list)
        self.assertEqual(len(vid.streams), 3)
        # video stream
        vstream = vid.streams[0]
        self.assertIsInstance(vstream, Stream)
        self.assertIsNotNone(vstream.codec)
        self.assertAlmostEqual(vstream.dar, 16/9)
        self.assertEqual(vstream.dar_text, '16:9')
        self.assertEqual(vstream.dimension, (320, 180))
        self.assertEqual(vstream.dimension_text, '320x180')
        self.assertAlmostEqual(vstream.frame_rate, 25.0)
        self.assertEqual(vstream.frame_rate_text, '25 fps')
        self.assertEqual(vstream.height, 180)
        self.assertEqual(vstream.index, 0)
        self.assertIsNotNone(vstream.info_string)
        self.assertIsNone(vstream.language_code)
        self.assertEqual(vstream.type, 'video')
        self.assertEqual(vstream.width, 320)
        # audio stream
        astream = vid.streams[1]
        self.assertIsNotNone(astream.codec)
        self.assertEqual(astream.index, 1)
        self.assertIsNone(astream.language_code)
        self.assertEqual(astream.type, 'audio')
        # subtitle stream
        sstream = vid.streams[2]
        self.assertIsNotNone(sstream.codec)
        self.assertEqual(sstream.index, 2)
        self.assertIsNone(sstream.language_code)
        self.assertEqual(sstream.type, 'subtitle')
        print('')
        print(vid.format_metadata())


if __name__ == '__main__':
    unittest.main()
