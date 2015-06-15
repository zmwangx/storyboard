#!/usr/bin/env python3

"""Generate video storyboards with metadata reports.

Classes
-------
.. autosummary::
    Font
    StoryBoard

Routines
--------
.. autosummary::
    create_thumbnail
    draw_text_block
    tile_images
    main

----

"""

# pylint: disable=too-many-lines

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import pkg_resources
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from storyboard import fflocate
from storyboard.frame import extract_frame as _extract_frame
from storyboard import metadata
from storyboard import util
from storyboard.util import read_param as _read_param
from storyboard import version


# load default font
DEFAULT_FONT_FILE = pkg_resources.resource_filename(
    __name__,
    'SourceCodePro-Regular.otf'
)
DEFAULT_FONT_SIZE = 16


# pylint: disable=too-many-locals,invalid-name
# In this file we use a lot of short local variable names to save space.
# These short variable names are carefully documented when not obvious.


class Font(object):

    """Wrapper for a font loaded by PIL.ImageFont.

    Parameters
    ----------
    font_file : str
        Path to the font file to be loaded. If ``None``, load the
        default font defined by the module variable
        ``DEFAULT_FONT_FILE``. Default is ``None``. Note that the font
        must be supported by FreeType.
    font_size : int
        Font size to be loaded. If ``None``, use the default font size
        defined by the module variable ``DEFAULT_FONT_SIZE``. Default is
        ``None``.

    Raises
    ------
    OSError
        If the font cannot be loaded (by ``PIL.ImageFont.truetype``).

    Attributes
    ----------
    obj
        A Pillow font object, e.g., of the type
        ``PIL.ImageFont.FreeTypeFont``.
    size : int
        The font size.

    Notes
    -----
    We are creating this wrapper because there's no guarantee that a
    font loaded by Pillow will have the ``.size`` property, and
    sometimes it certainly doesn't (try
    ``PIL.ImageFont.load_default()``, for instance). The font size,
    however, is crucial for some of other drawings, so we would like to
    keep it around all the time.

    """

    # pylint: disable=too-few-public-methods

    def __init__(self, font_file=None, font_size=None):
        """Initialize the Font class.

        See class docstring for parameters of the constructor.

        """

        if font_file is None:
            font_file = DEFAULT_FONT_FILE
        if font_size is None:
            font_size = DEFAULT_FONT_SIZE

        try:
            self.obj = ImageFont.truetype(font_file, size=font_size)
        except IOError:
            raise OSError("font file '%s' cannot be loaded" % font_file)
        self.size = font_size


def draw_text_block(canvas, xy, text, params=None):
    """Draw a block of text.

    You need to specify a canvas to draw upon. If you are not sure about
    the size of the canvas, there is a `dry_run` option (see "Other
    Parameters" that help determine the size of the text block before
    creating the canvas.

    Parameters
    ----------
    canvas : PIL.ImageDraw.Image
        The canvas to draw the text block upon. If the `dry_run` option
        is on (see "Other Parameters"), `canvas` can be ``None``.
    xy : tuple
        Tuple ``(x, y)`` consisting of x and y coordinates of the
        topleft corner of the text block.
    text : str
        Text to be drawn, can be multiline.
    params : dict, optional
        Optional parameters enclosed in a dict. Default is ``None``.
        See the "Other Parameters" section for understood key/value
        pairs.

    Returns
    -------
    (width, height)
        Size of text block.

    Other Parameters
    ----------------
    font : Font, optional
        Default is the font constructed by ``Font()`` without arguments.
    color : color, optional
        Color of text; can be in any color format accepted by Pillow
        (used for the ``fill`` argument of
        ``PIL.ImageDraw.Draw.text``). Default is ``'black'``.
    spacing : float, optional
        Line spacing as a float. Default is 1.2.
    dry_run : bool, optional
        If ``True``, do not draw anything, only return the size of the
        text block. Default is ``False``.

    """

    if params is None:
        params = {}
    x, y = xy
    font = _read_param(params, 'font', Font())
    color = _read_param(params, 'color', 'black')
    spacing = _read_param(params, 'spacing', 1.2)
    dry_run = _read_param(params, 'dry_run', False)

    if not dry_run:
        draw = ImageDraw.Draw(canvas)

    line_height = int(round(font.size * spacing))
    width = 0
    height = 0
    for line in text.splitlines():
        w, _ = font.obj.getsize(line)
        if not dry_run:
            draw.text((x, y), line, fill=color, font=font.obj)
        if w > width:
            width = w  # update width to that of the current widest line
        height += line_height
        y += line_height
    return (width, height)


