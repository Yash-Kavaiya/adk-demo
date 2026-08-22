package tools

// ChapterAnalysis is the structured output from the TranscriptAnalystAgent
type ChapterAnalysis struct {
	ChapterTitle       string          `json:"chapter_title"`
	Summary            string          `json:"summary"`
	LearningObjectives []string        `json:"learning_objectives"`
	Concepts           []ConceptNote   `json:"concepts"`
	Tables             []TableSpec     `json:"tables"`
	Charts             []ChartSpec     `json:"charts"`
	Diagrams           []DiagramSpec   `json:"diagrams"`
	Glossary           []GlossaryItem  `json:"glossary"`
	Exercises          []Exercise      `json:"exercises"`
	FrameCaptions      []FrameCaption  `json:"frame_captions"`
}

// ConceptNote represents a core concept in the chapter
type ConceptNote struct {
	Heading     string   `json:"heading"`
	Explanation string   `json:"explanation"`
	KeyPoints   []string `json:"key_points"`
}

// TableSpec defines a table to be rendered
type TableSpec struct {
	Title   string     `json:"title"`
	Caption string     `json:"caption"`
	Headers []string   `json:"headers"`
	Rows    [][]string `json:"rows"`
	Note    string     `json:"note,omitempty"`
}

// ChartSpec defines a chart to be rendered
type ChartSpec struct {
	Title      string    `json:"title"`
	Caption    string    `json:"caption"`
	ChartType  string    `json:"chart_type"` // "bar", "line", "pie"
	XLabel     string    `json:"x_label"`
	YLabel     string    `json:"y_label"`
	Categories []string  `json:"categories"`
	SeriesName string    `json:"series_name"`
	Values     []float64 `json:"values"`
}

// DiagramSpec defines a conceptual diagram
type DiagramSpec struct {
	Title         string   `json:"title"`
	Caption       string   `json:"caption"`
	DiagramType   string   `json:"diagram_type"` // "flowchart", "sequence", "hierarchy", "mindmap"
	Elements      []string `json:"elements"`
	Relationships []string `json:"relationships"`
}

// Exercise represents a review question
type Exercise struct {
	Question string `json:"question"`
	Answer   string `json:"answer"`
}

// GlossaryItem defines a term and definition
type GlossaryItem struct {
	Term       string `json:"term"`
	Definition string `json:"definition"`
}

// FrameCaption provides optional caption override for a frame
type FrameCaption struct {
	FrameFile string `json:"frame_file"`
	Caption   string `json:"caption"`
}

// MediaBundle contains all media assets for a video
type MediaBundle struct {
	VideoID          string       `json:"video_id"`
	VideoPath        string       `json:"video_path"`
	AudioPath        string       `json:"audio_path"`
	TranscriptPath   string       `json:"transcript_path"`
	TranscriptSource string       `json:"transcript_source"` // "captions", "whisper", "none"
	Frames           []FrameAsset `json:"frames"`
}

// FrameAsset represents a single extracted frame
type FrameAsset struct {
	File         string  `json:"file"`
	TimestampSec float64 `json:"timestamp_sec"`
	PHash        string  `json:"phash"`
}

// AssetsManifest lists all rendered assets for a chapter
type AssetsManifest struct {
	ChapterSlug string         `json:"chapter_slug"`
	ChapterDir  string         `json:"chapter_dir"`
	Figures     []FigureAsset  `json:"figures"`
	Tables      []TableAsset   `json:"tables"`
}

// FigureAsset represents a figure (frame or chart)
type FigureAsset struct {
	Filename string `json:"filename"`
	Kind     string `json:"kind"` // "frame", "chart"
	Caption  string `json:"caption"`
	Label    string `json:"label"`
}

// TableAsset represents a table fragment
type TableAsset struct {
	TexFile string `json:"tex_file"`
	Caption string `json:"caption"`
	Label   string `json:"label"`
}

// GlossaryDict converts glossary items to a map
func (ca *ChapterAnalysis) GlossaryDict() map[string]string {
	result := make(map[string]string)
	for _, item := range ca.Glossary {
		result[item.Term] = item.Definition
	}
	return result
}

// FrameCaptionsDict converts frame captions to a map
func (ca *ChapterAnalysis) FrameCaptionsDict() map[string]string {
	result := make(map[string]string)
	for _, fc := range ca.FrameCaptions {
		result[fc.FrameFile] = fc.Caption
	}
	return result
}
