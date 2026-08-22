package tools

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// YouTubeVideo represents basic video metadata
type YouTubeVideo struct {
	VideoID    string `json:"video_id"`
	Title      string `json:"title"`
	URL        string `json:"url"`
	Duration   int    `json:"duration_sec"`
	UploadDate string `json:"upload_date"`
}

// ListChannelVideos fetches all videos from a YouTube channel via yt-dlp
func ListChannelVideos(channelURL string, maxVideos, minDuration, maxDuration int) (string, []YouTubeVideo, error) {
	cmd := exec.Command("yt-dlp",
		"--flat-playlist",
		"--dump-single-json",
		channelURL,
	)
	out, err := cmd.Output()
	if err != nil {
		return "", nil, fmt.Errorf("yt-dlp error: %w", err)
	}

	var data struct {
		Title   string `json:"title"`
		Uploader string `json:"uploader"`
		Entries []struct {
			ID       string  `json:"id"`
			Title    string  `json:"title"`
			URL      string  `json:"url"`
			Duration float64 `json:"duration"`
		} `json:"entries"`
	}

	if err := json.Unmarshal(out, &data); err != nil {
		return "", nil, fmt.Errorf("json parse error: %w", err)
	}

	title := data.Title
	if title == "" {
		title = data.Uploader
	}
	if title == "" {
		title = "YouTube Channel"
	}

	var videos []YouTubeVideo
	for _, entry := range data.Entries {
		dur := int(entry.Duration)
		if minDuration > 0 && dur < minDuration {
			continue
		}
		if maxDuration > 0 && dur > maxDuration {
			continue
		}
		vUrl := entry.URL
		if vUrl == "" && entry.ID != "" {
			vUrl = fmt.Sprintf("https://www.youtube.com/watch?v=%s", entry.ID)
		}
		videos = append(videos, YouTubeVideo{
			VideoID:  entry.ID,
			Title:    entry.Title,
			URL:      vUrl,
			Duration: dur,
		})
		if maxVideos > 0 && len(videos) >= maxVideos {
			break
		}
	}

	return title, videos, nil
}

// DownloadVideo downloads a video at capped resolution via yt-dlp
func DownloadVideo(url, destDir string, maxHeight int) (string, error) {
	os.MkdirAll(destDir, 0755)
	outTemplate := filepath.Join(destDir, "video.%(ext)s")
	format := fmt.Sprintf("bestvideo[height<=%d]+bestaudio/best[height<=%d]/best", maxHeight, maxHeight)

	cmd := exec.Command("yt-dlp",
		"-f", format,
		"--merge-output-format", "mp4",
		"-o", outTemplate,
		url,
	)
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("download error: %w", err)
	}

	mp4Path := filepath.Join(destDir, "video.mp4")
	if _, err := os.Stat(mp4Path); err == nil {
		return mp4Path, nil
	}
	return "", fmt.Errorf("downloaded video not found at %s", mp4Path)
}

// ExtractAudio extracts 16kHz mono audio from video via ffmpeg
func ExtractAudio(videoPath, destDir string) (string, error) {
	os.MkdirAll(destDir, 0755)
	audioPath := filepath.Join(destDir, "audio.wav")
	cmd := exec.Command("ffmpeg",
		"-y",
		"-i", videoPath,
		"-vn",
		"-acodec", "pcm_s16le",
		"-ar", "16000",
		"-ac", "1",
		audioPath,
	)
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("audio extraction error: %w", err)
	}
	return audioPath, nil
}

// LoadTranscriptText loads and returns transcript text
func LoadTranscriptText(path string, maxChars int) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	text := string(data)
	if maxChars > 0 && len(text) > maxChars {
		return text[:maxChars], nil
	}
	return text, nil
}
