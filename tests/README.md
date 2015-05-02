The basic tests (`test_*.py` in `tests/`) can be run by

    python setup.py test

The complete test suite (including `doctest` and more tests in `tests/more`) can be run by

    nosetests --verbose --exe --with-coverage --cover-erase --cover-package=storyboard --with-doctest

Optionally, you may install tox (`pip install tox`), and run all tests on all supported Python versions (unavailable interpreters are skipped) as well as build the docs, all with a single command

    tox

from the project root.
