package tools

import (
	"os"
	"path/filepath"
	"testing"
)

func TestWorkspaceManifestRoundtrip(t *testing.T) {
	tmpDir := t.TempDir()
	ws, err := NewWorkspace(tmpDir, "test-channel")
	if err != nil {
		t.Fatalf("Failed to create workspace: %v", err)
	}

	// Initialize manifest
	manifest := &ChannelManifest{
		ChannelURL:   "https://youtube.com/@test",
		ChannelTitle: "Test Channel",
		ChannelSlug:  "test-channel",
		CreatedAt:    "2024-01-01T00:00:00Z",
		Videos:       make([]*VideoRecord, 0),
	}

	if err := ws.SaveManifest(manifest); err != nil {
		t.Fatalf("Failed to save manifest: %v", err)
	}

	// Load manifest
	loaded, err := ws.LoadManifest()
	if err != nil {
		t.Fatalf("Failed to load manifest: %v", err)
	}

	if loaded.ChannelURL != manifest.ChannelURL {
		t.Errorf("ChannelURL mismatch: got %s, want %s", loaded.ChannelURL, manifest.ChannelURL)
	}
	if loaded.ChannelTitle != manifest.ChannelTitle {
		t.Errorf("ChannelTitle mismatch: got %s, want %s", loaded.ChannelTitle, manifest.ChannelTitle)
	}
}

func TestWorkspaceUpdateVideo(t *testing.T) {
	tmpDir := t.TempDir()
	ws, err := NewWorkspace(tmpDir, "test-channel")
	if err != nil {
		t.Fatalf("Failed to create workspace: %v", err)
	}

	// Initialize manifest with a video
	manifest := &ChannelManifest{
		ChannelURL:   "https://youtube.com/@test",
		ChannelTitle: "Test Channel",
		ChannelSlug:  "test-channel",
		CreatedAt:    "2024-01-01T00:00:00Z",
		Videos: []*VideoRecord{
			{
				VideoID:       "video_1",
				Title:         "Test Video 1",
				URL:           "https://youtu.be/video_1",
				DurationSec:   300,
				ChapterNumber: 1,
				Status:        StatusPending,
			},
		},
	}

	if err := ws.SaveManifest(manifest); err != nil {
		t.Fatalf("Failed to save manifest: %v", err)
	}

	// Update video status
	if err := ws.UpdateVideo("video_1", map[string]interface{}{"status": string(StatusMedia)}); err != nil {
		t.Fatalf("Failed to update video: %v", err)
	}

	// Verify update
	loaded, err := ws.LoadManifest()
	if err != nil {
		t.Fatalf("Failed to load manifest: %v", err)
	}

	record := loaded.ByID("video_1")
	if record == nil {
		t.Fatal("Video not found")
	}
	if record.Status != StatusMedia {
		t.Errorf("Status mismatch: got %s, want %s", record.Status, StatusMedia)
	}
}

func TestWorkspacePendingVideos(t *testing.T) {
	tmpDir := t.TempDir()
	ws, err := NewWorkspace(tmpDir, "test-channel")
	if err != nil {
		t.Fatalf("Failed to create workspace: %v", err)
	}

	manifest := &ChannelManifest{
		ChannelURL:   "https://youtube.com/@test",
		ChannelTitle: "Test Channel",
		ChannelSlug:  "test-channel",
		CreatedAt:    "2024-01-01T00:00:00Z",
		Videos: []*VideoRecord{
			{VideoID: "v1", Title: "V1", URL: "u1", ChapterNumber: 1, Status: StatusPending},
			{VideoID: "v2", Title: "V2", URL: "u2", ChapterNumber: 2, Status: StatusVerified},
			{VideoID: "v3", Title: "V3", URL: "u3", ChapterNumber: 3, Status: StatusWritten},
			{VideoID: "v4", Title: "V4", URL: "u4", ChapterNumber: 4, Status: StatusFailed},
		},
	}

	if err := ws.SaveManifest(manifest); err != nil {
		t.Fatalf("Failed to save manifest: %v", err)
	}

	pending, err := ws.PendingVideos()
	if err != nil {
		t.Fatalf("Failed to get pending videos: %v", err)
	}

	// Should return v1 (pending), v3 (written), v4 (failed) - all except v2 (verified)
	if len(pending) != 3 {
		t.Errorf("Expected 3 pending videos (all except verified), got %d", len(pending))
	}
}

