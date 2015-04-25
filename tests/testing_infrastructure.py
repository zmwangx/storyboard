#!/usr/bin/env python3

"""Some shared testing infrastructure."""

from contextlib import contextmanager
import io
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
import os
import shutil
import sys
import tempfile


class NormalizedStringIO(StringIO):
    """StringIO, with write operations normalized to unicode."""

    def __init__(self, buffer=None):
        super(NormalizedStringIO, self).__init__(buffer)

    @staticmethod
    def normalized(s):
        # s is Python2 str or unicode, or Python3 str or bytes
        # goal is to convert to Python2 unicode, or Python3 str
        try:
            if type(s) is not unicode:
                return s.decode('utf-8')
            else:
                return s
        except NameError:
            if type(s) is not str:
                return s.decode('utf-8')
            else:
                return s

    def write(self, s):
        super(NormalizedStringIO, self).write(self.normalized(s))

    def writelines(self,lines):
        lines = [self.normalized(line) for line in lines]
        super(NormalizedStringIO, self).writelines(lines)


class Tee(io.TextIOBase):
    """Duplicate all output to a text stream on a StringIO stream.

    This class implements a write-only (unreadable, unseekable)
    io.TextIOBase based on a given io.TextIOBase stream, and duplicates
    all write operations on a intrinsic StringIO stream. The class can
    be used to tee output, e.g., sys.stderr, to a string. To use this
    class, make normal calls as if it is the base stream, with the
    exception that one can call getvalue() as if it is also a StringIO.

    """

    def __init__(self, textio):
        try:
            if not textio.writable():
                raise io.UnsupportedOperation("not writable")
        except AttributeError:
            # somehow Python2 sys.stderr, a file object, does not have
            # the writable method of io.IOBase
            pass
        self._textio = textio
        self._stringio = NormalizedStringIO()

    def close(self):
        self._stringio.close()

    @property
    def closed(self):
        return self._textio.closed

    def detach(self):
        return self._textio.detach()

    @property
    def encoding(self):
        return self._textio.encoding

    @property
    def errors(self):
        return self._textio.errors

    def fileno(self):
        return self._textio.fileno()

    def flush(self):
        self._textio.flush()
        self._stringio.flush()

    def getvalue(self):
        return self._stringio.getvalue()

    def isatty(self):
        return self._textio.isatty()

    @staticmethod
    def read(size):
        raise io.UnsupportedOperation("not readable")

    @staticmethod
    def readable():
        return False

    @staticmethod
    def readline(size=-1):
        raise io.UnsupportedOperation("not readable")

    @staticmethod
    def readlines(hint=-1):
        raise io.UnsupportedOperation("not readable")

    @staticmethod
    def seek(offset, whence=os.SEEK_SET):
        raise io.UnsupportedOperation("not seekable")

    @staticmethod
    def seekable():
        return False

    @staticmethod
    def tell():
        raise io.UnsupportedOperation("not seekable")

    @staticmethod
    def truncate(size=None):
        raise io.UnsupportedOperation("not seekable")

    @staticmethod
    def writable():
        return True

    def write(self, s):
        bytes_written = self._textio.write(s)
        self._stringio.write(s)
        return bytes_written

    def writelines(lines):
        self._textio.writelines(lines)
        self._stringio.writelines(lines)


@contextmanager
def capture_stdout():
    """Single use context manager for capturing stdout in a StringIO.

    The negative effect is that some properties of the stream are
    changed, e.g., isatty().

    """

    saved_stdout = sys.stdout
    sys.stdout = NormalizedStringIO()
    yield
    sys.stdout = saved_stdout

@contextmanager
def capture_stderr():
    """Single use context manager for capturing stderr in a StringIO.

    The negative effect is that some properties of the stream are
    changed, e.g., isatty().

    """

    saved_stderr = sys.stderr
    sys.stderr = NormalizedStringIO()
    yield
    sys.stderr = saved_stderr

@contextmanager
def tee_stderr():
    """Single use context manager for teeing stderr to a StringIO.
    """
    saved_stderr = sys.stderr
    sys.stderr = Tee(sys.stderr)
    yield
    sys.stderr = saved_stderr


@contextmanager
def change_home():
    """Single use context manager for changing HOME to temp directory.
    """
    if 'HOME' in os.environ:
        saved_home = os.environ['HOME']
    else:
        saved_home = None
    tmp_home = tempfile.mkdtemp()
    os.environ['HOME'] = tmp_home
    yield tmp_home
    shutil.rmtree(tmp_home)
    if saved_home is not None:
        os.environ['HOME'] = saved_home
