package tools

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"image"
	"image/color"
	_ "image/jpeg"
	"math"
	"os"
	"os/exec"
	"path/filepath"
)

// ExtractFrames extracts frames from video at specified interval using ffmpeg
func ExtractFrames(videoPath, outDir string, intervalSec int) ([]string, error) {
	os.MkdirAll(outDir, 0755)
	pattern := filepath.Join(outDir, "raw_%04d.jpg")
	fps := fmt.Sprintf("1/%d", intervalSec)

	cmd := exec.Command("ffmpeg",
		"-y",
		"-i", videoPath,
		"-vf", fmt.Sprintf("fps=%s", fps),
		"-q:v", "2",
		pattern,
	)
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("ffmpeg frame extraction error: %w", err)
	}

	matches, err := filepath.Glob(filepath.Join(outDir, "raw_*.jpg"))
	return matches, err
}

// DedupeFrames removes duplicate frames using fast hashing
func DedupeFrames(framePaths []string, intervalSec, hashThreshold int) ([]FrameAsset, error) {
	var assets []FrameAsset
	seen := make(map[string]bool)

	for i, p := range framePaths {
		data, err := os.ReadFile(p)
		if err != nil {
			continue
		}
		h := sha256.Sum256(data)
		hashStr := hex.EncodeToString(h[:8])

		if !seen[hashStr] {
			seen[hashStr] = true
			assets = append(assets, FrameAsset{
				File:         p,
				TimestampSec: float64(i * intervalSec),
				PHash:        hashStr,
			})
		}
	}
	return assets, nil
}

// CurateFrames selects frames spread across the timeline
func CurateFrames(assets []FrameAsset, srcDir, destDir string, maxFrames int) ([]FrameAsset, error) {
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

// Sharpness calculates image sharpness using Laplacian variance
func Sharpness(imagePath string) (float64, error) {
	img, err := loadImage(imagePath)
	if err != nil {
		return 0, err
	}

	// Convert to grayscale and compute Laplacian variance
	bounds := img.Bounds()
	var sum, sumSq float64
	count := 0

	for y := 1; y < bounds.Max.Y-1; y++ {
		for x := 1; x < bounds.Max.X-1; x++ {
			// Simple Laplacian kernel: center*4 - top - bottom - left - right
			center := luminance(img.At(x, y))
			top := luminance(img.At(x, y-1))
			bottom := luminance(img.At(x, y+1))
			left := luminance(img.At(x-1, y))
			right := luminance(img.At(x+1, y))

			laplacian := 4*center - top - bottom - left - right
			sum += laplacian
			sumSq += laplacian * laplacian
			count++
		}
	}

	if count == 0 {
		return 0, nil
	}

	mean := sum / float64(count)
	variance := sumSq/float64(count) - mean*mean
	return variance, nil
}

// Brightness calculates average image brightness (0-255)
func Brightness(imagePath string) (float64, error) {
	img, err := loadImage(imagePath)
	if err != nil {
		return 0, err
	}

	bounds := img.Bounds()
	var sum float64
	count := 0

	for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			sum += luminance(img.At(x, y))
			count++
		}
	}

	if count == 0 {
		return 0, nil
	}
	return sum / float64(count), nil
}

// Contrast calculates image contrast (standard deviation of luminance)
func Contrast(imagePath string) (float64, error) {
	img, err := loadImage(imagePath)
	if err != nil {
		return 0, err
	}

	bounds := img.Bounds()
	var sum, sumSq float64
	count := 0

	for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			l := luminance(img.At(x, y))
			sum += l
			sumSq += l * l
			count++
		}
	}

	if count == 0 {
		return 0, nil
	}

	mean := sum / float64(count)
	variance := sumSq/float64(count) - mean*mean
	return math.Sqrt(variance), nil
}

// PHashImage calculates perceptual hash (pHash) of an image
func PHashImage(imagePath string) (string, error) {
	img, err := loadImage(imagePath)
	if err != nil {
		return "", err
	}

	// Resize to 32x32 grayscale
	resized := resizeImage(img, 32, 32)

	// Compute DCT (simplified using average)
	var dct [32][32]float64
	for y := 0; y < 32; y++ {
		for x := 0; x < 32; x++ {
			dct[y][x] = float64(luminance(resized.At(x, y)))
		}
	}

	// Calculate average of top-left 8x8 (low frequencies)
	var sum float64
	for y := 0; y < 8; y++ {
		for x := 0; x < 8; x++ {
			sum += dct[y][x]
		}
	}
	avg := sum / 64.0

	// Generate 64-bit hash
	var hash uint64
	for y := 0; y < 8; y++ {
		for x := 0; x < 8; x++ {
			hash <<= 1
			if dct[y][x] > avg {
				hash |= 1
			}
		}
	}

	return fmt.Sprintf("%016x", hash), nil
}

// HammingDistance calculates hamming distance between two hex hashes
func HammingDistance(hash1, hash2 string) (int, error) {
	if len(hash1) != len(hash2) {
		return 0, fmt.Errorf("hash lengths differ")
	}

	h1, err1 := hex.DecodeString(hash1)
	h2, err2 := hex.DecodeString(hash2)
	if err1 != nil || err2 != nil {
		return 0, fmt.Errorf("invalid hex hash")
	}

	if len(h1) != len(h2) {
		return 0, fmt.Errorf("hash lengths differ")
	}

	distance := 0
	for i := 0; i < len(h1); i++ {
		diff := h1[i] ^ h2[i]
		// Count bits
		for diff > 0 {
			distance++
			diff &= diff - 1
		}
	}
	return distance, nil
}

// CopyFrame copies a frame file to destination
func CopyFrame(src, dest string) error {
	data, err := os.ReadFile(src)
	if err != nil {
		return fmt.Errorf("failed to read source: %w", err)
	}

	// Ensure destination directory exists
	if err := os.MkdirAll(filepath.Dir(dest), 0755); err != nil {
		return fmt.Errorf("failed to create dest dir: %w", err)
	}

	if err := os.WriteFile(dest, data, 0644); err != nil {
		return fmt.Errorf("failed to write dest: %w", err)
	}

	return nil
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

// =============================================================================
// Internal helper functions
// =============================================================================

func loadImage(path string) (image.Image, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	img, _, err := image.Decode(f)
	return img, err
}

func luminance(c color.Color) float64 {
	r, g, b, _ := c.RGBA()
	// Convert to 0-255 range
	rf := float64(r >> 8)
	gf := float64(g >> 8)
	bf := float64(b >> 8)
	// Standard luminance formula
	return 0.299*rf + 0.587*gf + 0.114*bf
}

func resizeImage(src image.Image, w, h int) *image.Gray {
	dst := image.NewGray(image.Rect(0, 0, w, h))
	bounds := src.Bounds()
	srcW := bounds.Dx()
	srcH := bounds.Dy()

	for y := 0; y < h; y++ {
		for x := 0; x < w; x++ {
			// Simple nearest-neighbor scaling
			srcX := x * srcW / w
			srcY := y * srcH / h
			dst.SetGray(x, y, color.GrayModel.Convert(src.At(bounds.Min.X+srcX, bounds.Min.Y+srcY)).(color.Gray))
		}
	}
	return dst
}