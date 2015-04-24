#!/usr/bin/env python3

from __future__ import division

import argparse
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import hashlib
import os
import tempfile
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

    def test_option_reader(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--str')
        parser.add_argument('--int', type=int)
        parser.add_argument('--float', type=float)
        parser.add_argument('--true', action='store_true')
        parser.add_argument('--false', action='store_false')
        cli_arg_string = "--str from-cli --int 0 --float 0.5 --true --false"
        cli_args = parser.parse_args(cli_arg_string.split())

        config = configparser.ConfigParser()
        config.add_section('sec')
        config.set('sec', 'str', 'from-config-file')
        config.set('sec', 'int', '1')
        config.set('sec', 'float', '1.5')
        config.set('sec', 'true', 'no')
        config.set('sec', 'false', 'yes')
        config.set('sec', 'confonly-str', 'from-config-file')
        config.set('sec', 'confonly-int', '1')
        config.set('sec', 'confonly-float', '1.5')
        config.set('sec', 'confonly-true', 'no')  # note the twist here
        config.set('sec', 'confonly-false', 'yes')
        config.add_section('dummysec')
        fd, conf_file = tempfile.mkstemp(prefix='storyboard-test-',
                                         suffix='.conf')
        os.close(fd)
        with open(conf_file, 'w') as f:
            config.write(f)

        fd, malformed_conf_file = tempfile.mkstemp(prefix='storyboard-test-',
                                                   suffix='.conf')
        os.close(fd)
        with open(malformed_conf_file, 'w') as f:
            f.write("no section\n")

        defaults = {
            'str': 'from-defaults',
            'int': 2,
            'float': 2.5,
            'true': True,
            'false': False,
            'confonly-str': 'from-defaults',
            'confonly-int': 2,
            'confonly-float': 2.5,
            'confonly-true': True,
            'confonly-false': False,
            'defaultonly-str': 'from-defaults',
            'defaultonly-int': 2,
            'defaultonly-float': 2.5,
            'defaultonly-true': True,
            'defaultonly-false': False,
        }

        or1 = OptionReader(
            cli_args=cli_args,
            config_files=conf_file,
            section='sec',
            defaults=defaults,
        )
        self.assertEqual(or1.opt('str'), 'from-cli')
        self.assertEqual(or1.opt('int', opttype=int), 0)
        self.assertAlmostEqual(or1.opt('float', opttype=float), 0.5)
        self.assertTrue(or1.opt('true', opttype=bool))
        self.assertFalse(or1.opt('false', opttype=bool))
        self.assertEqual(or1.opt('confonly-str'), 'from-config-file')
        self.assertEqual(or1.opt('confonly-int', opttype=int), 1)
        self.assertAlmostEqual(or1.opt('confonly-float', opttype=float), 1.5)
        self.assertFalse(or1.opt('confonly-true', opttype=bool))
        self.assertTrue(or1.opt('confonly-false', opttype=bool))
        self.assertEqual(or1.opt('defaultonly-str'), 'from-defaults')
        self.assertEqual(or1.opt('defaultonly-int', opttype=int), 2)
        self.assertAlmostEqual(or1.opt('defaultonly-float', opttype=float),
                               2.5)
        self.assertTrue(or1.opt('defaultonly-true', opttype=bool))
        self.assertFalse(or1.opt('defaultonly-false', opttype=bool))
        self.assertIsNone(or1.opt('non-existent-opt'))
        with self.assertRaises(ValueError):
            or1.opt('confonly-str', opttype=bool)
        with self.assertRaises(ValueError):
            or1.opt('confonly-str', opttype=tuple)
        self.assertEqual(or1.cli_opt('str'), 'from-cli')
        self.assertIsNone(or1.cli_opt('confonly-str'))
        self.assertEqual(or1.cfg_opt('confonly-str'), 'from-config-file')
        self.assertEqual(or1.cfg_opt('confonly-str', opttype=str),
                         'from-config-file')
        self.assertIsNone(or1.cfg_opt('defaultonly-str'))
        self.assertEqual(or1.default_opt('defaultonly-str'), 'from-defaults')
        self.assertIsNone(or1.default_opt('non-existent-opt'))
        with self.assertRaises(ValueError):
            or1.cfg_opt('confonly-str', opttype=bool)
        with self.assertRaises(ValueError):
            or1.cfg_opt('confonly-str', opttype=tuple)

        or2 = OptionReader(
            cli_args=None,
            config_files=conf_file,
            section='sec',
            defaults=defaults,
        )
        self.assertEqual(or2.opt('str'), 'from-config-file')
        self.assertEqual(or2.opt('int', opttype=int), 1)
        self.assertAlmostEqual(or2.opt('float', opttype=float), 1.5)
        self.assertFalse(or2.opt('true', opttype=bool))
        self.assertTrue(or2.opt('false', opttype=bool))

        or3 = OptionReader(
            cli_args=None,
            config_files=conf_file,
            section='dummysec',
            defaults=defaults,
        )
        self.assertEqual(or3.opt('confonly-str'), 'from-defaults')
        self.assertEqual(or3.opt('confonly-int', opttype=int), 2)
        self.assertAlmostEqual(or3.opt('confonly-float', opttype=float), 2.5)
        self.assertTrue(or3.opt('confonly-true', opttype=bool))
        self.assertFalse(or3.opt('confonly-false', opttype=bool))

        or4 = OptionReader(
            cli_args=None,
            config_files=conf_file,
            section='nonexistent-sec',
            defaults=defaults,
        )
        self.assertEqual(or4.opt('confonly-str'), 'from-defaults')
        self.assertEqual(or4.opt('confonly-int', opttype=int), 2)
        self.assertAlmostEqual(or4.opt('confonly-float', opttype=float), 2.5)
        self.assertTrue(or4.opt('confonly-true', opttype=bool))
        self.assertFalse(or4.opt('confonly-false', opttype=bool))

        or5 = OptionReader()
        self.assertIsNone(or5.opt('str'))

        with self.assertRaises(configparser.Error):
            or6 = OptionReader(
                config_files=[conf_file, malformed_conf_file],
                section='sec',
            )

        os.remove(conf_file)


if __name__ == '__main__':
    unittest.main()
