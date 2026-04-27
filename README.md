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

In March 2026 Chaturbate switched their stream format to Low-Latency HLS
with split audio/video CMAF (separate audio and video chunklists,
per-segment `init_*.m4s` MOOV atoms). ffmpeg 8.x's HLS demuxer doesn't
handle the per-segment init reload cleanly and recordings end up with
audio that stops mid-stream while video keeps going. ffprobe on an
affected file shows it right away: video duration is normal, audio
duration is a fraction of that. This is not specific to this project,
it hits every recording tool built on ffmpeg's HLS demuxer.

### Working ffmpeg ranges

- ffmpeg 6.1.2: fails (predates LL-HLS-CMAF support)
- ffmpeg 7.x range from late-2025 alpine: works
- ffmpeg 8.x: broken against the new CB format

### Working image (master / `:latest`)

`ghcr.io/despernal/recordurbate-docker:latest` is currently pinned to the
2025-10-28 build digest:

```
sha256:33ba571d0b4c745a5fd9d13947111b746e752c1e19142aad890ad80bf878245b
```

That build's ffmpeg handles the new CMAF format correctly. If a future
rebuild ever produces a regression you can pin compose back to that
digest or retag it with `crane`.

## This branch (`n_m3u8dl-re`): replace ffmpeg's HLS demuxer with N_m3u8DL-RE

This branch is the long-term fix. Instead of relying on ffmpeg's HLS
demuxer (which is broken on CMAF in 8.x and may regress again as alpine
floats forward), the recorder now uses
[`N_m3u8DL-RE`](https://github.com/nilaoda/N_m3u8DL-RE) for the segment
download. The cam-recording community has converged on this as the
working answer: see ctbcap's `n_m3u8dl-re` branch and StreaMonitor #342
for the same approach.

ffmpeg is still installed and still does the muxing, but it never sees
the HLS stream directly. The CMAF demuxer bug is bypassed entirely.

### How recording flows on this branch

1. The patched `is_online` posts to `chaturbate.com/get_edge_hls_url_ajax/`.
   The response carries both `room_status` and the live `url` for the
   m3u8, so one round trip resolves both questions.
2. If the room is public, `is_online` returns the m3u8 URL (truthy);
   `bot.py`'s recording loop captures it and spawns `N_m3u8DL-RE` with
   the URL plus per-streamer `--save-dir` / `--save-name` plus the flags
   loaded from the recorder config file.
3. `N_m3u8DL-RE` pulls segments natively. Segment retries stay inside
   one process, so transient reconnects no longer fragment the recording
   into a billion small files.
4. Output goes through `ffmpeg --live-pipe-mux` for a single live-merged
   file.

### Branch image tag

```
docker pull ghcr.io/despernal/recordurbate-docker:n_m3u8dl-re
```

Branch builds publish to that tag. `:latest` stays untouched while this
branch is in flight; only a merge to master moves `:latest`.

### Pinned versions in the n_m3u8dl-re image

So the build is reproducible and a tampered or regressed dependency
shows up at build time, not at record time:

- **Recordurbate source**: SHA `0479d71a4e37b6efcd4a5eac1bbceb5b4592beb8`
  (last touch on upstream master, 2023-12-12). Pulled via
  `codeload.github.com/.../zip/<sha>` so the tree is byte-identical
  every build.
- **N_m3u8DL-RE**: `v0.5.1-beta` `linux-musl-x64` (2025-10-29 release).
  Verified on download by sha256 `7105e26b76b099b41fcd490b9d09b3d43be971a880b6323fb988b688be00ab82`.
  The `musl-x64` build is alpine-native; no `gcompat` shim needed.
- **Base image**: `python:3.13-alpine3.22`.
- **Patch**: `bot.py.patch` was generated by diffing the patched copy
  against the pinned upstream, so it always applies cleanly.

### Tuning recorder behavior

`N_m3u8DL-RE` flags live in `/app/configs/n_m3u8dl-re.config`. The file
format mirrors `youtube-dl.config`: one CLI flag (or flag + value) per
line, `#` comments and blank lines ignored, `--flag=value` and
`--flag value` both fine.

Shipped defaults are tuned for live recording: `--auto-select`,
`--live-real-time-merge`, `--live-pipe-mux`, `--live-keep-segments=False`,
`--no-log`, `--disable-update-check`.

Edit the file on the host (no rebuild needed; `/app/configs` is
bind-mounted) and restart the container to apply.

If you hit audio-sync trouble, drop `--live-pipe-mux` from the config
and set environment variable `N_M3U8DL_NO_FFMPEG_PIPE=1` on the
container. That switches to the separate-files-then-merge mode used by
ctbcap, which trades a small post-merge delay for tighter A/V sync.

### Verification recipe

To validate a candidate image without disturbing prod:

1. Build the image.
2. Run a test container that shares the same network namespace as your
   prod recorder, e.g. `--network=container:wireguard`. CB sees the
   same IP it always sees, so no anti-bot delta.
3. Configure with ONE streamer that you know is currently live.
4. Bind-mount a throwaway output dir.
5. Let it record for two or three minutes.
6. Force-finalize the in-progress file:
   ```
   docker exec <test-container> ps -ef | grep N_m3u8DL-RE
   docker exec <test-container> kill -2 <pid>
   ```
   `SIGINT` (`-2`) finalizes the MOOV cleanly. `SIGTERM`/`SIGKILL`
   skip the MOOV write and you'll get a corrupt file.
7. `ffprobe -v error -show_entries stream=codec_type,duration <file>`
   on the result. Clean recordings show `< 1s` drift between video
   duration and audio duration; broken ones show many seconds to many
   minutes of audio loss.

A 1m41s test recording on the first build of this branch showed
`33 ms` audio drift, vs `43 ms` on the rolled-back ffmpeg 7.x
baseline. So this branch is at least as good as the rollback for
A/V alignment, plus it kills the fragmentation issue.

### References

- [StreaMonitor issue #342](https://github.com/lossless1/StreaMonitor/issues/342)
  -- main thread documenting the bug across multiple recording tools
- [ctbcap n_m3u8dl-re branch](https://github.com/KFERMercer/ctbcap/tree/n_m3u8dl-re)
  -- working workaround using N_m3u8DL-RE, source for this approach
- [chaturbate-dvr issue #155](https://github.com/teacat/chaturbate-dvr/issues/155)
  -- same symptoms reported in a sister project
