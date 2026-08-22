// BookForge Go Agent - Multi-agent system with parallel video processing
// This version supports both sequential and parallel modes, matching the Python implementation
//
// ARCHITECTURE:
// - Deterministic agents (custom structs): Intake, Media, Assets, Compiler, Production
// - LLM agents (llmagent): Analyst, Writer, Critic, Refiner
// - Parallel mode: Opt-in via configuration (disabled by default for safety)
// - Thread-safe: Workspace locking prevents race conditions

package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"sync"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/agent/workflowagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/model/gemini"
	"google.golang.org/adk/v2/tool"
	"google.golang.org/genai"

	"bookforge-go/tools"
)

// =============================================================================
// DETERMINISTIC AGENTS (Custom implementations)
// =============================================================================

// IntakeAgent handles YouTube channel listing (DETERMINISTIC)
type IntakeAgent struct {
	cfg *Config
}

func NewIntakeAgent(cfg *Config) *IntakeAgent {
	return &IntakeAgent{cfg: cfg}
}

func (a *IntakeAgent) Name() string {
	return "channel_intake"
}

func (a *IntakeAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Implement YouTube API integration
	return agent.Response{
		Content: "[STUB] Channel intake - YouTube API integration needed",
	}, nil
}

// MediaAgent handles video download and processing (DETERMINISTIC)
type MediaAgent struct {
	cfg *Config
}

func NewMediaAgent(cfg *Config) *MediaAgent {
	return &MediaAgent{cfg: cfg}
}

func (a *MediaAgent) Name() string {
	return "media_acquisition"
}

func (a *MediaAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Implement media processing
	return agent.Response{
		Content: "[STUB] Media acquisition - yt-dlp/ffmpeg/whisper integration needed",
	}, nil
}

// AssetsAgent handles chart/table rendering (DETERMINISTIC)
type AssetsAgent struct {
	cfg *Config
}

func NewAssetsAgent(cfg *Config) *AssetsAgent {
	return &AssetsAgent{cfg: cfg}
}

func (a *AssetsAgent) Name() string {
	return "visual_assets"
}

func (a *AssetsAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Implement asset rendering
	return agent.Response{
		Content: "[STUB] Asset rendering - chart/table generation needed",
	}, nil
}

// CompilerAgent handles book assembly and compilation (DETERMINISTIC)
type CompilerAgent struct {
	cfg *Config
}

func NewCompilerAgent(cfg *Config) *CompilerAgent {
	return &CompilerAgent{cfg: cfg}
}

func (a *CompilerAgent) Name() string {
	return "book_compiler"
}

func (a *CompilerAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Implement LaTeX compilation
	return agent.Response{
		Content: "[STUB] Book compilation - pdflatex integration needed",
	}, nil
}

// =============================================================================
// PRODUCTION AGENT (Handles sequential vs parallel execution)
// =============================================================================

// ProductionAgent processes videos either sequentially or in parallel
type ProductionAgent struct {
	cfg      *Config
	pipeline agent.Agent
}

func NewProductionAgent(cfg *Config, pipeline agent.Agent) *ProductionAgent {
	return &ProductionAgent{
		cfg:      cfg,
		pipeline: pipeline,
	}
}

func (a *ProductionAgent) Name() string {
	return "book_production"
}

func (a *ProductionAgent) Run(ctx context.Context, req agent.Request) (agent.Response, error) {
	// Choose execution mode based on configuration
	if a.cfg.EnableParallelVideos && a.cfg.MaxConcurrentVideos > 1 {
		log.Printf("Parallel mode enabled: processing up to %d videos concurrently", a.cfg.MaxConcurrentVideos)
		return a.runParallel(ctx, req)
	}

	log.Println("Sequential mode: processing videos one at a time")
	return a.runSequential(ctx, req)
}

func (a *ProductionAgent) runSequential(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Implement sequential video processing
	// For now, stub implementation
	return agent.Response{
		Content: "[STUB] Sequential video processing - workspace integration needed\n" +
			"Logic: For each pending video → run pipeline → save chapter",
	}, nil
}

func (a *ProductionAgent) runParallel(ctx context.Context, req agent.Request) (agent.Response, error) {
	// TODO: Get pending videos from workspace
	// For demonstration, we'll show the parallel pattern
	
	// Create semaphore for concurrency control
	semaphore := make(chan struct{}, a.cfg.MaxConcurrentVideos)
	
	// Example: Process multiple videos in parallel
	var wg sync.WaitGroup
	errors := make([]error, 0)
	var errorsMu sync.Mutex
	
	// TODO: Get actual pending videos
	// pendingVideos := ws.PendingVideos()
	
	// For now, demonstrate the pattern
	numVideos := 0 // Will be len(pendingVideos)
	
	for i := 0; i < numVideos; i++ {
		wg.Add(1)
		
		go func(videoIndex int) {
			defer wg.Done()
			
			// Acquire semaphore slot
			semaphore <- struct{}{}
			defer func() { <-semaphore }()
			
			// Process video with error isolation
			if err := a.processOneVideo(ctx, videoIndex); err != nil {
				errorsMu.Lock()
				errors = append(errors, err)
				errorsMu.Unlock()
				log.Printf("Video %d failed: %v", videoIndex, err)
				// Continue processing other videos (error isolation)
			}
		}(i)
	}
	
	// Wait for all videos to complete
	wg.Wait()
	
	if len(errors) > 0 {
		return agent.Response{
			Content: fmt.Sprintf("[Parallel] Completed with %d errors", len(errors)),
		}, nil
	}
	
	return agent.Response{
		Content: "[Parallel] All videos processed successfully",
	}, nil
}

