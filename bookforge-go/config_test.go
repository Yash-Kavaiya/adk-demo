package main

import (
	"os"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.AnalystModel == "" {
		t.Error("AnalystModel should have default value")
	}
	if cfg.WriterModel == "" {
		t.Error("WriterModel should have default value")
	}
	if cfg.CriticModel == "" {
		t.Error("CriticModel should have default value")
	}
	if cfg.WorkspaceRoot != "data" {
		t.Errorf("WorkspaceRoot default = %q, want \"data\"", cfg.WorkspaceRoot)
	}
	if cfg.MaxVideos != 0 {
		t.Errorf("MaxVideos default = %d, want 0", cfg.MaxVideos)
	}
	if !cfg.CompileLaTeX {
		t.Error("CompileLaTeX default should be true")
	}
	if cfg.EnableParallelVideos {
		t.Error("EnableParallelVideos default should be false")
	}
	if cfg.MaxConcurrentVideos != 1 {
		t.Errorf("MaxConcurrentVideos default = %d, want 1", cfg.MaxConcurrentVideos)
	}
}

func TestLoadConfigFromEnv(t *testing.T) {
	// Save original env
	origEnv := map[string]string{}
	envVars := []string{
		"BOOKFORGE_ANALYST_MODEL",
		"BOOKFORGE_WRITER_MODEL",
		"BOOKFORGE_CRITIC_MODEL",
		"BOOKFORGE_WORKSPACE_ROOT",
		"BOOKFORGE_MAX_VIDEOS",
		"BOOKFORGE_COMPILE_LATEX",
		"BOOKFORGE_ENABLE_PARALLEL_VIDEOS",
		"BOOKFORGE_MAX_CONCURRENT_VIDEOS",
	}
	for _, v := range envVars {
		origEnv[v] = os.Getenv(v)
	}

	// Set test env
	os.Setenv("BOOKFORGE_ANALYST_MODEL", "test-analyst")
	os.Setenv("BOOKFORGE_WRITER_MODEL", "test-writer")
	os.Setenv("BOOKFORGE_CRITIC_MODEL", "test-critic")
	os.Setenv("BOOKFORGE_WORKSPACE_ROOT", "/custom/workspace")
	os.Setenv("BOOKFORGE_MAX_VIDEOS", "5")
	os.Setenv("BOOKFORGE_COMPILE_LATEX", "false")
	os.Setenv("BOOKFORGE_ENABLE_PARALLEL_VIDEOS", "true")
	os.Setenv("BOOKFORGE_MAX_CONCURRENT_VIDEOS", "3")

	// Load config
	cfg := LoadConfigFromEnv()

	// Restore original env
	for _, v := range envVars {
		if origEnv[v] == "" {
			os.Unsetenv(v)
		} else {
			os.Setenv(v, origEnv[v])
		}
	}

	// Verify
	if cfg.AnalystModel != "test-analyst" {
		t.Errorf("AnalystModel = %q, want \"test-analyst\"", cfg.AnalystModel)
	}
	if cfg.WriterModel != "test-writer" {
		t.Errorf("WriterModel = %q, want \"test-writer\"", cfg.WriterModel)
	}
	if cfg.CriticModel != "test-critic" {
		t.Errorf("CriticModel = %q, want \"test-critic\"", cfg.CriticModel)
	}
	if cfg.WorkspaceRoot != "/custom/workspace" {
		t.Errorf("WorkspaceRoot = %q, want \"/custom/workspace\"", cfg.WorkspaceRoot)
	}
	if cfg.MaxVideos != 5 {
		t.Errorf("MaxVideos = %d, want 5", cfg.MaxVideos)
	}
	if cfg.CompileLaTeX {
		t.Error("CompileLaTeX should be false")
	}
	if !cfg.EnableParallelVideos {
		t.Error("EnableParallelVideos should be true")
	}
	if cfg.MaxConcurrentVideos != 3 {
		t.Errorf("MaxConcurrentVideos = %d, want 3", cfg.MaxConcurrentVideos)
	}
}

func TestValidateConfig(t *testing.T) {
	tests := []struct {
		name        string
		cfg         *Config
		wantError   bool
		errorContains string
	}{
		{
			name: "valid config",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "model2",
				CriticModel:          "model3",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  2,
			},
			wantError: false,
		},
		{
			name: "empty workspace_root",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "model2",
				CriticModel:          "model3",
				WorkspaceRoot:        "",
				MaxConcurrentVideos:  2,
			},
			wantError:     true,
			errorContains: "workspace_root cannot be empty",
		},
		{
			name: "empty analyst_model",
			cfg: &Config{
				AnalystModel:         "",
				WriterModel:          "model2",
				CriticModel:          "model3",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  2,
			},
			wantError:     true,
			errorContains: "analyst_model cannot be empty",
		},
		{
			name: "empty writer_model",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "",
				CriticModel:          "model3",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  2,
			},
			wantError:     true,
			errorContains: "writer_model cannot be empty",
		},
		{
			name: "empty critic_model",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "model2",
				CriticModel:          "",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  2,
			},
			wantError:     true,
			errorContains: "critic_model cannot be empty",
		},
		{
			name: "zero max_concurrent_videos",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "model2",
				CriticModel:          "model3",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  0,
			},
			wantError:     true,
			errorContains: "max_concurrent_videos must be at least 1",
		},
		{
			name: "negative max_concurrent_videos",
			cfg: &Config{
				AnalystModel:         "model1",
				WriterModel:          "model2",
				CriticModel:          "model3",
				WorkspaceRoot:        "/workspace",
				MaxConcurrentVideos:  -1,
			},
			wantError:     true,
			errorContains: "max_concurrent_videos must be at least 1",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.cfg.Validate()
			if tt.wantError {
				if err == nil {
					t.Error("Expected error, got nil")
				} else if tt.errorContains != "" && !containsString(err.Error(), tt.errorContains) {
					t.Errorf("Error message %q does not contain %q", err.Error(), tt.errorContains)
				}
			} else {
				if err != nil {
					t.Errorf("Unexpected error: %v", err)
				}
			}
		})
	}
}

func containsString(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > len(substr) && (s[:len(substr)] == substr || containsString(s[1:], substr)))
}