package tools

import (
	"fmt"
	"os/exec"
	"regexp"
	"strings"
)

// LaTeX special characters that need escaping
var latexSpecials = map[rune]string{
	'&':  `\&`,
	'%':  `\%`,
	'$':  `\$`,
	'#':  `\#`,
	'_':  `\_`,
	'{':  `\{`,
	'}':  `\}`,
	'~':  `\textasciitilde{}`,
	'^':  `\textasciicircum{}`,
	'\\': `\textbackslash{}`,
}

// TexEscape escapes LaTeX special characters
func TexEscape(text string) string {
	var result strings.Builder
	for _, ch := range text {
		if escaped, ok := latexSpecials[ch]; ok {
			result.WriteString(escaped)
		} else {
			result.WriteRune(ch)
		}
	}
	return result.String()
}

// RenderTableFragment renders a table spec to LaTeX booktabs fragment
func RenderTableFragment(spec TableSpec, destPath string) (string, error) {
	ncols := len(spec.Headers)
	if ncols == 0 {
		ncols = 1
	}

	colSpec := strings.Repeat("l", ncols)
	
	var lines []string
	lines = append(lines, `\begin{table}[htbp]`)
	lines = append(lines, `  \centering`)
	lines = append(lines, fmt.Sprintf(`  \caption{%s}`, TexEscape(spec.Caption)))
	lines = append(lines, fmt.Sprintf(`  \begin{tabular}{%s}`, colSpec))
	lines = append(lines, `    \toprule`)
	
	// Headers
	headers := make([]string, len(spec.Headers))
	for i, h := range spec.Headers {
		headers[i] = TexEscape(h)
	}
	lines = append(lines, fmt.Sprintf("    %s \\\\", strings.Join(headers, " & ")))
	lines = append(lines, `    \midrule`)
	
	// Rows
	for _, row := range spec.Rows {
		cells := make([]string, ncols)
		for i := 0; i < ncols; i++ {
			if i < len(row) {
				cells[i] = TexEscape(row[i])
			} else {
				cells[i] = ""
			}
		}
		lines = append(lines, fmt.Sprintf("    %s \\\\", strings.Join(cells, " & ")))
	}
	
	lines = append(lines, `    \bottomrule`)
	lines = append(lines, `  \end{tabular}`)
	
	if spec.Note != "" {
		noteEscaped := TexEscape(spec.Note)
		lines = append(lines, fmt.Sprintf(`  \\[2pt]\begin{minipage}{0.9\textwidth}\footnotesize %s\end{minipage}`, noteEscaped))
	}
	
	lines = append(lines, `\end{table}`)
	
	content := strings.Join(lines, "\n") + "\n"
	return destPath, WriteText(destPath, content)
}

// RenderChart renders a chart spec to PDF using plotting library
// TODO: Implement using gonum/plot or similar
func RenderChart(spec ChartSpec, destPath string) (string, error) {
	return "", fmt.Errorf("chart rendering not yet implemented - need Go plotting library")
}

// Preamble is the shared LaTeX document preamble
const Preamble = `\documentclass[11pt,openany]{book}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shapes,shapes.geometric}
\usepackage{morefloats}
\extrafloats{100}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{caption}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\hypersetup{colorlinks=true, linkcolor=blue!50!black, urlcolor=blue!50!black}
`

// ChapterWrapper wraps a chapter body for standalone compilation
func ChapterWrapper(preamble, body string) string {
	return fmt.Sprintf("%s\n\\begin{document}\n%s\n\\end{document}\n", preamble, body)
}

// AssembleMainTex creates the main.tex file for the book
func AssembleMainTex(bookTitle, authorLine string, chapterPaths []string) string {
	var inputs []string
	for _, path := range chapterPaths {
		inputs = append(inputs, fmt.Sprintf(`\input{%s/chapter.tex}`, path))
	}
	
	chaptersBlock := strings.Join(inputs, "\n\n")
	
	return fmt.Sprintf(`\input{preamble.tex}
\title{%s}
\author{%s}
\date{\today}
\begin{document}
\frontmatter
\maketitle
\tableofcontents
\mainmatter

%s

\backmatter
\end{document}
`, TexEscape(bookTitle), TexEscape(authorLine), chaptersBlock)
}

