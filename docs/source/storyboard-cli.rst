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
:ref:`storyboard-options`). By default, JPEG of quality 85 is
used. The path to the image file is then printed to stdout for further
manipulation,

See the section :ref:`storyboard-options` for the list of command line
options and their detailed explanations. Some of them can also be
stored in a configuration file,
``$XDG_CONFIG_HOME/storyboard/storyboard.conf`` (or
``~/.config/storyboard/storyboard.conf`` if the environment variable
``XDG_CONFIG_HOME`` is not defined), under the ``storyboard-cli``
section. If that is the case, then the config file option is also
documented. Note that an option specified on the command line always
overrides its config file equivalent.

See `configparser's doc
<https://docs.python.org/3/library/configparser.html>`_ for the format
of a valid configuration file, or learn from the :ref:`sample
configuration file <storyboard-sample-config-file>`.

Additional customizations
-------------------------

**Note that not all customizations available in this package are
exposed through the CLI.** In fact, there are a host of parameters you
can tweak, exposed in the method ``gen_storyboard`` of
``storyboard.storyboard.StoryBoard``. See "Other Parameters" in the
`API reference
<./storyboard.storyboard.html#storyboard.storyboard.StoryBoard.gen_storyboard>`_
for details.

It is very easy to write a custom wrapper around the
``storyboard.storyboard.StoryBoard`` class. See the source code of
``storyboard.storyboard.main`` for an example implementation (the
source code location is linked next to `the API reference
<./storyboard.storyboard.html#storyboard.storyboard.main>`_.

.. _storyboard-options:

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

-f, --output-format=FORMAT
            The output format of the storyboard image(s). ``FORMAT``
            should be either ``jpeg`` or ``png``. Default is ``jpeg``.

            Note that ``jpeg`` format results in progressive JPEG
            images (optimized for transfer and display on the Web).

            This option can be stored in the config file as::

              output_format = (jpeg|png)

--quality=QUALITY
            Quality of output image(s) as an integer between 1
            and 100. Only meaning when the output format is JPEG; PNG
            is lossless anyway. Default is 85.

            This option can be stored in the config file as::

              quality = QUALITY

--exclude-sha1sum
            Exclude SHA-1 digest from the metadata section of the
            storyboard. By default the digest is included. Keep in
            mind that computing the SHA-1 digest is a rather expensive
            operation.

            This option can be stored in the config file as::

              exclude_sha1sum = (on|off)

--include-sha1sum
            Include SHA-1 digest in the metadata section of the
            storyboard. This option always overrides
            ``--exclude-sha1sum``. It is only useful when
            ``exclude_sha1sum`` is turned on by default in the config
            file.

--video-duration=SECONDS
            Duration of the video in seconds (float). Most of the time
            this option is not needed; the duration is extracted from
            container metadata. However, in the rare situation where
            ffprobe cannot extract or extracts the wrong duration (in
            that case the storyboard will be ruined as thumbnail
            timestamps are computed from the total duration), use this
            option to manually pass in the duration of the video.

            Note, however, that this option activates `output seeking
            <https://trac.ffmpeg.org/wiki/Seeking#Outputseeking>`_
            (i.e., decode and seek frame by frame), which is extremely
            slow, and the current implementation of frame extraction
            in `storyboard` (extract each frame seperately) makes it
            even slower. The issue is already documented; see `#3
            <https://github.com/zmwangx/storyboard/issues/3>`_ and
            `#24
            <https://github.com/zmwangx/storyboard/issues/24>`_. Please
            comment in #24 if you want to see improvements to this, or
            if you have a good idea of implementation.

-v, --verbose=STATE
            Whether to print progress information to stderr (actual
            output metadata is printed to stdout and not
            affected). STATE is optional and can take one of the three
            values: ``on``, ``off``, or ``auto``; default is
            ``auto``. If STATE is ``auto``, then progress information
            is printed if and only stderr is connected to a tty.

            This option can be stored in the config file as::

              verbose = (auto|on|off)

--version   Print version number (e.g., ``0.1``) and exit.

.. _storyboard-sample-config-file:

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

   # Name or path of the ffmpeg and ffprobe binaries, should be in the
   # search path.
   ffmpeg_bin = ffmpeg
   ffprobe_bin = ffprobe

   # Image output format, either 'jpeg' or 'png'. Default is 'jpeg'.
   output_format = jpeg

   # Image output quality, integer between 1 and 100. Only meaningful
   # when output format is 'jpeg'. Default is 85.
   quality = 85

   # Uncomment to always exclude SHA-1 digest from the storyboard.
   # exclude_sha1sum = on

   # The verbosity option can be on, off, or auto.
   verbose = auto

   # You may include other sections, e.g., metadata-cli.
