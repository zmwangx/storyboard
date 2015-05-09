``metadata`` command line interface
===================================

The module :doc:`storyboard.metadata <storyboard.metadata>` comes with
a console script, which is essentially an entry point to its
``main()`` function. It extracts video metadata (container-level and
per-stream) using FFprobe, and prints them in a human readable manner
(more so than FFprobe). An example output is::

  Filename:               2015_mar_1080_cc.m4v
  File size:              6083965352 (5.67GiB)
  Container format:       MPEG-4 Part 14 (M4V)
  Duration:               01:34:45.27
  Pixel dimensions:       1920x1080
  Display aspect ratio:   16:9
  Scan type:              Progressive scan
  Frame rate:             29.97 fps
  Streams:
      #0: Audio (eng), AAC (Low-Complexity), 99 kb/s
      #1: Video, H.264 (Main Profile level 4.1), 1920x1080 (DAR 16:9), 29.97 fps, 8453 kb/s
      #2: Subtitle (eng), closed caption (EIA-608 / CEA-708)

See `this gist
<https://gist.github.com/zmwangx/ee8986c2f0596f1ebbb0>`_ for a direct
comparison of ``metadata`` and ``ffprobe``'s human readability.

Synopsis
--------

The basic invocation is::

  metadata [OPTIONS] VIDEO [VIDEO...]

As can be seen from the invocation, one can specify multiple video
files, and the outputs for two adjacent files will be separated by a
blank line.

See the section :ref:`metadata-options` for the list of command line
options and their detailed explanations. Some of them can also be
stored in a configuration file,
``$XDG_CONFIG_HOME/storyboard/storyboard.conf`` (or
``~/.config/storyboard/storyboard.conf`` if the environment variable
``XDG_CONFIG_HOME`` is not defined), under the ``metadata-cli``
section. If that is the case, then the config file option is also
documented. Note that an option specified on the command line always
overrides its config file equivalent.

See `configparser's doc
<https://docs.python.org/3/library/configparser.html>`_ for the format
of a valid configuration file, or learn from the :ref:`sample
configuration file <metadata-sample-config-file>`.

.. _metadata-options:

Options
-------

-h, --help  Print help text and exit.

--ffprobe-bin=NAME
            The name or path of the ffprobe binary, which should be on
            the system or environment's search path. The binary is
            guessed from OS type if this option is not specified
            (e.g., ``ffprobe`` on OS X and Linux, and ``ffprobe.exe``
            on Windows).

            This option can be stored in the config file as::

              ffprobe_bin = NAME

-s, --include-sha1sum
            Include hexadecimal SHA-1 digest in the output. By default
            the digest is not included. Keep in mind that computing
            the SHA-1 digest is an expensive operation.

            This option can be stored in the config file as::

              include_sha1sum = (on|off)

--exclude-sha1sum
            Exclude SHA-1 digest in the output. This option always
            overrides ``--include-sha1sum``. It is only useful when
            ``include_sha1sum`` is turned on by default in the config
            file.

-v, --verbose=STATE
            Whether to print progress information to stderr (actual
            output metadata is printed to stdout and not
            affected). STATE is optional and can take one of the three
            values: ``on``, ``off``, or ``auto``; default is
            ``auto``. If STATE is ``auto``, then progress information
            is printed if and only if the ``--include-sha1sum`` option
            is also supplied *and* stderr is connected to a tty.

            This option can be stored in the config file as::

              verbose = (auto|on|off)

--version   Print version number (e.g., ``0.1``) and exit.

.. _metadata-sample-config-file:

Sample configuration file
-------------------------

The following config file should be put in
``$XDG_CONFIG_HOME/storyboard/storyboard.conf`` (or
``~/.config/storyboard/storyboard.conf`` if the environment variable
``XDG_CONFIG_HOME`` is not defined) to take effect

.. code-block:: ini

   # This is a sample configuration file for the metadata CLI script.
   # It has to be in $XDG_CONFIG_HOME/storyboard/storyboard.conf (or
   # ~/.config/storyboard/storyboard.conf if the environment variable
   # XDG_CONFIG_HOME is not defined) to take effect.

   [metadata-cli]

   # Name or path of ffprobe binary, should be in the search path.
   ffprobe_bin = ffprobe

   # Uncomment to always include SHA-1 digest in output (slow).
   # include_sha1sum = on

   # The verbosity option can be on, off, or auto.
   verbose = auto

   # You may include other sections, e.g., storyboard-cli.
