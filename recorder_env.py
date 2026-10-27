"""Per-recorder arguments + environment for the pipe-mux A/V alignment fix.

N_m3u8DL-RE --live-pipe-mux muxes the separate live audio and video tracks
without -copyts, so each track is started at zero on its own and the gap
between the first audio and video fragment turns into a constant lip-sync
error (different for every recording). The fix routes N_m3u8DL-RE's ffmpeg
through ffmpeg_av_sync (--ffmpeg-binary-path), which adds
`-copyts -avoid_negative_ts make_zero` to the pipe-mux call only.

Why not RE_LIVE_PIPE_OPTIONS: setting it also makes N_m3u8DL-RE insert `-re`
before the video pipe, and ffmpeg's docs warn against -re on live input.
Options come from config.json "pipe_mux_options" ("" = off, old behaviour).
"""
DEFAULT_PIPE_MUX_OPTIONS = "-copyts -avoid_negative_ts make_zero"
WRAPPER = "/app/ffmpeg_av_sync.py"


def pipe_mux_args(recorder_args, options):
    """Extra N_m3u8DL-RE args: the wrapper, if this recorder pipe-muxes, the fix is on,
    and the config did not already pick an ffmpeg binary."""
    if ("--live-pipe-mux" not in recorder_args or not options or not options.strip()
            or "--ffmpeg-binary-path" in recorder_args):
        return []
    return ["--ffmpeg-binary-path", WRAPPER]


def pipe_mux_env(base_env, options):
    """Copy of base_env carrying the options to the wrapper."""
    env = dict(base_env)
    env["PIPE_MUX_OPTIONS"] = options or ""
    return env
