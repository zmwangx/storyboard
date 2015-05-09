Issues
======

Reporting
~~~~~~~~~

Please report issues or browse a list of known issues at
https://github.com/zmwangx/storyboard/issues. See :ref:`known` for
instructions on how to report issues related to an unknown codec.

.. _known:

Known issues
~~~~~~~~~~~~

- ``storyboard`` uses ``PIL.ImageFont`` from Pillow to draw text,
  which is rather primitive and only allows one font at a time (no
  fallback).  The default font packaged is Source Code Pro Regular,
  which only draws its supported code points, and leave unknown code
  points as boxes. In particular, there is no CJK support, so CJK
  characters in video filenames won't come out very nice.

  You can specify your own font file that covers (part of) CJK code
  points, but the catch is that you should really use fixed-width
  fonts (unless you want to blow up the beautiful formatting, in which
  case you might as well use a proprietary player to generate a
  storyboard that's bad-looking inside out). It's basically impossible
  to have a truly fixed-width font that mixes CJK glyphs with Latin
  glyths, since they are so different — CJK glyphs are intrinsically
  square-shaped, while Latin glyphs are not.  This is just a sad fact
  of life and there's nothing we can do about it. Therefore, there's
  no CJK support in ``storyboard`` (CJK characters won't break
  ``storyboard`` — they just come out as boxes). Hopefully you're
  using ASCII filenames anyway; if you're not, you really should.

- ``metadata.py`` treats each codec separately, and the list of
  supported codecs is far from complete (currently the list is mostly
  what I encounter in day-to-day use). If you encounter an
  audio/video/subtitle codec that triggers stupid output, please
  report an issue or open a pull request. If it's not a commonly seen
  codec and cannot be encoded by FFmpeg, please try to link a sample
  video with the relevant codec so that I can inspect and test.

- ``ffprobe`` might report the wrong duration for certain VOB or other
  videos, which screws up the whole thing. See `issue #3
  <https://github.com/zmwangx/storyboard/issues/3>`__. As a fallback,
  you can use the option ``--video-duration`` of ``storyboard`` (see
  :doc:`CLI reference <storyboard-cli>`), or if you are using the API,
  the optional parameter ``video_duration`` to
  ``storyboard.storyboard.StoryBoard`` or
  ``storyboard.metadata.Video`` (see API reference). Note, however,
  that the implementation of frame extraction in this case requires
  decoding frame by frame, an aspect that is unlikely to be improved;
  worse still, the current implementation requires decoding from the
  beginning of the video for each storyboard frame, so the whole
  process takes **extremely long**. This problem is documented in
  `issue #24 <https://github.com/zmwangx/storyboard/issues/24>`_ and
  might be improved in the future.
