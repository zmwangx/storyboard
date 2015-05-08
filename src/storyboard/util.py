#!/usr/bin/env python3

"""Supporting utilities.

Classes
-------
.. autosummary::
    ProgressBar
    OptionReader

Routines
--------
.. autosummary::
    read_param
    round_up
    evaluate_ratio
    humansize
    humantime

----

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import math
import os
import re
import sys
import time


def read_param(params, key, default):
    """Read and return a parameter from a dict.

    If the key `key` is absent from the dict `params`, return the
    default value `default` instead.

    Parameters
    ----------
    params : dict
        A dict containing parameters.
    key : str
        Name of the parameter, i.e., its corresponding key in `params`.
    default
        Default value for the parameter, if `key` is absent from `params`.

    Returns
    -------
    value
        If `key` in `params`, return ``params[key]``; otherwise, return
        `default` instead.

    """

    if not isinstance(key, str):
        raise ValueError('invalid parameter name %s' % str(key))

    return params[key] if key in params else default


def round_up(number, ndigits=0):
    """Round a floating point number *upward* to a given precision.

    Unlike the builtin `round`, the return value `round_up` is always
    the smallest float *greater than or equal to* the given number
    matching the specified precision.

    Parameters
    ----------
    number : float
        Number to be rounded up.
    ndigits : int, optional
        Number of decimal digits in the result. Default is 0.

    Returns
    -------
    float

    Examples
    --------
    >>> round_up(math.pi)
    4.0
    >>> round_up(math.pi, ndigits=1)
    3.2
    >>> round_up(math.pi, ndigits=2)
    3.15
    >>> round_up(-math.pi, ndigits=4)
    -3.1415

    """

    multiplier = 10 ** ndigits
    return math.ceil(number * multiplier) / multiplier


# patterns numerator:denominator and numerator/denominator
_NUM_COLON_DEN = re.compile(r'^([1-9][0-9]*):([1-9][0-9]*)$')
_NUM_SLASH_DEN = re.compile(r'^([1-9][0-9]*)/([1-9][0-9]*)$')


def evaluate_ratio(ratio_str):
    """Evaluate ratio in the form num:den or num/den.

    Note that numerator and denominator should both be positive
    integers.

    Parameters
    ----------
    ratio_str : str
        The ratio as a string (either ``'num:den'`` or ``'num/den'``
        where ``num`` and ``den``, the numerator and denominator, are
        positive integers.

    Returns
    -------
    ratio : float
        The ratio as a float, or ``None`` if `ratio_str` is malformed.

    Examples
    --------
    >>> evaluate_ratio('16:9')
    1.7777777777777777
    >>> evaluate_ratio('16/9')
    1.7777777777777777
    >>> print(evaluate_ratio('0/9'))
    None

    """

    match = _NUM_COLON_DEN.match(ratio_str)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        return numerator / denominator
    match = _NUM_SLASH_DEN.match(ratio_str)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        return numerator / denominator
    return None


def humansize(size):
    """Return a human readable string of the given size in bytes."""
    multiplier = 1024.0
    if size < multiplier:
        return "%dB" % size
    for unit in ['Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        size /= multiplier
        if size < multiplier:
            if size < 10:
                return "%.2f%sB" % (round_up(size, 2), unit)
            elif size < 100:
                return "%.1f%sB" % (round_up(size, 1), unit)
            else:
                return "%.0f%sB" % (round_up(size, 0), unit)
            break
    else:
        return "%.1f%sB" % (round_up(size, 1), unit)


def humantime(seconds, ndigits=2, one_hour_digit=False):
    """Format a duration as a human readable string.

    The duration in seconds (a nonnegative float) is formatted as
    ``HH:MM:SS.frac``, where the number of fractional digits is
    controlled by `ndigits`; if `ndigits` is 0, the decimal point is not
    printed. The number of hour digits (``HH``) can be reduced to one
    with the `one_hour_digits` option.

    Parameters
    ----------
    seconds : float
        Duration in seconds, must be nonnegative.
    ndigits : int, optional
        Number of digits after the decimal point for the seconds part.
        Default is 2. If 0, the decimal point is suppressed.
    one_hour_digit : bool, optional
        If ``True``, only print one hour digit (e.g., nine hours is
        printed as 9:00:00.00). Default is ``False``, i.e., two hour
        digits (nine hours is printed as 09:00:00.00).

    Returns
    -------
    human_readable_duration : str

    Raises
    ------
    ValueError:
        If `seconds` is negative.

    Examples
    --------
    >>> humantime(10.55)
    '00:00:10.55'
    >>> humantime(10.55, ndigits=1)
    '00:00:10.6'
    >>> humantime(10.55, ndigits=0)
    '00:00:11'
    >>> humantime(10.55, one_hour_digit=True)
    '0:00:10.55'
    >>> # two hours digits for >= 10 hours, even if one_hour_digit is
    >>> # set to True
    >>> humantime(86400, one_hour_digit=True)
    '24:00:00.00'
    >>> humantime(-1)
    Traceback (most recent call last):
        ...
    ValueError: seconds=-1.000000 is negative, expected nonnegative value

    """

    # pylint: disable=invalid-name
    if seconds < 0:
        raise ValueError("seconds=%f is negative, "
                         "expected nonnegative value" % seconds)

    hh = int(seconds) // 3600  # hours
    mm = (int(seconds) // 60) % 60  # minutes
    ss = seconds - (int(seconds) // 60) * 60  # seconds
    hh_str = "%01d" % hh if one_hour_digit else "%02d" % hh
    mm_str = "%02d" % mm
    if ndigits == 0:
        ss_str = "%02d" % round(ss)
    else:
        ss_format = "%0{0}.{1}f".format(ndigits + 3, ndigits)
        ss_str = ss_format % ss
    return "%s:%s:%s" % (hh_str, mm_str, ss_str)


# default progress bar update interval
_PROGRESS_UPDATE_INTERVAL = 1.0
# the format string for a progress bar line
#
# 0: processed size, e.g., 2.02GiB
# 1: elapsed time (7 chars), e.g., 0:00:04
# 2: current processing speed, e.g., 424MiB (/s is already hardcoded)
# 3: the bar, in the form "=====>   "
# 4: number of percent done, e.g., 99
# 5: estimated time remaining (11 chars), in the form "ETA H:MM:SS"; if
#    finished, fill with space
_FORMAT_STRING = '\r{0:>7s} {1} [{2:>7s}/s] [{3}] {4:>3s}% {5}'


class ProgressBar(object):
    """Progress bar for file processing.

    To generate a progress bar, init a ProgressBar instance, then update
    frequently with the `update` method, passing in the size of newly
    processed chunk. The `force_update` method should only be called if
    you want to overwrite the processed size, which is automatically
    calculated incrementally. After you finish processing the
    file/stream, you must call the `finish` method to wrap it up. Any
    further calls after the `finish` method has been called lead to
    a ``RuntimeError``.

    Each ProgressBar instance defines several public attributes listed
    below. Some are available during processing, and some after
    processing. These attributes are meant for informational purposes,
    and you should not manually tamper with them (which mostly likely
    leads to undefined behavior).

    The progress bar format is inspired by ``pv(1)`` (pipe viewer).

    Parameters
    ----------
    totalsize : int
        Total size, in bytes, of the file/stream to be processed.
    interval : float, optional
        Update (refresh) interval of the progress bar, in
        seconds. Default is 1.0.

    Attributes
    ----------
    totalsize : int
        Total size of file/stream, in bytes. Available throughout.
    processed : int
        Process size. Available only during processing (deleted after
        the `finish` call).
    start : float
        Starting time (an absolute time returned by
        ``time.time()``). Available throughout.
    interval : float
        Update (refresh) interval of the progress bar, in
        seconds. Available only during processing (deleted after the
        `finish` call).
    elapsed : float
        Total elapsed time, in seconds. Only available after the
        `finish` call.

    Notes
    -----
    For developers: ProgressBar also defines three private attributes,
    `_last`, `_last_processed` and `_barlen`, during processing (deleted
    after the `finish` call). `_last` stores the absolute time of last
    update (refresh), `_last_processed` stores the processed size at the
    time of the last update (refresh), and `_barlen` stores the length
    of the progress bar (only the bar portion).

    There is another private attribute `__finished` (bool) keeping track
    of whether `finish` has been called. (Protected with double leading
    underscores since no one should ever tamper with this.)

    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, totalsize, interval=_PROGRESS_UPDATE_INTERVAL):
        """Initialize the ProgressBar class.

        See class docstring for parameters of the constructor.

        """

        self.totalsize = totalsize
        self.processed = 0
        self.start = time.time()
        self.interval = interval
        self._last = self.start
        self._last_processed = 0
        self.__finished = False

        # calculate bar length
        try:
            ncol, _ = os.get_terminal_size()
        except (AttributeError, OSError):
            # Python2 do not have os.get_terminal_size.  Also,
            # os.get_terminal_size fails if stdout is redirected to a
            # pipe (pretty stupid -- should check stderr; relevant
            # Python bug: https://bugs.python.org/issue14841). In either
            # case, Assume a minimum of 80 columns.
            ncol = 80
        self._barlen = (ncol - 48) if ncol >= 58 else 10

    def update(self, chunk_size):
        """Update the progress bar for a newly processed chunk.

        The size of the processed chunk is registered. Whether the
        progress bar is refreshed depends on whether we have reached the
        refresh interval since the last refresh (handled automatically).

        Parameters
        ----------
        chunk_size : int
            The size of the newly processed chunk (since last update),
            in bytes. This size will be added to the `processed`
            attribute.

        Raises
        ------
        RuntimeError:
            If `finish` has been called on the ProgressBar instance.

        """

        if self.__finished:
            raise RuntimeError('operation on finished progress bar')

        self.processed += chunk_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def force_update(self, processed_size):
        """Force update the progress bar with a given processed size.

        The `processed` attribute is overwritten by the new value.

        Parameters
        ----------
        processed_size :
            Processed size of the file/stream, in bytes. Existing value
            is overwritten by this value.

        Raises
        ------
        RuntimeError:
            If `finish` has been called on the ProgressBar instance.

        """

        if self.__finished:
            raise RuntimeError('operation on finished progress bar')

        self.processed = processed_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def finish(self):
        """Finish file progressing and wrap up on the progress bar.

        Always call this method exactly once after you finish
        processing. This method adds the finishing touches to the
        progress bar, deletes several attributes (`processed`,
        `interval`), and adds a new attribute (`elapsed`).

        After `finish` is called on a ProgressBar attribute, it enters a
        read-only mode: you may read the `totalsize`, `start`, and
        `elapsed` attributes, but any method call leads to a
        ``RuntimeError``.

        Raises
        ------
        RuntimeError:
            If `finish` has already been called on the ProgressBar
            instance before.

        """

        # pylint: disable=attribute-defined-outside-init

        if self.__finished:
            raise RuntimeError('operation on finished progress bar')

        self.elapsed = time.time() - self.start
        if self.elapsed < 0.001:
            self.elapsed = 0.001  # avoid division by zero
        del self.processed
        del self.interval
        del self._last
        del self._last_processed

        self.__finished = True

        processed_s = humansize(self.totalsize)
        elapsed_s = self._humantime(self.elapsed)
        speed_s = humansize(self.totalsize / self.elapsed)
        bar_s = '=' * (self._barlen - 1) + '>'
        percent_s = '100'
        eta_s = ' ' * 11
        sys.stderr.write(_FORMAT_STRING.format(
            processed_s, elapsed_s, speed_s, bar_s, percent_s, eta_s
        ))
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _update_output(self):
        """Update the progress bar and surrounding data as appropriate.

        Whether the progress bar is refreshed depends on whether we have
        reached the refresh interval since the last refresh (handled
        automatically).

        Raises
        ------
        RuntimeError:
            If `finish` has already been called on the ProgressBar
            instance before.

        """

        if self.__finished:
            raise RuntimeError('operation on finished progress bar')

        elapsed_since_last = time.time() - self._last
        if elapsed_since_last < self.interval:
            return

        if elapsed_since_last < 0.001:
            elapsed_since_last = 0.001  # avoid division by zero

        # speed in the last second, in bytes per second
        speed = ((self.processed - self._last_processed) / elapsed_since_last)

        # update last stats for the next update
        self._last = time.time()
        self._last_processed = self.processed

        # _s suffix stands for string
        processed_s = humansize(self.processed)
        elapsed_s = self._humantime(time.time() - self.start)
        speed_s = humansize(speed)
        percentage = self.processed / self.totalsize  # absolute
        percent_s = str(int(percentage * 100))
        # generate bar
        length = int(round(self._barlen * percentage))
        fill = self._barlen - length
        if length == 0:
            bar_s = " " * self._barlen
        else:
            bar_s = '=' * (length - 1) + '>' + ' ' * fill
        # calculate ETA
        remaining = self.totalsize - self.processed
        # estimate based on current speed
        eta = remaining / speed
        eta_s = "ETA %s" % self._humantime(eta)

        sys.stderr.write(_FORMAT_STRING.format(
            processed_s, elapsed_s, speed_s, bar_s, percent_s, eta_s
        ))
        sys.stderr.flush()

    @staticmethod
    def _humantime(seconds):
        """Customized humantime for ProgressBar."""
        return humantime(seconds, ndigits=0, one_hour_digit=True)


