#!/usr/bin/env python3

from __future__ import division

import os
import subprocess
import tempfile
import unittest

from PIL import Image, ImageFont, ImageFont

from storyboard import fflocate
from storyboard.frame import Frame
from storyboard.storyboard import *
from storyboard.storyboard import _draw_text_block
from storyboard.storyboard import _create_thumbnail


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

    def test_font(self):
        # test default font with default size
        font = Font()
        self.assertEqual(font.size, DEFAULT_FONT_SIZE)
        self.assertIsInstance(font.obj, ImageFont.FreeTypeFont)
        self.assertEqual(font.obj.path, DEFAULT_FONT_FILE)
        self.assertEqual(font.obj.size, DEFAULT_FONT_SIZE)
        # test default font with custom size
        font = Font(font_size=10)
        self.assertEqual(font.size, 10)
        self.assertIsInstance(font.obj, ImageFont.FreeTypeFont)
        self.assertEqual(font.obj.path, DEFAULT_FONT_FILE)
        self.assertEqual(font.obj.size, 10)
        # test a nonexistent font
        with self.assertRaises(OSError):
            font = Font(font_file='')

    def test_draw_text_block(self):
        canvas = Image.new('RGBA', (100, 100), 'white')
        text = "hello,\nworld!\n"
        text_block_size = _draw_text_block(canvas, (10, 10), text)
        # the following test is based on the current DEFAULT_FONT_FILE
        # and DEFAULT_FONT_SIZE (SourceCodePro-Regular at size 16)
        self.assertEqual(text_block_size, (60, 38))
        canvas.close()

    def test_create_thumbnail(self):
        frame = Frame(15.50, Image.new('RGBA', (320, 180), 'pink'))
        # default aspect ratio
        thumbnail = _create_thumbnail(frame, 180)
        self.assertEqual(thumbnail.size, (180, 101))
        thumbnail.close()
        # custom aspect ratio with timestamp overlay
        thumbnail = _create_thumbnail(
            frame, 180,
            params={
                'aspect_ratio': 1/1,
                'draw_timestamp': True,
                'timestamp_align': 'center',
            }
        )
        self.assertEqual(thumbnail.size, (180, 180))
        thumbnail.close()

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
        board.close()


if __name__ == '__main__':
    unittest.main()