def create_thumbnail(frame, width, params=None):
    """Create thumbnail of a video frame.

    The timestamp of the frame can be overlayed to the thumbnail. See
    "Other Parameters" to how to enable this feature and relevant
    options.

    Parameters
    ----------
    frame : storyboard.frame.Frame
        The video frame to be thumbnailed.
    width : int
        Width of the thumbnail.
    params : dict, optional
        Optional parameters enclosed in a dict. Default is ``None``.
        See the "Other Parameters" section for understood key/value
        pairs.

    Returns
    -------
    thumbnail : PIL.Image.Image

    Other Parameters
    ----------------
    aspect_ratio : float, optional
        Aspect ratio of the thumbnail. If ``None``, use the aspect ratio
        (only considering the pixel dimensions) of the frame. Default is
        ``None``.
    draw_timestamp : bool, optional
        Whether to draw frame timestamp over the timestamp. Default is
        ``False``.
    timestamp_font : Font, optional
        Font for the timestamp, if `draw_timestamp` is ``True``.
        Default is the font constructed by ``Font()`` without arguments.
    timestamp_align : {'right', 'center', 'left'}, optional
        Horizontal alignment of the timestamp over the thumbnail, if
        `draw_timestamp` is ``True``. Default is ``'right'``. Note that
        the timestamp is always vertically aligned towards the bottom of
        the thumbnail.

    """

    if params is None:
        params = {}
    if 'aspect_ratio' in params:
        aspect_ratio = params['aspect_ratio']
    else:
        image_width, image_height = frame.image.size
        aspect_ratio = image_width / image_height
    height = int(round(width / aspect_ratio))
    size = (width, height)
    draw_timestamp = _read_param(params, 'draw_timestamp', False)
    if draw_timestamp:
        timestamp_font = _read_param(params, 'timestamp_font', Font())
        timestamp_align = _read_param(params, 'timestamp_align', 'right')

    thumbnail = frame.image.resize(size, Image.LANCZOS)

    if draw_timestamp:
        draw = ImageDraw.Draw(thumbnail)

        timestamp_text = util.humantime(frame.timestamp, ndigits=0)
        timestamp_width, timestamp_height = \
            draw.textsize(timestamp_text, timestamp_font.obj)

        # calculate upperleft corner of the timestamp overlay
        # we hard code a margin of 5 pixels
        timestamp_y = height - 5 - timestamp_height
        if timestamp_align == 'right':
            timestamp_x = width - 5 - timestamp_width
        elif timestamp_align == 'left':
            timestamp_x = 5
        elif timestamp_align == 'center':
            timestamp_x = int((width - timestamp_width) / 2)
        else:
            raise ValueError("timestamp alignment option '%s' not recognized"
                             % timestamp_align)

        # draw white timestamp with 1px thick black border
        for x_offset in range(-1, 2):
            for y_offset in range(-1, 2):
                draw.text((timestamp_x + x_offset, timestamp_y + y_offset),
                          timestamp_text,
                          fill='black', font=timestamp_font.obj)
        draw.text((timestamp_x, timestamp_y),
                  timestamp_text,
                  fill='white', font=timestamp_font.obj)

    return thumbnail


