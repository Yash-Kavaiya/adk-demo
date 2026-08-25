"""LaTeX tooling: escaping, table fragments, charts, compile smoke."""

import pytest

from bookforge.schemas import ChartSpec, TableSpec
from bookforge.tools import latex
from bookforge.tools.workspace import Workspace


def test_tex_escape():
    assert latex.tex_escape("50% & $5 #a_b") == r"50\% \& \$5 \#a\_b"


def test_render_table_fragment(tmp_path):
    spec = TableSpec(
        title="t",
        caption="Optimizers compared & ranked",
        headers=["Name", "LR"],
        rows=[["Adam", "1e-3"], ["SGD", "1e-2"]],
    )
    frag = latex.render_table_fragment(spec, tmp_path / "table_1.tex")
    body = frag.read_text(encoding="utf-8")
    assert r"\toprule" in body and r"\bottomrule" in body
    assert r"Optimizers compared \& ranked" in body
    assert "Adam & 1e-3" in body


def test_render_chart_pdf(tmp_path):
    spec = ChartSpec(
        title="Accuracy",
        caption="Accuracy by epoch",
        chart_type="line",
        x_label="epoch",
        y_label="acc",
        categories=["1", "2", "3"],
        values=[0.5, 0.7, 0.9],
    )
    pdf = latex.render_chart(spec, tmp_path / "chart_1.pdf")
    assert pdf.exists() and pdf.read_bytes()[:5] == b"%PDF-"


def test_sanitize_fixes_htmlish_end_figure():
    messy = r"\begin{figure}[htbp]\centering\includegraphics{f.jpg}\end{figure>" + "\n"
    clean = latex.sanitize_chapter_tex(messy)
    assert r"\end{figure}" in clean
    assert r"\end{figure>" not in clean
    assert r"\textbackslash{}" in latex.sanitize_chapter_tex(r"use \backslash foo")


def test_sanitize_chapter_tex():
    messy = (
        "```latex\n\\documentclass{book}\n\\usepackage{x}\n"
        "\\begin{document}\n\\chapter{Hi}\n\\end{document}\n```"
    )
    clean = latex.sanitize_chapter_tex(messy)
    assert "documentclass" not in clean
    assert "usepackage" not in clean
    assert "begin{document}" not in clean
    assert clean.startswith("\\chapter{Hi}")


def test_find_referenced_files():
    body = (
        r"\includegraphics[width=0.8\textwidth]{chapters/01_x/figures/f.jpg}"
        r"\input{chapters/01_x/tables/table_1.tex}"
    )
    refs = latex.find_referenced_files(body)
    assert refs == ["chapters/01_x/figures/f.jpg", "chapters/01_x/tables/table_1.tex"]


@pytest.mark.skipif(not latex.pdflatex_available(), reason="pdflatex missing")
def test_compile_minimal_book(tmp_path):
    """End-to-end: preamble + one chapter with a table fragment -> PDF."""
    ws = Workspace(tmp_path, "demo")
    chapter_dir = ws.root / "chapters" / "01_intro"
    (chapter_dir / "tables").mkdir(parents=True)

    spec = TableSpec(title="t", caption="Cap", headers=["A", "B"], rows=[["1", "2"]])
    latex.render_table_fragment(spec, chapter_dir / "tables" / "table_1.tex")

    body = (
        "\\chapter{Intro}\\label{ch:01-intro}\n"
        "\\section{Key Data and Comparisons}\n"
        "See Table~\\ref{tab:ch01-1}.\n"
        "\\input{chapters/01_intro/tables/table_1.tex}\n"
    )
    Workspace.write_text(chapter_dir / "chapter.tex", body)
    Workspace.write_text(ws.root / "preamble.tex", latex.PREAMBLE)
    main = Workspace.write_text(
        ws.root / "main.tex",
        latex.assemble_main_tex("Demo Book", "Tests", ["chapters/01_intro"]),
    )
    ok, log = latex.compile_tex(main, ws.book_dir, passes=1, cwd=ws.root)
    assert ok, log
    assert (ws.book_dir / "main.pdf").exists()
