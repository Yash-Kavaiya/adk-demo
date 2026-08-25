"""Progress / ETA formatting."""

from bookforge.progress import ProgressTracker, format_duration


def test_format_duration():
    assert format_duration(0) == "0s"
    assert format_duration(9) == "9s"
    assert format_duration(75) == "1m15s"
    assert format_duration(3661) == "1h01m"


def test_eta_uses_default_then_rolling_average():
    tracker = ProgressTracker(total=4, default_chapter_sec=120)
    assert tracker.eta_sec() == 480
    msg = tracker.start_chapter(0, "Intro")
    assert "[1/4] Starting: Intro" in msg
    assert "ETA ~" in msg
    done = tracker.finish_chapter(0, "Intro", "written")
    assert "[1/4] Finished: Intro (written)" in done
    assert tracker.done == 1
    assert tracker.remaining == 3
    assert tracker.eta_sec() == 360  # still using default avg after a sub-second finish


def test_failed_chapters_counted():
    tracker = ProgressTracker(total=2, default_chapter_sec=10)
    tracker.start_chapter(0, "A")
    tracker.finish_chapter(0, "A", "failed")
    assert tracker.failed == 1
    assert "1 failed" in tracker.summary()
