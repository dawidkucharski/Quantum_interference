from __future__ import annotations

import argparse
import html
from pathlib import Path


def _rel(from_dir: Path, to_path: Path) -> str:
    return to_path.relative_to(from_dir).as_posix()


def _titleize(name: str) -> str:
    return name.replace("_", " ").strip()


def _collect_figure_dirs(outputs_dir: Path) -> list[Path]:
    dirs = [
        p
        for p in outputs_dir.iterdir()
        if p.is_dir() and (p.name.startswith("figures") or p.name.startswith("sweep") or p.name == "demo")
    ]
    # Prefer newest by mtime
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs


def _collect_images(fig_dir: Path, *, max_items: int) -> list[Path]:
    exts = {".png", ".jpg", ".jpeg", ".svg"}
    imgs = [p for p in fig_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
    imgs.sort(key=lambda p: p.name)
    return imgs[: max_items if max_items > 0 else len(imgs)]


def _maybe_pdf_for(image_path: Path) -> Path | None:
    pdf = image_path.with_suffix(".pdf")
    return pdf if pdf.exists() else None


def build_gallery(*, outputs_dir: Path, out_html: Path, max_items_per_dir: int) -> None:
    outputs_dir = outputs_dir.resolve()
    out_html.parent.mkdir(parents=True, exist_ok=True)

    fig_dirs = _collect_figure_dirs(outputs_dir)

    # Also include PDF-only dirs (e.g. mdpi onecol pdf) even if they lack PNGs.
    # We'll list a few representative PDFs in that case.
    pdf_only_dirs: list[Path] = []
    for d in fig_dirs:
        has_img = any(p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"} for p in d.iterdir() if p.is_file())
        has_pdf = any(p.suffix.lower() == ".pdf" for p in d.iterdir() if p.is_file())
        if has_pdf and not has_img:
            pdf_only_dirs.append(d)

    def _list_pdfs(d: Path) -> list[Path]:
        pdfs = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
        pdfs.sort(key=lambda p: p.name)
        return pdfs[: max_items_per_dir if max_items_per_dir > 0 else len(pdfs)]

    # Build links relative to outputs_dir so the gallery works when opened as /outputs/gallery.html.
    base = outputs_dir

    parts: list[str] = []
    parts.append("<!doctype html>")
    parts.append("<html lang='en'>")
    parts.append("<head>")
    parts.append("<meta charset='utf-8'/>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1'/>")
    parts.append("<title>Quantum Interference – Outputs Gallery</title>")
    parts.append(
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:20px;line-height:1.35}"
        "h1{font-size:20px;margin:0 0 12px}"
        "h2{font-size:16px;margin:18px 0 8px}"
        ".note{color:#444;font-size:13px;margin-bottom:12px}"
        ".dir{margin:18px 0;padding:12px;border:1px solid #ddd;border-radius:10px}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}"
        ".card{border:1px solid #eee;border-radius:10px;padding:10px}"
        ".name{font-size:12px;color:#333;margin:6px 0 0;word-break:break-all}"
        "img{max-width:100%;height:auto;border-radius:6px;background:#fafafa}"
        "a{color:#0b63ce;text-decoration:none} a:hover{text-decoration:underline}"
        "</style>"
    )
    parts.append("</head>")
    parts.append("<body>")
    parts.append("<h1>Outputs gallery</h1>")
    parts.append(
        "<div class='note'>Browse current figures in <code>outputs/</code>. "
        "PNG/SVG are previewed inline; PDFs are linked.</div>"
    )

    # Quick links
    parts.append("<div class='dir'>")
    parts.append("<b>Figure folders</b><br/>")
    for d in fig_dirs:
        rel = _rel(base, d)
        parts.append(f"<a href='{html.escape(rel)}/'>{html.escape(d.name)}</a><br/>")
    parts.append("</div>")

    for d in fig_dirs:
        imgs = _collect_images(d, max_items=max_items_per_dir)
        pdfs = _list_pdfs(d) if not imgs else []

        parts.append("<div class='dir'>")
        parts.append(f"<h2>{html.escape(d.name)}</h2>")
        parts.append(f"<div class='note'>Folder: <code>{html.escape(_rel(base, d))}</code></div>")

        if imgs:
            parts.append("<div class='grid'>")
            for img in imgs:
                rel_img = _rel(base, img)
                pdf = _maybe_pdf_for(img)
                parts.append("<div class='card'>")
                parts.append(f"<a href='{html.escape(rel_img)}' target='_blank'>")
                parts.append(f"<img src='{html.escape(rel_img)}' loading='lazy'/>")
                parts.append("</a>")
                name = img.name
                parts.append("<div class='name'>")
                parts.append(html.escape(name))
                if pdf is not None:
                    rel_pdf = _rel(base, pdf)
                    parts.append(f"<br/><a href='{html.escape(rel_pdf)}' target='_blank'>Open PDF</a>")
                parts.append("</div>")
                parts.append("</div>")
            parts.append("</div>")
        elif pdfs:
            parts.append("<div class='note'>No preview images found; listing PDFs:</div>")
            for pdf in pdfs:
                rel_pdf = _rel(base, pdf)
                parts.append(f"<a href='{html.escape(rel_pdf)}' target='_blank'>{html.escape(pdf.name)}</a><br/>")
        else:
            parts.append("<div class='note'>No figures found in this directory.</div>")

        parts.append("</div>")

    parts.append("</body></html>")

    out_html.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a simple HTML gallery for outputs/ figures.")
    ap.add_argument("--outputs", type=str, default="outputs", help="Outputs directory to scan.")
    ap.add_argument("--out", type=str, default="outputs/gallery.html", help="HTML file to write.")
    ap.add_argument(
        "--max-items-per-dir",
        type=int,
        default=12,
        help="Max images/PDF links to include per figure directory (0 = all).",
    )
    args = ap.parse_args()

    outputs_dir = Path(args.outputs)
    out_html = Path(args.out)

    if not outputs_dir.exists() or not outputs_dir.is_dir():
        raise SystemExit(f"Not a directory: {outputs_dir}")

    build_gallery(outputs_dir=outputs_dir, out_html=out_html, max_items_per_dir=int(args.max_items_per_dir))
    print(f"Wrote gallery: {out_html}")


if __name__ == "__main__":
    main()
