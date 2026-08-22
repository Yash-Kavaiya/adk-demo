// BookForge Go Agent - Multi-agent system that turns YouTube channels into LaTeX books
// This is a Go implementation of the Python BookForge agent using Google ADK Go v2.0
package main

import (
	"context"
	"log"
	"os"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/agent/workflowagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/model/gemini"
	"google.golang.org/adk/v2/tool"
	"google.golang.org/genai"
)

// Config holds BookForge configuration settings
type Config struct {
	AnalystModel  string
	WriterModel   string
	CriticModel   string
	WorkspaceRoot string
	MaxVideos     int
	CompileLaTeX  bool
}

// DefaultConfig returns default configuration
func DefaultConfig() *Config {
	return &Config{
		AnalystModel:  "gemini-2.0-flash-exp",
		WriterModel:   "gemini-exp-1206",
		CriticModel:   "gemini-2.0-flash-exp",
		WorkspaceRoot: "data",
		MaxVideos:     0, // 0 means all videos
		CompileLaTeX:  true,
	}
}

// createIntakeAgent creates the channel intake agent
func createIntakeAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "channel_intake",
		Model: model,
		Description: "Fetches every video link of a YouTube channel into a resumable JSON manifest",
		Instruction: `You are the Channel Intake Agent for BookForge.

Extract the YouTube channel URL from the user's message and list all videos from that channel.

Create a manifest with:
- Channel URL, title, and slug
- Video list with: video_id, title, url, duration, upload_date, chapter_number
- Status tracking (pending/media/analyzed/assets/written/verified/failed)

The manifest is resumable - if it exists, load and continue from where it left off.`,
		Tools: []tool.Tool{
			// TODO: Add YouTube listing tool
		},
	})
}

// createMediaAgent creates the media acquisition agent
func createMediaAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "media_acquisition",
		Model: model,
		Description: "Downloads video, extracts transcript and deduped frames",
		Instruction: `You are the Media Acquisition Agent for BookForge.

For the current video:
1. Download at capped resolution (480p)
2. Extract transcript (prefer captions, fallback to whisper)
3. Extract frames every 5 seconds
4. Deduplicate frames using perceptual hashing

Store all media in the video directory and update the manifest.`,
		Tools: []tool.Tool{
			// TODO: Add download, transcript, frame extraction tools
		},
	})
}

// createAnalystAgent creates the transcript analysis agent
func createAnalystAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "transcript_analyst",
		Model: model,
		Description: "Analyzes transcript and produces structured chapter analysis",
		Instruction: `You are the Transcript Analyst for BookForge.

Read the timestamped transcript and produce a rigorous, textbook-grade analysis:

1. chapter_title - academic chapter title
2. summary - one dense paragraph
3. learning_objectives - 2-8 measurable objectives
4. concepts - 1-12 core ideas with explanations (3-8 sentences each)
5. tables - comparison/specification tables with real data
6. charts - numeric data for visualization
7. diagrams - conceptual diagrams (flowchart, sequence, hierarchy, mindmap)
8. glossary - technical terms
9. exercises - review questions with answers
10. frame_captions - optional per-frame caption overrides

Be faithful to the transcript. Prefer omission over invention.`,
		Tools: []tool.Tool{
			// Analysis outputs structured JSON
		},
	})
}

// createAssetsAgent creates the visual assets agent
func createAssetsAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "visual_assets",
		Model: model,
		Description: "Renders charts, tables, and curates frames into chapter assets",
		Instruction: `You are the Visual Assets Agent for BookForge.

Turn the analysis into real files:
1. Render tables as booktabs LaTeX fragments
2. Render charts as matplotlib PDFs
3. Curate frames spread across the video timeline

Create an assets manifest listing all figures and tables for the writer to reference.`,
		Tools: []tool.Tool{
			// TODO: Add rendering tools
		},
	})
}

// createWriterAgent creates the chapter writing agent
func createWriterAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "chapter_writer",
		Model: model,
		Description: "Composes LaTeX chapter body from analysis and assets",
		Instruction: `You are the Chapter Writer for BookForge.

Compose a complete LaTeX chapter body following this structure:
- \chapter command with title and label
- Overview section (summary)
- Learning Objectives (itemize)
- One section per concept
- Key Data and Comparisons (tables and charts)
- Conceptual Models (TikZ diagrams)
- Key Takeaways (itemize)
- Glossary (description list)
- Exercises and Solutions

Rules:
- Reference ONLY files in the assets manifest
- Escape LaTeX special characters in prose
- No documentclass, usepackage, or begin/end document
- Target 1200-2500 words

Output ONLY the LaTeX chapter body.`,
		Tools: []tool.Tool{},
	})
}

