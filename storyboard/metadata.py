#!/usr/bin/env python3

"""Extract video metadata and generate string for pretty-printing."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import fractions
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time

def _round_up(number, ndigits=0):
    """Round a nonnegative number UPWARD to a given precision in decimal digits.

    Keyword arguments:
    number -- nonnegative floating point number
    ndigits -- number of decimal digits to round to, default is 0

    Returns: float
    """
    multiplier = 10 ** ndigits
    return math.ceil(number * multiplier) / multiplier

_NUM_COLON_DEN = re.compile(r'^([1-9][0-9]*):([1-9][0-9]*)$')
_NUM_SLASH_DEN = re.compile(r'^([1-9][0-9]*)/([1-9][0-9]*)$')
def _evaluate_ratio(ratio_str):
    """Evaluate ratio in the form num:den or num/den.

    Note that numerator and denominator should both be positive integers.

    Keyword arguments:
    ratio_str: the ratio as a string (either 'num:den' or 'num/den' where num
               and den are positive integers

    Returns: the ratio as a float (or None if malformed)
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

def _humansize(size):
    """Return a human readable string of the given size in bytes."""
    multiplier = 1024.0
    if size < multiplier:
        return "%dB" % size
    for unit in ['Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        size /= multiplier
        if size < multiplier:
            if size < 10:
                return "%.2f%sB" % (_round_up(size, 2), unit)
            elif size < 100:
                return "%.1f%sB" % (_round_up(size, 1), unit)
            else:
                return "%.0f%sB" % (_round_up(size, 0), unit)
            break
    else:
        return "%.1f%sB" % (_round_up(size, 1), unit)

def _humantime(seconds, ndigits=2, one_hour_digit=False):
    """Return a human readable string of the given duration in seconds.

    Keyword arguments:
    ndigits - number of digits after the decimal point for the seconds part,
              default is 2
    one_hour_digit - if True, only print one hour digit; default is two hour
                     digits
    """
    hh = int(seconds) // 3600 # hours
    mm = (int(seconds) // 60) % 60 # minutes
    ss = seconds - (int(seconds) // 60) * 60 # seconds
    hh_format = "%01d" if one_hour_digit else "%02d"
    mm_format = "%02d"
    ss_format = "%02d" if ndigits == 0 else \
                "%0{0}.{1}f".format(ndigits + 3, ndigits)
    format_string = "{0}:{1}:{2}".format(hh_format, mm_format, ss_format)
    return format_string % (hh, mm, ss)

_PROGRESS_UPDATE_INTERVAL = 1.0
class ProgressBar(object):
    """Progress bar for file processing.

    Format inspired by pv(1) (pipe viewer).
    """

    def __init__(self, totalsize, interval = _PROGRESS_UPDATE_INTERVAL):
        self.totalsize = totalsize
        self.processed = 0
        self.last_processed = 0
        self.start = time.time()
        self.last = self.start
        self.elapsed = None # to be set after finishing
        # calculate bar length
        try:
            ncol, _ = os.get_terminal_size()
        except AttributeError:
            # python2 do not have os.get_terminal_size
            # assume a minimum of 80 columns
            ncol = 80
        self.barlen = (ncol - 47) if ncol >= 57 else 10
        # generate the format string for a progress bar line
        #
        # 0: processed size, e.g., 2.02GiB
        # 1: elapsed time (7 chars), e.g., 0:00:04
        # 2: current processing speed, e.g., 424MiB (/s is already hardcoded)
        # 3: the bar, in the form "=====>   "
        # 4: number of percent done, e.g., 99
        # 5: estimated time remaining (11 chars), in the form "ETA H:MM:SS"; if
        #    finished, fill with space
        self.fmtstr = '{0:>7s} {1} [{2:>7s}/s] [{3}] {4:>3s}% {5}\r'

    def update(self, chunk_size):
        """Update the progress bar for the newly processed chunk.

        Keyword arguments:
        chunk_size: the size of the new chunk since the last update
        """
        self.processed += chunk_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def refresh(self, processed_size):
        """Refresh the progress bar with the updated processed size.

        Keyword arguments:
        processed_size: size of the processed part of the file, overwrites
                        existing value
        """
        self.processed = processed_size
        if self.processed > self.totalsize:
            self.processed = self.totalsize
        self._update_output()

    def finish(self):
        self.elapsed = time.time() - self.start
        self.processed = self.totalsize
        self.last = None
        self.last_processed = None

        processed_s = _humansize(self.totalsize)
        elapsed_s = self._humantime(self.elapsed)
        speed_s = _humansize(self.totalsize / self.elapsed)
        bar = '=' * (self.barlen - 1) + '>'
        percent_s = '100'
        eta_s = ' ' * 11
        sys.stderr.write(self.fmtstr.format(
            processed_s, elapsed_s, speed_s, bar, percent_s, eta_s
        ))
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _update_output(self):
        if time.time() - self.last < 1:
            return

        # speed in the last second
        speed = (self.processed - self.last_processed) / \
                (time.time() - self.last) # bytes per second
        # update last stats for the next update
        self.last = time.time()
        self.last_processed = self.processed

        # _s suffix stands for string
        processed_s = _humansize(self.processed)
        elapsed_s = self._humantime(time.time() - self.start)
        speed_s = _humansize(speed)
        percentage = self.processed / self.totalsize # absolute
        percent_s = str(int(percentage * 100))
        # generate bar
        length = int(round(self.barlen * percentage))
        fill = self.barlen - length
        if length == 0:
            bar = " " * self.barlen
        else:
            bar = '=' * (length - 1) + '>' + ' ' * fill
        # calculate ETA
        remaining = self.totalsize - self.processed
        # estimate based on current speed
        eta = remaining / speed
        eta_s = "ETA %s" % self._humantime(eta)

        sys.stderr.write(self.fmtstr.format(
            processed_s, elapsed_s, speed_s, bar, percent_s, eta_s
        ))
        sys.stderr.flush()

    def _humantime(self, seconds):
        # pylint: disable=no-self-use
        """Customized _humantime"""
        return _humantime(seconds, ndigits=0, one_hour_digit=True)

class Stream(object):
    """Container for stream metadata."""

    # pylint: disable=too-many-instance-attributes
    # a stream can have any number of attributes

    def __init__(self):
        # general stream attributes
        self.index = None
        self.type = None
        self.codec = None
        self.info_string = None
        self.bit_rate = None
        self.bit_rate_text = None
        self.language_code = None
        # video stream specific attributes
        self.height = None
        self.width = None
        self.dimension = None
        self.dimension_text = None
        self.frame_rate = None
        self.frame_rate_text = None
        self.dar = None # display aspect ratio
        self.dar_text = None

class Video(object):
    """Container for video and streams metadata."""

    # pylint: disable=too-many-instance-attributes
    # again, a video can have any number of metadata attributes

    def __init__(self, video, ffprobe_bin='ffprobe'):
        self.path = os.path.abspath(video)
        if not os.path.exists(self.path):
            raise OSError("'" + video + "' does not exist")
        self.filename = os.path.basename(self.path)
        if hasattr(self.filename, 'decode'):
            # python2 str
            self.filename = self.filename.decode('utf-8')

        self._call_ffprobe(ffprobe_bin)
        self._extract_container_format()
        self._extract_title()
        self._extract_size()
        self._extract_duration()
        self._extract_scan_type(ffprobe_bin)
        self.sha1sum = None
        self.dimension = None
        self.dimension_text = None
        self.dar = None
        self.dar_text = None
        self.frame_rate = None
        self.frame_rate_text = None
        self._extract_streams()

    def compute_sha1sum(self):
        """Compute SHA-1 hex digest of the video file."""
        if not self.sha1sum:
            self._extract_sha1sum()
        return self.sha1sum

    def pretty_print_metadata(self, include_sha1sum=False):
        """Pretty print video metadata.

        Keyword arguments:
        includ_sha1sum: boolean, whether to include SHA-1 hexdigest of the video
                        file -- defaults to false; keep in mind that computing
                        SHA-1 is an expansive operation, and is only done upon
                        request

        Returns: a string that can be printed directly
        """
        # pylint: disable=invalid-name
        # s is fully recognizable as the variable name of the string, and in
        # fact, it is the only variable here
        s = ""
        # title
        if self.title:
            s += "Title:                  %s\n" % self.title
        # filename
        s += "Filename:               %s\n" % self.filename
        # size
        s += "File size:              %d (%s)\n" % (self.size, self.size_human)
        # sha1sum
        if include_sha1sum:
            self.compute_sha1sum()
            s += "SHA-1 digest:           %s\n" % self.sha1sum
        # container format
        s += "Container format:       %s\n" % self.format
        # duration
        s += "Duration:               %s\n" % self.duration_human
        # dimension
        if self.dimension_text:
            s += "Pixel dimensions:       %s\n" % self.dimension_text
        # aspect ratio
        if self.dar_text:
            s += "Display aspect ratio:   %s\n" % self.dar_text
        # scanning type
        if self.scan_type:
            s += "Scan type:              %s\n" % self.scan_type
        # frame rate
        if self.frame_rate:
            s += "Frame rate:             %s\n" % self.frame_rate_text
        # streams
        s += "Streams:\n"
        for stream in self.streams:
            s += "    #%d: %s\n" % (stream.index, stream.info_string)
        return s.strip()

    def _call_ffprobe(self, ffprobe_bin):
        """Call ffprobe and store json output in self._ffprobe.

        ffprobe is called with -show_format and -show_streams options.
        """
        ffprobe_args = [ffprobe_bin,
                        '-loglevel', 'fatal',
                        '-print_format', 'json',
                        '-show_format', '-show_streams',
                        self.path]
        proc = subprocess.Popen(ffprobe_args,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_out, ffprobe_err = proc.communicate()
        if proc.returncode != 0:
            msg = "ffprobe failed on '%s'\n%s" %(self.path, ffprobe_err)
            msg = msg.strip()
            raise OSError(msg)
        self._ffprobe = json.loads(ffprobe_out.decode('utf-8'))

    def _extract_title(self):
        """Extract title of the video (if any) and store in self.title."""
        video_container_metadata = self._ffprobe['format']
        if 'tags' in video_container_metadata and \
           'title' in video_container_metadata['tags']:
            self.title = video_container_metadata['tags']['title']
        else:
            self.title = None
        if hasattr(self.title, 'decode'):
            # python2 str
            self.title = self.title.decode('utf-8')

    def _extract_container_format(self):
        """Extract container format of the video and store in self.format."""
        format_name = self._ffprobe['format']['format_name']
        # format_long_name = self._ffprobe['format']['format_long_name']
        # lowercase extension without period
        extension = os.path.splitext(self.path)[1].lower()[1:]
        if format_name == 'mpegts':
            self.format = "MPEG transport stream"
        elif format_name == 'mpeg':
            self.format = "MPEG program stream"
        elif format_name == 'mov,mp4,m4a,3gp,3g2,mj2':
            if extension in ['mov', 'qt']:
                self.format = "QuickTime movie"
            elif extension in ['3gp']:
                self.format = "3GPP"
            elif extension in ['3g2']:
                self.format = "3GPP2"
            elif extension in ['mj2', 'mjp2']:
                self.format = "Motion JPEG 2000"
            else:
                # mp4, m4v, m4a, etc.
                self.format = "MPEG-4 Part 14 (%s)" % extension.upper()
        elif format_name == 'mpegvideo':
            self.format = "MPEG video"
        elif format_name == 'matroska,webm':
            if extension in ['webm']:
                self.format = "WebM"
            else:
                self.format = "Matroska"
        elif format_name == 'flv':
            self.format = "Flash video"
        elif format_name == 'ogg':
            self.format = "Ogg"
        elif format_name == 'avi':
            self.format = "Audio Video Interleaved"
        elif format_name == 'asf':
            # Microsoft Advanced Systems Format
            self.format = "Advanced Systems Format"
        else:
            self.format = extension.upper()

    def _extract_size(self):
        """Extract size of the video file.

        Store the numeric value (in bytes) in self.size, and the human readable
        string in self.size_human.
        """
        self.size = int(self._ffprobe['format']['size'])
        self.size_human = _humansize(self.size)

    def _extract_duration(self):
        """Extract duration of the video.

        Store the numeric value (in seconds) in self.duration, and the human
        readable string in self.duration_human.
        """
        self.duration = float(self._ffprobe['format']['duration'])
        self.duration_human = _humantime(self.duration)

    _SHA_CHUNK_SIZE = 65536
    def _extract_sha1sum(self, print_progress=False):
        """Extract SHA-1 hexdigest of the video file."""
        with open(self.path, 'rb') as video:
            sha1 = hashlib.sha1()
            totalsize = os.path.getsize(self.path)
            chunksize = self._SHA_CHUNK_SIZE

            if print_progress:
                pbar = ProgressBar(totalsize)
            for chunk in iter(lambda: video.read(chunksize), b''):
                sha1.update(chunk)
                if print_progress:
                    pbar.update(chunksize)
            if print_progress:
                pbar.finish()

            self.sha1sum = sha1.hexdigest()

    def _extract_scan_type(self, ffprobe_bin):
        """Determine the scan type of the video.

        Progressive or interlaced scan. Saved in self.scan_type.
        """
        # experimental feature
        #
        # Scan the first megabyte of the video and use FFprobe to determine if
        # there are interlaced frames; if so, decide that the video is
        # interlaced.
        #
        # This is of course a dirty hack and an oversimplification. For intance,
        # there's no distinction between fully interlaced video and telecined
        # video. (In fact I know little about telecine, so I don't have to plan
        # to distinguish it.)

        # read first megabyte of the video
        with open(self.path, 'rb') as video:
            head = video.read(1000000)
        # pass the first megabyte to ffprobe
        ffprobe_args = [ffprobe_bin,
                        '-select_streams', 'v',
                        '-show_frames',
                        '-']
        proc = subprocess.Popen(ffprobe_args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_out, _ = proc.communicate(input=head)
        if b'interlaced_frame=1' in ffprobe_out:
            self.scan_type = 'Interlaced scan'
        else:
            self.scan_type = 'Progressive scan'

    def _process_video_stream(self, stream):
        # pylint: disable=too-many-statements
        """Process video stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "video")

        Returns: a Stream object containing stream metadata.
        """
        if stream['codec_type'] != "video":
            raise ValueError("passed stream is not a video stream")

        # pylint: disable=invalid-name
        s = Stream()
        s.type = "video"

        # codec
        if 'codec_name' not in stream:
            s.codec = "unknown codec"
        elif stream['codec_name'] == "h264":
            if 'profile' in stream and 'level' in stream:
                s.codec = "H.264 (%s Profile level %.1f)" %\
                          (stream['profile'], stream['level'] / 10.0)
            else:
                s.codec = "H.264"
        elif stream['codec_name'] == "mpeg2video":
            if 'profile' in stream:
                s.codec = "MPEG-2 video (%s Profile)" % stream['profile']
            else:
                s.codec = "MPEG-2 video"
        elif stream['codec_name'] == "mpeg4":
            if 'profile' in stream:
                s.codec = "MPEG-4 Part 2 (%s)" % stream['profile']
            else:
                s.codec = "MPEG-4 Part 2"
        elif stream['codec_name'] == "mjpeg":
            s.codec = "MJPEG"
        elif stream['codec_name'] == "theora":
            s.codec = "Theora"
        else:
            s.codec = stream['codec_long_name']

        # dimension
        s.width = stream['width']
        s.height = stream['height']
        s.dimension = (s.width, s.height)
        s.dimension_text = "%dx%d" % (s.width, s.height)
        if self.dimension is None:
            # set video dimension to dimension of the first video stream
            self.dimension = s.dimension
            self.dimension_text = s.dimension_text

        # display aspect ratio (DAR)
        if 'display_aspect_ratio' in stream:
            s.dar = _evaluate_ratio(stream['display_aspect_ratio'])
        if s.dar is not None:
            s.dar_text = stream['display_aspect_ratio']
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
        if 'r_frame_rate' in stream:
            s.frame_rate = _evaluate_ratio(stream['r_frame_rate'])
        elif 'avg_frame_rate' in stream:
            s.frame_rate = _evaluate_ratio(stream['avg_frame_rate'])
        else:
            s.frame_rate = None

        if s.frame_rate is not None:
            fps = s.frame_rate
            if abs(fps - int(fps)) < 0.0001: # integer
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
        if 'bit_rate' in stream:
            s.bit_rate = float(stream['bit_rate'])
            s.bit_rate_text = '%d kb/s' % int(round(s.bit_rate / 1000))
        else:
            s.bit_rate = None
            s.bit_rate_text = None

        # assemble info string
        s.info_string = "Video, %s, %s (DAR %s)" % \
                        (s.codec, s.dimension_text, s.dar_text)
        if s.frame_rate_text:
            s.info_string += ", " + s.frame_rate_text
        if s.bit_rate_text:
            s.info_string += ", " + s.bit_rate_text

        return s

    def _process_audio_stream(self, stream):
        # pylint: disable=no-self-use,too-many-statements
        """Process audio stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "audio")

        Returns: a Stream object containing stream metadata.
        """
        if stream['codec_type'] != "audio":
            raise ValueError("passed stream is not an audio stream")

        # pylint: disable=invalid-name
        s = Stream()
        s.type = "audio"

        # codec
        if 'codec_name' not in stream:
            s.codec = "unknown codec"
        elif stream['codec_name'] == "aac":
            if 'profile' in stream:
                if stream['profile'] == "LC":
                    profile = "Low Complexity"
                else:
                    profile = stream['profile']
                s.codec = "AAC (%s)" % profile
            else:
                s.codec = "AAC"
        elif stream['codec_name'] == "ac3":
            s.codec = "Dolby AC-3"
        elif stream['codec_name'] == "mp3":
            s.codec = "MP3"
        elif stream['codec_name'] == "vorbis":
            s.codec = "Vorbis"
        else:
            s.codec = stream['codec_long_name']

        # bit rate
        if 'bit_rate' in stream:
            s.bit_rate = float(stream['bit_rate'])
            s.bit_rate_text = '%d kb/s' % int(round(s.bit_rate / 1000))
        else:
            s.bit_rate = None
            s.bit_rate_text = None

        # language
        if 'tags' in stream:
            if 'language' in stream['tags']:
                s.language_code = stream['tags']['language']
            elif 'LANGUAGE' in stream['tags']:
                s.language_code = stream['tags']['LANGUAGE']

        # assemble info string
        if s.language_code:
            s.info_string = "Audio (%s), %s" % (s.language_code, s.codec)
        else:
            s.info_string = "Audio, %s" % s.codec
        if s.bit_rate_text:
            s.info_string += ", " + s.bit_rate_text

        return s

    def _process_subtitle_stream(self, stream):
        # pylint: disable=no-self-use
        """Process subtitle stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "subtitle")

        Returns: a Stream object containing stream metadata.
        """
        if stream['codec_type'] != "subtitle":
            raise ValueError("passed stream is not a subtitle stream")

        # pylint: disable=invalid-name
        s = Stream()
        s.type = "subtitle"

        if 'codec_name' not in stream:
            if 'codec_tag_string' in stream and \
               stream['codec_tag_string'] == 'c608':
                s.codec = 'EIA-608'
            else:
                s.codec = "unknown codec"
        elif stream['codec_name'] == "srt":
            s.codec = "SubRip"
        elif stream['codec_name'] == "ass":
            s.codec = "ASS"
        elif stream['codec_name'] == "cc_dec":
            s.codec = "closed caption (EIA-608 / CEA-708)"
        else:
            s.codec = stream['codec_long_name']

        # language
        if 'tags' in stream:
            if 'language' in stream['tags']:
                s.language_code = stream['tags']['language']
            elif 'LANGUAGE' in stream['tags']:
                s.language_code = stream['tags']['LANGUAGE']

        # assemble info string
        if s.language_code:
            s.info_string = "Subtitle (%s), %s" % (s.language_code, s.codec)
        else:
            s.info_string = "Subtitle, %s" % s.codec

        return s

    def _process_stream(self, stream):
        """Convert an FFprobe stream object to our own stream object."""

        # Different codecs are dealt with differently. This function contains a
        # growing list of codecs I frequently encounter. I do not intend to be
        # exhaustive, but everyone is welcome to contribute code for their
        # favorite codecs.

        # pylint: disable=invalid-name
        # s is a Stream object for storing stream metadata

        if 'codec_type' not in stream:
            s = Stream()
            s.type = 'unknown'
            s.info_string = "Data"
        elif stream['codec_type'] == "video":
            s = self._process_video_stream(stream)
        elif stream['codec_type'] == "audio":
            s = self._process_audio_stream(stream)
        elif stream['codec_type'] == "subtitle":
            s = self._process_subtitle_stream(stream)
        else:
            s = Stream()
            s.type = stream['codec_type']
            s.info_string = 'Data'

        s.index = stream['index']

        return s

    def _extract_streams(self):
        """Extract metadata of streams.

        Save to self.streams, which is a list of Stream objects.
        """
        self.streams = []
        for stream in self._ffprobe['streams']:
            self.streams.append(self._process_stream(stream))

def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(description="Print video metadata.")
    parser.add_argument('videos', nargs='+', metavar='VIDEO',
                        help="path(s) to the video file(s)")
    parser.add_argument('--include-sha1sum', '-s', action='store_true',
                        help="print SHA-1 digest of video(s); slow")
    parser.add_argument('--ffprobe-binary', '-f', default='ffprobe',
                        help="""the name/path of the ffprobe binary; default is
                        'ffprobe'""")
    args = parser.parse_args()
    for video in args.videos:
        # pylint: disable=invalid-name
        v = Video(video, args.ffprobe_binary)
        print(v.pretty_print_metadata(include_sha1sum=args.include_sha1sum))
        print('')

if __name__ == "__main__":
    main()
