The basic tests (`test_*.py` in `tests/`) can be run by

    python setup.py test

The complete test suite (including `doctest` and more tests in `tests/more`) can be run by

    nosetests --verbose --exe --with-coverage --cover-erase --cover-package=storyboard --with-doctest
