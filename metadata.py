#!/usr/bin/env python
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
        if hasattr(self.filename, 'decode'):
            # python2 str
            self.filename = self.filename.decode('utf-8')

        self._call_ffprobe(ffprobe_bin)
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
        if hasattr(self.title, 'decode'):
            # python2 str
            self.title = self.title.decode('utf-8')

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
        try:
            with open(self.path, 'rb') as f:
                self.sha1sum = hashlib.sha1(f.read()).hexdigest()
        except OSError:
            # OS X + Py3K read bug for files larger than 2 GiB
            # see http://git.io/pDnA
            # workaround: read in chunks of 1 GiB
            with open(self.path, 'rb') as f:
                buf = b''
                for chunk in iter(lambda: f.read(2**30), b''):
                    buf += chunk
                self.sha1sum = hashlib.sha1(buf).hexdigest()

    def _extract_scan_type(self, ffprobe_bin):
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
        with open(self.path, 'rb') as f:
            head = f.read(1000000)
        # pass the first megabyte to ffprobe
        ffprobe_args = [ffprobe_bin,
                        '-select_streams', 'v',
                        '-show_frames',
                        '-']
        proc = subprocess.Popen(ffprobe_args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffprobe_out, ffprobe_err = proc.communicate(input=head)
        if b'interlaced_frame=1' in ffprobe_out:
            self.scan_type = 'Interlaced scan'
        else:
            self.scan_type = 'Progressive scan'

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

        if not 'codec_type' in stream:
            s.type = 'unknown'
            s.info_string = "Data"
        elif stream['codec_type'] == "video":
            s.type = "video"

            # codec
            if not 'codec_name' in stream:
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
            # end of video stream processing
        elif stream['codec_type'] == "audio":
            s.type = "audio"

            # codec
            if not 'codec_name' in stream:
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
            else:
                s.codec = stream['codec_name'].upper()

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
            if hasattr(s, 'language_code'):
                s.info_string = "Audio (%s), %s" % (s.language_code, s.codec)
            else:
                s.info_string = "Audio, %s" % s.codec
            if s.bit_rate_text:
                s.info_string += ", " + s.bit_rate_text
            # end of audio stream processing
        elif stream['codec_type'] == "subtitle":
            if not 'codec_name' in stream:
                if 'codec_tag_string' in stream and \
                   stream['codec_tag_string'] == 'c608':
                    s.codec = 'EIA-608'
                else:
                    s.codec = "unknown codec"
            elif stream['codec_name'] == "srt":
                s.codec = "SubRip"
            elif stream['codec_name'] == "ass":
                s.codec = "ASS"
            else:
                s.codec = stream['codec_name'].upper()

            # language
            if 'tags' in stream:
                if 'language' in stream['tags']:
                    s.language_code = stream['tags']['language']
                elif 'LANGUAGE' in stream['tags']:
                    s.language_code = stream['tags']['LANGUAGE']

            # assemble info string
            if hasattr(s, 'language_code'):
                s.info_string = "Subtitle (%s), %s" % (s.language_code, s.codec)
            else:
                s.info_string = "Subtitle, %s" % s.codec
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
