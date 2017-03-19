#!/usr/bin/env python3

"""Extract video metadata with FFprobe.

Classes
-------
.. autosummary::
    Stream
    Video

Routines
--------
.. autosummary::
    main

----

"""

# pylint: disable=too-many-lines

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import fractions
import hashlib
import json
import os
import subprocess
import sys

from storyboard import fflocate
from storyboard import util
from storyboard.util import read_param as _read_param
from storyboard import version


_FORMAT_MAP = {
    'aac': 'Raw ADTS AAC',
    'ac3': 'Raw AC-3',
    'aiff': 'Audio Interchange File Format (AIFF)',
    'asf': 'Advanced Systems Format',
    'avi': 'Audio Video Interleaved',
    'flac': 'Native FLAC',
    'flv': 'Flash video',
    'jpeg_pipe': 'JPEG',
    'matroska,webm': 'Matroska',
    'mp3': 'MP3',
    'mpeg': 'MPEG program stream',
    'mpegts': 'MPEG transport stream',
    'mpegvideo': 'Raw MPEG video',
    'mov,mp4,m4a,3gp,3g2,mj2': 'MPEG-4 Part 14',
    'ogg': 'Ogg',
    'rm': 'RealMedia',
    'png_pipe': 'PNG',
}

_VCODEC_MAP = {
    'h264': 'H.264',
    'hevc': 'HEVC',
    'mjpeg': 'Motion JPEG',
    'mpeg1video': 'MPEG-1 Part 2',
    'mpeg2video': 'MPEG-2 Part 2',
    'mpeg4': 'MPEG-4 Part 2',
    'png': 'PNG',
    'rv10': 'RealVideo 1.0',
    'rv20': 'RealVideo 2.0',
    'rv30': 'RealVideo 3.0',
    'rv40': 'RealVideo 4.0',
    'theora': 'Theora',
    'vp8': 'VP8',
    'vp9': 'VP9',
}

_ACODEC_MAP = {
    'aac': 'AAC',
    'ac3': 'Dolby AC-3',
    'cook': 'Cook (RealAudio G2)',
    'flac': 'FLAC (Free Lossless Audio Codec)',
    'mp3': 'MP3',
    'ra_144': 'RealAudio 1.0',
    'ra_288': 'RealAudio 2.0',
    'ralf': 'RealAudio Lossless',
    'real_144': 'RealAudio 1.0',
    'real_288': 'RealAudio 2.0',
    'vorbis': 'Vorbis',
}

_SCODEC_MAP = {
    'ass': 'SubStation Alpha',
    'cc_dec': 'closed caption (EIA-608 / CEA-708)',
    'srt': 'SubRip',
    'subrip': 'SubRip'
}


class Stream(object):

    """Container for stream metadata.

    Some of the documented attributes are optional; in particular, some
    attributes are video stream specific. (In that case of an
    unavailable attribute, the value will be ``None``)

    Attributes
    ----------
    index : int
        Stream index within the video container.

    type : str
        ``'video'``, ``'audio'``, ``'subtitle'``, ``'data'``, etc.

    codec : str
        (Long) name of codec.

    bit_rate : float
        Bit rate of stream, in kb/s.

    bit_rate_text : str
        Bit rate as a human readable string, e.g., ``'360 kb/s'``.

    language_code : str

    width : int

    height : int

    dimension : tuple
        ``(width, height)``, e.g., ``(1920, 1080)``.

    dimension_text : str
        Dimension as a human readable string, e.g. ``'1920x1080'``.

    frame_rate : float
        Frame rate of video stream, in frames per second (fps).

    frame_rate_text : str
        Frame rate as a human readable string, e.g., ``'24 fps'``.

    dar : float
        Display aspect ratio.

    dar_text : str
        Display aspect ratio as a human readable string, e.g.,
        ``'16:9'``.

    info_string : str
        Assembled string of stream metadata, intended for printing.

    """

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
    # a stream can have any number of attributes

    def __init__(self):
        """Initialize the Stream class."""
        # general stream attributes
        self.index = None
        self.type = None
        self.codec = None
        self.bit_rate = None
        self.bit_rate_text = None
        self.language_code = None
        # video stream specific attributes
        self.width = None
        self.height = None
        self.dimension = None
        self.dimension_text = None
        self.frame_rate = None
        self.frame_rate_text = None
        self.dar = None  # display aspect ratio
        self.dar_text = None
        # assembled
        self.info_string = None