func TestWorkspaceChapterDir(t *testing.T) {
	tmpDir := t.TempDir()
	ws, err := NewWorkspace(tmpDir, "test-channel")
	if err != nil {
		t.Fatalf("Failed to create workspace: %v", err)
	}

	record := &VideoRecord{
		VideoID:       "video_1",
		Title:         "Test Video",
		URL:           "https://youtu.be/video_1",
		DurationSec:   300,
		ChapterNumber: 1,
		Status:        StatusPending,
	}

	chapterDir := ws.ChapterDir(record)
	if chapterDir == "" {
		t.Fatal("ChapterDir returned empty path")
	}

	// Check subdirectories exist
	figuresDir := filepath.Join(chapterDir, "figures")
	tablesDir := filepath.Join(chapterDir, "tables")

	if _, err := os.Stat(figuresDir); os.IsNotExist(err) {
		t.Errorf("Figures directory not created: %s", figuresDir)
	}
	if _, err := os.Stat(tablesDir); os.IsNotExist(err) {
		t.Errorf("Tables directory not created: %s", tablesDir)
	}
}

func TestSlugify(t *testing.T) {
	tests := []struct {
		input    string
		maxLen   int
		expected string
	}{
		{"My Channel!", 48, "my-channel"},
		{"Test Channel (2024)", 48, "test-channel-2024"},
		{"###", 48, "untitled"},
		{"A Very Long Channel Name That Exceeds The Maximum Length Limit", 20, "a-very-long-channel"},
		{"UPPERCASE channel", 48, "uppercase-channel"},
		{"channel-with-dashes", 48, "channel-with-dashes"},
	}

	for _, tt := range tests {
		result := Slugify(tt.input, tt.maxLen)
		if result != tt.expected {
			t.Errorf("Slugify(%q, %d) = %q, want %q", tt.input, tt.maxLen, result, tt.expected)
		}
	}
}

func TestWriteText(t *testing.T) {
	tmpDir := t.TempDir()
	filePath := filepath.Join(tmpDir, "subdir", "test.txt")

	err := WriteText(filePath, "Hello, World!")
	if err != nil {
		t.Fatalf("WriteText failed: %v", err)
	}

	data, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("Failed to read file: %v", err)
	}

	if string(data) != "Hello, World!" {
		t.Errorf("File content mismatch: got %q, want %q", string(data), "Hello, World!")
	}
}

func TestManifestByID(t *testing.T) {
	manifest := &ChannelManifest{
		ChannelURL: "https://youtube.com/@test",
		ChannelSlug: "test-channel",
		Videos: []*VideoRecord{
			{VideoID: "video_1", Title: "Video 1", URL: "u1"},
			{VideoID: "video_2", Title: "Video 2", URL: "u2"},
		},
	}

	found := manifest.ByID("video_1")
	if found == nil {
		t.Fatal("ByID failed to find existing video")
	}
	if found.Title != "Video 1" {
		t.Errorf("Wrong video returned: %s", found.Title)
	}

	notFound := manifest.ByID("video_999")
	if notFound != nil {
		t.Error("ByID should return nil for non-existent video")
	}
}

func TestManifestAddVideo(t *testing.T) {
	manifest := &ChannelManifest{
		ChannelURL: "https://youtube.com/@test",
		ChannelSlug: "test-channel",
		Videos: make([]*VideoRecord, 0),
	}

	manifest.AddVideo(&VideoRecord{
		VideoID:       "video_1",
		Title:         "Video 1",
		URL:           "u1",
		ChapterNumber: 1,
	})

	if len(manifest.Videos) != 1 {
		t.Errorf("Expected 1 video, got %d", len(manifest.Videos))
	}
	if manifest.Videos[0].VideoID != "video_1" {
		t.Errorf("Wrong video ID: %s", manifest.Videos[0].VideoID)
	}
}