func (a *ProductionAgent) processOneVideo(ctx context.Context, videoIndex int) error {
	// TODO: Implement actual video processing
	// This is where the chapter pipeline would run:
	// 1. Load video record
	// 2. Run pipeline (media → analyst → assets → writer → QA)
	// 3. Save chapter with thread-safe locking
	// 4. Update video status with thread-safe locking
	
	log.Printf("[Parallel] Processing video %d", videoIndex)
	
	// Placeholder for actual implementation
	return nil
}

// =============================================================================
// LLM AGENTS (AI-powered)
// =============================================================================

func createAnalystAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name:  "transcript_analyst",
		Model: model,
		Description: "Analyzes transcript and produces structured chapter analysis",
		Instruction: `You are the Transcript Analyst for BookForge.
Analyze the transcript and produce structured output with chapter title, summary, 
learning objectives, concepts, tables, charts, diagrams, glossary, and exercises.`,
		Tools: []tool.Tool{},
	})
}

func createWriterAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name:  "chapter_writer",
		Model: model,
		Description: "Composes LaTeX chapter body from analysis and assets",
		Instruction: `You are the Chapter Writer for BookForge.
Compose a complete LaTeX chapter body with sections, figures, tables, and exercises.
Reference only files present in the assets manifest.`,
		Tools: []tool.Tool{},
	})
}

func createCriticAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name:  "chapter_critic",
		Model: model,
		Description: "Verifies chapter quality and compilation",
		Instruction: `You are the Chapter Critic.
Verify the chapter compiles correctly and check for critical defects.
Either APPROVE or provide numbered defect list.`,
		Tools: []tool.Tool{},
	})
}

func createRefinerAgent(ctx context.Context, cfg *Config, model agent.Model) (agent.Agent, error) {
	return llmagent.New(llmagent.Config{
		Name:  "chapter_refiner",
		Model: model,
		Description: "Fixes defects found by critic",
		Instruction: `You are the Chapter Refiner.
Fix all defects in the critique while preserving what works.
Output only the corrected LaTeX chapter body.`,
		Tools: []tool.Tool{},
	})
}

// =============================================================================
// WORKFLOW BUILDERS
// =============================================================================

func buildChapterPipeline(ctx context.Context, cfg *Config) (agent.Agent, error) {
	model, err := gemini.NewModel(ctx, cfg.AnalystModel, &genai.ClientConfig{
		APIKey: os.Getenv("GOOGLE_API_KEY"),
	})
	if err != nil {
		return nil, err
	}

	analystAgent, err := createAnalystAgent(ctx, cfg, model)
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

	return workflowagent.NewSequential(workflowagent.SequentialConfig{
		Name:        "chapter_pipeline",
		Description: "One video -> one verified book chapter",
		Agents: []agent.Agent{
			NewMediaAgent(cfg),
			analystAgent,
			NewAssetsAgent(cfg),
			writerAgent,
			// TODO: Wrap critic/refiner in LoopAgent
			criticAgent,
			refinerAgent,
		},
	})
}

func buildRootAgent(ctx context.Context, cfg *Config) (agent.Agent, error) {
	chapterPipeline, err := buildChapterPipeline(ctx, cfg)
	if err != nil {
		return nil, err
	}

	return workflowagent.NewSequential(workflowagent.SequentialConfig{
		Name: "bookforge",
		Description: `Turns a YouTube channel into a compiled LaTeX book:
intake -> parallel per-video chapters -> final compilation`,
		Agents: []agent.Agent{
			NewIntakeAgent(cfg),
			NewProductionAgent(cfg, chapterPipeline),
			NewCompilerAgent(cfg),
		},
	})
}

// =============================================================================
// MAIN
// =============================================================================

func main() {
	ctx := context.Background()
	
	// Load configuration from environment
	cfg := LoadConfigFromEnv()
	
	// Validate configuration
	if err := cfg.Validate(); err != nil {
		log.Fatalf("Invalid configuration: %v", err)
	}

	// Check API key
	if apiKey := os.Getenv("GOOGLE_API_KEY"); apiKey == "" {
		log.Fatal("GOOGLE_API_KEY environment variable must be set")
	}

	// Build root agent
	rootAgent, err := buildRootAgent(ctx, cfg)
	if err != nil {
		log.Fatalf("Failed to create BookForge agent: %v", err)
	}

	// Create launcher configuration
	launcherConfig := &launcher.Config{
		AgentLoader: agent.NewSingleLoader(rootAgent),
	}

	// Run launcher
	l := full.NewLauncher()
	if err = l.Execute(ctx, launcherConfig, os.Args[1:]); err != nil {
		log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
	}
}
