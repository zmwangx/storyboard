#!/usr/bin/env python3

"""Extract video metadata and generate string for pretty-printing."""

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

from storyboard import util

class Stream(object):
    """Container for stream metadata."""

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
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

    def __init__(self, video, ffprobe_bin='ffprobe', print_progress=False):
        self.path = os.path.abspath(video)
        if not os.path.exists(self.path):
            raise OSError("'" + video + "' does not exist")
        self.filename = os.path.basename(self.path)
        if hasattr(self.filename, 'decode'):
            # python2 str
            self.filename = self.filename.decode('utf-8')

        if print_progress:
            sys.stderr.write("Processing %s\n" % self.filename)
            sys.stderr.write("Crunching metadata...\n")

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

    def compute_sha1sum(self, print_progress=False):
        """Compute SHA-1 hex digest of the video file."""
        if not self.sha1sum:
            if print_progress:
                sys.stderr.write("Calculating SHA-1 digest...\n")
            self._extract_sha1sum(print_progress)
        return self.sha1sum

    def pretty_print_metadata(self, include_sha1sum=False, print_progress=False):
        """Pretty print video metadata.

        Keyword arguments:
        includ_sha1sum: boolean, whether to include SHA-1 hexdigest of the video
                        file -- defaults to false; keep in mind that computing
                        SHA-1 is an expansive operation, and is only done upon
                        request
        print_progress: boolean, whether to print progress information to stderr
                        -- defaults to false

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
            self.compute_sha1sum(print_progress)
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
        # pylint: disable=too-many-branches
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
        self.size_human = util.humansize(self.size)

    def _extract_duration(self):
        """Extract duration of the video.

        Store the numeric value (in seconds) in self.duration, and the human
        readable string in self.duration_human.
        """
        self.duration = float(self._ffprobe['format']['duration'])
        self.duration_human = util.humantime(self.duration)

    _SHA_CHUNK_SIZE = 65536
    def _extract_sha1sum(self, print_progress=False):
        """Extract SHA-1 hexdigest of the video file."""
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
        """Process video stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "video")

        Returns: a Stream object containing stream metadata.
        """
        # pylint: disable=too-many-statements,too-many-branches
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
            s.dar = util.evaluate_ratio(stream['display_aspect_ratio'])
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
            s.frame_rate = util.evaluate_ratio(stream['r_frame_rate'])
        elif 'avg_frame_rate' in stream:
            s.frame_rate = util.evaluate_ratio(stream['avg_frame_rate'])
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
        """Process audio stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "audio")

        Returns: a Stream object containing stream metadata.
        """
        # pylint: disable=no-self-use,too-many-statements,too-many-branches
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
        """Process subtitle stream.

        Keyword arguments:
        stream: a JSON stream object returned by ffprobe (stream['codec_type']
                must be "subtitle")

        Returns: a Stream object containing stream metadata.
        """
        # pylint: disable=no-self-use,too-many-branches
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
    parser.add_argument('--quiet', '-q', action='store_true',
                        help="""when enabled, suppress progress information and
                        only print the metadata you ask for""")
    args = parser.parse_args()
    ffprobe_bin = args.ffprobe_binary
    include_sha1sum = args.include_sha1sum
    print_progress = not(args.quiet)
    for video in args.videos:
        # pylint: disable=invalid-name
        v = Video(video, ffprobe_bin=ffprobe_bin, print_progress=print_progress)
        metadata_string = v.pretty_print_metadata(
            include_sha1sum=include_sha1sum,
            print_progress=print_progress
        )
        if print_progress:
            # print one empty line to separate progress info and output content
            sys.stderr.write("\n")
        print(metadata_string)
        print('')

if __name__ == "__main__":
    main()