class OptionReader(object):
    """Class for reading options from a list of fallbacks.

    OptionReader optionally takes command line arguments parsed by
    argparse, a list of possible configuration files, and a dictionary
    of default values. Then one can query the class for the value of an
    option using the ``opt(name)`` method. The value is determined in
    the order of CLI argument, value specified in config files, default
    value, and at last ``None`` if none of the above is available.

    Parameters
    ----------
    cli_args : argparse.Namespace, optional
        CLI arguments returned by
        ``argparse.ArgumentParser.parse_args()``. If ``None``, do not
        consider CLI arguments. Default is ``None``.
    config_files : str or list, optional
        Path(s) to the expected configuration file(s). If ``None``,
        do not read from config files. Default is ``None``.
    section : str, optional
        Name of the config file section to read from. Do not use
        ``DEFAULT``, as it is the reserved name for a special
        section. If ``None``, do not read from config files. Default is
        ``None``.
    defaults : dict, optional
        A dict containing default values of one or more options. If
        ``None``, do not consider default values. Default is ``None``.

    Raises
    ------
    configparser.Error:
        If some of the supplied configuration files are malformed.

    Notes
    -----
    For developers: there are three private attributes, ``_cli_opts``,
    ``_cfg_opts`` and ``_default_opts``, which are dicts containing CLI,
    config file, and default options, respectively.

    """

    def __init__(self, cli_args=None, config_files=None, section=None,
                 defaults=None):
        """
        Initialize the OptionReader class.

        See class docstring for parameters.

        """

        if section == 'DEFAULT':
            raise ValueError("section name DEFAULT is not allowed")

        # parse CLI arguments
        if cli_args is not None:
            # only include values that are not None
            self._cli_opts = dict((k, v) for k, v in cli_args.__dict__.items()
                                  if v is not None)
        else:
            self._cli_opts = {}

        # parse config files
        if config_files is not None and section is not None:
            config = configparser.ConfigParser()
            config.read(config_files)
            if config.has_section(section):
                self._cfg_opts = dict(config.items(section))
            else:
                self._cfg_opts = {}
        else:
            self._cfg_opts = {}

        # default options
        if defaults is not None:
            self._default_opts = defaults
        else:
            self._default_opts = {}

    def cli_opt(self, name):
        """
        Read the value of an option from the corresponding CLI argument.

        Parameters
        ----------
        name : str
            Name of the option.

        Returns
        -------
        value
            Value of the corresponding CLI argument if available, and
            ``None`` otherwise.

        """

        return self._cli_opts[name] if name in self._cli_opts else None

    def cfg_opt(self, name, opttype=None):
        """
        Read the value of an option from config files.

        Parameters
        ----------
        name : str
            Name of the option.
        opttype : {None, str, int, float, bool}
            Type of the option. The value of the option is converted to
            the corresponding type. If ``None``, no conversion is done
            (so the return type will actually be ``str``). If ``bool``,
            the returned value will be ``True`` if the default value is
            ``'yes'``, ``'on'``, or ``'1'``, and ``False`` if the
            default value is ``'no'``, ``'off'``, or ``'0'`` (case
            insensitive), just like
            ``configparser.ConfigParser.getboolean``.

        Returns
        -------
        value
            Value of the option in config files if available, and
            ``None`` otherwise.

        Raises
        ------
        ValueError:
            If the raw value of the option in config files (if
            available) cannot be converted to `opttype`, or if `opttype`
            is not one of the supported types.

        """

        # pylint: disable=too-many-return-statements

        if name not in self._cfg_opts:
            return None

        rawopt = self._cfg_opts[name]
        if opttype is None:
            return rawopt
        elif opttype is str:
            return rawopt
        elif opttype is int:
            return int(rawopt)
        elif opttype is float:
            return float(rawopt)
        elif opttype is bool:
            rawopt_lower = rawopt.lower()
            if rawopt_lower in {'yes', 'on', '1'}:
                return True
            elif rawopt_lower in {'no', 'off', '0'}:
                return False
            else:
                raise ValueError("not a boolean: %s" % rawopt)
        else:
            raise ValueError("unrecognized opttype %s" % str(opttype))

    def default_opt(self, name):
        """
        Read the default value of an option.

        Parameters
        ----------
        name : str
            Name of the option.

        Returns
        -------
        value
            Default value of the option if available, and ``None`` otherwise.

        """

        return self._default_opts[name] if name in self._default_opts else None

    def opt(self, name, opttype=None):
        """
        Read the value of an option.

        The value is determined in the following order: CLI argument,
        config files, default value, and at last ``None``.

        Parameters
        ----------
        name : str
            Name of the option.
        opttype : {None, str, int, float, bool}
            Type of the option, only useful for config files. See the
            `opttype` parameter of the `cfg_opt` method.

        Returns
        -------
        value
            Value of the option.

        Raises
        ------
        ValueError:
            If the raw value of the option in config files (if
            available) cannot be converted to `opttype`, or if `opttype`
            is not one of the supported types.

        """

        if name in self._cli_opts:
            return self._cli_opts[name]
        elif name in self._cfg_opts:
            return self.cfg_opt(name, opttype)
        elif name in self._default_opts:
            return self._default_opts[name]
        else:
            return None
