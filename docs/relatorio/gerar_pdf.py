"""Gera relatorio_tecnico.pdf a partir do relatorio_tecnico.md.

Converte o Markdown em HTML e usa o Chrome (modo headless) para imprimir em PDF.
Uso: python docs/relatorio/gerar_pdf.py
"""

import subprocess
from pathlib import Path

import markdown

PASTA = Path(__file__).resolve().parent
CHROME = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

ESTILO = """
@page { size: A4; margin: 20mm 18mm 20mm 18mm;
        @bottom-right { content: counter(page); font-size: 9pt; color: #4b6358; } }
@page :first { @bottom-right { content: none; } }
body { font-family: "Atkinson Hyperlegible", "Segoe UI", Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #0b2e24; }
h1 { color: #047857; font-size: 18pt; margin: 26px 0 10px; padding-bottom: 6px;
     border-bottom: 2px solid #d3e8dc; break-after: avoid; }
h2 { color: #065f46; font-size: 13pt; margin: 18px 0 8px; break-after: avoid; }
p, li { text-align: justify; }
img { max-width: 100%; display: block; margin: 10px auto; break-inside: avoid; }
img[alt="Dashboard"] { max-width: 72%; border: 1px solid #d3e8dc; }
table { width: 100%; border-collapse: collapse; margin: 10px 0 14px; font-size: 9.5pt; break-inside: avoid; }
th { background: #e3f6ec; color: #065f46; text-align: left; }
th, td { border: 1px solid #d3e8dc; padding: 5px 7px; vertical-align: top; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f3faf6; padding: 0 3px; border-radius: 3px; }
td code { word-break: break-all; }
blockquote { margin: 12px 0; padding: 8px 14px; background: #fef3e2; border-left: 4px solid #b45309; }
blockquote p { margin: 0; }
.lado-a-lado { display: flex; gap: 12px; break-inside: avoid; }
.lado-a-lado p { flex: 1; margin: 0; }
.capa { height: 245mm; display: flex; flex-direction: column; justify-content: center;
        break-after: page; border-left: 10px solid #047857; padding-left: 28px; }
.capa h1 { font-size: 28pt; border: 0; color: #0b2e24; margin: 18px 0 6px; }
.capa .instituicao, .capa .disciplina { color: #047857; font-weight: 700; margin: 2px 0; text-align: left; }
.capa .subtitulo { font-size: 13pt; color: #4b6358; text-align: left; }
.capa .integrantes { font-size: 12pt; margin-top: 50px; text-align: left; }
.capa .links, .capa .data { color: #4b6358; text-align: left; }
"""


def main():
    texto = (PASTA / "relatorio_tecnico.md").read_text(encoding="utf-8")
    corpo = markdown.markdown(texto, extensions=["tables", "md_in_html"])

    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório Técnico - Fila Virtual</title>
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>{ESTILO}</style></head><body>{corpo}</body></html>"""

    arq_html = PASTA / "relatorio_tecnico.html"
    arq_html.write_text(html, encoding="utf-8")

    chrome = next((c for c in CHROME if Path(c).exists()), None)
    if not chrome:
        print("Chrome/Edge nao encontrado. Abra relatorio_tecnico.html no navegador e imprima em PDF.")
        return

    pdf = PASTA / "relatorio_tecnico.pdf"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=5000", f"--print-to-pdf={pdf}", arq_html.as_uri()],
                   check=True, capture_output=True)
    print(f"PDF gerado: {pdf}")


if __name__ == "__main__":
    main()
