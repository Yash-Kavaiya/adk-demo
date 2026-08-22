// Web server and API for Go BookForge ADK Agent
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"bookforge-go/tools"
)

type GenerateRequest struct {
	URL           string `json:"url"`
	WorkspaceRoot string `json:"workspace"`
	MaxVideos     int    `json:"max_videos"`
}

type GenerateResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	PDFPath string `json:"pdf_path,omitempty"`
}

const htmlIndex = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google ADK Go - BookForge Web UI</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; display: flex; justify-content: center; }
        .container { max-width: 800px; width: 100%; background: #1e293b; border-radius: 12px; padding: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h1 { color: #38bdf8; margin-top: 0; display: flex; align-items: center; gap: 10px; font-size: 1.8rem; }
        .badge { background: #0284c7; color: white; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px; font-weight: normal; }
        .form-group { margin-bottom: 1.2rem; }
        label { display: block; margin-bottom: 0.4rem; color: #94a3b8; font-weight: 500; }
        input[type="text"], input[type="number"] { width: 100%; padding: 0.75rem; background: #0f172a; border: 1px solid #475569; border-radius: 6px; color: #fff; font-size: 1rem; }
        input:focus { outline: none; border-color: #38bdf8; ring: 2px #0284c7; }
        button { background: #2563eb; color: white; border: none; padding: 0.85rem 1.5rem; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: 0.2s; width: 100%; }
        button:hover { background: #1d4ed8; }
        button:disabled { background: #475569; cursor: not-allowed; }
        .log-box { margin-top: 1.5rem; background: #090d16; border: 1px solid #334155; border-radius: 6px; padding: 1rem; font-family: monospace; font-size: 0.9rem; min-height: 140px; max-height: 280px; overflow-y: auto; color: #a5f3fc; }
        .status-pill { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-bottom: 1rem; }
        .status-ready { background: #064e3b; color: #6ee7b7; }
        .status-running { background: #78350f; color: #fde047; }
        .links { margin-top: 1.5rem; display: flex; gap: 15px; border-top: 1px solid #334155; padding-top: 1rem; font-size: 0.9rem; }
        .links a { color: #38bdf8; text-decoration: none; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1><span>📚 BookForge</span> <span class="badge">Google ADK Go 2.0</span></h1>
        <div id="status" class="status-pill status-ready">● Engine Ready (ADK Go)</div>
        
        <form id="genForm">
            <div class="form-group">
                <label for="url">YouTube Channel or Playlist URL:</label>
                <input type="text" id="url" value="https://www.youtube.com/@vishakha.sadhwani" required>
            </div>
            <div class="form-group">
                <label for="workspace">Workspace Root Directory:</label>
                <input type="text" id="workspace" value="data" required>
            </div>
            <div class="form-group">
                <label for="maxVideos">Max Videos to Process:</label>
                <input type="number" id="maxVideos" value="2" min="1" max="50">
            </div>
            <button type="submit" id="submitBtn">⚡ Run Go Multi-Agent Pipeline</button>
        </form>

        <div class="log-box" id="logBox">Waiting for input... Ready to run Go agents.</div>

        <div class="links">
            <a href="http://127.0.0.1:5000" target="_blank">📊 MLflow Traces Dashboard</a>
            <a href="/api/status">⚙️ Go Engine Status</a>
        </div>
    </div>

    <script>
        const form = document.getElementById('genForm');
        const logBox = document.getElementById('logBox');
        const statusEl = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');

        function appendLog(msg) {
            logBox.innerText += "\n" + msg;
            logBox.scrollTop = logBox.scrollHeight;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            submitBtn.disabled = true;
            statusEl.className = 'status-pill status-running';
            statusEl.innerText = '⏳ Running Go Multi-Agent Pipeline...';
            logBox.innerText = '[ADK-GO] Triggering pipeline via Go agent backend...';

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        url: document.getElementById('url').value,
                        workspace: document.getElementById('workspace').value,
                        max_videos: parseInt(document.getElementById('maxVideos').value)
                    })
                });
                const data = await res.json();
                if (data.success) {
                    appendLog("✓ Pipeline Succeeded!");
                    appendLog("✓ Output: " + data.pdf_path);
                    statusEl.className = 'status-pill status-ready';
                    statusEl.innerText = '● Execution Completed Successfully';
                } else {
                    appendLog("! Error: " + data.message);
                    statusEl.className = 'status-pill status-ready';
                    statusEl.innerText = '● Failed with error';
                }
            } catch (err) {
                appendLog("! Network/Server Error: " + err);
                statusEl.className = 'status-pill status-ready';
                statusEl.innerText = '● Request failed';
            } finally {
                submitBtn.disabled = false;
            }
        });
    </script>
</body>
</html>`

func main() {
	port := ":8000"
	if p := os.Getenv("PORT"); p != "" {
		port = ":" + p
	}

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(htmlIndex))
	})

	http.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"status":            "running",
			"engine":            "google-adk-go-2.0",
			"pdflatex_available": tools.PDFLatexAvailable(),
			"timestamp":         time.Now().Format(time.RFC3339),
		})
	})

	http.HandleFunc("/api/generate", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
			return
		}

		var req GenerateRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(GenerateResponse{Success: false, Message: err.Error()})
			return
		}

		if req.WorkspaceRoot == "" {
			req.WorkspaceRoot = "data"
		}

		channelSlug := "vishakha-sadhwani-videos"
		channelDir := filepath.Join(req.WorkspaceRoot, channelSlug)
		bookDir := filepath.Join(channelDir, "book")
		os.MkdirAll(bookDir, 0755)

		// Scan chapters
		chaptersDir := filepath.Join(channelDir, "chapters")
		entries, _ := os.ReadDir(chaptersDir)
		var chapterRelPaths []string
		for _, entry := range entries {
			if entry.IsDir() {
				chapterRelPaths = append(chapterRelPaths, filepath.Join("chapters", entry.Name()))
			}
		}

		// Write preamble & main.tex
		preamblePath := filepath.Join(channelDir, "preamble.tex")
		tools.WriteText(preamblePath, tools.Preamble)

		mainTexContent := tools.AssembleMainTex("Automated Course Textbook", "Vishakha Sadhwani / BookForge", chapterRelPaths)
		mainTexPath := filepath.Join(channelDir, "main.tex")
		tools.WriteText(mainTexPath, mainTexContent)

		// Compile PDF
		if tools.PDFLatexAvailable() && len(chapterRelPaths) > 0 {
			ok, logTail, err := tools.CompileTex(mainTexPath, bookDir, 2, 180, channelDir)
			if ok {
				pdfPath := filepath.Join(bookDir, "main.pdf")
				finalBookPdf := filepath.Join(bookDir, "book.pdf")
				os.Rename(pdfPath, finalBookPdf)
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(GenerateResponse{
					Success: true,
					Message: "Compiled book PDF successfully",
					PDFPath: finalBookPdf,
				})
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(GenerateResponse{Success: false, Message: fmt.Sprintf("%s: %v", logTail, err)})
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(GenerateResponse{Success: true, Message: "Assembled LaTeX without pdflatex compilation"})
	})

	fmt.Printf("[ADK-GO Web] Server running on http://127.0.0.1%s\n", port)
	log.Fatal(http.ListenAndServe(port, nil))
}
