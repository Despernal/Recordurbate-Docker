# Recordurbate-Docker [![Docker Image CI](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml/badge.svg)](https://github.com/Despernal/Recordurbate-Docker/actions/workflows/docker-image.yml)

> **Heads up (April 2026):** Chaturbate switched to LL-HLS CMAF and ffmpeg 8.x
> can't demux it cleanly. `:latest` was rolled back to the 2025-10-28 build
> (digest `sha256:33ba571d...`), which is verified working. Long-term migration
> to `N_m3u8DL-RE` started on the [`n_m3u8dl-re` branch](../../tree/n_m3u8dl-re).
> that work is now merged into master.

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

## Lip sync

`--live-pipe-mux` hands the audio and video tracks to ffmpeg without
`-copyts`, so ffmpeg starts each track at zero on its own and the real gap
between them gets thrown away. You end up with a lip-sync offset that stays
the same for the whole file but changes from one recording to the next,
which is why some recordings looked fine and others didnt.

The recorder now starts N_m3u8DL-RE with `--ffmpeg-binary-path
/app/ffmpeg_av_sync.py`. That little wrapper looks for the pipe-mux call and
adds `-copyts -avoid_negative_ts make_zero` right before the output, so ffmpeg
keeps the original timestamps. Every other ffmpeg call goes through untouched.
It lives in `config.json` as `pipe_mux_options`; set it to `""` to get the old
behaviour back. Dont add `-start_at_zero`, it re-zeroes each track separately
and brings the offset right back (the wrapper strips it).

Why not `RE_LIVE_PIPE_OPTIONS`? Setting that env var also makes N_m3u8DL-RE
put `-re` on the video input, and `-re` on a live input is asking for trouble.

Heads up: an older version of this README said to set
`N_M3U8DL_NO_FFMPEG_PIPE=1`. Nothing in this image reads that variable.

## Hang watchdog

N_m3u8DL-RE has a known thing where it sometimes doesnt notice the
stream ended and just keeps polling forever ([nilaoda/N_m3u8DL-RE#594,
#409, #443](https://github.com/nilaoda/N_m3u8DL-RE/issues/594)).
Chaturbate's HLS doesnt reliably emit `#EXT-X-ENDLIST` either, so the
recorder hangs until something kills it. The community workaround is
"Ctrl+C and remux." This image bakes that in: per-recorder watchdog
checks the output file's mtime every tick, if it hasnt grown in 5
minutes (`HANG_SIGINT_AFTER`) the supervisor sends SIGINT, then SIGTERM
30s later (`HANG_SIGTERM_AFTER`) if the process is still alive. The
existing exit-detection branch then handles the `.part.ts -> .ts`
rename naturally.

Two paranoia paths for restarts too: on graceful shutdown (SIGTERM
from `docker restart` / salt redeploy / watchtower) the supervisor
SIGINTs each child, waits, and runs the same rename. On startup, a
reaper scans the videos dir for any leftover `.part.ts` files (host
crash, abrupt kill, pre-fix backlog) and renames them. Idempotent.

Healthy recordings stay untouched: every chunklist refresh that
produces a new segment bumps the file mtime, the watchdog resets. The
watchdog only fires when the file is demonstrably not growing.

This came out of 2026-05-18: 14 N_m3u8DL-RE processes running on the
prod chat container with output files frozen 3.5 to 10.9 days,
container at 314% CPU, ~76GB sitting in `.part.ts` files that never
got finalized. With the watchdog + shutdown finalize + startup reaper
all three failure modes are now covered.

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
