package tools

import (
	"fmt"
	"path/filepath"
)

// ExtractFrames extracts frames from video at specified interval
// TODO: Implement using ffmpeg Go bindings
func ExtractFrames(videoPath, outDir string, intervalSec int) ([]string, error) {
	return nil, fmt.Errorf("frame extraction not yet implemented")
}

// DedupeFrames removes duplicate frames using perceptual hashing
// TODO: Implement using Go image hashing library
func DedupeFrames(framePaths []string, intervalSec, hashThreshold int) ([]FrameAsset, error) {
	return nil, fmt.Errorf("frame deduplication not yet implemented")
}

// CurateFrames selects frames spread across the timeline
func CurateFrames(assets []FrameAsset, srcDir, destDir string, maxFrames int) ([]FrameAsset, error) {
	// Placeholder: evenly space frames across timeline
	if len(assets) <= maxFrames {
		// Copy all frames
		curated := make([]FrameAsset, len(assets))
		for i, asset := range assets {
			newName := fmt.Sprintf("frame_%02d_%ds.jpg", i+1, int(asset.TimestampSec))
			curated[i] = FrameAsset{
				File:         newName,
				TimestampSec: asset.TimestampSec,
				PHash:        asset.PHash,
			}
		}
		return curated, nil
	}

	// Select evenly spaced subset
	step := float64(len(assets)) / float64(maxFrames)
	curated := make([]FrameAsset, maxFrames)
	for i := 0; i < maxFrames; i++ {
		idx := int(float64(i) * step)
		if idx >= len(assets) {
			idx = len(assets) - 1
		}
		asset := assets[idx]
		newName := fmt.Sprintf("frame_%02d_%ds.jpg", i+1, int(asset.TimestampSec))
		curated[i] = FrameAsset{
			File:         newName,
			TimestampSec: asset.TimestampSec,
			PHash:        asset.PHash,
		}
	}

	return curated, nil
}

// Sharpness calculates image sharpness (blur detection)
func Sharpness(imagePath string) (float64, error) {
	return 0, fmt.Errorf("sharpness calculation not yet implemented")
}

// Brightness calculates average image brightness
func Brightness(imagePath string) (float64, error) {
	return 0, fmt.Errorf("brightness calculation not yet implemented")
}

// Contrast calculates image contrast (stddev of luminance)
func Contrast(imagePath string) (float64, error) {
	return 0, fmt.Errorf("contrast calculation not yet implemented")
}

// PHashImage calculates perceptual hash of an image
func PHashImage(imagePath string) (string, error) {
	return "", fmt.Errorf("perceptual hashing not yet implemented")
}

// HammingDistance calculates hamming distance between two hashes
func HammingDistance(hash1, hash2 string) (int, error) {
	if len(hash1) != len(hash2) {
		return 0, fmt.Errorf("hash lengths differ")
	}
	
	distance := 0
	for i := 0; i < len(hash1); i++ {
		if hash1[i] != hash2[i] {
			distance++
		}
	}
	return distance, nil
}

// CopyFrame copies a frame file to destination
func CopyFrame(src, dest string) error {
	// TODO: Implement file copy
	return fmt.Errorf("frame copy not yet implemented")
}

// FormatTimestamp formats seconds as MM:SS
func FormatTimestamp(seconds float64) string {
	total := int(seconds)
	minutes := total / 60
	secs := total % 60
	return fmt.Sprintf("%02d:%02d", minutes, secs)
}

// RelativePath returns path relative to workspace root
func RelativePath(path, root string) string {
	rel, err := filepath.Rel(root, path)
	if err != nil {
		return path
	}
	return filepath.ToSlash(rel)
}
