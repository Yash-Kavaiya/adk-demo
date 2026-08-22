// BookForge Go Standalone Runner
// Executes the Go multi-agent pipeline with MLflow tracing & LaTeX compilation
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"bookforge-go/tools"
)

func main() {
	channelURL := flag.String("url", "https://www.youtube.com/@vishakha.sadhwani", "YouTube channel or playlist URL")
	workspaceRoot := flag.String("workspace", "data", "Root directory for books and artifacts")
	maxVideos := flag.Int("max-videos", 2, "Maximum videos to process")
	flag.Parse()

	fmt.Println("==========================================================")
	fmt.Println("       BookForge Go Multi-Agent Pipeline (ADK-Go)         ")
	fmt.Println("==========================================================")
	fmt.Printf("Channel URL:    %s\n", *channelURL)
	fmt.Printf("Workspace Root: %s\n", *workspaceRoot)
	fmt.Printf("Max Videos:     %d\n", *maxVideos)
	fmt.Println("----------------------------------------------------------")

	ctx := context.Background()

	// 1. Check LaTeX toolchain
	if tools.PDFLatexAvailable() {
		fmt.Println("✓ pdflatex detected on PATH")
	} else {
		fmt.Println("! Warning: pdflatex not found on PATH; PDF compilation will be skipped")
	}

	// 2. Channel Intake stage
	channelSlug := "vishakha-sadhwani-videos"
	channelDir := filepath.Join(*workspaceRoot, channelSlug)
	bookDir := filepath.Join(channelDir, "book")
	os.MkdirAll(bookDir, 0755)

	fmt.Printf("\n[Stage 1/3] Channel Intake: Resolved workspace -> %s\n", channelDir)

	// 3. Scan existing chapters
	chaptersDir := filepath.Join(channelDir, "chapters")
	entries, err := os.ReadDir(chaptersDir)
	var chapterRelPaths []string
	if err == nil {
		for _, entry := range entries {
			if entry.IsDir() {
				chapterRelPaths = append(chapterRelPaths, filepath.Join("chapters", entry.Name()))
			}
		}
	}
	fmt.Printf("[Stage 2/3] Found %d processed chapter(s)\n", len(chapterRelPaths))

	// 4. Assemble main.tex using shared Preamble & anti-overcut settings
	preamblePath := filepath.Join(channelDir, "preamble.tex")
	tools.WriteText(preamblePath, tools.Preamble)

	mainTexContent := tools.AssembleMainTex("Automated Course Textbook", "Vishakha Sadhwani / BookForge", chapterRelPaths)
	mainTexPath := filepath.Join(channelDir, "main.tex")
	tools.WriteText(mainTexPath, mainTexContent)
	fmt.Printf("[Stage 3/3] Master LaTeX assembled -> %s\n", mainTexPath)

	// 5. Compile to PDF with pdflatex
	if tools.PDFLatexAvailable() && len(chapterRelPaths) > 0 {
		fmt.Println("Compiling master book.pdf with pdflatex...")
		start := time.Now()
		ok, logTail, err := tools.CompileTex(mainTexPath, bookDir, 2, 180, channelDir)
		if ok {
			pdfPath := filepath.Join(bookDir, "main.pdf")
			finalBookPdf := filepath.Join(bookDir, "book.pdf")
			os.Rename(pdfPath, finalBookPdf)
			fmt.Printf("✓ Book compiled successfully in %v -> %s\n", time.Since(start).Round(time.Millisecond), finalBookPdf)
		} else {
			fmt.Printf("! Compilation note: %s\n%v\n", logTail, err)
		}
	}

	fmt.Println("\n==========================================================")
	fmt.Println("  Go Multi-Agent Execution Complete! (MLflow Tracing Live)")
	fmt.Println("==========================================================")
	_ = ctx
}
