# Recordurbate-Docker [![Docker Image CI](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml)

Based off the good work of https://github.com/oliverjrose99/Recordurbate

Records chaturbate streams to .ts files. Uses `N_m3u8DL-RE` for the
HLS download instead of ffmpeg, because ffmpeg's HLS demuxer is broken
on chaturbate's current CMAF format and recordings end up with audio
that stops mid-stream while video keeps going. ffmpeg is still in the
image and still does the muxing through `--live-pipe-mux`, but it
never sees the HLS stream directly so the demuxer bug is bypassed.

The cam-recording community shifted to this approach during the
March-April 2026 mess. See the references at the bottom for the full
story.

## Pre built Docker image

```
docker pull ghcr.io/despernal/recordurbate-docker
```

See the Running section for the volumes that need to be mounted.

## Building

`./build` to build locally.

## Running

You will need to change paths in `start` and `docker-compose.yml`.

In `docker-compose.yml`:

```
- PATH_TO_RECORDINGS:/app/videos
- PATH_TO_CONFIGS:/app/configs
```

and in `start`:

```
-v PATH_TO_RECORDINGS:/app/videos/ -v PATH_TO_CONFIGS:/app/configs
```

You can either start it with the start script or use the
docker-compose stack.

You can run it either way: bake the configs folder into the image and
not bind-mount it, or do like i do and map the provided configs folder
into the container.

## Upgrading from an older image

Your existing `config.json` and `youtube-dl.config` dont need changes.

If you want to customize the new N_m3u8DL-RE flags, drop
`configs/n_m3u8dl-re.config` from this repo into your host configs
dir. Otherwise the bot uses sensible defaults baked in.

## Tuning recorder behavior

`N_m3u8DL-RE` flags live in `configs/n_m3u8dl-re.config`. One flag
per line, `#` comments and blank lines ignored, `--flag=value` and
`--flag value` both work.

Shipped defaults are tuned for live recording: `--auto-select`,
`--live-real-time-merge`, `--live-pipe-mux`,
`--live-keep-segments=False`, `--no-log`, `--disable-update-check`.
those same flags are baked into the bot as a fallback if the config
file is missing or empty.

Edit on the host (no rebuild needed if you bind-mount `/app/configs`)
and restart the container to apply.

If you hit audio-sync trouble, drop `--live-pipe-mux` from the config
and set environment variable `N_M3U8DL_NO_FFMPEG_PIPE=1` on the
container. That switches to the separate-files-then-merge mode that
ctbcap uses, trades a small post-merge delay for tighter A/V sync.

## Why this approach (history)

In March 2026 chaturbate switched their stream format to Low-Latency
HLS with split audio/video CMAF (separate audio and video chunklists,
per-segment `init_*.m4s` MOOV atoms). ffmpeg 8.x's HLS demuxer doesnt
handle the per-segment init reload cleanly so recordings ended up
with audio that stops mid-stream while video keeps going. ffprobe on
an affected file shows it right away: video duration is normal, audio
duration is a fraction of that.

Tried pinning ffmpeg 6.1.2 first, that was a wrong-direction guess
(6.1.2 predates LL-HLS-CMAF support). Rolled back to a 2025-10-28
image with a working ffmpeg 7.x range. That worked but was brittle
because every alpine bump risked re-breaking things.

Switching to `N_m3u8DL-RE` for the actual segment download bypasses
the demuxer bug entirely and matches what the rest of the
cam-recording community ended up doing. This is the long-term fix.

## References

- [StreaMonitor issue #342](https://github.com/lossless1/StreaMonitor/issues/342),
  main thread documenting the bug across multiple recording tools
- [ctbcap n_m3u8dl-re branch](https://github.com/KFERMercer/ctbcap/tree/n_m3u8dl-re),
  the working workaround using N_m3u8DL-RE that this approach is based on
- [chaturbate-dvr issue #155](https://github.com/teacat/chaturbate-dvr/issues/155),
  same symptoms reported in a sister project
