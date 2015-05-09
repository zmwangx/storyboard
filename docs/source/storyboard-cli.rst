``storyboard`` command line interface
=====================================

The module :doc:`storyboard.storyboard <storyboard.storyboard>` comes
with a console script, which is essentially an entry point to its
``main()`` function. It generates video storyboards with metadata
sheets. The :doc:`sample` page contains a few samples generated with
the default settings.

Synopsis
--------

The basic invocation is::

  storyboard [OPTIONS] VIDEO [VIDEO...]

As can be seen from the invocation, one can specify multiple video
files, and they will be processed one by one.

After a storyboard image is generated, it is saved to a temporary
file. The format of the image file (JPEG or PNG) can be controlled via
the ``-f,--output-format`` option, and the JPEG quality can be
controlled via the ``--quality`` option (more details in
:ref:`options`). By default, JPEG of quality 85 is used. The path to
the image file is then printed to stdout for further manipulation,

See the section :ref:`options` for the list of command line options
and their detailed explanations. Some of them can also be stored in a
configuration file, ``$XDG_CONFIG_HOME/storyboard/storyboard.conf``
(or ``~/.config/storyboard/storyboard.conf`` if the environment
variable ``XDG_CONFIG_HOME`` is not defined), under the
``storyboard-cli`` section. If that is the case, then the config file
option is also documented. Note that an option specified on the
command line always overrides its config file equivalent.

See `configparser's doc
<https://docs.python.org/3/library/configparser.html>`_ for the format
of a valid configuration file, or learn from the :ref:`sample
configuration file <sample-config-file>`.

.. _options:

Options
-------

-h, --help  Print help text and exit.

--ffmpeg-bin=NAME, --ffprobe-bin=NAME
            The name or path of the ffmpeg or ffprobe binary, both of
            which should be on the system or environment's search
            path. The binaries are guessed from OS type if this option
            is not specified (e.g., ``ffmpeg`` and ``ffprobe`` on OS X
            and Linux, and ``ffmpeg.exe`` and ``ffprobe.exe`` on
            Windows).

            These two options can be stored in the config file as::

              ffmpeg_bin = NAME
              ffprobe_bin = NAME

-v, --verbose=STATE
            Whether to print progress information to stderr (actual
            output metadata is printed to stdout and not
            affected). STATE is optional and can take one of the three
            values: ``on``, ``off``, or ``auto``; default is
            ``auto``. If STATE is ``auto``, then progress information
            is printed if and only stderr is connected to a tty.

            This option can be stored in the config file as::

              verbose = (auto|on|off)

--version   Print version number (e.g., `0.1`) and exit.

.. _sample-config-file:

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

   [storyboard-cli]

   # Name or path of the ffmpeg or ffprobe binary, should be in the
   # search path.
   ffmpeg_bin = ffmpeg
   ffprobe_bin = ffprobe

   # Uncomment to always exclude SHA-1 digest from the storyboard.
   # exclude_sha1sum = yes

   # The verbosity option can be on, off, or auto.
   verbose = auto

   # You may include other sections, e.g., metadata-cli.
