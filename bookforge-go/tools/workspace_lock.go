package tools

import (
	"sync"
)

// WorkspaceLock provides thread-safe access to workspace operations
// to prevent race conditions during parallel video processing
type WorkspaceLock struct {
	mu sync.Mutex
}

// NewWorkspaceLock creates a new workspace lock
func NewWorkspaceLock() *WorkspaceLock {
	return &WorkspaceLock{}
}

// Global lock manager for workspaces (keyed by workspace root)
var (
	workspaceLocks   = make(map[string]*WorkspaceLock)
	workspaceLocksRW sync.RWMutex
)

// GetWorkspaceLock returns or creates a lock for the given workspace path
func GetWorkspaceLock(workspaceRoot string) *WorkspaceLock {
	// Fast path: read lock to check if exists
	workspaceLocksRW.RLock()
	lock, exists := workspaceLocks[workspaceRoot]
	workspaceLocksRW.RUnlock()

	if exists {
		return lock
	}

	// Slow path: write lock to create
	workspaceLocksRW.Lock()
	defer workspaceLocksRW.Unlock()

	// Double-check in case another goroutine created it
	if lock, exists := workspaceLocks[workspaceRoot]; exists {
		return lock
	}

	// Create new lock
	lock = NewWorkspaceLock()
	workspaceLocks[workspaceRoot] = lock
	return lock
}

// SafeUpdateVideo updates a video record with automatic locking
func SafeUpdateVideo(ws *Workspace, videoID string, updates map[string]interface{}) (*ChannelManifest, error) {
	lock := GetWorkspaceLock(ws.Root)
	lock.mu.Lock()
	defer lock.mu.Unlock()

	// Load manifest
	manifest, err := ws.LoadManifest()
	if err != nil {
		return nil, err
	}

	// Find and update video
	var found bool
	for i := range manifest.Videos {
		if manifest.Videos[i].VideoID == videoID {
			// Apply updates
			if status, ok := updates["status"].(VideoStatus); ok {
				manifest.Videos[i].Status = status
			}
			if errorMsg, ok := updates["error"].(string); ok {
				manifest.Videos[i].Error = errorMsg
			}
			found = true
			break
		}
	}

	if !found {
		return nil, fmt.Errorf("video %s not found in manifest", videoID)
	}

	// Save manifest atomically
	if err := ws.SaveManifest(manifest); err != nil {
		return nil, err
	}

	return manifest, nil
}

// SafeLoadManifest loads manifest with read lock
func SafeLoadManifest(ws *Workspace) (*ChannelManifest, error) {
	lock := GetWorkspaceLock(ws.Root)
	lock.mu.Lock()
	defer lock.mu.Unlock()

	return ws.LoadManifest()
}

// SafeSaveManifest saves manifest with write lock
func SafeSaveManifest(ws *Workspace, manifest *ChannelManifest) error {
	lock := GetWorkspaceLock(ws.Root)
	lock.mu.Lock()
	defer lock.mu.Unlock()

	return ws.SaveManifest(manifest)
}
