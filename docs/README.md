Docs are hosted on Read the Docs: <https://storyboard.readthedocs.org>.

Denpendencies for building docs are listed in `requirements.txt`. The alternative list `rtfd-requirements.txt` is specifically for Read the Docs, and includes project-wide dependencies. HTML docs can be built by

    make html

or on Windows

    ./make.bat html

in this directory. Remember to clone recursively, or `git submodule update --init` before building the docs.
