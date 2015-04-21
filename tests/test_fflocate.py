#!/usr/bin/env python3

import unittest

from storyboard.fflocate import *


class TestFFlocate(unittest.TestCase):

    def test_guess_bins(self):
        bins = guess_bins()
        self.assertIsInstance(bins, tuple)
        self.assertIs(len(bins), 2)

    def test_check_bins(self):
        # insist that ffmpeg and ffprobe are installed in PATH in the testing
        # system
        self.assertTrue(check_bins(guess_bins()))
        self.assertTrue(check_bins((None, None)))
        with self.assertRaises(OSError):
            check_bins(('', ''))


if __name__ == '__main__':
    unittest.main()
