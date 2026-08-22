"""LaTeX helpers: deterministic asset rendering + compilation.

The book owns ONE preamble (here); chapters are preamble-free bodies, so each
chapter can also be compiled standalone by wrapping it in the same preamble.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from bookforge.schemas import ChartSpec, TableSpec
from bookforge.tools.workspace import Workspace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

_SPECIALS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(text: str) -> str:
    return "".join(_SPECIALS.get(ch, ch) for ch in str(text))


# ---------------------------------------------------------------------------
# Tables (booktabs fragments, \input by the chapter)
# ---------------------------------------------------------------------------


def render_table_fragment(spec: TableSpec, dest: Path) -> Path:
    ncols = max(1, len(spec.headers))
    col_spec = "l" * ncols
    lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        f"  \\caption{{{tex_escape(spec.caption)}}}",
        f"  \\begin{{tabular}}{{{col_spec}}}",
        "    \\toprule",
        "    " + " & ".join(tex_escape(h) for h in spec.headers) + " \\\\",
        "    \\midrule",
    ]
    for row in spec.rows:
        padded = list(row)[:ncols] + [""] * max(0, ncols - len(row))
        lines.append("    " + " & ".join(tex_escape(c) for c in padded) + " \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
    ]
    if spec.note:
        lines.append(
            f"  \\\\[2pt]\\begin{{minipage}}{{0.9\\textwidth}}\\footnotesize {tex_escape(spec.note)}\\end{{minipage}}"
        )
    lines.append("\\end{table}")
    return Workspace.write_text(Path(dest), "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Charts (matplotlib -> vector PDF)
# ---------------------------------------------------------------------------


def render_chart(spec: ChartSpec, dest: Path) -> Path:
    """Render a chart spec to PDF. Values come from the validated analysis."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dest = Path(dest)
    if dest.exists():
        return dest

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    values = list(spec.values or [])
    categories = list(spec.categories or [])
    if not categories:
        categories = [str(i + 1) for i in range(len(values))]
    elif len(categories) > len(values):
        categories = categories[: len(values)]
    elif len(values) > len(categories):
        values = values[: len(categories)]

    if not values:
        # Fallback if both empty
        categories = ["1"]
        values = [1.0]

    if spec.chart_type == "bar":
        ax.bar(categories, values, color="#1a73e8")
        ax.tick_params(axis="x", rotation=30)
        for tick in ax.get_xticklabels():
            tick.set_ha("right")
    elif spec.chart_type == "line":
        ax.plot(categories, values, marker="o", color="#1a73e8")
        ax.tick_params(axis="x", rotation=30)
        for tick in ax.get_xticklabels():
            tick.set_ha("right")
    elif spec.chart_type == "pie":
        ax.pie(values, labels=categories, autopct="%1.1f%%", startangle=90)
    else:
        # Default fallback to bar
        ax.bar(categories, values, color="#1a73e8")

    if spec.chart_type != "pie":
        if spec.x_label:
            ax.set_xlabel(spec.x_label)
        if spec.y_label:
            ax.set_ylabel(spec.y_label)
    ax.set_title(spec.title)
    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, format="pdf")
    plt.close(fig)
    return dest


# ---------------------------------------------------------------------------
# Book assembly
# ---------------------------------------------------------------------------

PREAMBLE = r"""\documentclass[11pt,openany]{book}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{textcomp}
\usepackage{booktabs}
\usepackage{xcolor}
\definecolor{primaryblue}{RGB}{37, 99, 235}
\definecolor{accentindigo}{RGB}{79, 70, 229}
\definecolor{softblue}{RGB}{238, 242, 255}
\definecolor{softgreen}{RGB}{236, 253, 245}
\definecolor{accentgreen}{RGB}{16, 185, 129}
\definecolor{darkslate}{RGB}{30, 41, 59}
\definecolor{lightgray}{RGB}{241, 245, 249}
\definecolor{bordergray}{RGB}{203, 213, 225}

\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shapes,shapes.geometric,shadows,calc,fit}

\tikzset{
    every node/.style={align=center},
    modernbox/.style={
        rectangle,
        draw=primaryblue,
        fill=softblue,
        thick,
        rounded corners=4pt,
        minimum height=1.0cm,
        minimum width=2.4cm,
        inner sep=6pt,
        align=center,
        font=\small\bfseries\color{darkslate},
        drop shadow={opacity=0.15, shadow xshift=1.5pt, shadow yshift=-1.5pt}
    },
    accentbox/.style={
        rectangle,
        draw=accentgreen,
        fill=softgreen,
        thick,
        rounded corners=4pt,
        minimum height=1.0cm,
        minimum width=2.4cm,
        inner sep=6pt,
        align=center,
        font=\small\bfseries\color{darkslate},
        drop shadow={opacity=0.15, shadow xshift=1.5pt, shadow yshift=-1.5pt}
    },
    neutralbox/.style={
        rectangle,
        draw=bordergray,
        fill=lightgray,
        thick,
        rounded corners=4pt,
        minimum height=1.0cm,
        minimum width=2.4cm,
        inner sep=6pt,
        align=center,
        font=\small\color{darkslate},
        drop shadow={opacity=0.10, shadow xshift=1pt, shadow yshift=-1pt}
    },
    flowarrow/.style={
        ->,
        >={Stealth[length=6pt, width=5pt]},
        thick,
        color=primaryblue,
        font=\footnotesize\color{darkslate}
    }
}
\usepackage{morefloats}
\extrafloats{100}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{caption}
\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
\hypersetup{colorlinks=true, linkcolor=primaryblue, urlcolor=accentindigo}
"""


