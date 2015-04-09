#!/usr/bin/env python3

"""Generate video storyboards with metadata reports."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import pkg_resources
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from storyboard import frame as Frame
from storyboard import metadata
from storyboard import util
from storyboard.version import __version__

# pylint: disable=too-many-locals,invalid-name
# In this file we use a lot of short local variable names to save space.
# These short variable names are carefully documented when not obvious.

def _draw_text_block(text, draw, xy, color, font, font_size, spacing):
    """Draw a block of text.

    Positional arguments:
    text      -- a string to be drawn (multi-line allowed)
    draw      -- an PIL.ImageDraw.ImageDraw object
    xy        -- (x, y) coordinate of topleft corner of the text block
    color     -- color of the text (used for the fill argument of draw.text)
    font      -- a font loaded by ImageFont
    font_size -- font size in pixels
    spacing   -- line spacing as a float, e.g., 1.2

    Return value:
    (width, height) -- size of the text block
    """
    x = xy[0]
    y = xy[1]
    line_height = int(round(font_size * spacing))
    width = 0
    height = 0
    for line in text.splitlines():
        (w, _) = draw.textsize(line, font=font)
        draw.text((x, y), line, fill=color, font=font)
        if w > width:
            width = w
        height += line_height
        y += line_height
    return (width, height)

class StoryBoard(object):
    """Class for storing video thumbnails and metadata, and creating storyboard
    on request.
    """
    # pylint: disable=bad-whitespace,too-few-public-methods
    # Here we use a lot of extra space for alignment purposes.

    def __init__(self, video, num_thumbnails=16,
                 ffmpeg_bin='ffmpeg', ffprobe_bin='ffprobe', codec='png',
                 print_progress=False):
        self.video = metadata.Video(
            video,
            ffprobe_bin=ffprobe_bin,
            print_progress=True,
        )
        self.frames = []
        duration = self.video.duration

        # generate equally spaced timestamps at 1/2N, 3/2N, ... (2N-1)/2N of the
        # video, where N is the number of thumbnails
        interval = duration / num_thumbnails
        timestamps = [ interval/2 ]
        for _ in range(1, num_thumbnails):
            timestamps.append(timestamps[-1] + interval)

        # generate frames accordingly
        counter = 0
        for timestamp in timestamps:
            counter += 1
            if print_progress:
                sys.stderr.write("\rCreating thumbnail %d/%d..." %
                                 (counter, num_thumbnails))
            self.frames.append(Frame.extract_frame(video, timestamp,
                                                   ffmpeg_bin, codec))
        if print_progress:
            sys.stderr.write("\n")

    def storyboard(self,
                   padding=(10,10), include_banner=True, print_progress=False,
                   font=None, font_size=16, text_spacing=1.2,
                   text_color='black',
                   include_sha1sum=True,
                   tiling=(4, 4), tile_width=480, tile_aspect_ratio=None,
                   tile_spacing=(4, 3),
                   draw_timestamp=True):
        """Create storyboard.

        Keyword arguments:

        General options:
        padding        -- (horizontal, vertical) padding to the entire
                          storyboard; default is (10, 10)
        include_banner -- boolean, whether or not to include a promotional
                          banner for this tool at the bottom; default is True
        print_progress -- boolean, whether or not to print progress
                          information; default is False

        Text options:
        font         -- a font object loaded from PIL.ImageFont; default is
                        SourceCodePro-Regular (included) at 16px
        font_size    -- font size in pixels, default is 16 (should match font)
        text_spacing -- line spacing as a float (text line height will be
                        calculated from round(font_size * text_spacing));
                        default is 1.2
        text_color   -- text color, either as RGBA 4-tuple or color name
                        string recognized by ImageColor; default is 'black'

        Metadata options:
        include_sha1sum -- boolean, whether or not to include SHA-1 checksum as
                           a printed metadata field; keep in mind that SHA-1
                           calculation is slow for large videos

        Tile options:
        tiling            -- (m, n) means m tiles horizontally and n tiles
                             vertically; m and n must satisfy m * n =
                             num_thumbnails (specified in __init__); default is
                             (4, 4)
        tile_width        -- width of each tile (int), default is 480
        tile_aspect_ratio -- aspect ratio of each tile; by default it is
                             determined first from the display aspect ratio
                             (DAR) of the video and then from the pixel
                             dimensions, but in case the result is wrong, you
                             can still specify the aspect ratio this way
        tile_spacing      -- (horizontal_spaing, vertical_spacing), default is
                             (4, 3), which means (before applying the global
                             padding), the tiles will be spaced from the left
                             and right edges by 4 pixels, and will have a
                             4 * 2 = 8 pixel horizontal spacing between two
                             adjacent tiles; same goes for vertical spacing;

        Timestamp options:
        draw_timestamp  -- boolean, whether or not to draw timestamps on the
                           thumbnails (lower-right corner); default is True

        Return value:
        Storyboard as a PIL.Image.Image image.
        """
        #! TO DO: check argument types and n * m = num_thumbnails
        if font is None:
            font_file = pkg_resources.resource_filename(__name__, 'SourceCodePro-Regular.otf')
            font = ImageFont.truetype(font_file, size=16)
        if tile_aspect_ratio is None:
            tile_aspect_ratio = self.video.dar

        # draw storyboard, meta sheet, and banner
        if print_progress:
            sys.stderr.write("Drawing main storyboard...\n")
        storyboard = self._draw_storyboard(tiling, tile_width,
                                           tile_aspect_ratio, tile_spacing,
                                           draw_timestamp,
                                           font)
        total_width = storyboard.size[0]
        if print_progress:
            sys.stderr.write("Generating metadata sheet...\n")
        meta_sheet = self._draw_meta_sheet(total_width, tile_spacing, font,
                                           font_size, text_spacing, text_color,
                                           include_sha1sum, print_progress)

        # assemble the parts
        if include_banner:
            if print_progress:
                sys.stderr.write("Drawing the bottom banner...\n")
            banner = self._draw_banner(total_width, font, font_size, text_color)
            total_height = storyboard.size[1] + meta_sheet.size[1] + \
                           banner.size[1]
            # add padding
            hp = padding[0] # horizontal padding
            vp = padding[1] # vertical padding
            total_width  += 2 * hp
            total_height += 2 * vp
            assembled = Image.new('RGBA', (total_width, total_height), 'white')
            if print_progress:
                sys.stderr.write("Assembling parts...\n")
            assembled.paste(meta_sheet, (hp, vp))
            assembled.paste(storyboard, (hp, vp + meta_sheet.size[1]))
            assembled.paste(banner,
                            (hp, vp + meta_sheet.size[1] + storyboard.size[1]))
        else:
            total_height = storyboard.size[1] + meta_sheet.size[1]
            # add padding
            hp = padding[0] # horizontal padding
            vp = padding[1] # vertical padding
            total_width  += 2 * hp
            total_height += 2 * vp
            assembled = Image.new('RGBA', (total_width, total_height), 'white')
            assembled.paste(meta_sheet, (hp, vp))
            assembled.paste(storyboard, (hp, vp + meta_sheet.size[1]))

        return assembled

    def _draw_storyboard(self, tiling, tile_width, tile_aspect_ratio,
                         tile_spacing,
                         draw_timestamp,
                         font):
        """Draw the storyboard (thumbnails only)."""
        horz_tiles   = tiling[0]
        vert_tiles   = tiling[1]
        tile_height  = int(tile_width / tile_aspect_ratio)
        tile_size    = (tile_width, tile_height)
        horz_spacing = tile_spacing[0]
        vert_spacing = tile_spacing[1]
        total_width  = horz_tiles * (tile_width  + 2 * horz_spacing)
        total_height = vert_tiles * (tile_height + 2 * vert_spacing)
        storyboard   = Image.new('RGBA', (total_width, total_height), 'white')
        if draw_timestamp:
            draw = ImageDraw.Draw(storyboard)
        for i in range(0, horz_tiles):
            for j in range(0, vert_tiles):
                index = j * vert_tiles + i
                frame = self.frames[index]
                upperleft = (tile_width  * i + horz_spacing * (2 * i + 1), \
                             tile_height * j + vert_spacing * (2 * j + 1))
                storyboard.paste(frame.image.resize(tile_size, Image.LANCZOS),
                                 upperleft)
                # timestamp
                if draw_timestamp:
                    lowerright = (upperleft[0] + tile_width,
                                  upperleft[1] + tile_height)
                    ts = util.humantime(frame.timestamp, ndigits=0)
                    ts_size = draw.textsize(ts, font)
                    ts_upperleft = (lowerright[0] - ts_size[0] - 5,
                                    lowerright[1] - ts_size[1] - 5)
                    (x, y) = ts_upperleft
                    for x_offset in range(-1, 2):
                        for y_offset in range(-1, 2):
                            draw.text((x + x_offset, y + y_offset),
                                      ts, fill='black', font=font)
                    draw.text((x, y), ts, fill='white', font=font)
        return storyboard

    def _draw_meta_sheet(self, total_width, tile_spacing,
                         font, font_size, text_spacing, text_color,
                         include_sha1sum, print_progress):
        """Draw the metadata sheet."""
        horz_spacing = tile_spacing[0]
        vert_spacing = tile_spacing[1]
        text         = self.video.pretty_print_metadata(
            include_sha1sum=include_sha1sum,
            print_progress=print_progress,
        )
        num_lines    = len(text.splitlines())
        total_height = int(round(font_size * text_spacing)) * num_lines + \
                       vert_spacing * 3 # double verticle spacing at the bottom
        upperleft    = (horz_spacing, vert_spacing)
        meta_sheet   = Image.new('RGBA', (total_width, total_height), 'white')
        draw         = ImageDraw.Draw(meta_sheet)
        _draw_text_block(text, draw, upperleft,
                         text_color, font, font_size, text_spacing)
        return meta_sheet

    def _draw_banner(self, total_width, font, font_size, text_color):
        """Draw the promotion banner."""
        # pylint: disable=no-self-use
        # This function is an integral part of the class.
        text         = "Generated by storyboard version %s. " % __version__ +\
                       "Fork me on GitHub: " +\
                       "github.com/zmwangx/storyboard"
        total_height = font_size + 3 * 2 # hard code vertical spacing in banner
        banner       = Image.new('RGBA', (total_width, total_height), 'white')
        draw         = ImageDraw.Draw(banner)
        text_width   = draw.textsize(text, font=font)[0]
        horz_spacing = (total_width - text_width) // 2
        draw.text((horz_spacing, 3), text, fill=text_color, font=font)
        return banner

def main():
    """CLI interface."""
    description = "Generate video storyboards with metadata reports."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('videos', metavar='VIDEO', nargs='+',
                        help="path(s) to the video file(s)")
    args = parser.parse_args()

    # process arguments
    include_sha1sum = True #! for the moment
    print_progress = True #! for the moment
    # detect OS, and if Windows, append .exe to the executables
    if os.name == 'nt':
        ffmpeg_bin = 'ffmpeg.exe'
        ffprobe_bin = 'ffprobe.exe'
    else:
        ffmpeg_bin = 'ffmpeg'
        ffprobe_bin = 'ffprobe'

    for video in args.videos:
        sb = StoryBoard(
            video,
            ffmpeg_bin=ffmpeg_bin,
            ffprobe_bin=ffprobe_bin,
            print_progress=print_progress,
        )

        storyboard = sb.storyboard(
            include_sha1sum=include_sha1sum,
            print_progress=print_progress,
        )

        _, path = tempfile.mkstemp(suffix='.jpg', prefix='storyboard-')
        storyboard.save(path, quality=90) #! will have output format and quality options
        if print_progress:
            sys.stderr.write("Done. Generated storyboard saved to:\n")
        print(path)

if __name__ == "__main__":
    main()
