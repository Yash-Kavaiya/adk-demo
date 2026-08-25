package main

import (
	"fmt"
	"os"
	"strconv"
)

// Config holds BookForge configuration settings with parallel support
type Config struct {
	// Model configuration
	AnalystModel string
	WriterModel  string
	CriticModel  string

	// Workspace
	WorkspaceRoot string
	MaxVideos     int
	CompileLaTeX  bool

	// Parallelization (safe defaults)
	EnableParallelVideos bool
	MaxConcurrentVideos  int
}

// DefaultConfig returns default configuration (sequential mode for safety)
func DefaultConfig() *Config {
	return &Config{
		AnalystModel:         "gemini-2.0-flash-exp",
		WriterModel:          "gemini-exp-1206",
		CriticModel:          "gemini-2.0-flash-exp",
		WorkspaceRoot:        "data",
		MaxVideos:            0,
		CompileLaTeX:         true,
		EnableParallelVideos: false, // OFF by default (safe)
		MaxConcurrentVideos:  1,     // Sequential by default
	}
}

// LoadConfigFromEnv loads configuration from environment variables
func LoadConfigFromEnv() *Config {
	cfg := DefaultConfig()

	// Model settings
	if val := os.Getenv("BOOKFORGE_ANALYST_MODEL"); val != "" {
		cfg.AnalystModel = val
	}
	if val := os.Getenv("BOOKFORGE_WRITER_MODEL"); val != "" {
		cfg.WriterModel = val
	}
	if val := os.Getenv("BOOKFORGE_CRITIC_MODEL"); val != "" {
		cfg.CriticModel = val
	}

	// Workspace settings
	if val := os.Getenv("BOOKFORGE_WORKSPACE_ROOT"); val != "" {
		cfg.WorkspaceRoot = val
	}
	if val := os.Getenv("BOOKFORGE_MAX_VIDEOS"); val != "" {
		if maxVids, err := strconv.Atoi(val); err == nil {
			cfg.MaxVideos = maxVids
		}
	}
	if val := os.Getenv("BOOKFORGE_COMPILE_LATEX"); val != "" {
		cfg.CompileLaTeX = val == "true" || val == "1"
	}

	// Parallelization settings
	if val := os.Getenv("BOOKFORGE_ENABLE_PARALLEL_VIDEOS"); val != "" {
		cfg.EnableParallelVideos = val == "true" || val == "1"
	}
	if val := os.Getenv("BOOKFORGE_MAX_CONCURRENT_VIDEOS"); val != "" {
		if maxConcurrent, err := strconv.Atoi(val); err == nil && maxConcurrent > 0 {
			cfg.MaxConcurrentVideos = maxConcurrent
		}
	}

	return cfg
}

// Validate checks configuration for errors
func (c *Config) Validate() error {
	if c.WorkspaceRoot == "" {
		return fmt.Errorf("workspace_root cannot be empty")
	}
	if c.AnalystModel == "" {
		return fmt.Errorf("analyst_model cannot be empty")
	}
	if c.WriterModel == "" {
		return fmt.Errorf("writer_model cannot be empty")
	}
	if c.CriticModel == "" {
		return fmt.Errorf("critic_model cannot be empty")
	}
	if c.MaxConcurrentVideos < 1 {
		return fmt.Errorf("max_concurrent_videos must be at least 1")
	}
	return nil
}