def chapter_wrapper(preamble: str, body: str) -> str:
    """Standalone-compilable wrapper used by the QA compile check."""
    return f"{preamble}\n\\begin{{document}}\n{body}\n\\end{{document}}\n"


def assemble_main_tex(
    book_title: str, author_line: str, chapter_rel_dirs: list[str]
) -> str:
    """main.tex that \\input's chapter bodies via workspace-root-relative paths."""
    inputs = [f"\\input{{{rel}/chapter.tex}}" for rel in chapter_rel_dirs]
    chapters_block = "\n\n".join(inputs)
    return (
        "\\input{preamble.tex}\n"
        f"\\title{{{tex_escape(book_title)}}}\n"
        f"\\author{{{tex_escape(author_line)}}}\n"
        "\\date{\\today}\n"
        "\\begin{document}\n"
        "\\frontmatter\n\\maketitle\n\\tableofcontents\n\\mainmatter\n\n"
        f"{chapters_block}\n\n"
        "\\backmatter\n\\end{document}\n"
    )


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


def pdflatex_available() -> bool:
    return shutil.which("pdflatex") is not None


def compile_tex(
    main_tex: Path,
    build_dir: Path,
    passes: int = 2,
    timeout_sec: int = 180,
    cwd: Path | None = None,
) -> tuple[bool, str]:
    """Compile `main_tex`; returns (ok, log_tail_for_diagnostics).

    `cwd` controls how relative paths inside the document (figure/table
    references, \\input) resolve. BookForge always compiles with cwd =
    workspace root so root-relative asset paths work everywhere.
    """
    main_tex = Path(main_tex)
    build_dir = Path(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    if not pdflatex_available():
        return False, "pdflatex not found on PATH"
    work_cwd = Path(cwd) if cwd else main_tex.parent
    main_ref = str(main_tex) if main_tex.is_absolute() else main_tex.name

    last_log = ""
    for _ in range(max(1, passes)):
        proc = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={build_dir}",
                main_ref,
            ],
            cwd=work_cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        last_log = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if proc.returncode != 0:
            return False, extract_latex_errors(last_log)
    return True, last_log[-1500:]


_LATEX_ERR = re.compile(r"^!.*(?:\n+l\.\d+.*)?", re.MULTILINE)


def extract_latex_errors(log: str, max_errors: int = 5) -> str:
    """Pull the '!' error lines + context out of a pdflatex log."""
    errors = _LATEX_ERR.findall(log)
    if not errors:
        return log[-1500:]
    return "\n---\n".join(errors[:max_errors])


# ---------------------------------------------------------------------------
# Cheap static checks (run before paying for a compile)
# ---------------------------------------------------------------------------


def find_referenced_files(tex_body: str) -> list[str]:
    """All filenames referenced via includegraphics / input."""
    refs = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex_body)
    refs += re.findall(r"\\input\{([^}]+)\}", tex_body)
    return refs


def sanitize_chapter_tex(tex: str) -> str:
    """Strip markdown fences / stray commentary an LLM may add despite rules."""
    body = (tex or "").strip()
    fence = re.match(r"^```(?:latex|tex)?\s*\n(?P<body>.*)\n?```\s*$", body, re.DOTALL)
    if fence:
        body = fence.group("body").strip()
    # never trust LLM-supplied preamble material
    body = re.sub(r"\\documentclass[^\n]*\n", "", body)
    body = re.sub(r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\}\n?", "", body)
    body = re.sub(r"\\usetikzlibrary\{[^}]*\}\n?", "", body)
    body = re.sub(r"\\begin\{document\}|\\end\{document\}", "", body)

    # Ensure tikzpicture has align=center or every node/.style={align=center} so \\ in node labels doesn't crash LR mode
    body = re.sub(
        r"\\begin\{tikzpicture\}(?:\[([^\]]*)\])?",
        lambda m: r"\begin{tikzpicture}[" + (m.group(1) + ", " if m.group(1) else "") + r"every node/.append style={align=center}]" if "align=center" not in (m.group(1) or "") else m.group(0),
        body,
    )

    # Unwrap redundant \begin{table}...\input{.../tables/table_*.tex}...\end{table}
    # because table fragments already contain \begin{table}...\end{table}
    body = re.sub(
        r"\\begin\{table\}(?:\[[^\]]*\])?\s*(\\centering\s*)?(?:\\caption\{[^}]*\}\s*)?(?:\\label\{[^}]*\}\s*)?(\\input\{[^}]*tables/table_\d+\.tex\})\s*(?:\\caption\{[^}]*\}\s*)?(?:\\label\{[^}]*\}\s*)?\\end\{table\}",
        r"\2",
        body,
    )

    # Auto-wrap common standalone math commands that LLMs output in text mode without $...$
    math_symbols = [
        r"\\approx",
        r"\\sim",
        r"\\le\b",
        r"\\ge\b",
        r"\\leq\b",
        r"\\geq\b",
        r"\\neq\b",
        r"\\times\b",
        r"\\pm\b",
        r"\\mp\b",
        r"\\cdot\b",
        r"\\in\b",
        r"\\notin\b",
        r"\\subset\b",
        r"\\subseteq\b",
        r"\\infty\b",
    ]
    for sym in math_symbols:
        # If preceded and followed by non-$, wrap it in $ $
        body = re.sub(rf"(?<!\$)\b({sym})(?!\$)", r"$\1$", body)

    return body.strip() + "\n"
