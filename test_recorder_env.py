"""Tests for the pipe-mux A/V alignment fix: ffmpeg_av_sync.rewrite + recorder_env.

Bug: N_m3u8DL-RE --live-pipe-mux runs `ffmpeg -i <video pipe> -i <audio pipe> -c copy -f mpegts` WITHOUT -copyts,
so ffmpeg starts each track at zero on its own and the real gap between the first audio and the first video
fragment becomes a constant lip-sync error (measured: source audio starts 181 ms before video; production output
starts both at 1.400 s; with -copyts the 181 ms is preserved, and a viewer confirmed the fixed file looks right).
Fix: N_m3u8DL-RE --ffmpeg-binary-path points at ffmpeg_av_sync, which adds the timestamp options to the PIPE-MUX
call only. Not RE_LIVE_PIPE_OPTIONS: setting that makes N_m3u8DL-RE also insert `-re` on the video pipe, which
ffmpeg's docs warn against on live input (backpressure, lost segments).

Run: python3 -m unittest test_recorder_env   (stdlib only - also run by the Dockerfile build)
"""
import unittest

from ffmpeg_av_sync import rewrite
from recorder_env import DEFAULT_PIPE_MUX_OPTIONS, WRAPPER, pipe_mux_args, pipe_mux_env

# the exact argv N_m3u8DL-RE v0.5.1 PipeUtil.StartPipeMux builds (no RE_LIVE_PIPE_OPTIONS)
PIPEMUX = ["-y", "-fflags", "+genpts", "-loglevel", "quiet", "-i", "/tmp/RE_pipe_aaaa", "-i", "/tmp/RE_pipe_bbbb",
           "-map", "0", "-map", "1", "-strict", "unofficial", "-c", "copy", "-metadata", "date=2026-10-27T12:00:00",
           "-ignore_unknown", "-copy_unknown", "-f", "mpegts", "-shortest", "/app/videos/x/x-20261027.part.ts"]
OPTS = DEFAULT_PIPE_MUX_OPTIONS
PIPE_ARGS = ["--auto-select", "--live-real-time-merge", "--live-pipe-mux", "--no-log"]


class Rewrite(unittest.TestCase):
    def test_pipe_mux_gets_copyts_right_before_the_output(self):
        out = rewrite(PIPEMUX, OPTS)
        i = out.index("-f")
        self.assertEqual(out[i - 3:i], ["-copyts", "-avoid_negative_ts", "make_zero"])
        self.assertEqual(out[i:], ["-f", "mpegts", "-shortest", "/app/videos/x/x-20261027.part.ts"])
        self.assertEqual([a for a in out if a not in ("-copyts", "-avoid_negative_ts", "make_zero")], PIPEMUX)

    def test_re_is_dropped_from_the_pipe_mux_call(self):
        out = rewrite(PIPEMUX[:5] + ["-re"] + PIPEMUX[5:], OPTS)
        self.assertNotIn("-re", out)

    def test_every_other_ffmpeg_call_passes_through_untouched(self):
        """The same binary probes media info and muxes after download - never touch those."""
        for argv in (["-i", "/app/videos/x/x.part.ts"], ["-hide_banner", "-i", "a.mp4", "-f", "null", "-"],
                     ["-y", "-i", "v.mp4", "-i", "a.m4a", "-map", "0", "-map", "1", "-c", "copy", "out.mkv"]):
            self.assertEqual(rewrite(argv, OPTS), argv, argv)

    def test_start_at_zero_is_never_added(self):
        """-copyts -start_at_zero re-zeroes EACH input - the very bug (another recorder tried it and reverted)."""
        out = rewrite(PIPEMUX, "-copyts -start_at_zero -avoid_negative_ts make_zero")
        self.assertNotIn("-start_at_zero", out)
        self.assertIn("-copyts", out)

    def test_already_copyts_is_left_alone(self):
        once = rewrite(PIPEMUX, OPTS)
        self.assertEqual(rewrite(once, OPTS), once)

    def test_empty_options_pass_through(self):
        for off in ("", "  ", None):
            self.assertEqual(rewrite(PIPEMUX, off), PIPEMUX)


class RecorderEnv(unittest.TestCase):
    def test_default_options(self):
        self.assertEqual(DEFAULT_PIPE_MUX_OPTIONS, "-copyts -avoid_negative_ts make_zero")

    def test_pipe_mux_recorder_gets_the_wrapper(self):
        self.assertEqual(pipe_mux_args(PIPE_ARGS, OPTS), ["--ffmpeg-binary-path", WRAPPER])

    def test_no_wrapper_without_pipe_mux_or_when_switched_off(self):
        self.assertEqual(pipe_mux_args(["--auto-select"], OPTS), [])
        for off in ("", "  ", None):
            self.assertEqual(pipe_mux_args(PIPE_ARGS, off), [])

    def test_an_explicit_ffmpeg_path_in_the_config_wins(self):
        self.assertEqual(pipe_mux_args(PIPE_ARGS + ["--ffmpeg-binary-path", "/opt/ff"], OPTS), [])

    def test_env_carries_the_options_and_does_not_mutate_the_caller(self):
        base = {"PATH": "/bin"}
        env = pipe_mux_env(base, OPTS)
        self.assertEqual(env["PIPE_MUX_OPTIONS"], OPTS)
        self.assertEqual(env["PATH"], "/bin")
        self.assertEqual(base, {"PATH": "/bin"})


if __name__ == "__main__":
    unittest.main()
