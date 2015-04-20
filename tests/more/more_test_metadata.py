#!/usr/bin/env python3

import os
import re
import unittest

from storyboard.metadata import *


HERE = os.path.dirname(os.path.realpath(__file__))
SAMPLEDIR = os.path.join(HERE, 'samples')
RESULT_FILE_PATTERN = re.compile(r'.*\.out$')


class MoreTestMetadata(unittest.TestCase):

    def more_test_metadata(self):
        for filename in os.listdir(SAMPLEDIR):
            if RESULT_FILE_PATTERN.match(filename):
                continue
            sample_path = os.path.join(SAMPLEDIR, filename)
            result_path = sample_path + '.out'
            sample = Video(sample_path)
            result = sample.format_metadata(params={
                'include_sha1sum': True,
            }).strip()
            with open(result_path, 'r') as fd:
                expected_result = fd.read().strip()
            self.assertEqual(result, expected_result)

if __name__ == '__main__':
    unittest.main()
