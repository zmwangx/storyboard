Installation
============

Dependencies
------------

* `FFmpeg <https://ffmpeg.org/>`_. Specifically, ``ffmpeg`` and
  ``ffprobe`` are required. See the `official download page
  <https://ffmpeg.org/download.html>`_ for installation options. On OS
  X, it is recommended that you use Homebrew: ::

    brew install ffmpeg

  Be sure to review the list of options in ``brew info
  ffmpeg``. storyboard should not depend on any of those options to
  function, but FFmpeg is a great tool in its own right (several
  orders of magnitude greater than storyboard), so you might want to
  link against optional dependencies for a better FFmpeg experience.

  Note that Libav is not and will not be supported, since ``avconv``
  and especially ``avprobe`` are crippled. Ubuntu and Debian users —
  blame your narrow-minded maintainers (see `The FFmpeg/Libav
  situation
  <http://blog.pkh.me/p/13-the-ffmpeg-libav-situation.html>`_). Fortunately,
  FFmpeg has made its comeback to Ubuntu's official repositories in
  `15.04 vivid <http://packages.ubuntu.com/vivid/ffmpeg>`_, after
  several years of unfair treatment.

* `Pillow <https://github.com/python-pillow/Pillow>`_. Wheel
  distributions of Pillow are provided for OS X and Windows on `PyPI
  <https://pypi.python.org/pypi/Pillow/>`_, so it is usually enough to
  do::

    pip install Pillow

  Pillow is listed as a requirement of storyboard in ``setup.py`` so
  you don't need to run this manually.

  On other platforms you have to satisfy the external dependencies of
  Pillow, especially ``libjpeg`` and ``libfreetype``. See `the
  official installation guide
  <https://pillow.readthedocs.org/installation.html>`_ for details.

Installation
------------

End users should install via ``pip``, and developers should use
``git`` instead.

Using pip
~~~~~~~~~

::

  pip install storyboard

To install a pre-release or development version, run::

  pip install --pre storyboard

Using git
~~~~~~~~~

If you want to be involved in the development (much appreciated), or
test the package on your platform, you need to clone the repo from
GitHub: ::

  git clone --recurse-submodules git@github.com:zmwangx/storyboard.git

There are some additional Python dependencies for testing and building
the documentations, which are listed in ``tests/requirements.txt`` and
``docs/requirements.txt``. ``virtualenv`` is highly recommended (since
the doc building environment is rather picky about versions — blame
NumPy on this). Therefore, to fully setup the development and build
environment, one would do

.. code-block:: bash

   pip install virtualenv
   cd $PROJECT_ROOT
   virtualenv venv
   source venv/bin/activate
   pip install -r requirements.txt -r tests/requirements.txt -r docs/requirements.txt -e .

Testing and doc building instructions are available in
`tests/README.md
<https://github.com/zmwangx/storyboard/blob/master/tests/README.md>`_
and `docs/README.md
<https://github.com/zmwangx/storyboard/blob/master/docs/README.md>`_,
respectively.
