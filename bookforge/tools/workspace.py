"""Filesystem workspace + manifest management.

The workspace is the durable memory of the pipeline; the ADK session state
only carries small JSON pointers into it.

Layout under <root>/<channel_slug>/:
    manifest.json
    videos/<video_id>/video.mp4 audio.wav transcript.txt media.json
        frames_raw/ frames/
    chapters/<NN>_<slug>/chapter.tex figures/ tables/
    build/
    book/main.tex preamble.tex book.pdf
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from bookforge.schemas import ChannelManifest, VideoRecord

logger = logging.getLogger(__name__)


def slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "untitled"


class Workspace:
    def __init__(self, root: Path, channel_slug: str) -> None:
        self.root = Path(root) / channel_slug
        self.videos_dir = self.root / "videos"
        self.chapters_dir = self.root / "chapters"
        self.build_dir = self.root / "build"
        self.book_dir = self.root / "book"
        for d in (
            self.root,
            self.videos_dir,
            self.chapters_dir,
            self.build_dir,
            self.book_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    # -- manifest -----------------------------------------------------------

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def manifest_exists(self) -> bool:
        return self.manifest_path.exists()

    def load_manifest(self) -> ChannelManifest:
        return ChannelManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )

    def save_manifest(self, manifest: ChannelManifest) -> None:
        self._atomic_write_json(self.manifest_path, manifest.model_dump(mode="json"))

    def init_manifest(
        self, channel_url: str, channel_title: str, slug: str
    ) -> ChannelManifest:
        manifest = ChannelManifest(
            channel_url=channel_url,
            channel_title=channel_title,
            channel_slug=slug,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.save_manifest(manifest)
        return manifest

    def update_video(self, video_id: str, **changes) -> ChannelManifest:
        manifest = self.load_manifest()
        record = manifest.by_id(video_id)
        if record is None:
            raise KeyError(f"video {video_id} not in manifest")
        for key, value in changes.items():
            setattr(record, key, value)
        self.save_manifest(manifest)
        return manifest

    def pending_videos(self) -> list[VideoRecord]:
        """Videos whose chapter is not yet verified (resume source of truth)."""
        manifest = self.load_manifest()
        return [
            v
            for v in sorted(manifest.videos, key=lambda x: x.chapter_number)
            if v.status not in ("verified",)
        ]

    # -- per-video paths ------------------------------------------------------

    def video_dir(self, video_id: str) -> Path:
        d = self.videos_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def chapter_dir(self, record: VideoRecord) -> Path:
        d = self.chapters_dir / f"{record.chapter_number:02d}_{slugify(record.title)}"
        for sub in (d, d / "figures", d / "tables"):
            sub.mkdir(parents=True, exist_ok=True)
        return d

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, encoding="utf-8", suffix=".tmp"
        ) as tmp:
            json.dump(payload, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    @staticmethod
    def write_text(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", dir=path.parent, delete=False, encoding="utf-8", suffix=".tmp"
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
        return path
