package tools

import (
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"testing"
)

func TestHammingDistance(t *testing.T) {
	tests := []struct {
		hash1     string
		hash2     string
		wantDist  int
		wantError bool
	}{
		{"0000000000000000", "0000000000000000", 0, false},
		{"ffffffffffffffff", "0000000000000000", 64, false},
		{"abcdef1234567890", "abcdef1234567890", 0, false},
		{"abcdef1234567890", "abcdef1234567891", 1, false}, // last hex digit differs (1 bit: 0=0000, 1=0001)
		{"abc", "def", 0, true}, // different lengths
	}

	for _, tt := range tests {
		dist, err := HammingDistance(tt.hash1, tt.hash2)
		if tt.wantError {
			if err == nil {
				t.Errorf("HammingDistance(%q, %q) expected error, got nil", tt.hash1, tt.hash2)
			}
		} else {
			if err != nil {
				t.Errorf("HammingDistance(%q, %q) unexpected error: %v", tt.hash1, tt.hash2, err)
			}
			if dist != tt.wantDist {
				t.Errorf("HammingDistance(%q, %q) = %d, want %d", tt.hash1, tt.hash2, dist, tt.wantDist)
			}
		}
	}
}

func TestCopyFrame(t *testing.T) {
	tmpDir := t.TempDir()
	src := filepath.Join(tmpDir, "source.jpg")
	dest := filepath.Join(tmpDir, "dest", "copied.jpg")

	// Create a simple test image file
	testData := []byte("fake image data")
	if err := os.WriteFile(src, testData, 0644); err != nil {
		t.Fatalf("Failed to create source file: %v", err)
	}

	if err := CopyFrame(src, dest); err != nil {
		t.Fatalf("CopyFrame failed: %v", err)
	}

	// Verify destination file exists and has same content
	data, err := os.ReadFile(dest)
	if err != nil {
		t.Fatalf("Failed to read dest file: %v", err)
	}

	if string(data) != string(testData) {
		t.Errorf("Copied file content mismatch")
	}
}

func TestCopyFrameNonExistentSource(t *testing.T) {
	tmpDir := t.TempDir()
	src := filepath.Join(tmpDir, "nonexistent.jpg")
	dest := filepath.Join(tmpDir, "dest.jpg")

	err := CopyFrame(src, dest)
	if err == nil {
		t.Error("CopyFrame should fail for non-existent source")
	}
}

func TestFormatTimestamp(t *testing.T) {
	tests := []struct {
		input    float64
		expected string
	}{
		{0, "00:00"},
		{30, "00:30"},
		{60, "01:00"},
		{90, "01:30"},
		{3600, "60:00"},
		{3661, "61:01"},
	}

	for _, tt := range tests {
		result := FormatTimestamp(tt.input)
		if result != tt.expected {
			t.Errorf("FormatTimestamp(%v) = %q, want %q", tt.input, result, tt.expected)
		}
	}
}

func TestRelativePath(t *testing.T) {
	tests := []struct {
		path  string
		root  string
		expected string
	}{
		{"/home/user/project/data/channel/video.mp4", "/home/user/project", "data/channel/video.mp4"},
		{"C:\\project\\data\\channel\\video.mp4", "C:\\project", "data/channel/video.mp4"},
		{"/a/b/c", "/a/b", "c"},
		{"/a/b", "/a/b", "."},
	}

	for _, tt := range tests {
		result := RelativePath(tt.path, tt.root)
		if result != tt.expected {
			t.Errorf("RelativePath(%q, %q) = %q, want %q", tt.path, tt.root, result, tt.expected)
		}
	}
}

