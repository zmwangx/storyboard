``metadata`` command line interface
===================================

The module :doc:`storyboard.metadata <storyboard.metadata>` comes with
a console script, which is essentially an entry point to its
``main()`` function. It extracts video metadata (container-level and
per-stream) using FFprobe, and prints them in a human readable manner
(more so than FFprobe). See `this gist
<https://gist.github.com/zmwangx/ee8986c2f0596f1ebbb0>`_ for a direct
comparison of ``metadata`` and ``ffprobe``'s human readability. The
basic invocation is::

  metadata [OPTIONS] VIDEO [VIDEO...]

See the section :ref:`options` for the list of command line options
and their detailed explanations. Some of them can also be stored in a
configuration file, ``~/.config/storyboard.conf``, under the
``metadata-cli`` section, in which case the config file option is also
documented. Note that an option specified on the command line always
overwrites those in config files.

See `configparser's doc
<https://docs.python.org/3/library/configparser.html>`_ for format of
a valid configuration file, or learn from the :ref:`sample
configuration file <sample-config-file>`.

.. _options:

Options
-------

-h, --help  Print help text and exit.

--ffprobe-bin=NAME
            The name or path of the ffprobe binary, which should be on
            the system or environment's search path. The binay is
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

--version   Print version number (e.g., `0.1`) and exit.

.. _sample-config-file:

Sample configuration file
-------------------------

The following config file should be put in
``~/.config/storyboard.conf`` to take effect.

.. code-block:: ini

   # This is a sample configuration file for the metadata CLI script.
   # It has to be in ~/.config/storyboard.conf to take effect.

   [metadata-cli]

   # Name or path of ffprobe binary, should be in the search path.
   ffprobe_bin = ffprobe

   # Uncomment to always include SHA-1 digest in output (slow).
   # include_sha1sum = on

   # The verbosity option can be on, off, or auto.
   verbose = auto

   # You may include other sections, e.g., storyboard-cli.
