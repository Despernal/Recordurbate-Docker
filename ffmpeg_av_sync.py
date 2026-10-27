#!/usr/bin/env python3
"""ffmpeg wrapper that keeps the source A/V alignment in N_m3u8DL-RE pipe-mux recordings.

N_m3u8DL-RE --live-pipe-mux muxes the separate audio and video tracks with
`ffmpeg -fflags +genpts -i <video pipe> -i <audio pipe> ... -c copy -f mpegts`
and no -copyts, so ffmpeg starts each track at zero on its own. The real gap
between the first audio and first video fragment is lost and becomes a
constant lip-sync error for the whole recording.

N_m3u8DL-RE runs this file as its ffmpeg (--ffmpeg-binary-path). For the
pipe-mux call only, it adds the options in $PIPE_MUX_OPTIONS (default
"-copyts -avoid_negative_ts make_zero") right before the output, drops any
"-re", and never adds "-start_at_zero" (with -copyts that re-zeroes each input
separately, which is the bug again). Every other call (media-info probes,
mux-after-done) is passed through untouched. Real binary: $REAL_FFMPEG.
"""
import os
import sys

DEFAULT_OPTIONS = "-copyts -avoid_negative_ts make_zero"
_NEVER = ("-start_at_zero",)


def _is_pipe_mux(argv):
    pipes = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "-i" and "RE_pipe_" in os.path.basename(argv[i + 1])]
    has_genpts = any(a == "-fflags" and b == "+genpts" for a, b in zip(argv, argv[1:]))
    has_ts_out = any(a == "-f" and b == "mpegts" for a, b in zip(argv, argv[1:]))
    return len(pipes) >= 2 and has_genpts and has_ts_out


def rewrite(argv, options):
    """The argv ffmpeg should really get. Only the pipe-mux call is changed."""
    if not options or not options.strip() or not _is_pipe_mux(argv) or "-copyts" in argv:
        return list(argv)
    add = [t for t in options.split() if t not in _NEVER]
    out = [a for a in argv if a != "-re"]
    last_f = max(i for i, a in enumerate(out[:-1]) if a == "-f" and out[i + 1] == "mpegts")
    return out[:last_f] + add + out[last_f:]


def main():
    real = os.environ.get("REAL_FFMPEG", "/usr/bin/ffmpeg")
    args = rewrite(sys.argv[1:], os.environ.get("PIPE_MUX_OPTIONS", DEFAULT_OPTIONS))
    os.execv(real, [real] + args)


if __name__ == "__main__":
    main()
