"""Typed contracts shared between BookForge agents.

`ChapterAnalysis` is the structured hand-off between the Transcript Analyst
(LLM) and the deterministic asset/writer stages. Keep it strict: the writer
must never need to invent data.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Manifest (videos.json)
# ---------------------------------------------------------------------------

VideoStatus = Literal[
    "pending", "media", "analyzed", "assets", "written", "verified", "failed"
]


class VideoRecord(BaseModel):
    video_id: str
    title: str
    url: str
    duration_sec: int = 0
    upload_date: str = ""
    chapter_number: int = 0
    status: VideoStatus = "pending"
    error: str = ""


class ChannelManifest(BaseModel):
    channel_url: str
    channel_title: str = ""
    channel_slug: str
    created_at: str = ""
    videos: list[VideoRecord] = Field(default_factory=list)

    def by_id(self, video_id: str) -> VideoRecord | None:
        return next((v for v in self.videos if v.video_id == video_id), None)


# ---------------------------------------------------------------------------
# Media assets
# ---------------------------------------------------------------------------


class FrameAsset(BaseModel):
    file: str  # path relative to the video dir
    timestamp_sec: float
    phash: str


class MediaBundle(BaseModel):
    video_id: str
    video_path: str = ""
    audio_path: str = ""
    transcript_path: str = ""
    transcript_source: Literal["captions", "whisper", "none"] = "none"
    frames: list[FrameAsset] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Chapter analysis (LLM structured output)
# ---------------------------------------------------------------------------


class ConceptNote(BaseModel):
    heading: str
    explanation: str = Field(description="3-8 sentences, precise, textbook style")
    key_points: list[str] = Field(default_factory=list)


class TableSpec(BaseModel):
    title: str
    caption: str
    headers: list[str]
    rows: list[list[str]]
    note: str = ""


class ChartSpec(BaseModel):
    title: str
    caption: str
    chart_type: Literal["bar", "line", "pie"] = "bar"
    x_label: str = ""
    y_label: str = ""
    categories: list[str] = Field(default_factory=list)
    series_name: str = "value"
    values: list[float] = Field(default_factory=list)


class DiagramSpec(BaseModel):
    title: str
    caption: str
    diagram_type: Literal["flowchart", "sequence", "hierarchy", "mindmap"] = "flowchart"
    elements: list[str] = Field(
        default_factory=list,
        description="Ordered nodes/steps/concepts the diagram must show",
    )
    relationships: list[str] = Field(
        default_factory=list, description='Edges as "A -> B : label"'
    )


class Exercise(BaseModel):
    question: str
    answer: str


class GlossaryItem(BaseModel):
    term: str
    definition: str


class FrameCaptionItem(BaseModel):
    frame_file: str
    caption: str


class ChapterAnalysis(BaseModel):
    """Validated JSON emitted by the TranscriptAnalystAgent."""

    chapter_title: str
    summary: str = Field(description="One-paragraph executive summary")
    learning_objectives: list[str] = Field(min_length=2, max_length=8)
    concepts: list[ConceptNote] = Field(min_length=1, max_length=12)
    tables: list[TableSpec] = Field(default_factory=list, max_length=6)
    charts: list[ChartSpec] = Field(default_factory=list, max_length=6)
    diagrams: list[DiagramSpec] = Field(default_factory=list, max_length=4)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list, max_length=10)
    frame_captions: list[FrameCaptionItem] = Field(
        default_factory=list,
        description="Optional per-frame caption overrides",
    )

    @property
    def glossary_dict(self) -> dict[str, str]:
        return {item.term: item.definition for item in self.glossary}

    @property
    def frame_captions_dict(self) -> dict[str, str]:
        return {item.frame_file: item.caption for item in self.frame_captions}


# ---------------------------------------------------------------------------
# Visual asset manifest (produced by VisualAssetAgent)
# ---------------------------------------------------------------------------


class FigureAsset(BaseModel):
    filename: str  # file inside the chapter figures/ dir
    kind: Literal["frame", "chart"]
    caption: str
    label: str  # latex label, e.g. fig:ch03-01


class TableAsset(BaseModel):
    tex_file: str  # fragment path inside chapter tables/ dir
    caption: str
    label: str


class AssetsManifest(BaseModel):
    chapter_slug: str
    chapter_dir: str
    figures: list[FigureAsset] = Field(default_factory=list)
    tables: list[TableAsset] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# State coercion helpers (ADK may store str or dict under an output_key)
# ---------------------------------------------------------------------------


def coerce_analysis(value: object) -> ChapterAnalysis:
    if isinstance(value, ChapterAnalysis):
        return value
    if isinstance(value, str):
        return ChapterAnalysis.model_validate_json(value)
    return ChapterAnalysis.model_validate(value)


def coerce_assets_manifest(value: object) -> AssetsManifest:
    if isinstance(value, AssetsManifest):
        return value
    if isinstance(value, str):
        return AssetsManifest.model_validate_json(value)
    return AssetsManifest.model_validate(value)
