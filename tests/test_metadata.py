#!/usr/bin/env python3

from __future__ import division

import os
import subprocess
import sys
import tempfile
import unittest

from storyboard import fflocate
from storyboard.metadata import *
from storyboard.util import humansize, humantime
from storyboard import version

from .testing_infrastructure import capture_stdout, capture_stderr, tee_stderr
from .testing_infrastructure import change_home


class TestMetadata(unittest.TestCase):

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

    def test_video(self):
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
        # sha1sum
        sha1sum = vid.compute_sha1sum()
        self.assertEqual(vid.sha1sum, sha1sum)
        self.assertEqual(len(sha1sum), 40)
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
        print(vid.format_metadata(params={'include_sha1sum': True}))
        # specifically test the video_duration option
        vid = Video(self.videofile, params={
            'ffprobe_bin': self.ffprobe_bin,
            'video_duration': 10.0,
            'print_progress': False,
        })
        self.assertAlmostEqual(vid.duration, 10.0)
        self.assertEqual(humantime(vid.duration), vid.duration_text)

    def assertSha1sumIncluded(self):
        # sys.stdout has to support getvalue (e.g., through
        # capture_stdout)
        self.assertRegex(sys.stdout.getvalue(), 'SHA-1 digest:')

    def assertSha1sumNotIncluded(self):
        self.assertNotRegex(sys.stdout.getvalue(), 'SHA-1 digest:')

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
                    self.assertSha1sumNotIncluded()
                    self.assertProgressNotPrinted()

            # wrong ffprobe
            with capture_stdout():
                with capture_stderr():
                    with self.assertRaises(SystemExit):
                        sys.argv[1:] = ['--ffprobe-bin', '', self.videofile]
                        main()

            # include sha1sum through CLI argument, but stderr is not a tty
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = ['--include-sha1sum', self.videofile]
                    main()
                    self.assertSha1sumIncluded()
                    self.assertProgressNotPrinted()

            # include sha1sum through CLI argument, and stderr is a tty
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = ['--include-sha1sum', self.videofile]
                        main()
                        self.assertSha1sumIncluded()
                        self.assertProgressPrinted()

            # include sha1sum, stderr is not tty, force verbose on
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = ['--include-sha1sum', '-v', 'on',
                                    self.videofile]
                    main()
                    self.assertSha1sumIncluded()
                    self.assertProgressPrinted()

            # include sha1sum, stderr is a tty, force verbose off
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = ['--include-sha1sum', '-v', 'off',
                                        self.videofile]
                        main()
                        self.assertSha1sumIncluded()
                        self.assertProgressNotPrinted()

            # write a config file
            with open(config_file, 'w') as f:
                f.write("[metadata-cli]\n"
                        "include_sha1sum = on\n"
                        "verbose = on\n")

            # config file only
            with capture_stdout():
                with capture_stderr():
                    sys.argv[1:] = [self.videofile]
                    main()
                    self.assertSha1sumIncluded()
                    self.assertProgressPrinted()

            # overwrite include_sha1sum with --exclude-sha1sum
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = ['--exclude-sha1sum', self.videofile]
                        main()
                        self.assertSha1sumNotIncluded()
                        self.assertProgressPrinted()

            # overwrite both
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = ['--exclude-sha1sum', '-v', 'auto',
                                        self.videofile]
                        main()
                        self.assertSha1sumNotIncluded()
                        self.assertProgressNotPrinted()

            # bogus config file
            with open(config_file, 'w') as f:
                f.write("[metadata-cli]\n"
                        "verbose = unrecognizable\n")

            # verbose not in on, off, auto leads to warning
            if sys.stderr.isatty():
                with capture_stdout():
                    with tee_stderr():
                        sys.argv[1:] = [self.videofile]
                        main()
                        self.assertSha1sumNotIncluded()
                        self.assertRegex(sys.stderr.getvalue(), 'warning')

            # another bogus config file
            with open(config_file, 'w') as f:
                f.write("[metadata-cli]\n"
                        "include_sha1sum = unrecognizable\n\n")

            with capture_stdout():
                with capture_stderr():
                    with self.assertRaises(ValueError):
                        sys.argv[1:] = [self.videofile]
                        main()


if __name__ == '__main__':
    unittest.main()
