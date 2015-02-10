#!/usr/bin/env python3
from __future__ import division

import argparse
import fractions
import hashlib
import json
import os
import subprocess

class Stream:
    pass

class Video:
    def __init__(self, video, ffprobe_bin='ffprobe'):
        self.path = os.path.abspath(video)
        if not os.path.exists(self.path):
            raise OSError("'" + video + "' does not exist")
        self.filename = os.path.basename(self.path)

        self._call_ffprobe(ffprobe_bin)
        self._extract_title()
        self._extract_size()
        self._extract_duration()
        self.sha1sum = None
        self.dimension = None
        self.dimension_text = None
        self.dar = None
        self.dar_text = None
        self._extract_streams()

    def compute_sha1sum(self):
        if not self.sha1sum:
            self._extract_sha1sum()
        return self.sha1sum

    def pretty_print_metadata(self, include_sha1sum=False):
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
        # duration
        s += "Duration:               %s\n" % self.duration_human
        # dimension
        if self.dimension_text:
            s += "Pixel dimensions:       %s\n" % self.dimension_text
        # aspect ratio
        if self.dar_text:
            s += "Display aspect ratio:   %s\n" % self.dar_text
        # streams
        s += "Streams:\n"
        for stream in self.streams:
            s += "    #%d: %s\n" % (stream.index, stream.info_string)
        return s.strip()

    def _call_ffprobe(self, ffprobe_bin):
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
        format = self._ffprobe['format']
        if 'tags' in format and 'title' in format['tags']:
            self.title = format['tags']['title']
        else:
            self.title = None

    def _extract_size(self):
        self.size = int(self._ffprobe['format']['size'])
        tmp = self.size
        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
            if tmp < 1024.0:
                self.size_human = "%.1f%sB" % (tmp, unit)
                break
            tmp /= 1024.0
        else:
            self.size_human = "%.1f%sB" % (tmp, 'Yi')

    def _extract_duration(self):
        self.duration = float(self._ffprobe['format']['duration'])
        t = self.duration
        hh = int(t) // 3600
        mm = (int(t) // 60) % 60
        ss = t - (int(t) // 60) * 60
        self.duration_human = "%02d:%02d:%05.2f" % (hh, mm, ss)

    def _extract_sha1sum(self):
        with open(self.path, 'rb') as f:
            self.sha1sum = hashlib.sha1(f.read()).hexdigest()

    def _process_stream(self, stream):
        """Convert an FFprobe stream object to our own stream object."""

        # Different codecs are dealt with differently. This function contains a
        # growing list of codecs I frequently encounter. I do not intend to be
        # exhaustive, but everyone is welcome to contribute code for their
        # favorite codecs.
        #
        # TO DO: subtitle streams

        s = Stream()
        s.index = stream['index']
        if stream['codec_type'] == "video":
            s.type = "video"

            # codec
            if stream['codec_name'] == "h264":
                s.codec = "H.264 (%s Profile level %.1f)" %\
                        (stream['profile'], stream['level'] / 10.0)
            elif stream['codec_name'] == "mpeg2video":
                s.codec = "MPEG-2 video (%s Profile)" % stream['profile']
            elif stream['codec_name'] == "mpeg4":
                s.codec = "MPEG-4 Part 2 (%s)" % stream['profile']
            elif stream['codec_name'] == "mjpeg":
                s.codec = "MJPEG"
            else:
                s.codec = stream['codec_name'].upper()

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
            if 'display_aspect_ratio' in stream and \
               stream['display_aspect_ratio'][:2]  != '0:' and \
               stream['display_aspect_ratio'][-2:] != ':0':
                s.dar = eval(stream['display_aspect_ratio'].replace(':', '/'))
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
            if 'r_frame_rate' in stream and \
               stream['r_frame_rate'][:2] !=  '0/' and \
               stream['r_frame_rate'][-2:] != '/0':
                s.frame_rate = eval(stream['r_frame_rate'])
            elif 'avg_frame_rate' in stream and \
                 stream['avg_frame_rate'][:2]  != '0/' and \
                 stream['avg_frame_rate'][-2:] != '/0':
                s.frame_rate = eval(stream['avg_frame_rate'])
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
            # end of video stream processing
        elif stream['codec_type'] == "audio":
            s.type = "audio"

            # codec
            if stream['codec_name'] == "aac":
                if stream['profile'] == "LC":
                    profile = "Low Complexity"
                else:
                    profile = stream['profile']
                s.codec = "AAC (%s)" % profile
            elif stream['codec_name'] == "ac3":
                s.codec = "Dolby AC-3"
            elif stream['codec_name'] == "mp3":
                s.codec = "MP3"
            else:
                s.codec = stream['codec_name'].upper()

            # bit rate
            if 'bit_rate' in stream:
                s.bit_rate = float(stream['bit_rate'])
                s.bit_rate_text = '%d kb/s' % int(round(s.bit_rate / 1000))
            else:
                s.bit_rate = None
                s.bit_rate_text = None

            # assemble info string
            s.info_string = "Audio, %s" % s.codec
            if s.bit_rate_text:
                s.info_string += ", " + s.bit_rate_text
            # end of audio stream processing
        else:
            s.type = stream['codec_type']
            s.info_string = 'Data'

        return s

    def _extract_streams(self):
        self.streams = []
        for stream in self._ffprobe['streams']:
            self.streams.append(self._process_stream(stream))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Print video metadata.")
    parser.add_argument('videos', nargs='+', metavar='VIDEO',
                        help="path to the video(s)")
    parser.add_argument('--include-sha1sum', '-s', action='store_true',
                        help="print SHA-1 digest of video(s); slow")
    parser.add_argument('--ffprobe-binary', '-f', default='ffprobe',
                        help="""the name/path of the ffprobe binary; default is
                        'ffprobe'""")
    args = parser.parse_args()
    for video in args.videos:
        v = Video(video, args.ffprobe_binary)
        print(v.pretty_print_metadata(include_sha1sum=args.include_sha1sum))
        print('')