// createCriticAgent creates the chapter verification agent
func createCriticAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "chapter_critic",
		Model: model,
		Description: "Verifies chapter by compiling and checking assets",
		Instruction: `You are the Chapter Critic - the quality gate.

Verification protocol:
1. Compile the chapter with pdflatex
2. Check all asset references exist
3. Verify structure (required sections present)
4. Check faithfulness (numbers match analysis)

Decision:
- If compile succeeds and no critical defects: APPROVE
- Otherwise: emit numbered defect list (CRITICAL/MAJOR/MINOR)`,
		Tools: []tool.Tool{
			// TODO: Add compile and approval tools
		},
	})
}

// createRefinerAgent creates the chapter refinement agent
func createRefinerAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "chapter_refiner",
		Model: model,
		Description: "Fixes defects found by the critic",
		Instruction: `You are the Chapter Refiner.

Fix EVERY defect in the critique while preserving what works.

Hard rules:
- Fix LaTeX compile errors first
- Never reference assets not in the manifest
- Keep required section order
- Escape special characters

Output ONLY the corrected LaTeX chapter body.`,
		Tools: []tool.Tool{},
	})
}

// createCompilerAgent creates the book compilation agent
func createCompilerAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name: "book_compiler",
		Model: model,
		Description: "Assembles main.tex and compiles final book PDF",
		Instruction: `You are the Book Compiler.

Assemble the final book:
1. Create preamble.tex (shared LaTeX packages)
2. Create main.tex (title, TOC, chapter inputs)
3. Compile with pdflatex (2 passes)
4. Produce book.pdf

Exclude failed chapters from the book.`,
		Tools: []tool.Tool{
			// TODO: Add compilation tools
		},
	})
}

// buildChapterPipeline creates the per-video chapter processing workflow
func buildChapterPipeline(ctx context.Context, cfg *Config) (agent.Agent, error) {
	model, err := gemini.NewModel(ctx, cfg.AnalystModel, &genai.ClientConfig{
		APIKey: os.Getenv("GOOGLE_API_KEY"),
	})
	if err != nil {
		return nil, err
	}

	// Create sub-agents
	mediaAgent, err := createMediaAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	analystAgent, err := createAnalystAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	assetsAgent, err := createAssetsAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	writerAgent, err := createWriterAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	criticAgent, err := createCriticAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	refinerAgent, err := createRefinerAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	// Sequential workflow: media -> analyst -> assets -> writer -> QA loop
	return workflowagent.NewSequential(workflowagent.SequentialConfig{
		Name:        "chapter_pipeline",
		Description: "One video -> one verified book chapter",
		Agents: []agent.Agent{
			mediaAgent,
			analystAgent,
			assetsAgent,
			writerAgent,
			// TODO: Add loop agent for critic/refiner
			criticAgent,
			refinerAgent,
		},
	})
}

// buildRootAgent creates the main BookForge agent
func buildRootAgent(ctx context.Context, cfg *Config) (agent.Agent, error) {
	model, err := gemini.NewModel(ctx, cfg.AnalystModel, &genai.ClientConfig{
		APIKey: os.Getenv("GOOGLE_API_KEY"),
	})
	if err != nil {
		return nil, err
	}

	intakeAgent, err := createIntakeAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	chapterPipeline, err := buildChapterPipeline(ctx, cfg)
	if err != nil {
		return nil, err
	}

	compilerAgent, err := createCompilerAgent(ctx, cfg, model)
	if err != nil {
		return nil, err
	}

	// Main sequential workflow
	return workflowagent.NewSequential(workflowagent.SequentialConfig{
		Name: "bookforge",
		Description: `Turns a YouTube channel URL into a compiled LaTeX book:
intake -> per-video chapters -> final compilation`,
		Agents: []agent.Agent{
			intakeAgent,
			// TODO: Add production loop agent
			chapterPipeline,
			compilerAgent,
		},
	})
}

func main() {
	ctx := context.Background()
	cfg := DefaultConfig()

	// Load configuration from environment
	if apiKey := os.Getenv("GOOGLE_API_KEY"); apiKey == "" {
		log.Fatal("GOOGLE_API_KEY environment variable must be set")
	}

	// Build the root agent
	rootAgent, err := buildRootAgent(ctx, cfg)
	if err != nil {
		log.Fatalf("Failed to create BookForge agent: %v", err)
	}

	// Configure launcher
	launcherConfig := &launcher.Config{
		AgentLoader: agent.NewSingleLoader(rootAgent),
	}

	// Run with full launcher (supports CLI and web UI)
	l := full.NewLauncher()
	if err = l.Execute(ctx, launcherConfig, os.Args[1:]); err != nil {
		log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
	}
}