def tile_images(images, tile, params=None):
    """
    Combine images into a composite image through 2D tiling.

    For example, 16 thumbnails can be combined into an 4x4 array. As
    another example, three images of the same width (think of the
    metadata sheet, the bare storyboard, and the promotional banner) can
    be combined into a 1x3 array, i.e., assembled vertically.

    The image list is processed column-first.

    Note that except if you use the `tile_size` option (see "Other
    Parameters"), you should make sure that images passed into this
    function satisfy the condition that the widths of all images in each
    column and the heights of all images in each row match perfectly;
    otherwise, this function will give up and raise a ValueError.

    Parameters
    ----------
    images : list
        A list of PIL.Image.Image objects, satisfying the necessary
        height and width conditions (see explanation above).
    tile : tuple
        A tuple ``(m, n)`` indicating `m` columns and `n` rows. The
        product of `m` and `n` should be the length of `images`, or a
        `ValueError` will arise.
    params : dict, optional
        Optional parameters enclosed in a dict. Default is ``None``.
        See the "Other Parameters" section for understood key/value
        pairs.

    Returns
    -------
    PIL.Image.Image
        The composite image.

    Raises
    ------
    ValueError
        If the length of `images` does not match the product of columns
        and rows (as defined in `tile`), or the widths and heights of
        the images do not satisfy the necessary consistency conditions.

    Other Parameters
    ----------------
    tile_size : tuple, optional
        A tuple ``(width, height)``. If this parameter is specified,
        width and height consistency conditions won't be checked, and
        every image will be resized to (width, height) when
        combined. Default is ``None``.
    tile_spacing : tuple, optional
        A tuple ``(hor, ver)`` specifying the horizontal and vertical
        spacing between adjacent tiles. Default is ``(0, 0)``.
    margins : tuple, optional
        A tuple ``(hor, ver)`` specifying the horizontal and vertical
        margins (padding) around the combined image. Default is ``(0,
        0)``.
    canvas_color : color, optional
        A color in any format recognized by Pillow. This is only
        relevant if you have nonzero tile spacing or margins, when the
        background shines through the spacing or margins. Default is
        ``'white'``.
    close_separate_images : bool
        Whether to close the separate after combining. Closing the
        images will release the corresponding resources. Default is
        ``False``.

    """

    # pylint: disable=too-many-branches

    if params is None:
        params = {}
    cols, rows = tile
    if len(images) != cols * rows:
        msg = "{} images cannot fit into a {}x{}={} array".format(
            len(images), cols, rows, cols * rows)
        raise ValueError(msg)
    hor_spacing, ver_spacing = _read_param(params, 'tile_spacing', (0, 0))
    hor_margin, ver_margin = _read_param(params, 'margins', (0, 0))
    canvas_color = _read_param(params, 'canvas_color', 'white')
    close_separate_images = _read_param(params, 'close_separate_images', False)
    if 'tile_size' in params and params['tile_size'] is not None:
        tile_size = params['tile_size']
        tile_width, tile_height = tile_size
        canvas_width = (tile_width * cols + hor_spacing * (cols - 1) +
                        hor_margin * 2)
        canvas_height = (tile_height * rows + ver_spacing * (rows - 1) +
                         ver_margin * 2)
        resize = True
    else:
        # check column width consistency, bark if not
        # calculate total width along the way
        canvas_width = hor_spacing * (cols - 1) + hor_margin * 2
        for col in range(0, cols):
            # reference width set by the first image in the column
            ref_index = 0 * cols + col
            ref_width, ref_height = images[ref_index].size
            canvas_width += ref_width
            for row in range(1, rows):
                index = row * cols + col
                width, height = images[index].size
                if width != ref_width:
                    msg = ("the width of image #{} "
                           "(row #{}, col #{}, {}x{}) "
                           "does not agree with that of image #{} "
                           "(row #{}, col #{}, {}x{})".format(
                               index, row, col, width, height,
                               ref_index, 0, col, ref_width, ref_height,
                           ))
                    raise ValueError(msg)
        # check row height consistency, bark if not
        # calculate total height along the way
        canvas_height = ver_spacing * (rows - 1) + ver_margin * 2
        for row in range(0, rows):
            # reference width set by the first image in the column
            ref_index = row * cols + 0
            ref_width, ref_height = images[ref_index].size
            canvas_height += ref_height
            for col in range(1, cols):
                index = row * cols + col
                width, height = images[index].size
                if height != ref_height:
                    msg = ("the height of image #{} "
                           "(row #{}, col #{}, {}x{}) "
                           "does not agree with that of image #{} "
                           "(row #{}, col #{}, {}x{})".format(
                               index, row, col, width, height,
                               ref_index, 0, col, ref_width, ref_height,
                           ))
                    raise ValueError(msg)
        # passed tests, will assemble as is
        resize = False

    # start assembling images
    canvas = Image.new('RGBA', (canvas_width, canvas_height), canvas_color)
    y = ver_margin
    for row in range(0, rows):
        x = hor_margin
        for col in range(0, cols):
            image = images[row * cols + col]

            if resize:
                canvas.paste(image.resize(tile_size, Image.LANCZOS), (x, y))
            else:
                canvas.paste(image, (x, y))

            # accumulate width of this column, as well as horizontal spacing
            x += image.size[0] + hor_spacing
        # accumulate height of this row, as well as vertical spacing
        y += images[row * cols + 0].size[1] + ver_spacing

    if close_separate_images:
        for image in images:
            image.close()

    return canvas