class Video(object):

    """Container for video and streams metadata.

    A ``Video`` object holds video metadata (including container
    metadata and per-stream metadata), and generates a formatted string
    for printing upon request (the `format_metadata` method).

    Some of the documented attributes might not be available for certain
    video files (in that case the value will be ``None``).

    Parameters
    ----------
    video : str
        Path to the video file.
    params : dict, optional
        Optional parameters enclosed in a dict. Default is ``None``. See
        the "Other Parameters" section for understood key/value pairs.

    Raises
    ------
    OSError
        If fails to extract metadata with ffprobe, e.g., if the file is
        not present, or in a format that is not recognized by ffprobe,
        or if ffprobe cannot be called, etc.

    Other Parameters
    ----------------
    ffprobe_bin : str, optional
        Name/path of the ffprobe binary (should be callable). By default
        the name is guessed based on OS type. (See the
        storyboard.fflocate module.)
    video_duration : float, optional
        Duration of the video in seconds. If ``None``, extract the
        duration from container metadata. Default is ``None``. This is
        only needed in edge cases where the duration of the video cannot
        be read off from container metadata, or the duration extracted
        is wrong. See `#3
        <https://github.com/zmwangx/storyboard/issues/3>`_ for details.
    print_progress : bool, optional
        Whether to print progress information (to stderr). Default is
        False.
    debug : bool, optional
        Print extra debug information. Default is False.

    Attributes
    ----------
    format : str
        (Long) name of container format.

    title : str

    size : int
        Size of video file in bytes.

    size_text : str
        Size as a human readable string, e.g., ``'128MiB'``.

    duration : float
        Duration of video in seconds.

    duration_text : str
        Duration as a human readable string, e.g., ``'00:02:53.33'``.

    scan_type : str
        ``'Progressive scan'``, ``'Interlaced scan'``, or ``'Telecined
        video'``.

    dimension : (width, height)
        E.g., ``(1920, 1080)``.

    dimension_text : str
        Dimension as a human readable string, e.g. ``'1920x1080'``.

    sha1sum : str
        The SHA-1 hex digest of the video file (40 character hexadecimal
        string). Since computing SHA-1 digest is an expensive operation,
        this attribute is only calculated and set upon request, either
        through `compute_sha1sum` or `format_metadata` with the
        ``include_sha1sum`` optional parameter set to ``True``.

    frame_rate : float
        Frame rate of video stream, in frames per second (fps).

    frame_rate_text : str
        Frame rate as a human readable string, e.g., ``'24 fps'``.

    dar : float
        Display aspect ratio.

    dar_text : str
        Display aspect ratio as a human readable string, e.g.,
        ``'16:9'``.

    streams : list
        A list of Stream objects, containing per-stream metadata.

    Notes
    -----
    The unmodified JSON output of ``ffprobe -show_format -show_streams``
    on the video is saved in a private instance attribute `_ffprobe`.

    """

    # pylint: disable=too-many-instance-attributes
    # again, a video can have any number of metadata attributes

    def __init__(self, video, params=None):
        """Initialize the Video class.

        See class docstring for parameters of the constructor.

        """

        if params is None:
            params = {}
        if 'debug' in params and params['debug']:
            self.__debug = True
        self.__dp("entered StoryBoard.__init__")
        if 'ffprobe_bin' in params:
            ffprobe_bin = params['ffprobe_bin']
        else:
            _, ffprobe_bin = fflocate.guess_bins()
        video_duration = _read_param(params, 'video_duration', None)
        print_progress = _read_param(params, 'print_progress', False)

        self.path = os.path.abspath(video)
        if not os.path.exists(self.path):
            raise OSError("'" + video + "' does not exist")
        self.filename = os.path.basename(self.path)
        if hasattr(self.filename, 'decode'):
            # python2 str, need to be decoded to unicode for proper
            # printing
            self.filename = self.filename.decode('utf-8')

        if print_progress:
            sys.stderr.write("Processing %s\n" % self.filename)
            sys.stderr.write("Crunching metadata...\n")

        self._call_ffprobe(ffprobe_bin)

        self.title = self._get_title()
        self.format = self._get_format()
        self.size, self.size_text = self._get_size()
        if video_duration is None:
            self.duration, self.duration_text = self._get_duration()
        else:
            self.duration = video_duration
            self.duration_text = util.humantime(video_duration)
        self.sha1sum = None  # SHA-1 digest is generated upon request

        # the remaining attributes will be dynamically set when parsing
        # streams
        self.dimension = None
        self.dimension_text = None
        self.frame_rate = None
        self.frame_rate_text = None
        self.dar = None
        self.dar_text = None

        self._process_streams()

        # detect if the file contains any video streams at all and try
        # to extract scan type only if it does
        for stream in self.streams:
            if stream.type == 'video':
                break
        else:
            # no video stream
            self.scan_type = None
            self.__dp("left StoryBoard.__init__")
            return
        self.scan_type = self._get_scan_type(ffprobe_bin, print_progress)
        self.__dp("left StoryBoard.__init__")

    def format_metadata(self, params=None):
        """Return video metadata in one formatted string.

        Parameters
        ----------
        params : dict, optional
            Optional parameters enclosed in a dict. Default is ``None``.
            See the "Other Parameters" section for understood key/value
            pairs.

        Returns
        -------
        str
            A formatted string loaded with video and per-stream
            metadata, which can be printed directly. See the "Examples"
            section for a printed example.

        Other Parameters
        ----------------
        include_sha1sum : bool, optional
            Whether to include the SHA-1 hex digest. Default is
            False. Keep in mind that computing SHA-1 digest is an
            expensive operation, and hence is only performed upon
            request.
        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is False.

        Examples
        --------
        >>> import os
        >>> import tempfile
        >>> import requests
        >>> video_uri = 'https://dl.bintray.com/zmwangx/pypi/sample-h264-aac-srt.mkv'
        >>> tempdir = tempfile.mkdtemp()
        >>> video_file = os.path.join(tempdir, 'sample-h264-aac-srt.mkv')
        >>> r = requests.get(video_uri, stream=True)
        >>> with open(video_file, 'wb') as fd:
        ...     for chunk in r.iter_content(65536):
        ...         bytes_written = fd.write(chunk)
        >>> print(Video(video_file).format_metadata({'include_sha1sum': True}))
        Title:                  Example video: H.264 + AAC + SRT in Matroska container
        Filename:               sample-h264-aac-srt.mkv
        File size:              4842 (4.73KiB)
        SHA-1 digest:           95E7D9F9359D8D7BA4EC441BC8CB3830A58EE102
        Container format:       Matroska
        Duration:               00:00:02.08
        Pixel dimensions:       128x72
        Display aspect ratio:   16:9
        Scan type:              Progressive scan
        Frame rate:             25 fps
        Streams:
            #0: Video, H.264 (High Profile level 1.0), 128x72 (DAR 16:9), 25 fps
            #1: Audio (und), AAC (Low-Complexity)
            #2: Subtitle, SubRip
        >>> os.remove(video_file)
        >>> os.rmdir(tempdir)
        """

        self.__dp("entered StoryBoard.format_metadata")
        if params is None:
            params = {}
        include_sha1sum = _read_param(params, 'include_sha1sum', False)
        print_progress = _read_param(params, 'print_progress', False)

        lines = []  # holds the lines that will be joined in the end
        # title
        if self.title:
            lines.append("Title:                  %s" % self.title)
        # filename
        lines.append("Filename:               %s" % self.filename)
        # size
        lines.append("File size:              %d (%s)" %
                     (self.size, self.size_text))
        # sha1sum
        if include_sha1sum:
            self._get_sha1sum(print_progress)
            lines.append("SHA-1 digest:           %s" % self.sha1sum)
        # container format
        lines.append("Container format:       %s" % self.format)
        # duration
        if self.duration_text:
            lines.append("Duration:               %s" % self.duration_text)
        else:
            lines.append("Duration:               Not available")
        # dimension
        if self.dimension_text:
            lines.append("Pixel dimensions:       %s" % self.dimension_text)
        # aspect ratio
        if self.dar_text:
            lines.append("Display aspect ratio:   %s" % self.dar_text)
        # scanning type
        if self.scan_type:
            lines.append("Scan type:              %s" % self.scan_type)
        # frame rate
        if self.frame_rate:
            lines.append("Frame rate:             %s" % self.frame_rate_text)
        # streams
        lines.append("Streams:")
        for stream in self.streams:
            lines.append("    #%d: %s" % (stream.index, stream.info_string))
        self.__dp("left StoryBoard.format_metadata")
        return '\n'.join(lines).strip()

    def compute_sha1sum(self, params=None):
        """Computes the SHA-1 digest of the video file.

        Parameters
        ----------
        params : dict, optional
            Optional parameters enclosed in a dict. Default is ``None``.
            See the "Other Parameters" section for understood key/value
            pairs.

        Returns
        -------
        sha1sum : str
            The SHA-1 hex digest of the video file (40 character
            hexadecimal string).

        Other Parameters
        ----------------
        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is False.

        Notes
        -----
        Since computing SHA-1 digest is an expensive operation, the
        digest is only calculated and set upon request, either through
        this method or `format_metadata` with the ``include_sha1sum``
        optional parameter set to ``True``. Further requests load the
        calculated value rather than repeat the computation.

        """

        self.__dp("entered StoryBoard.compute_sha1sum")
        if params is None:
            params = {}
        print_progress = _read_param(params, 'print_progress', False)

        self.__dp("left StoryBoard.compute_sha1sum")
        return self._get_sha1sum(print_progress=print_progress)

    def _call_ffprobe(self, ffprobe_bin):
        """Call ffprobe to extract video metadata.

        ffprobe is called with the -show_format and -show_streams
        options, and its JSON output is parsed and stored in the
        `_ffprobe` attribute.

        Parameters
        ----------
        ffprobe_bin : str
            Name/path of the ffprobe binary (should be callable).

        Raises
        ------
        OSError
            If the ffprobe call returns with nonzero status.

        """

        self.__dp("entered StoryBoard._call_ffprobe")
        ffprobe_args = [
            ffprobe_bin,
            '-print_format', 'json',
            '-show_format', '-show_streams',
            '-hide_banner',
            self.path
        ]
        proc = subprocess.Popen(ffprobe_args,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_out, ffprobe_err = proc.communicate()
        ffprobe_out = ffprobe_out.decode('utf-8', 'ignore')
        ffprobe_err = ffprobe_err.decode('utf-8', 'ignore')

        self.__dp("ffprobe stdout:")
        self.__dp(ffprobe_out)
        self.__dp("ffprobe stderr:")
        self.__dp(ffprobe_err)
        if proc.returncode != 0:
            msg = ("ffprobe failed on '%s'\nffprobe error message:\n%s"
                   % (self.path, ffprobe_err.strip()))
            raise OSError(msg)
        self._ffprobe = json.loads(ffprobe_out)
        self.__dp("left StoryBoard._call_ffprobe")

    def _get_title(self):
        """Get title of video (if any).

        Returns
        -------
        title : str
            Or ``None`` if not present.

        Notes
        -----
        The title, if present, is stored in ``.format.tags.title`` of
        FFprobe's JSON output.

        """

        self.__dp("entered StoryBoard._get_title")
        video_container_metadata = self._ffprobe['format']
        title = None
        if 'tags' in video_container_metadata:
            if 'title' in video_container_metadata['tags']:
                title = video_container_metadata['tags']['title']
            elif 'TITLE' in video_container_metadata['tags']:
                title = video_container_metadata['tags']['TITLE']
        self.__dp("left StoryBoard._get_title")
        return title

    def _get_format(self):
        """Get container format of the video.

        Returns
        -------
        format : str
            e.g., ``"MPEG-4 Part 14 (MP4)"``, ``"MPEG transport
            stream"``, ``"Matroska"``

        Notes
        -----
        The container format is stored in ``.format.format_name`` and
        ``.format.format_long_name`` in FFprobe's JSON output. Both the
        short names and long names returned by FFprobe are usually not
        very satisfactory, so we roll our own names for common formats.

        """

        # pylint: disable=too-many-branches

        self.__dp("entered StoryBoard._get_format")
        format_name = self._ffprobe['format']['format_name']
        # lowercase extension without period
        extension = os.path.splitext(self.path)[1].lower()[1:]

        if format_name in _FORMAT_MAP:
            fmt = _FORMAT_MAP[format_name]

            # some formats that require special treatment (i.e., a
            # collection of formats sharing a common format_name, in
            # which case further subdivision is required)
            if format_name == 'mov,mp4,m4a,3gp,3g2,mj2':
                if extension in ['mov', 'qt']:
                    fmt = "QuickTime movie"
                elif extension in ['3gp']:
                    fmt = "3GPP"
                elif extension in ['3g2']:
                    fmt = "3GPP2"
                elif extension in ['mj2', 'mjp2']:
                    fmt = "Motion JPEG 2000"
                else:
                    # mp4, m4v, m4a, etc.
                    fmt = "MPEG-4 Part 14 (%s)" % extension.upper()
            elif format_name == 'matroska,webm':
                if extension in ['webm']:
                    fmt = "WebM"
                else:
                    fmt = "Matroska"
            elif format_name == 'rm':
                if extension in ['rmvb']:
                    fmt = "RealMedia Variable Bitrate (RMVB)"
                else:
                    fmt = "RealMedia"
        else:
            fmt = extension.upper()

        self.__dp("left StoryBoard._get_format")
        return fmt

    def _get_size(self):
        """Get size of the video file.

        Returns
        -------
        size : int
            Size in bytes.
        size_text: str
            Size as a human readable string, e.g., ``'128MiB'``.

        """

        self.__dp("entered StoryBoard._get_size")
        size = int(self._ffprobe['format']['size'])
        size_text = util.humansize(size)
        self.__dp("left StoryBoard._get_size")
        return (size, size_text)

    def _get_duration(self):
        """Get duration of the video.

        Returns
        -------
        duration : float
            Duration in seconds. ``None`` if duration is not available.
        duration_text : str
            Duration as a human readable string, e.g.,
            ``'00:02:53.33'``. ``None`` if duration is not available.

        """

        self.__dp("entered StoryBoard._get_duration")
        if 'duration' in self._ffprobe['format']:
            duration = float(self._ffprobe['format']['duration'])
            duration_text = util.humantime(duration)
            self.__dp("left StoryBoard._get_duration")
            return (duration, duration_text)
        else:
            self.__dp("left StoryBoard._get_duration")
            return (None, None)

    _SHA_CHUNK_SIZE = 65536
    """Chunk size used when computing the SHA-1 digest."""

    def _get_sha1sum(self, print_progress=False):
        """Get SHA-1 hex digest of the video file.

        In addition to returned the digest, it is also stored in the
        `sha1sum` attribute for future requests. Be aware that computing
        SHA-1 digest is an expensive operation.

        Parameters
        ----------
        print_progress : bool
            Whether to print progress information (to stderr). Default
            is False.

        Returns
        -------
        sha1sum : str
            A SHA-1 hex digest.

        """

        self.__dp("entered StoryBoard._get_sha1sum")
        # directly return if already computed
        if self.sha1sum is not None:
            self.__dp("left StoryBoard._get_sha1sum")
            return self.sha1sum

        if print_progress:
            sys.stderr.write("Computing SHA-1 digest...\n")
        with open(self.path, 'rb') as video:
            sha1 = hashlib.sha1()
            totalsize = os.path.getsize(self.path)
            chunksize = self._SHA_CHUNK_SIZE

            if print_progress:
                pbar = util.ProgressBar(totalsize)
            for chunk in iter(lambda: video.read(chunksize), b''):
                sha1.update(chunk)
                if print_progress:
                    pbar.update(chunksize)
            if print_progress:
                pbar.finish()

            self.sha1sum = sha1.hexdigest().upper()
            self.__dp("left StoryBoard._get_sha1sum")
            return self.sha1sum

    def _get_scan_type(self, ffprobe_bin, print_progress=False):
        """Determine the scan type of the video.

        Parameters
        ----------
        ffprobe_bin : str
            Name/path of the ffprobe binary (should be callable).
        print_progress : bool
            Whether to print progress information (to stderr). Default
            is False.

        Returns
        -------
        scan_type : str
            ``'Progressive scan'``, ``'Interlaced scan'``, or
            ``'Telecined video'``. ``None`` if the file is a pure audio
            file (possibly with album art) or too short (with fewer than
            forty frames).

        Notes
        -----
        In order to determine the scan type, we examie the first forty
        video frames with ffprobe (-show_frames). Each ffprobe frame
        object contains a key named ``interlaced``, which is 0 if the
        frame is progressive or 1 if the frame is interlaced.

        If less than forty video frames are available, then either we
        are dealing with an audio file, or the video file is just too
        short. Either case we do not try to determine the scan type,
        and just set it to None.

        Otherwise, we drop the first twenty frames (since there are
        sometimes junk frames at the beginning), and count the number
        of interlaced frames in the latter twenty frames. If they are
        all progressive or all interlaced, then the answer is
        obvious. If there are 8 interlaced frames out of 20, then it
        is highly probable that the video is telecined. Other than
        that it's pretty confusing, and I would just call it
        interlaced, since a deinterlacer might come in handy anyway.

        Note that this solution assumes that the output format of the
        relevant ffprobe command is

        ::

            {
                "frames": [
                    { frame object ... },
                    { frame object ... },
                    ...

        See https://github.com/zmwangx/storyboard/issues/11 for details.

        """

        # pylint: disable=too-many-branches

        self.__dp("entered StoryBoard._get_scan_type")
        if print_progress:
            sys.stderr.write("Trying to determine scan type...\n")

        ffprobe_args = [
            ffprobe_bin,
            '-select_streams', 'v',
            '-show_frames',
            '-print_format', 'json',
            self.path,
        ]
        proc = subprocess.Popen(ffprobe_args,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = iter(proc.stdout.readline, b'')

        # skip two lines:
        # {
        #     "frames" : [
        self.__dp(next(lines).decode('utf-8'), newline=False)
        self.__dp(next(lines).decode('utf-8'), newline=False)

        # empty string for incremental storage of json object
        obj_str = ''
        objs = []
        counter = 0
        for line in lines:
            self.__dp(line.decode('utf-8'), newline=False)
            obj_str += line.decode('utf-8').strip()
            try:
                # a complete frame object might be followed by a comma
                # in the array
                if obj_str[-1] == ',':
                    objs.append(json.loads(obj_str[0:-1]))
                else:
                    objs.append(json.loads(obj_str))

                counter += 1
                if print_progress:
                    sys.stderr.write("\rInspecting frame %d/40..." % counter)

                obj_str = ''
                if len(objs) >= 40:
                    proc.terminate()
                    proc.communicate()
                    break
            except ValueError:
                # incomplete frame object
                pass
        if print_progress:
            sys.stderr.write("\n")
        if len(objs) < 40:
            # frame count less than 40, either file is audio or file is
            # video but too short
            self.__dp("left StoryBoard._get_scan_type")
            return None

        # drop the first half of the frame objects
        frames = objs[20:]
        # count interlaced frames in the remaining 20 frames
        num_interlaced = 0
        for frame in frames:
            if 'interlaced_frame' in frame:
                num_interlaced += frame['interlaced_frame']

        self.__dp("left StoryBoard._get_scan_type")
        if num_interlaced == 0:
            return "Progressive scan"
        elif num_interlaced == 20:
            return "Interlaced scan"
        elif num_interlaced == 8:
            # telecined, 3:2 pull down
            return "Telecined video"
        else:
            # confused, see https://github.com/zmwangx/storyboard/issues/11
            return "Interlaced scan"

    def _process_streams(self):
        """Extract per-stream metadata of all streams in the video.

        Extracted metadata are saved to the `streams` attribute.

        """
        self.__dp("entered StoryBoard._process_streams")
        self.streams = []
        for stream in self._ffprobe['streams']:
            self.streams.append(self._process_stream(stream))
        self.__dp("left StoryBoard._process_streams")

    def _process_stream(self, stream_dict):
        """Process a single stream object returned by FFprobe.

        A FFprobe-generated JSON stream object (one single stream) is
        interpreted and save to our in-house Stream object.

        Parameters
        ----------
        stream_dict : dict
            A dict representing a FFprobe-generated JSON stream object
            (one single stream).

        Returns
        -------
        stream : Stream
            A Stream object containing parsed metadata.

        Notes
        -----
        Different codecs are dealt with differently
        here. `_process_video_stream`, `_process_audio_stream` and
        `_process_subtitle_stream` encompass a growing list of codecs I
        frequently encounter. I do not intend to be exhaustive, but
        everyone is welcome to contribute code for their favorite (or
        hated) codecs.

        """

        self.__dp("entered StoryBoard._process_stream")
        if 'codec_type' not in stream_dict:
            stream = Stream()
            stream.type = 'unknown'
            stream.info_string = "Data"
        else:
            codec_type = stream_dict['codec_type']
            if codec_type == "video":
                stream = self._process_video_stream(stream_dict)
            elif codec_type == "audio":
                stream = self._process_audio_stream(stream_dict)
            elif codec_type == "subtitle":
                stream = self._process_subtitle_stream(stream_dict)
            else:
                stream = Stream()
                stream.type = codec_type
                stream.info_string = 'Data'

        stream.index = stream_dict['index']

        self.__dp("left StoryBoard._process_stream")
        return stream

    def _process_video_stream(self, stream_dict):
        """Process video stream object returned by FFprobe.

        Also set Video's `dimension`, `dimension_text`, `dar`,
        `dar_text`, `frame_rate`, and `frame_rate_text` attributes
        (attributes of ``self`` ) if they are available in this video
        stream and they are not already set.

        Parameters
        ----------
        stream_dict : dict
            A dict representing a FFprobe-generated JSON video stream
            object.

        Returns
        -------
        stream : Stream
            A Stream object containing parsed metadata.

        """

        # pylint: disable=too-many-statements,too-many-branches

        self.__dp("entered StoryBoard._process_video_stream")
        sdict = stream_dict  # alias to the long long name

        if sdict['codec_type'] != "video":
            raise ValueError("stream_dict is not a video stream")

        # pylint: disable=invalid-name
        # the stream appears way to often
        s = Stream()
        s.type = "video"

        # codec
        if 'codec_name' not in sdict:
            s.codec = "unknown codec"
        elif sdict['codec_name'] in _VCODEC_MAP:
            codec_name = sdict['codec_name']
            s.codec = _VCODEC_MAP[codec_name]

            # some codecs that need special treatment
            if ((codec_name in {'h264', 'hevc'} and
                 'profile' in sdict and 'level' in sdict)):
                # H.264 and HEVC have profiles and levels. Examples:
                #     H.264 (High Profile level 1.1)
                #     HEVC (Main Profile level 3.0)
                s.codec = ("%s (%s Profile level %.1f)" %
                           (s.codec, sdict['profile'], sdict['level'] / 10.0))
            elif (codec_name in {'mpeg1video', 'mpeg2video'} and
                  'profile' in sdict):
                # MPEG-1 Part 2 and MPEG-2 Part 2 has profiles. Example:
                #     MPEG-1 Part 2 (Main Profile)
                #     MPEG-2 Part 2 (Main Profile)
                s.codec = "%s (%s Profile)" % (s.codec, sdict['profile'])
            elif codec_name in {'mpeg4'} and 'profile' in sdict:
                # MPEG-4 Part 2 has profiles. Example:
                #     MPEG-4 Part 2 (Simple Profile)
                # This case is different in that FFprobe's profile field
                # already includes the word "Profile".
                s.codec = "%s (%s)" % (s.codec, sdict['profile'])
        else:
            s.codec = sdict['codec_long_name']

        # dimension
        s.width = sdict['width']
        s.height = sdict['height']
        s.dimension = (s.width, s.height)
        s.dimension_text = "%dx%d" % (s.width, s.height)
        if self.dimension is None:
            # set video dimension to dimension of the first video stream
            self.dimension = s.dimension
            self.dimension_text = s.dimension_text

        # display aspect ratio (DAR)
        if 'display_aspect_ratio' in sdict:
            s.dar = util.evaluate_ratio(sdict['display_aspect_ratio'])
        if s.dar is not None:
            s.dar_text = sdict['display_aspect_ratio']
        else:
            gcd = fractions.gcd(s.width, s.height)
            reduced_width = s.width // gcd
            reduced_height = s.height // gcd
            s.dar = reduced_width / reduced_height
            s.dar_text = "%d:%d" % (reduced_width, reduced_height)
        if self.dar is None:
            # set video DAR to DAR of the first video stream
            self.dar = s.dar
            self.dar_text = s.dar_text

        # frame rate
        if 'r_frame_rate' in sdict:
            s.frame_rate = util.evaluate_ratio(sdict['r_frame_rate'])
        elif 'avg_frame_rate' in sdict:
            s.frame_rate = util.evaluate_ratio(sdict['avg_frame_rate'])
        else:
            s.frame_rate = None

        if s.frame_rate is not None:
            fps = s.frame_rate
            if abs(fps - int(fps)) < 0.0001:  # integer
                s.frame_rate_text = '%d fps' % int(fps)
            else:
                s.frame_rate_text = "%.2f fps" % fps
        else:
            s.frame_rate_text = None

        if self.frame_rate is None:
            # set video frame rate to that of the first video stream
            self.frame_rate = s.frame_rate
            self.frame_rate_text = s.frame_rate_text

        # bit rate
        if 'bit_rate' in sdict:
            s.bit_rate = float(sdict['bit_rate'])
            s.bit_rate_text = '%d kb/s' % int(round(s.bit_rate / 1000))
        else:
            s.bit_rate = None
            s.bit_rate_text = None

        # assemble info string
        s.info_string = ("Video, %s, %s (DAR %s)" %
                         (s.codec, s.dimension_text, s.dar_text))
        if s.frame_rate_text:
            s.info_string += ", " + s.frame_rate_text
        if s.bit_rate_text:
            s.info_string += ", " + s.bit_rate_text

        self.__dp("left StoryBoard._process_video_stream")
        return s

    def _process_audio_stream(self, stream_dict):
        """Process audio stream object returned by FFprobe.

        Parameters
        ----------
        stream_dict : dict
            A dict representing a FFprobe-generated JSON audio stream
            object.

        Returns
        -------
        stream : Stream
            A Stream object containing parsed metadata.

        """

        # pylint: disable=too-many-statements,too-many-branches

        self.__dp("entered StoryBoard._process_audio_stream")
        sdict = stream_dict  # alias to the long long name

        if sdict['codec_type'] != "audio":
            raise ValueError("stream_dict is not a audio stream")

        # pylint: disable=invalid-name
        # the stream appears way to often
        s = Stream()
        s.type = "audio"

        # codec
        if 'codec_name' not in sdict:
            s.codec = "unknown codec"
        elif sdict['codec_name'] in _ACODEC_MAP:
            codec_name = sdict['codec_name']
            s.codec = _ACODEC_MAP[codec_name]

            # some codecs that need special treatment
            if codec_name == "aac" and 'profile' in sdict:
                if sdict['profile'] == 'LC':
                    profile = 'Low-Complexity'
                elif sdict['profile'] == 'HE-AACv2':
                    profile = 'HE-AAC v2'
                else:
                    profile = sdict['profile']
                s.codec = "AAC (%s)" % profile
        else:
            s.codec = sdict['codec_long_name']

        # bit rate
        if 'bit_rate' in sdict:
            s.bit_rate = float(sdict['bit_rate'])
            s.bit_rate_text = '%d kb/s' % int(round(s.bit_rate / 1000))
        else:
            s.bit_rate = None
            s.bit_rate_text = None

        # language
        if 'tags' in sdict:
            if 'language' in sdict['tags']:
                s.language_code = sdict['tags']['language']
            elif 'LANGUAGE' in sdict['tags']:
                s.language_code = sdict['tags']['LANGUAGE']

        # assemble info string
        if s.language_code:
            s.info_string = "Audio (%s), %s" % (s.language_code, s.codec)
        else:
            s.info_string = "Audio, %s" % s.codec
        if s.bit_rate_text:
            s.info_string += ", " + s.bit_rate_text

        self.__dp("left StoryBoard._process_audio_stream")
        return s

    def _process_subtitle_stream(self, stream_dict):
        """Process subtitle stream object returned by FFprobe.

        Parameters
        ----------
        stream_dict : dict
            A dict representing a FFprobe-generated JSON subtitle stream
            object.

        Returns
        -------
        stream : Stream
            A Stream object containing parsed metadata.

        """

        # pylint: disable=too-many-statements,too-many-branches

        self.__dp("entered StoryBoard._process_subtitle_stream")
        sdict = stream_dict  # alias to the long long name

        if sdict['codec_type'] != "subtitle":
            raise ValueError("stream_dict is not a subtitle stream")

        # pylint: disable=invalid-name
        # the stream appears way to often
        s = Stream()
        s.type = "subtitle"

        if 'codec_name' not in sdict:
            if (('codec_tag_string' in sdict and
                 sdict['codec_tag_string'] == 'c608')):
                s.codec = 'EIA-608'
            else:
                s.codec = "unknown codec"
        elif sdict['codec_name'] in _SCODEC_MAP:
            codec_name = sdict['codec_name']
            s.codec = _SCODEC_MAP[codec_name]
        else:
            s.codec = sdict['codec_long_name']

        # language
        if 'tags' in sdict:
            if 'language' in sdict['tags']:
                s.language_code = sdict['tags']['language']
            elif 'LANGUAGE' in sdict['tags']:
                s.language_code = sdict['tags']['LANGUAGE']

        # assemble info string
        if s.language_code:
            s.info_string = "Subtitle (%s), %s" % (s.language_code, s.codec)
        else:
            s.info_string = "Subtitle, %s" % s.codec

        self.__dp("left StoryBoard._process_subtitle_stream")
        return s

    def __dp(self, string, newline=True):
        """Debug printing."""
        if hasattr(self, "_Video__debug") and self.__debug:
            if newline:
                print(string, file=sys.stderr)
            else:
                sys.stderr.write(string)
            sys.stderr.flush()


def main():
    """CLI interface."""

    # pylint: disable=too-many-locals,too-many-statements,too-many-branches

    description = """Print video metadata.

    You may supply a list of videos, and the output for each video will
    be followed by a blank line to distinguish it from others. Below is
    the list of available options and their brief explanations. Some of
    the options can also be stored in a configuration file,
    $XDG_CONFIG_HOME/storyboard/storyboard.conf (or if $XDG_CONFIG_HOME
    is not defined, ~/.config/storyboard/storyboard.conf), under the
    "metadata-cli" section (the conf file format follows that described
    in https://docs.python.org/3/library/configparser.html).

    For more detailed explanations, see
    http://storyboard.rtfd.org/en/stable/metadata-cli.html (or replace
    "stable" with the version you are using).
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'videos', nargs='+', metavar='VIDEO',
        help="Path(s) to the video file(s).")
    parser.add_argument(
        '--ffprobe-bin', metavar='NAME',
        help="""The name/path of the ffprobe binary. The binay is
        guessed from OS type if this option is not specified.""")
    parser.add_argument(
        '--include-sha1sum', '-s', action='store_const', const=True,
        help="Include SHA-1 digest of the video(s).")
    parser.add_argument(
        '--exclude-sha1sum', action='store_true',
        help="""Exclude SHA-1 digest of the video(s). Overrides
        '--include-sha1sum'. This option is only useful if
        include_sha1sum is turned on by default in the config file.""")
    parser.add_argument(
        '--verbose', '-v', choices=['auto', 'on', 'off'],
        nargs='?', const='auto',
        help="""Whether to print progress information to stderr. Default
        is 'auto'.""")
    parser.add_argument(
        '--version', action='version', version=version.__version__)
    cli_args = parser.parse_args()

    if 'XDG_CONFIG_HOME' in os.environ:
        config_file = os.path.join(os.environ['XDG_CONFIG_HOME'],
                                   'storyboard/storyboard.conf')
    else:
        config_file = os.path.expanduser('~/.config/storyboard/storyboard.conf')

    defaults = {
        'ffprobe_bin': fflocate.guess_bins()[1],
        'include_sha1sum': False,
        'verbose': 'auto',
    }

    optreader = util.OptionReader(
        cli_args=cli_args,
        config_files=config_file,
        section='metadata-cli',
        defaults=defaults,
    )
    ffprobe_bin = optreader.opt('ffprobe_bin')
    include_sha1sum = optreader.opt('include_sha1sum', opttype=bool)
    if cli_args.exclude_sha1sum:
        # force override
        include_sha1sum = False
    verbose = optreader.opt('verbose')
    if verbose == 'on':
        print_progress = True
    elif verbose == 'off':
        print_progress = False
    else:
        if verbose != 'auto':
            msg = ("warning: '%s' is a not a valid argument to --verbose; "
                   "ignoring and using 'auto' instead\n" % verbose)
            sys.stderr.write(msg)
        if include_sha1sum and sys.stderr.isatty():
            print_progress = True
        else:
            print_progress = False

    # test ffprobe_bin
    try:
        fflocate.check_bins((None, ffprobe_bin))
    except OSError:
        msg = ("fatal error: '%s' does not exist on PATH or is corrupted "
               "(expected FFprobe)\n" % ffprobe_bin)
        sys.stderr.write(msg)
        exit(1)

    # real stuff happens from here
    returncode = 0
    for video in cli_args.videos:
        # pylint: disable=invalid-name
        try:
            v = Video(video, params={
                'ffprobe_bin': ffprobe_bin,
                'print_progress': print_progress,
            })
        except OSError as err:
            sys.stderr.write("error: %s\n\n" % str(err))
            returncode = 1
            continue

        metadata_string = v.format_metadata(params={
            'include_sha1sum': include_sha1sum,
            'print_progress': print_progress,
        })

        if print_progress:
            # print one empty line to separate progress info and output
            # content
            sys.stderr.write("\n")
        print(metadata_string)
        print('')
    return returncode


if __name__ == "__main__":
    exit(main())
