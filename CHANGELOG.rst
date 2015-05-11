Changelog
---------

0.1.01
~~~~~~

* Officially added support for PyPy2 and PyPy3 (although PyPy,
  especially PyPy2, is slower than CPython in this case)
* A few extremely minor bug fixes and improvements; nothing changed
  from a user's perspective

0.1
~~~

*Date: 2015-05-08*

Hey, the stable is here!

* Completed documentation: http://storyboard.rtfd.org
* Added ``--include-sha1sum`` option to console script ``storyboard``
  (useful when SHA-1 digest is disabled from config file)
* Fixed frame extraction when video duration is missing or wrong in
  container metadata

0.1b2
~~~~~

*Date: 2015-05-08*

* CLI overhaul (be sure to check out the `CLI reference
  <https://storyboard.readthedocs.org/en/latest/cli.html>`_); the CLI
  is stable now
* Greatly improved docs (not finished yet, will be completed before
  the soon-to-be-released 0.1)

0.1b1
~~~~~

*Date: 2015-04-21*

* Completely refactored API (API is much more extensible now, and
  should be relatively stable from this point onward, at least until
  0.1 stable)
* Almost complete rewrite under the hood -- everything should be much
  more robust now
* Support more formats and codecs, improve handling of existing
  formats and codecs
* Much better error handling in many places (e.g., when duration is
  unavailable, it is just marked as unavailable in the output, rather
  than throws)
* Upped the game for several orders of maginitude on the doc side --
  now you can build beautiful autodocs (I've yet to construct the
  manual part of the docs, so I won't release the docs to RTD or
  pythonhosted.org just yet)
* Integrated with Travis (Ubuntu), AppVeyor (Windows), Coveralls.io
  (web interface for coverage), and Landscape.io (Python code quality
  check -- basically linter as a CI) to ensure code quality

0.1a4
~~~~~

*Date: 2015-04-14*

* Improved error handling at various places
* Wrote a test suite (and successfully tested on Ubuntu 14.04 LTS)

0.1a3
~~~~~

*Date: 2015-04-11*

* Reimplement scan type detection (now much more robust, and able to
  detect telecine)
* Tested on Windows 8.1, and fixed progress bar printing issue within
  cmd.exe and PowerShell (see `#14
  <https://github.com/zmwangx/storyboard/issues/14>`__)

0.1a2
~~~~~

*Date: 2015-04-09*

* Print progress information to console
* Version info included in banner

0.1a1
~~~~~

*Date: 2015-04-05*

* Initial release
