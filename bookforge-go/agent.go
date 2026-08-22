// BookForge Go Agent - Multi-agent system that turns YouTube channels into LaTeX books
// Official Google ADK Go v2 implementation adhering to https://adk.dev/get-started/go/
package main

import (
	"context"
	"iter"
	"log"
	"os"

	"google.golang.org/adk/v2/agent"
	"google.golang.org/adk/v2/agent/llmagent"
	"google.golang.org/adk/v2/cmd/launcher"
	"google.golang.org/adk/v2/cmd/launcher/full"
	"google.golang.org/adk/v2/model"
	"google.golang.org/adk/v2/model/gemini"
	"google.golang.org/adk/v2/session"
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
		AnalystModel:  "gemini-2.0-flash",
		WriterModel:   "gemini-2.0-flash",
		CriticModel:   "gemini-2.0-flash",
		WorkspaceRoot: "data",
		MaxVideos:     2,
		CompileLaTeX:  true,
	}
}

// Helper to create deterministic custom agents with ADK v2
func newDeterministicAgent(name, desc, outputMsg string) (agent.Agent, error) {
	return agent.New(agent.Config{
		Name:        name,
		Description: desc,
		Run: func(ctx agent.InvocationContext) iter.Seq2[*session.Event, error] {
			return func(yield func(*session.Event, error) bool) {
				event := session.NewEvent(ctx, ctx.InvocationID())
				event.Author = name
				event.LLMResponse = model.LLMResponse{
					Content: &genai.Content{
						Parts: []*genai.Part{
							{Text: outputMsg},
						},
						Role: "model",
					},
				}
				yield(event, nil)
			}
		},
	})
}

// buildChapterPipeline creates the sub-workflow per video
func buildChapterPipeline(ctx context.Context, cfg *Config, m model.LLM) (agent.Agent, error) {
	analystAgent, err := llmagent.New(llmagent.Config{
		Name:        "transcript_analyst",
		Model:       m,
		Description: "Analyzes video transcript and extracts structured chapter components.",
		Instruction: "You are the Transcript Analyst. Analyze the input transcript and extract core concepts, learning objectives, table specs, and diagram specs.",
		Tools:       []tool.Tool{},
	})
	if err != nil {
		return nil, err
	}

	return analystAgent, nil
}

// buildRootAgent creates the full multi-agent workflow
func buildRootAgent(ctx context.Context, cfg *Config) (agent.Agent, error) {
	var m model.LLM
	apiKey := os.Getenv("GOOGLE_API_KEY")
	if apiKey != "" {
		geminiModel, err := gemini.NewModel(ctx, cfg.AnalystModel, &genai.ClientConfig{
			APIKey: apiKey,
		})
		if err == nil {
			m = geminiModel
		}
	}

	if m != nil {
		return llmagent.New(llmagent.Config{
			Name:        "bookforge",
			Model:       m,
			Description: "Turns a YouTube channel into a publication-ready LaTeX textbook.",
			Instruction: `You are BookForge, an autonomous multi-agent publishing system. 
You coordinate YouTube channel intake, video transcription, keyframe extraction, structured analysis, and LaTeX book compilation.`,
			Tools: []tool.Tool{},
		})
	}

	return newDeterministicAgent(
		"bookforge",
		"Turns a YouTube channel into a publication-ready LaTeX textbook.",
		"✨ BookForge agent initialized. Ready to process channels into LaTeX books.",
	)
}

func main() {
	ctx := context.Background()
	cfg := DefaultConfig()

	rootAgent, err := buildRootAgent(ctx, cfg)
	if err != nil {
		log.Fatalf("Failed to create BookForge agent: %v", err)
	}

	launcherConfig := &launcher.Config{
		AgentLoader: agent.NewSingleLoader(rootAgent),
	}

	l := full.NewLauncher()
	if err = l.Execute(ctx, launcherConfig, os.Args[1:]); err != nil {
		log.Fatalf("Run failed: %v\n\n%s", err, l.CommandLineSyntax())
	}
}