class StoryBoard(object):
    """Class for creating video storyboard.

    Parameters
    ----------
    video
        Either a string specifying the path to the video file, or a
        ``storyboard.metadata.Video`` object.
    params : dict, optional
        Optional parameters enclosed in a dict. Default is
        ``None``. See the "Other Parameters" section for understood
        key/value pairs.

    Raises
    ------
    OSError
        If ffmpeg and ffprobe binaries do not exist or seem corrupted,
        or if the video does not exist or cannot be recognized by
        FFprobe.

    Other Parameters
    ----------------
    bins : tuple, optional
        A tuple (ffmpeg_bin, ffprobe_bin), specifying the name of path
        of FFmpeg and FFprobe's binaries on your system. If ``None``,
        the bins are guessed according to type of OS, using
        ``storyboard.fflocate.guess_bins`` (e.g., on OS X and Linux
        systems, the natural names are ``'ffmpeg'`` and ``'ffprobe'``;
        on Windows, the names have ``'.exe'`` suffixes). Default is
        ``None``.
    frame_codec : str, optional
        Image codec to use when extracting frames using FFmpeg. Default
        is ``'png'``. Use this option with caution only if your FFmpeg
        cannot encode PNG, which is unlikely.
    video_duration : float, optional
        Duration of the video in seconds, passed to the
        ``storyboard.metadata.Video`` constructor. If ``None``, extract
        the duration from video container metadata. Default is
        ``None``. You should rarely need this option, unless the
        duration of the video cannot be extracted from video container
        metadata, or the duration extracted is wrong. Either case is
        fatal to the storyboard (since the frames extracted depend on
        the duration), and this option provides a fallback. See `#3
        <https://github.com/zmwangx/storyboard/issues/3>`_ for details.
    print_progress : bool, optional
        Whether to print progress information (to stderr). Default is
        ``False``.

    Attributes
    ----------
    video : storyboard.metadata.Video
    frames : list
        List of equally spaced frames in the video, as
        ``storyboard.frame.Frame`` objects. The list is empty after
        `__init__`. See the `gen_frames` method.

    Notes
    -----
    For developers: there are two private attributes. ``_bins`` is a
    tuple of two strs holding the name or path of the ffmpeg and ffprobe
    binaries; ``_frame_codec`` is a str holding the image codec used by
    FFmpeg when generating frames (usually no one needs to touch this).

    """

    def __init__(self, video, params=None):
        """Initialize the StoryBoard class.

        See the module docstring for parameters and exceptions.

        """

        if params is None:
            params = {}
        if 'bins' in params and params['bins'] is not None:
            bins = params['bins']
            assert isinstance(bins, tuple) and len(bins) == 2
        else:
            bins = fflocate.guess_bins()
        frame_codec = _read_param(params, 'frame_codec', 'png')
        video_duration = _read_param(params, 'video_duration', None)
        print_progress = _read_param(params, 'print_progress', False)

        fflocate.check_bins(bins)

        # seek frame by frame if video duration is specially given
        # (indicating that normal input seeking may not work)
        self._seek_frame_by_frame = video_duration is not None

        self._bins = bins
        if isinstance(video, metadata.Video):
            self.video = video
        elif isinstance(video, str):
            self.video = metadata.Video(video, params={
                'ffprobe_bin': bins[1],
                'video_duration': video_duration,
                'print_progress': print_progress,
            })
        else:
            raise ValueError("expected str or storyboard.metadata.Video "
                             "for the video argument, got %s" %
                             type(video).__name__)
        self.frames = []
        self._frame_codec = frame_codec

    def gen_storyboard(self, params=None):
        """Generate full storyboard.

        A full storyboard has three sections, arranged vertically in the
        order listed: a metadata sheet, a bare storyboard, and a
        promotional banner.

        The metadata sheet consists of formatted metadata generated by
        ``storyboard.metadata.Video.format_metadata``; you may choose
        whether to include the SHA-1 hex digest of the video file (see
        `include_sha1sum` in "Other Parameters"). The bare storyboard is
        an array (usually 4x4) of thumbnails, generated from equally
        spaced frames from the video. The promotional banner briefly
        promotes this package (storyboard).

        The metadata sheet and promotional banner are optional and can
        be turned off individually. See `include_metadata_sheet` and
        `include_promotional_banner` in "Other Parameters".

        `Here <https://i.imgur.com/9T2zM8R.jpg>`_ is a basic example of
        a full storyboard.

        Parameters
        ----------
        params : dict, optional
            Optional parameters enclosed in a dict. Default is
            ``None``. See the "Other Parameters" section for understood
            key/value pairs.

        Returns
        -------
        full_storyboard : PIL.Image.Image

        Other Parameters
        ----------------
        include_metadata_sheet: bool, optional
            Whether to include a video metadata sheet in the
            storyboard. Default is ``True``.
        include_promotional_banner: bool, optional
            Whether to include a short promotional banner about this
            package (storyboard) at the bottom of the
            storyboard. Default is ``True``.

        background_color : color, optional
            Background color of the storyboard, in any color format
            recognized by Pillow. Default is ``'white'``.
        section_spacing : int, optional
            Vertical spacing between adjacent sections (metadata sheet
            and bare storyboard, bare storyboard and promotional
            banner). If ``None``, use the vertical tile spacing (see
            `tile_spacing`). Default is ``None``.
        margins : tuple, optional
            A tuple ``(hor, ver)`` specifying the horizontal and
            vertical margins (padding) around the entire storyboard (all
            sections included). Default is ``(10, 10)``.

        tile : tuple, optional
            A tuple ``(cols, rows)`` specifying the number of columns
            and rows for the array of thumbnails in the
            storyboard. Default is ``(4, 4)``.
        tile_spacing : tuple, optional
            A tuple ``(hor, ver)`` specifying the horizontal and
            vertical spacing between adjacent thumbnails. Default is
            ``(8, 6)``.

        thumbnail_width : int, optional
            Width of each thumbnail. Default is 480 (as in 480x270 for a
            16:9 video).
        thumbnail_aspect_ratio : float, optional
            Aspect ratio of generated thumbnails. If ``None``, first try
            to use the display aspect ratio of the video
            (``self.video.dar``), then the aspect ratio of the frames if
            ``self.video.dar`` is not available. Default is ``None``.

        draw_timestamp : bool, optional
            Whether to draw frame timestamps on top of thumbnails (as an
            overlay).  Default is ``True``.
        timestamp_font : Font, optional
            Font used for timestamps, if `draw_timestamp` is
            ``True``. Default is the font constructed by ``Font()``
            without arguments.
        timestamp_align : {'right', 'center', 'left'}, optional
            Horizontal alignment of timestamps over the thumbnails, if
            `draw_timestamp` is ``True``. Default is ``'right'``. Note
            that timestamps are always vertically aligned to the bottom.

        text_font: Font, optional
            Font used for metadata sheet and promotional banner. Default
            is the font constructed by ``Font()`` without arguments.
        text_color: color, optional
            Color of metadata and promotional text, in any format
            recognized by Pillow. Default is ``'black'``.
        line_spacing: float, optional
            Line spacing of metadata text as a float, e.g., 1.0 for
            single spacing, 1.5 for one-and-a-half spacing, and 2.0 for
            double spacing. Default is 1.2.

        include_sha1sum: bool, optional
            Whether to include the SHA-1 hex digest of the video file in
            the metadata fields. Default is ``False``. Be aware that
            computing SHA-1 digest is an expensive operation.

        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is ``False``.

        """

        # process parameters -- a ton of them
        if params is None:
            params = {}
        include_metadata_sheet = _read_param(
            params, 'include_metadata_sheet', True)
        include_promotional_banner = _read_param(
            params, 'include_promotional_banner', True)
        background_color = _read_param(params, 'background_color', 'white')
        margins = _read_param(params, 'margins', (10, 10))
        tile = _read_param(params, 'tile', (4, 4))
        tile_spacing = _read_param(params, 'tile_spacing', (8, 6))
        if (('section_spacing' in params and
             params['section_spacing'] is not None)):
            section_spacing = params['section_spacing']
        else:
            section_spacing = tile_spacing[1]
        thumbnail_width = _read_param(params, 'thumbnail_width', 480)
        thumbnail_aspect_ratio = _read_param(
            params, 'thumbnail_aspect_ratio', None)
        draw_timestamp = _read_param(params, 'draw_timestamp', True)
        timestamp_font = _read_param(params, 'timestamp_font', Font())
        timestamp_align = _read_param(params, 'timestamp_align', 'right')
        text_font = _read_param(params, 'text_font', Font())
        text_color = _read_param(params, 'text_color', 'black')
        line_spacing = _read_param(params, 'line_spacing', 1.2)
        include_sha1sum = _read_param(params, 'include_sha1sum', False)
        print_progress = _read_param(params, 'print_progress', False)

        # draw bare storyboard, metadata sheet, and promotional banner
        if print_progress:
            sys.stderr.write("Generating main storyboard...\n")
        bare_storyboard = self._gen_bare_storyboard(
            tile, thumbnail_width,
            params={
                'tile_spacing': tile_spacing,
                'background_color': background_color,
                'thumbnail_aspect_ratio': thumbnail_aspect_ratio,
                'draw_timestamp': draw_timestamp,
                'timestamp_font': timestamp_font,
                'timestamp_align': timestamp_align,
                'print_progress': print_progress,
            }
        )
        total_width, _ = bare_storyboard.size

        if include_metadata_sheet:
            if print_progress:
                sys.stderr.write("Generating metadata sheet...\n")
            metadata_sheet = self._gen_metadata_sheet(total_width, params={
                'text_font': text_font,
                'text_color': text_color,
                'line_spacing': line_spacing,
                'background_color': background_color,
                'include_sha1sum': include_sha1sum,
                'print_progress': print_progress,
            })

        if include_promotional_banner:
            if print_progress:
                sys.stderr.write("Generating promotional banner...\n")
            banner = self._gen_promotional_banner(total_width, params={
                'text_font': text_font,
                'text_color': text_color,
                'background_color': background_color,
            })

        # combine different sections
        if print_progress:
            sys.stderr.write("Assembling pieces...\n")
        sections = []
        if include_metadata_sheet:
            sections.append(metadata_sheet)
        sections.append(bare_storyboard)
        if include_promotional_banner:
            sections.append(banner)
        storyboard = tile_images(sections, (1, len(sections)), params={
            'tile_spacing': (0, section_spacing),
            'margins': margins,
            'canvas_color': background_color,
            'close_separate_images': True,
        })

        return storyboard

    def gen_frames(self, count, params=None):
        """Extract equally spaced frames from the video.

        When tasked with extracting N frames, this method extracts them
        at positions 1/2N, 3/2N, 5/2N, ... , (2N-1)/2N of the video. The
        extracted frames are stored in the `frames` attribute.

        Note that new frames are extracted only if the number of
        existing frames in the `frames` attribute doesn't match the
        specified `count` (0 at instantiation), in which case new frames
        are extracted to match the specification, and the `frames`
        attribute is overwritten.

        Parameters
        ----------
        count : int
            Number of (equally-spaced) frames to generate.
        params : dict, optional
            Optional parameters enclosed in a dict. Default is
            ``None``. See the "Other Parameters" section for understood
            key/value pairs.

        Returns
        -------
        None
            Access the generated frames through the `frames` attribute.

        RAISES
        ------
        OSError
            If frame extraction with FFmpeg fails.

        Other Parameters
        ----------------
        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is False.

        """

        if params is None:
            params = {}
        print_progress = _read_param(params, 'print_progress', False)

        if len(self.frames) == count:
            return

        duration = self.video.duration
        interval = duration / count
        timestamps = [interval * (i + 1/2) for i in range(0, count)]
        counter = 0
        for timestamp in timestamps:
            counter += 1
            if print_progress:
                sys.stderr.write("\rExtracting frame %d/%d..." %
                                 (counter, count))
            try:
                frame = _extract_frame(self.video.path, timestamp, params={
                    'ffmpeg_bin': self._bins[0],
                    'codec': self._frame_codec,
                    'frame_by_frame': self._seek_frame_by_frame,
                })
                self.frames.append(frame)
            except:
                # \rExtracting frame %d/%d... isn't terminated by
                # newline yet
                if print_progress:
                    sys.stderr.write("\n")
                raise
        if print_progress:
            sys.stderr.write("\n")

    def _gen_bare_storyboard(self, tile, thumbnail_width, params=None):
        """Generate bare storyboard (thumbnails only).

        Parameters
        ----------
        tile : tuple
            A tuple ``(cols, rows)`` specifying the number of columns
            and rows for the array of thumbnails.
        thumbnail_width : int
            Width of each thumbnail.
        params : dict, optional
            Optional parameters enclosed in a dict. Default is
            ``None``. See the "Other Parameters" section for understood
            key/value pairs.

        Returns
        -------
        base_storyboard : PIL.Image.Image

        Other Parameters
        ----------------
        tile_spacing : tuple, optional
            See the `tile_spacing` parameter of the `tile_images`
            function. Default is ``(0, 0)``.

        background_color : color, optional
            See the `canvas_color` paramter of the `tile_images`
            function. Default is ``'white'``.

        thumbnail_aspect_ratio : float, optional
            Aspect ratio of generated thumbnails. If ``None``, first try
            to use the display aspect ratio of the video
            (``self.video.dar``), then the aspect ratio of the frames if
            ``self.video.dar`` is not available. Default is ``None``.

        draw_timestamp : bool, optional
            See the `draw_timestamp` parameter of the `create_thumbnail`
            function. Default is ``False``.
        timestamp_font : Font, optional
            See the `timestamp_font` parameter of the `create_thumbnail`
            function. Default is the font constructed by ``Font()``
            without arguments.
        timestamp_align : {'right', 'center', 'left'}, optional
            See the `timestamp_align` parameter of the
            `create_thumbnail` function. Default is ``'right'``.

        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is False.

        """

        if params is None:
            params = {}
        tile_spacing = _read_param(params, 'tile_spacing', (0, 0))
        background_color = _read_param(params, 'background_color', 'white')
        if (('thumbnail_aspect_ratio' in params and
             params['thumbnail_aspect_ratio'] is not None)):
            thumbnail_aspect_ratio = params['thumbnail_aspect_ratio']
        elif self.video.dar is not None:
            thumbnail_aspect_ratio = self.video.dar
        else:
            # defer calculation to after generating frames
            thumbnail_aspect_ratio = None
        draw_timestamp = _read_param(params, 'draw_timestamp', False)
        if draw_timestamp:
            timestamp_font = _read_param(params, 'timestamp_font', Font())
            timestamp_align = _read_param(params, 'timestamp_align', 'right')
        print_progress = _read_param(params, 'print_progress', False)

        cols, rows = tile
        if (not(isinstance(cols, int) and isinstance(rows, int) and
                cols > 0 and rows > 0)):
            raise ValueError('tile is not a tuple of positive integers')
        thumbnail_count = cols * rows
        self.gen_frames(cols * rows, params={
            'print_progress': print_progress,
        })
        if thumbnail_aspect_ratio is None:
            frame_size = self.frames[0].image.size
            thumbnail_aspect_ratio = frame_size[0] / frame_size[1]

        thumbnails = []
        counter = 0
        for frame in self.frames:
            counter += 1
            if print_progress:
                sys.stderr.write("\rGenerating thumbnail %d/%d..." %
                                 (counter, thumbnail_count))
            thumbnails.append(create_thumbnail(frame, thumbnail_width, params={
                'aspect_ratio': thumbnail_aspect_ratio,
                'draw_timestamp': draw_timestamp,
                'timestamp_font': timestamp_font,
                'timestamp_align': timestamp_align,
            }))
        if print_progress:
            sys.stderr.write("\n")

        if print_progress:
            sys.stderr.write("Tiling thumbnails...\n")
        return tile_images(thumbnails, tile, params={
            'tile_spacing': tile_spacing,
            'canvas_color': background_color,
            'close_separate_images': True,
        })

    def _gen_metadata_sheet(self, total_width, params=None):
        """Generate metadata sheet.

        Parameters
        ----------
        total_width : int
            Total width of the metadata sheet. Usually determined by the
            width of the bare storyboard.
        params : dict, optional
            Optional parameters enclosed in a dict. Default is
            ``None``. See the "Other Parameters" section for understood
            key/value pairs.

        Returns
        -------
        metadata_sheet : PIL.Image.Image

        Other Parameters
        ----------------
        text_font : Font, optional
            Default is the font constructed by ``Font()`` without
            arguments.
        text_color: color, optional
            Default is 'black'.
        line_spacing : float, optional
            Line spacing as a float. Default is 1.2.
        background_color: color, optional
            Default is 'white'.
        include_sha1sum: bool, optional
            See the `include_sha1sum` option of
            `storyboard.metadata.Video.format_metadata`. Beware that
            computing SHA-1 digest is an expensive operation.
        print_progress : bool, optional
            Whether to print progress information (to stderr). Default
            is False.

        """

        if params is None:
            params = {}
        text_font = _read_param(params, 'text_font', Font())
        text_color = _read_param(params, 'text_color', 'black')
        line_spacing = _read_param(params, 'line_spacing', 1.2)
        background_color = _read_param(params, 'background_color', 'white')
        include_sha1sum = _read_param(params, 'include_sha1sum', False)
        print_progress = _read_param(params, 'print_progress', False)

        text = self.video.format_metadata(params={
            'include_sha1sum': include_sha1sum,
            'print_progress': print_progress,
        })

        _, total_height = draw_text_block(None, (0, 0), text, params={
            'font': text_font,
            'spacing': line_spacing,
            'dry_run': True,
        })

        metadata_sheet = Image.new('RGBA', (total_width, total_height),
                                   background_color)
        draw_text_block(metadata_sheet, (0, 0), text, params={
            'font': text_font,
            'color': text_color,
            'spacing': line_spacing,
        })

        return metadata_sheet

    @staticmethod
    def _gen_promotional_banner(total_width, params=None):
        """Generate promotion banner.

        This is the promotional banner for the storyboard package.

        Parameters
        ----------
        total_width : int
            Total width of the metadata sheet. Usually determined by the
            width of the bare storyboard.
        params : dict, optional
            Optional parameters enclosed in a dict. Default is
            ``None``. See the "Other Parameters" section for understood
            key/value pairs.

        Returns
        -------
        banner : PIL.Image.Image

        Other Parameters
        ----------------
        text_font : Font, optional
            Default is the font constructed by ``Font()`` without
            arguments.
        text_color: color, optional
            Default is 'black'.
        background_color: color, optional
            Default is 'white'.

        """

        if params is None:
            params = {}
        text_font = _read_param(params, 'text_font', Font())
        text_color = _read_param(params, 'text_color', 'black')
        background_color = _read_param(params, 'background_color', 'white')

        text = ("Generated by storyboard version %s. "
                "Fork me on GitHub: git.io/storyboard"
                % version.__version__)
        text_width, total_height = draw_text_block(None, (0, 0), text, params={
            'font': text_font,
            'dry_run': True,
        })

        banner = Image.new('RGBA', (total_width, total_height),
                           background_color)
        # center the text -- calculate the x coordinate of its topleft
        # corner
        text_x = int((total_width - text_width) / 2)
        draw_text_block(banner, (text_x, 0), text, params={
            'font': text_font,
            'color': text_color,
        })

        return banner