// Test image analysis functions with a synthetic image
func TestImageAnalysis(t *testing.T) {
	// Create a simple test image
	tmpDir := t.TempDir()
	imgPath := filepath.Join(tmpDir, "test.png")

	// Create a 100x100 gray image
	img := image.NewGray(image.Rect(0, 0, 100, 100))
	for y := 0; y < 100; y++ {
		for x := 0; x < 100; x++ {
			// Gradient pattern
			val := uint8((x + y) % 256)
			img.SetGray(x, y, color.Gray{Y: val})
		}
	}

	f, err := os.Create(imgPath)
	if err != nil {
		t.Fatalf("Failed to create test image: %v", err)
	}
	if err := png.Encode(f, img); err != nil {
		t.Fatalf("Failed to encode test image: %v", err)
	}
	f.Close()

	// Test Sharpness
	sharpness, err := Sharpness(imgPath)
	if err != nil {
		t.Logf("Sharpness error (may be expected): %v", err)
	} else {
		t.Logf("Sharpness: %f", sharpness)
		if sharpness < 0 {
			t.Error("Sharpness should be non-negative")
		}
	}

	// Test Brightness
	brightness, err := Brightness(imgPath)
	if err != nil {
		t.Fatalf("Brightness error: %v", err)
	}
	t.Logf("Brightness: %f", brightness)
	if brightness < 0 || brightness > 255 {
		t.Error("Brightness should be in range 0-255")
	}

	// Test Contrast
	contrast, err := Contrast(imgPath)
	if err != nil {
		t.Fatalf("Contrast error: %v", err)
	}
	t.Logf("Contrast: %f", contrast)
	if contrast < 0 {
		t.Error("Contrast should be non-negative")
	}

	// Test PHashImage
	phash, err := PHashImage(imgPath)
	if err != nil {
		t.Fatalf("PHashImage error: %v", err)
	}
	t.Logf("PHash: %s", phash)
	if len(phash) != 16 {
		t.Errorf("PHash should be 16 hex chars, got %d", len(phash))
	}

	// Test HammingDistance with same image
	dist, err := HammingDistance(phash, phash)
	if err != nil {
		t.Fatalf("HammingDistance error: %v", err)
	}
	if dist != 0 {
		t.Errorf("HammingDistance of same hash should be 0, got %d", dist)
	}
}

func TestDedupeFrames(t *testing.T) {
	tmpDir := t.TempDir()

	// Create some test frame files
	framePaths := make([]string, 5)
	for i := 0; i < 5; i++ {
		path := filepath.Join(tmpDir, "frame_"+string(rune('0'+i))+".jpg")
		// Write different content for each frame
		data := []byte("frame content " + string(rune('0'+i)))
		if err := os.WriteFile(path, data, 0644); err != nil {
			t.Fatalf("Failed to create frame %d: %v", i, err)
		}
		framePaths[i] = path
	}

	// Test deduplication with interval 5, threshold 6
	assets, err := DedupeFrames(framePaths, 5, 6)
	if err != nil {
		t.Fatalf("DedupeFrames error: %v", err)
	}

	// All frames have different content, so all should be kept
	if len(assets) != 5 {
		t.Errorf("Expected 5 unique frames, got %d", len(assets))
	}

	// Test with duplicate frames
	dupPaths := append(framePaths, framePaths[0]) // Add duplicate of first frame
	assets2, err := DedupeFrames(dupPaths, 5, 6)
	if err != nil {
		t.Fatalf("DedupeFrames error: %v", err)
	}
	// Should still be 5 unique frames
	if len(assets2) != 5 {
		t.Errorf("Expected 5 unique frames with duplicate, got %d", len(assets2))
	}
}

func TestCurateFrames(t *testing.T) {
	assets := []FrameAsset{
		{File: "frame_0.jpg", TimestampSec: 0, PHash: "hash0"},
		{File: "frame_1.jpg", TimestampSec: 5, PHash: "hash1"},
		{File: "frame_2.jpg", TimestampSec: 10, PHash: "hash2"},
		{File: "frame_3.jpg", TimestampSec: 15, PHash: "hash3"},
		{File: "frame_4.jpg", TimestampSec: 20, PHash: "hash4"},
	}

	// Test with maxFrames >= len(assets)
	curated, err := CurateFrames(assets, "", "", 10)
	if err != nil {
		t.Fatalf("CurateFrames error: %v", err)
	}
	if len(curated) != 5 {
		t.Errorf("Expected 5 frames, got %d", len(curated))
	}

	// Test with maxFrames < len(assets)
	curated2, err := CurateFrames(assets, "", "", 3)
	if err != nil {
		t.Fatalf("CurateFrames error: %v", err)
	}
	if len(curated2) != 3 {
		t.Errorf("Expected 3 frames, got %d", len(curated2))
	}
	// Should be evenly spaced (algorithm: step = len/maxFrames = 5/3 = 1.66)
	// indices: 0*1.66=0, 1*1.66=1, 2*1.66=3
	if curated2[0].TimestampSec != 0 {
		t.Errorf("First frame should be at 0s, got %f", curated2[0].TimestampSec)
	}
	if curated2[2].TimestampSec != 15 {
		t.Errorf("Last frame should be at 15s (index 3), got %f", curated2[2].TimestampSec)
	}
}