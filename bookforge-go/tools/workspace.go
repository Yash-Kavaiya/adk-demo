package tools

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
)

// VideoStatus represents the processing status of a video
type VideoStatus string

const (
	StatusPending  VideoStatus = "pending"
	StatusMedia    VideoStatus = "media"
	StatusAnalyzed VideoStatus = "analyzed"
	StatusAssets   VideoStatus = "assets"
	StatusWritten  VideoStatus = "written"
	StatusVerified VideoStatus = "verified"
	StatusFailed   VideoStatus = "failed"
)

// VideoRecord represents a single video in the channel manifest
type VideoRecord struct {
	VideoID       string      `json:"video_id"`
	Title         string      `json:"title"`
	URL           string      `json:"url"`
	DurationSec   int         `json:"duration_sec"`
	UploadDate    string      `json:"upload_date"`
	ChapterNumber int         `json:"chapter_number"`
	Status        VideoStatus `json:"status"`
	Error         string      `json:"error,omitempty"`
}

// ChannelManifest represents the entire channel processing state
type ChannelManifest struct {
	ChannelURL   string         `json:"channel_url"`
	ChannelTitle string         `json:"channel_title"`
	ChannelSlug  string         `json:"channel_slug"`
	CreatedAt    string         `json:"created_at"`
	Videos       []*VideoRecord `json:"videos"`
}

// Workspace manages the filesystem structure for BookForge
type Workspace struct {
	Root         string
	ChannelSlug  string
	VideosDir    string
	ChaptersDir  string
	BuildDir     string
	BookDir      string
	ManifestPath string
}

// NewWorkspace creates a new workspace manager
func NewWorkspace(root, channelSlug string) (*Workspace, error) {
	wsRoot := filepath.Join(root, channelSlug)
	
	ws := &Workspace{
		Root:         wsRoot,
		ChannelSlug:  channelSlug,
		VideosDir:    filepath.Join(wsRoot, "videos"),
		ChaptersDir:  filepath.Join(wsRoot, "chapters"),
		BuildDir:     filepath.Join(wsRoot, "build"),
		BookDir:      filepath.Join(wsRoot, "book"),
		ManifestPath: filepath.Join(wsRoot, "manifest.json"),
	}

	// Create directory structure
	dirs := []string{
		ws.Root,
		ws.VideosDir,
		ws.ChaptersDir,
		ws.BuildDir,
		ws.BookDir,
	}

	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0755); err != nil {
			return nil, fmt.Errorf("failed to create directory %s: %w", dir, err)
		}
	}

	return ws, nil
}

// ManifestExists checks if the manifest file exists
func (ws *Workspace) ManifestExists() bool {
	_, err := os.Stat(ws.ManifestPath)
	return err == nil
}

// LoadManifest loads the channel manifest from disk
func (ws *Workspace) LoadManifest() (*ChannelManifest, error) {
	data, err := os.ReadFile(ws.ManifestPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read manifest: %w", err)
	}

	var manifest ChannelManifest
	if err := json.Unmarshal(data, &manifest); err != nil {
		return nil, fmt.Errorf("failed to parse manifest: %w", err)
	}

	return &manifest, nil
}

// SaveManifest saves the channel manifest to disk atomically
func (ws *Workspace) SaveManifest(manifest *ChannelManifest) error {
	data, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal manifest: %w", err)
	}

	// Atomic write using temp file
	tmpPath := ws.ManifestPath + ".tmp"
	if err := os.WriteFile(tmpPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write temp manifest: %w", err)
	}

	if err := os.Rename(tmpPath, ws.ManifestPath); err != nil {
		os.Remove(tmpPath) // cleanup on error
		return fmt.Errorf("failed to rename manifest: %w", err)
	}

	return nil
}

// InitManifest creates a new manifest
func (ws *Workspace) InitManifest(channelURL, channelTitle, slug string) (*ChannelManifest, error) {
	manifest := &ChannelManifest{
		ChannelURL:   channelURL,
		ChannelTitle: channelTitle,
		ChannelSlug:  slug,
		CreatedAt:    time.Now().UTC().Format(time.RFC3339),
		Videos:       make([]*VideoRecord, 0),
	}

	if err := ws.SaveManifest(manifest); err != nil {
		return nil, err
	}

	return manifest, nil
}

// UpdateVideo updates a video record in the manifest
func (ws *Workspace) UpdateVideo(videoID string, updates map[string]interface{}) error {
	manifest, err := ws.LoadManifest()
	if err != nil {
		return err
	}

	var found *VideoRecord
	for _, v := range manifest.Videos {
		if v.VideoID == videoID {
			found = v
			break
		}
	}

	if found == nil {
		return fmt.Errorf("video %s not found in manifest", videoID)
	}

	// Apply updates
	if status, ok := updates["status"].(string); ok {
		found.Status = VideoStatus(status)
	}
	if err, ok := updates["error"].(string); ok {
		found.Error = err
	}

	return ws.SaveManifest(manifest)
}

// PendingVideos returns all videos not yet verified
func (ws *Workspace) PendingVideos() ([]*VideoRecord, error) {
	manifest, err := ws.LoadManifest()
	if err != nil {
		return nil, err
	}

	pending := make([]*VideoRecord, 0)
	for _, v := range manifest.Videos {
		if v.Status != StatusVerified {
			pending = append(pending, v)
		}
	}

	return pending, nil
}

// VideoDir returns the directory for a specific video
func (ws *Workspace) VideoDir(videoID string) string {
	dir := filepath.Join(ws.VideosDir, videoID)
	os.MkdirAll(dir, 0755)
	return dir
}

// ChapterDir returns the directory for a specific chapter
func (ws *Workspace) ChapterDir(record *VideoRecord) string {
	slug := Slugify(record.Title, 48)
	dirName := fmt.Sprintf("%02d_%s", record.ChapterNumber, slug)
	dir := filepath.Join(ws.ChaptersDir, dirName)
	
	// Create subdirectories
	os.MkdirAll(dir, 0755)
	os.MkdirAll(filepath.Join(dir, "figures"), 0755)
	os.MkdirAll(filepath.Join(dir, "tables"), 0755)
	
	return dir
}

// WriteText writes text to a file atomically
func WriteText(path, content string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	tmpPath := path + ".tmp"
	if err := os.WriteFile(tmpPath, []byte(content), 0644); err != nil {
		return err
	}

	if err := os.Rename(tmpPath, path); err != nil {
		os.Remove(tmpPath)
		return err
	}

	return nil
}

// Slugify converts text to a filesystem-safe slug
func Slugify(text string, maxLen int) string {
	// Convert to lowercase
	slug := strings.ToLower(text)
	
	// Replace non-alphanumeric with hyphens
	re := regexp.MustCompile(`[^a-z0-9]+`)
	slug = re.ReplaceAllString(slug, "-")
	
	// Trim leading/trailing hyphens
	slug = strings.Trim(slug, "-")
	
	// Limit length
	if len(slug) > maxLen {
		slug = slug[:maxLen]
	}
	slug = strings.TrimRight(slug, "-")
	
	if slug == "" {
		slug = "untitled"
	}
	
	return slug
}

// ByID finds a video record by ID
func (m *ChannelManifest) ByID(videoID string) *VideoRecord {
	for _, v := range m.Videos {
		if v.VideoID == videoID {
			return v
		}
	}
	return nil
}

// AddVideo adds a video to the manifest
func (m *ChannelManifest) AddVideo(record *VideoRecord) {
	m.Videos = append(m.Videos, record)
}
