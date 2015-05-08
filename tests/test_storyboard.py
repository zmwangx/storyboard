#!/usr/bin/env python3

from __future__ import division

import imghdr
import os
import subprocess
import tempfile
import unittest

from PIL import Image, ImageFont

from storyboard import fflocate
from storyboard.frame import Frame
from storyboard.storyboard import *

from .testing_infrastructure import capture_stdout, capture_stderr, tee_stderr
from .testing_infrastructure import change_home


class TestStoryBoard(unittest.TestCase):

    def setUp(self):
        if not hasattr(self, 'assertRegex'):
            self.assertRegex = self.assertRegexpMatches
            self.assertNotRegex = self.assertNotRegexpMatches

        # create a mock srt subtitle file
        fd, self.srtfile = tempfile.mkstemp(prefix='storyboard-test-',
                                            suffix='.srt')
        os.close(fd)
        with open(self.srtfile, 'w') as fd:
            fd.write("1\n"
                     "00:00:01,000 --> 00:00:02,000\n"
                     "SubRip is the way to go\n")

        # create video file
        fd, self.videofile = tempfile.mkstemp(prefix='storyboard-test-',
                                              suffix='.mkv')
        os.close(fd)
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
        text_block_size = draw_text_block(canvas, (10, 10), text)
        # the following test is based on the current DEFAULT_FONT_FILE
        # and DEFAULT_FONT_SIZE (SourceCodePro-Regular at size 16)
        self.assertEqual(text_block_size, (60, 38))
        canvas.close()

    def test_create_thumbnail(self):
        frame = Frame(15.50, Image.new('RGBA', (320, 180), 'pink'))
        # default aspect ratio
        thumbnail = create_thumbnail(frame, 180)
        self.assertEqual(thumbnail.size, (180, 101))
        thumbnail.close()
        # custom aspect ratio with timestamp overlay
        thumbnail = create_thumbnail(
            frame, 180,
            params={
                'aspect_ratio': 1/1,
                'draw_timestamp': True,
                'timestamp_align': 'center',
            }
        )
        self.assertEqual(thumbnail.size, (180, 180))
        thumbnail.close()

    def test_tile_images(self):
        standard = Image.new('RGBA', (50, 50))
        larger = Image.new('RGBA', (60, 60))
        # default, consistent
        combined = tile_images(
            [standard, standard, standard, standard], (2, 2)
        )
        self.assertEqual(combined.size, (100, 100))
        combined.close()
        # default, wrong number of images
        with self.assertRaises(ValueError):
            combined = tile_images(
                [standard, standard, standard], (2, 2)
            )
        # default, inconsistent
        with self.assertRaises(ValueError):
            combined = tile_images(
                [standard, standard, standard, larger], (2, 2)
            )
        # inconsistent but work around with tile_size
        combined = tile_images(
            [standard, standard, standard, larger], (2, 2), params={
                'tile_size': (40, 40)
            }
        )
        self.assertEqual(combined.size, (80, 80))
        combined.close()
        # with all other options
        combined = tile_images(
            [standard, standard, standard, standard, standard, standard],
            (2, 3),
            params={
                'tile_spacing': (20, 10),
                'margins': (20, 10),
                'canvas_color': 'pink',
                'close_separate_images': True,
            }
        )
        self.assertEqual(combined.size, (160, 190))
        combined.close()
        # make sure that the separate images are closed
        with self.assertRaises(ValueError):
            standard.resize((25, 25))
        larger.close()

    def test_storyboard(self):
        sb = StoryBoard(self.videofile, params={
            'bins': (self.ffmpeg_bin, self.ffprobe_bin),
            'print_progress': True,
        })
        board = sb.gen_storyboard(params={
            'include_sha1sum': True,
            'print_progress': True,
        })
        # 480 * 4 (thumbnails) + 8 * 3 (tile spacing) + 10 * 2 (margins)
        # = 1964
        self.assertEqual(board.size[0], 1964)
        board.close()

    def assertImageFormat(self, image_format):
        image = sys.stdout.getvalue().strip()
        self.assertEqual(imghdr.what(image), image_format)
        # clean up
        os.remove(image)

    def assertProgressPrinted(self):
        # sys.stderr is not empty
        self.assertNotEqual(sys.stderr.getvalue(), '')

    def assertProgressNotPrinted(self):
        # sys.stderr is not empty
        self.assertEqual(sys.stderr.getvalue(), '')

    def test_main(self):
        with change_home() as home:
            config_dir = os.path.join(home, '.config')
            os.mkdir(config_dir)
            config_file = os.path.join(config_dir, 'storyboard.conf')

            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = ['--version']
                    with self.assertRaises(SystemExit):
                        main()
                    # cat output of stdout and stderr, since Python2
                    # prints version to stderr while Python3 prints
                    # version to stdout
                    output = (sys.stdout.getvalue().strip() +
                              sys.stderr.getvalue().strip())
                    self.assertEqual(output, version.__version__)

            # default
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = [self.videofile]
                    main()
                    self.assertImageFormat('jpeg')
                    self.assertProgressNotPrinted()

            # default, stderr is a tty
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = [self.videofile]
                        main()
                        self.assertImageFormat('jpeg')
                        self.assertProgressPrinted()

            # PNG via CLI argument
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = ['--output-format', 'png', self.videofile]
                    main()
                    self.assertImageFormat('png')
                    self.assertProgressNotPrinted()

            # PNG and verbose via config file
            with open(config_file, 'w') as f:
                f.write("[storyboard-cli]\n"
                        "output_format = png\n"
                        "verbose = on\n")
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = [self.videofile]
                    main()
                    self.assertImageFormat('png')
                    self.assertProgressPrinted()

            # bogus config file leads to warning
            with open(config_file, 'w') as f:
                f.write("[storyboard-cli]\n"
                        "verbose = unrecognizable\n")
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = [self.videofile]
                        main()
                        self.assertImageFormat('jpeg')
                        self.assertRegex(sys.stderr.getvalue(), 'warning')

            # another bogus config file
            with open(config_file, 'w') as f:
                f.write("[storyboard-cli]\n"
                        "output_format = no_such_format\n\n")
            with capture_stdout():
                with capture_stderr():
                    with self.assertRaises(SystemExit):
                        sys.argv[1:] = [self.videofile]
                        main()
                    self.assertRegex(sys.stderr.getvalue(), 'error')


if __name__ == '__main__':
    unittest.main()
