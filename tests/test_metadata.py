#!/usr/bin/env python3

from __future__ import division

import os
import subprocess
import tempfile
import unittest

from storyboard import fflocate
from storyboard.metadata import *
from storyboard.util import humansize


class TestMetadata(unittest.TestCase):

    def setUp(self):
        _, self.videofile = tempfile.mkstemp(prefix='storyboard-test-',
                                             suffix='.mp4')
        bins = fflocate.guess_bins()
        fflocate.check_bins(bins)  # error if bins do not exist
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
        vid = Video(self.videofile, params={
            'ffprobe_bin': self.ffprobe_bin,
            'print_progress': False,
        })
        self.assertEqual(vid.path, self.videofile)
        self.assertEqual(vid.filename, os.path.basename(self.videofile))
        self.assertIsNone(vid.title)
        self.assertIsInstance(vid.size, int)
        self.assertEqual(humansize(vid.size), vid.size_text)
        self.assertEqual(vid.format, 'MPEG-4 Part 14 (MP4)')
        self.assertAlmostEqual(vid.duration, 10.0)
        self.assertEqual(vid.duration_text, '00:00:10.00')
        self.assertEqual(vid.dimension, (320, 180))
        self.assertEqual(vid.dimension_text, '320x180')
        self.assertAlmostEqual(vid.dar, 16/9)
        self.assertEqual(vid.dar_text, '16:9')
        self.assertEqual(vid.scan_type, 'Progressive scan')
        self.assertAlmostEqual(vid.frame_rate, 25.0)
        self.assertEqual(vid.frame_rate_text, '25 fps')
        self.assertIsInstance(vid.streams, list)
        self.assertEqual(len(vid.streams), 1)
        stream = vid.streams[0]
        self.assertIsInstance(stream, Stream)
        self.assertIsNotNone(stream.codec)
        self.assertAlmostEqual(stream.dar, 16/9)
        self.assertEqual(stream.dar_text, '16:9')
        self.assertEqual(stream.dimension, (320, 180))
        self.assertEqual(stream.dimension_text, '320x180')
        self.assertAlmostEqual(stream.frame_rate, 25.0)
        self.assertEqual(stream.frame_rate_text, '25 fps')
        self.assertEqual(stream.height, 180)
        self.assertEqual(stream.index, 0)
        self.assertIsNotNone(stream.info_string)
        self.assertIsNone(stream.language_code)
        self.assertEqual(stream.type, 'video')
        self.assertEqual(stream.width, 320)
        print('')
        print(vid.format_metadata())


if __name__ == '__main__':
    unittest.main()