def main():
    """CLI interface."""

    # pylint: disable=too-many-statements,too-many-branches

    description = """Generate video storyboards with metadata reports.

    You may supply a list of videos. For each video, the generated
    storyboard image will be saved to a secure temporary file, and its
    absolute path will be printed to stdout for further manipulations
    (permanent archiving, uploading to an image hosting website,
    etc). Note that stdout is guaranteed to only receive the image
    paths, one per line, so you may embed this program in a streamlined
    script; stderr, on the other hand, may receive progress information
    without guaranteed format (see the --print-progress option).

    Below is the list of available options and their brief
    explanations. The options can also be stored in a configuration
    file, $XDG_CONFIG_HOME/storyboard/storyboard.conf (or if
    $XDG_CONFIG_HOME is not defined,
    ~/.config/storyboard/storyboard.conf), under the "storyboard-cli"
    section (the conf file format follows that described in
    https://docs.python.org/3/library/configparser.html).

    Note that the storyboard is in fact much more customizable; see the
    API reference of
    storyboard.storyboard.StoryBoard.gen_storyboard. Those customization
    parameters are not exposed in the CLI, but you may easily write a
    wrapper script around the storyboard.storyboard if you'd like to.

    For more detailed explanations, see
    http://storyboard.rtfd.org/en/stable/storyboard-cli.html (or replace
    "stable" with the version you are using).
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'videos', nargs='+', metavar='VIDEO',
        help="Path(s) to the video file(s).")
    parser.add_argument(
        '--ffmpeg-bin', metavar='NAME',
        help="""The name/path of the ffmpeg binary. The binay is
        guessed from OS type if this option is not specified.""")
    parser.add_argument(
        '--ffprobe-bin', metavar='NAME',
        help="""The name/path of the ffprobe binary. The binay is
        guessed from OS type if this option is not specified.""")
    parser.add_argument(
        '-f', '--output-format', choices=['jpeg', 'png'],
        help="Output format of the storyboard image. Default is JPEG.")
    parser.add_argument(
        '--quality', type=int,
        help="""Quality of the output image, should be an integer
        between 1 and 100. Only meaningful when the output format is
        JPEG. Default is 85.""")
    parser.add_argument(
        '--video-duration', type=float, metavar='SECONDS',
        help="""Video duration in seconds (float). By default the
        duration is extracted from container metadata, but in case it is
        not available or wrong, use this option to correct it and get a
        saner storyboard. Note however that this option activates output
        seeking (i.e., seeking the video frame by frame) in thumbnail
        generation, so it will be *infinitely* slower than without this
        option.""")
    parser.add_argument(
        '--exclude-sha1sum', '-s', action='store_const', const=True,
        help="Exclude SHA-1 digest of the video(s) from storyboard(s).")
    parser.add_argument(
        '--include-sha1sum', action='store_true',
        help="""Include SHA-1 digest of the video(s). Overrides
        '--exclude-sha1sum'. This option is only useful if
        exclude_sha1sum is turned on by default in the config file.""")
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

    ffmpeg_bin_guessed, ffprobe_bin_guessed = fflocate.guess_bins()
    defaults = {
        'ffmpeg_bin': ffmpeg_bin_guessed,
        'ffprobe_bin': ffprobe_bin_guessed,
        'output_format': 'jpeg',
        'quality': 85,
        'video_duration': None,
        'exclude-sha1sum': False,
        'verbose': 'auto',
    }

    optreader = util.OptionReader(
        cli_args=cli_args,
        config_files=config_file,
        section='storyboard-cli',
        defaults=defaults,
    )
    bins = (optreader.opt('ffmpeg_bin'), optreader.opt('ffprobe_bin'))
    output_format = optreader.opt('output_format')
    if output_format not in ['jpeg', 'png']:
        msg = ("fatal error: output format should be either 'jpeg' or 'png'; "
               "'%s' received instead\n" % output_format)
        sys.stderr.write(msg)
        exit(1)
    suffix = '.jpg' if output_format == 'jpeg' else '.png'
    quality = optreader.opt('quality', opttype=int)
    video_duration = optreader.opt('video_duration', opttype=float)
    include_sha1sum = not optreader.opt('exclude_sha1sum', opttype=bool)
    if cli_args.include_sha1sum:
        # force override
        include_sha1sum = True
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
        if sys.stderr.isatty():
            print_progress = True
        else:
            print_progress = False

    # test bins
    try:
        fflocate.check_bins(bins)
    except OSError:
        msg = ("fatal error: at least one of '%s' and '%s' does not exist on "
               "PATH or is corrupted (expected ffmpeg and ffprobe)\n" % bins)
        sys.stderr.write(msg)
        exit(1)

    # real stuff happens from here
    returncode = 0
    for video in cli_args.videos:
        try:
            storyboard_image = StoryBoard(video, params={
                'bins': bins,
                'video_duration': video_duration,
                'print_progress': print_progress,
            }).gen_storyboard(params={
                'include_sha1sum': include_sha1sum,
                'print_progress': print_progress,
            })
        except OSError as err:
            sys.stderr.write("error: %s\n\n" % str(err))
            returncode = 1
            continue

        tempfd, storyboard_file = tempfile.mkstemp(
            prefix='storyboard-', suffix=suffix)
        os.close(tempfd)
        if output_format == 'jpeg':
            storyboard_image.save(storyboard_file, 'jpeg', quality=quality,
                                  optimize=True, progressive=True)
        else:  # 'png'
            storyboard_image.save(storyboard_file, 'png', optimize=True)

        if print_progress:
            sys.stderr.write("\n")
            sys.stderr.write("storyboard saved to: ")
            sys.stderr.flush()
            print(storyboard_file)
            sys.stderr.write("\n")
        else:
            print(storyboard_file)
    return returncode


if __name__ == "__main__":
    exit(main())
