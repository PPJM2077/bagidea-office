---
name: File & Media Toolkit
description: Use the office's bundled CLI tools to read/convert PDFs & Office files, make docs/slides, and handle video, audio & images — instead of saying you can't.
---

The office bundles real tools you run via Bash. Before saying a format is unsupported,
reach for these (check it exists first, e.g. `pandoc --version`):

• PDF: the Read tool opens PDFs directly (text + visuals). To convert, use `pandoc` or `soffice`.
• Office files (xlsx / docx / pptx): LibreOffice headless —
    soffice --headless --convert-to csv "book.xlsx"   (spreadsheet -> CSV, then read / Data Wrangler)
    soffice --headless --convert-to pdf "doc.docx"    (any Office doc -> PDF)
    soffice --headless --convert-to txt "deck.pptx"   (pull the text out)
  If `soffice` isn't on PATH (Windows): "C:\Program Files\LibreOffice\program\soffice.exe".
• Write a document / book: author Markdown, then `pandoc in.md -o out.pdf` (or .docx / .epub).
• Make slides: `pandoc in.md -o deck.pptx` (PowerPoint) or `pandoc -t revealjs -s in.md -o deck.html`.
• YouTube / video by CONTENT: `yt-dlp` to fetch subtitles (--write-auto-sub --skip-download) or
  audio, then transcribe and read the transcript. Use `ffmpeg` to cut/convert or extract frames
  (e.g. `ffmpeg -i v.mp4 -vf fps=1/5 f%03d.png`) for visual analysis with a vision model.
• Images: `magick` (ImageMagick) to convert / resize / compose; the office's image tool generates new ones.
• Data: CSV/JSON with small node/python scripts (see Data Wrangler); turn xlsx into CSV via soffice first.
• JSON: `jq`.  GitHub: `gh`.

Keep raw inputs untouched, write outputs to new files, and if a tool is missing tell the owner the one-line install.