// CompileTex compiles LaTeX to PDF using pdflatex
func CompileTex(mainTexPath, buildDir string, passes, timeoutSec int, cwd string) (bool, string, error) {
	if !PDFLatexAvailable() {
		return false, "pdflatex not found on PATH", fmt.Errorf("pdflatex not available")
	}

	var lastLog string
	for i := 0; i < passes; i++ {
		cmd := exec.Command("pdflatex",
			"-interaction=nonstopmode",
			"-halt-on-error",
			fmt.Sprintf("-output-directory=%s", buildDir),
			mainTexPath,
		)
		if cwd != "" {
			cmd.Dir = cwd
		}

		out, err := cmd.CombinedOutput()
		lastLog = string(out)
		if err != nil {
			return false, ExtractLatexErrors(lastLog, 5), nil
		}
	}

	return true, lastLog, nil
}

// PDFLatexAvailable checks if pdflatex is on PATH
func PDFLatexAvailable() bool {
	_, err := exec.LookPath("pdflatex")
	return err == nil
}

// FindReferencedFiles extracts all file references from LaTeX
func FindReferencedFiles(texBody string) []string {
	var refs []string
	
	// Find \includegraphics{filename}
	graphicsRe := regexp.MustCompile(`\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}`)
	matches := graphicsRe.FindAllStringSubmatch(texBody, -1)
	for _, match := range matches {
		refs = append(refs, match[1])
	}
	
	// Find \input{filename}
	inputRe := regexp.MustCompile(`\\input\{([^}]+)\}`)
	matches = inputRe.FindAllStringSubmatch(texBody, -1)
	for _, match := range matches {
		refs = append(refs, match[1])
	}
	
	return refs
}

// SanitizeChapterTex removes markdown fences and unwanted preamble
func SanitizeChapterTex(tex string) string {
	body := strings.TrimSpace(tex)
	
	// Strip markdown fences
	fenceRe := regexp.MustCompile("(?s)^```(?:latex|tex)?\\s*\\n(.*)\\n?```\\s*$")
	if match := fenceRe.FindStringSubmatch(body); match != nil {
		body = strings.TrimSpace(match[1])
	}
	
	// Remove preamble material
	body = regexp.MustCompile(`(?m)^\\documentclass[^\n]*\n`).ReplaceAllString(body, "")
	body = regexp.MustCompile(`(?m)^\\usepackage(?:\[[^\]]*\])?\{[^}]*\}\n?`).ReplaceAllString(body, "")
	body = regexp.MustCompile(`(?m)^\\usetikzlibrary\{[^}]*\}\n?`).ReplaceAllString(body, "")
	body = regexp.MustCompile(`\\begin\{document\}|\\end\{document\}`).ReplaceAllString(body, "")
	
	// Unwrap redundant table wrappers
	tableWrapRe := regexp.MustCompile(`\\begin\{table\}(?:\[[^\]]*\])?\s*(?:\\centering\s*)?(?:\\caption\{[^}]*\}\s*)?(?:\\label\{[^}]*\}\s*)?(\\input\{[^}]*tables/table_\d+\.tex\})\s*(?:\\caption\{[^}]*\}\s*)?(?:\\label\{[^}]*\}\s*)?\\end\{table\}`)
	body = tableWrapRe.ReplaceAllString(body, "$1")
	
	return strings.TrimSpace(body) + "\n"
}

// ExtractLatexErrors pulls error lines from pdflatex log
func ExtractLatexErrors(log string, maxErrors int) string {
	errRe := regexp.MustCompile(`(?m)^!.*(?:\n+l\.\d+.*)?`)
	errors := errRe.FindAllString(log, -1)
	
	if len(errors) == 0 {
		if len(log) > 1500 {
			return log[len(log)-1500:]
		}
		return log
	}
	
	if len(errors) > maxErrors {
		errors = errors[:maxErrors]
	}
	
	return strings.Join(errors, "\n---\n")
}
