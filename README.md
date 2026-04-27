# Recordurbate-Docker [![Docker Image CI](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml)

Based off the good work of https://github.com/oliverjrose99/Recordurbate

Following upstream we are switching to yt-dlp.
You will need to change your configs.

This part

`    "youtube-dl_cmd": "yt-dlp",`

I have left the old youtube-dl in there for the time being but you will need to transition

## Pre built Docker image

You can use the following to just pull the image and pass in your own configs and recordings folder

`docker pull ghcr.io/despernal/recordurbate-docker`

See Running section for more info on the volumes that need to be mounted.

## Building
To build this just run the build script

`./build`

## Running
You will need to change paths in

`start` and 
`docker-compose.yml` 

In `docker-compose.yml` you will need to change the the following

```   
      - PATH_TO_RECORDINGS:/app/videos
      - PATH_TO_CONFIGS:/app/configs
```
and in `start` you will need to change the following

```
-v PATH_TO_RECORDINGS:/app/videos/ -v PATH_TO_CONFIGS:/app/configs
```

You can either start it with the start script or do like i do and just use the docker-compose stack to start it

You can run this either way by baking in the configs folder and just not mapping the configs volume out to a real folder on the host.

Or do like i do an just map the provided configs folder into the container and add the appropriate volume mounts.

I have been running this in a container for years sharing it because someone asked.

## Known issue: ffmpeg 8.x and Chaturbate's LL-HLS CMAF format (April 2026)

In March 2026 Chaturbate switched their stream format to Low-Latency HLS with
split audio/video CMAF (separate audio and video chunklists, per-segment
`init_*.m4s` MOOV atoms). ffmpeg 8.x's HLS demuxer doesn't handle the
per-segment init reload cleanly and recordings end up with audio that stops
mid-stream while video keeps going. ffprobe on an affected file shows it
right away: video duration is normal, audio duration is a fraction of that.
This is not specific to this project, it hits every recording tool built on
ffmpeg's HLS demuxer.

### Working ffmpeg ranges

- ffmpeg 6.1.2: fails (predates LL-HLS-CMAF support)
- ffmpeg 7.x range from late-2025 alpine: works
- ffmpeg 8.x: broken against the new CB format

### Working image

`ghcr.io/despernal/recordurbate-docker:latest` is currently pinned to the
2025-10-28 build digest:

```
sha256:33ba571d0b4c745a5fd9d13947111b746e752c1e19142aad890ad80bf878245b
```

That build's ffmpeg handles the new CMAF format correctly. If a future
rebuild ever produces a regression you can pin compose back to that digest
or retag it with `crane`.

### Long-term migration

The cam-recording community has converged on `N_m3u8DL-RE` as a replacement
for ffmpeg's HLS demuxer for these streams. The `ctbcap` project ships an
`n_m3u8dl-re` branch with that approach. This repo's `n_m3u8dl-re` branch is
where the same migration is being explored; branch builds publish to a
separate `:n_m3u8dl-re` tag so you can try them without disturbing `:latest`.

### References

- [StreaMonitor issue #342](https://github.com/lossless1/StreaMonitor/issues/342)
  -- main thread documenting the bug across multiple recording tools
- [ctbcap n_m3u8dl-re branch](https://github.com/teasherm/ctbcap/tree/n_m3u8dl-re)
  -- working workaround using N_m3u8DL-RE
- [chaturbate-dvr issue #155](https://github.com/teacat/chaturbate-dvr/issues/155)
  -- same symptoms reported in a sister project





