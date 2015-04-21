#!/usr/bin/env python3

from __future__ import division

import hashlib
import unittest

from storyboard.util import *


class TestUtil(unittest.TestCase):

    def test_round_up(self):
        self.assertAlmostEqual(round_up(1.0), 1.0)
        self.assertAlmostEqual(round_up(0.5), 1.0)
        self.assertAlmostEqual(round_up(0.0), 0.0)
        self.assertAlmostEqual(round_up(-0.5), 0.0)
        self.assertAlmostEqual(round_up(-1.0), -1.0)

    def test_evaluate_ratio(self):
        self.assertAlmostEqual(evaluate_ratio('15:20'), 3/4)
        self.assertAlmostEqual(evaluate_ratio('15/20'), 3/4)
        self.assertIsNone(evaluate_ratio('0:1'))
        self.assertIsNone(evaluate_ratio('1:0'))
        self.assertIsNone(evaluate_ratio('0:0'))
        self.assertIsNone(evaluate_ratio('0/1'))
        self.assertIsNone(evaluate_ratio('1/0'))
        self.assertIsNone(evaluate_ratio('0/0'))

    def test_humansize(self):
        self.assertEqual(humansize(1), '1B')
        self.assertEqual(humansize(100), '100B')
        self.assertEqual(humansize(1000), '1000B')
        self.assertEqual(humansize(10000), '9.77KiB')
        self.assertEqual(humansize(100000), '97.7KiB')
        self.assertEqual(humansize(10000000), '9.54MiB')
        self.assertEqual(humansize(100000000), '95.4MiB')
        self.assertEqual(humansize(1000000000), '954MiB')
        self.assertEqual(humansize(10000000000), '9.32GiB')

    def test_humantime(self):
        with self.assertRaises(ValueError):
            humantime(-1)
        self.assertEqual(humantime(1.006), '00:00:01.01')
        self.assertEqual(humantime(1.006, ndigits=1), '00:00:01.0')
        self.assertEqual(humantime(1.006, ndigits=0), '00:00:01')
        self.assertEqual(humantime(1.006, one_hour_digit=True), '0:00:01.01')
        self.assertEqual(humantime(10000), '02:46:40.00')
        self.assertEqual(humantime(50000, one_hour_digit=True), '13:53:20.00')

    def test_progress_bar(self):
        chunksize = 65536
        chunk = b'\x00' * chunksize
        nchunks = 16
        totalsize = chunksize * nchunks
        sha1 = hashlib.sha1()
        pbar = ProgressBar(totalsize, interval=0.001)
        pbar.force_update(totalsize)
        self.assertEqual(pbar.processed, totalsize)
        pbar.force_update(0)
        self.assertEqual(pbar.processed, 0)
        processed = 0
        for _ in range(0, nchunks):
            sha1.update(chunk)
            processed += chunksize
            pbar.update(chunksize)
            self.assertEqual(pbar.processed, processed)
        pbar.finish()
        self.assertEqual(sha1.hexdigest(),
                         '3b71f43ff30f4b15b5cd85dd9e95ebc7e84eb5a3')
        self.assertEqual(pbar.totalsize, totalsize)
        with self.assertRaises(AttributeError):
            pbar.processed
        with self.assertRaises(AttributeError):
            pbar.interval
        with self.assertRaises(RuntimeError):
            pbar.update(chunksize)
        with self.assertRaises(RuntimeError):
            pbar.force_update(0)
        with self.assertRaises(RuntimeError):
            pbar.finish()


if __name__ == '__main__':
    unittest.main()
