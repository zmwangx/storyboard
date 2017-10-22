#!/usr/bin/env bash

# This script is for informational purposes only. You should not run it to
# overwrite the already generated samples in source control, or the tests are
# most likely to fail.

set -e

here=$(dirname "$(realpath "$0")")
sample_dir=${here}/samples
mkdir -p "${sample_dir}"
cd "${sample_dir}"

# H.264 in MP4 container
ffmpeg -f lavfi -i color=c=black:s=128x72:d=2 -c:v h264 h264.mp4

# H.264 in 3GP container
ffmpeg -i h264.mp4 -c copy h264.3gp

# H.264 in 3G2 container
ffmpeg -i h264.mp4 -c copy h264.3g2

# H.264 in MOV container
ffmpeg -i h264.mp4 -c copy h264.mov

# H.264 in MPEG-TS container
ffmpeg -i h264.mp4 -c copy -c:v h264 h264.ts

# H.264 in FLV container
ffmpeg -i h264.mp4 -c copy -c:v h264 h264.flv

# H.264 @High4.0 in MP4 container
ffmpeg -i h264.mp4 -c:v libx264 -preset veryslow -profile:v high -level 4.0 h264_high4.0.mp4

# HEVC in MP4 container
ffmpeg -i h264.mp4 -c:v hevc hevc.mp4

# MJPEG in MP4 container
#
# MJPEG is significantly more space consuming (37K when the source H.264 video
# is 2.9K), so we cut it short at the expense of not being able to detect scan
# type.
ffmpeg -i h264.mp4 -t 0.2 -c:v mjpeg mjpeg.mp4

# MPEG-1 Part 2 in MP4 container
ffmpeg -i h264.mp4 -c:v mpeg1video mpeg1video.mp4

# MPEG-2 Part 2 in MP4 container
ffmpeg -i h264.mp4 -c:v mpeg2video mpeg2video.mp4

# MPEG-2 in MPEG-PS container
ffmpeg -i mpeg2video.mp4 -c copy mpeg2video.mpg

# MPEG-2 Part 2 in raw MPEG video container
#
# Note that this file doesn't have duration in its container metadata.
ffmpeg -i h264.mp4 -c:v mpeg2video mpeg2video.m2v

# MPEG-4 Part 2 in MP4 container
ffmpeg -i h264.mp4 -c:v mpeg4 mpeg4.mp4

# Theora in Ogg container
ffmpeg -i h264.mp4 -c:v theora theora.ogv

# VP8 in WebM container
ffmpeg -i h264.mp4 -c:v vp8 vp8.webm

# VP9 in WebM container
ffmpeg -i h264.mp4 -c:v vp9 vp9.webm

# H.264 + SubRip in Matroska container
cat >srt.srt <<EOF
1
00:00:01,000 --> 00:00:02,000
SubRip is the way to go
EOF
ffmpeg -i h264.mp4 -i srt.srt -map 0 -map 1 -metadata:s:2 language=en -c copy h264.srt.mkv

# H.264 + ASS in Matroska container
ffmpeg -i srt.srt -c:s ass ass.ass
ffmpeg -i h264.mp4 -i ass.ass -map 0 -map 1 -metadata:s:2 language=en -c copy h264.ass.mkv

rm srt.srt
rm ass.ass

# Interlaced H.264 in MP4 container
ffmpeg -i h264.mp4 -c:v h264 -flags +ildct+ilme h264_interlaced.mp4

# AAC (LC) in raw ADTS AAC container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a libfdk_aac aac.aac

# Dolby AC-3 in raw AC-3 container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a ac3 ac3.ac3

# FLAC in Native FLAC container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a flac flac.flac

# PCM in AIFF container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 aiff.aiff

# HE-AAC in raw ADTS AAC container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a libfdk_aac -profile:a aac_he aac_he.aac

# MP3 in MP3 container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a mp3 mp3.mp3

# Vorbis in Ogg container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 -c:a libvorbis vorbis.oga

# JPEG in JPEG container
convert -size 100x100 xc:white jpeg.jpeg

# PNG in PNG container
convert -size 100x100 xc:white png.png

# MP3 + MJPEG in MP3 container
ffmpeg -i mp3.mp3 -i jpeg.jpeg -map 0 -map 1 mp3.jpeg.mp3

# MP3 + PNG in MP3 container
ffmpeg -i mp3.mp3 -i png.png -map 0 -map 1 mp3.png.mp3

# Mono PCM in WAV container
ffmpeg -f lavfi -i aevalsrc=0:d=0.1 mono.wav

# Stereo PCM in WAV container
ffmpeg -i mono.wav -filter_complex '[0:a][0:a]amerge=inputs=2' stereo.wav

# Stereo MP3 in MP3 container
ffmpeg -i stereo.wav -c:a mp3 stereo.mp3

# 5.1 PCM in WAV container
ffmpeg -i mono.wav -filter_complex '[0:a][0:a][0:a][0:a][0:a][0:a]amerge=inputs=6,channelmap=0|1|2|3|4|5:5.1' -y 5.1.wav

# 5.1 (side) PCM in WAV container
ffmpeg -i mono.wav -filter_complex '[0:a][0:a][0:a][0:a][0:a][0:a]amerge=inputs=6,channelmap=0|1|2|3|4|5:5.1(side)' -y 5.1-side.wav

# H.264 + AAC in MP4 container
ffmpeg -i h264.mp4 -i aac.aac -c copy -bsf:a aac_adtstoasc -map 0 -map 1 h264.aac.mp4

# RealVideo 1.0 + RealAudio 1.0 in RealMedia container (requires width and height be multiples of 16)
ffmpeg -i h264.aac.mp4 -vf scale=256/144 -c:v rv10 -c:a real_144 realvideo1.realaudio1.rm

# H.264 + AAC + SRT in Matroska container with title
ffmpeg -i h264.srt.mkv -i h264.aac.mp4 -c copy -map 0:0 -map 1:1 -map 0:1 -metadata title="Example video: H.264 + AAC + SRT in Matroska container" h264.aac.srt.mkv

# generate metadata outputs
for f in *; do
    metadata --include-sha1sum "${f}" >"${f}.out"
done
