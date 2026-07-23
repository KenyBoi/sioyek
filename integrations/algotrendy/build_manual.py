#!/usr/bin/env python3
"""Build a pinned AlgoTrendy user-manual PDF and provenance manifest."""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import quote


SOURCE_FILES = (
    "README.md",
    "setup-and-access.md",
    "navigation.md",
    "workflows.md",
    "safety-and-boundaries.md",
    "troubleshooting-and-escalation.md",
    "screenshots-and-visual-evidence.md",
    "visual-patterns.md",
    "glossary-and-references.md",
    "agent_matching.md",
    "strategy_candidate_pool_vs_registry.md",
    "filter_gate_validation_metrics.md",
    "information_driven_features.md",
    "edge_signals_microstructure.md",
    "whale_flow_microstructure_research.md",
    "meta_labeling_gate_philosophy.md",
    "lakehouse_popos_runpod_fallback.md",
)
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MERMAID_BLOCK_RE = re.compile(
    r'<pre class="mermaid"><code>(?P<source>.*?)</code></pre>', re.DOTALL
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def executable(value: str | None, fallback: str) -> str:
    return value or shutil.which(fallback) or fallback


def render_mermaid_blocks(
    document: Path, output_dir: Path, mmdc_value: str | None, use_mermaid_ink: bool
) -> None:
    source = document.read_text(encoding="utf-8")
    matches = list(MERMAID_BLOCK_RE.finditer(source))
    if not matches:
        return

    mermaid_dir = output_dir / "mermaid"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    if mmdc_value and use_mermaid_ink:
        raise SystemExit("choose either --mmdc or --mermaid-ink, not both")
    mmdc = mmdc_value or shutil.which("mmdc")
    command_prefix = [mmdc] if mmdc else [executable(None, "npx"), "--yes", "@mermaid-js/mermaid-cli@11.16.0"]
    replacements: list[tuple[int, int, str]] = []
    for index, match in enumerate(matches, start=1):
        diagram_source = html_lib.unescape(match.group("source"))
        source_path = mermaid_dir / f"diagram-{index:02d}.mmd"
        svg_path = mermaid_dir / f"diagram-{index:02d}.svg"
        source_path.write_text(diagram_source, encoding="utf-8")
        if use_mermaid_ink:
            encoded = base64.urlsafe_b64encode(diagram_source.encode("utf-8")).decode("ascii").rstrip("=")
            subprocess.run(
                ["curl", "-fsSL", f"https://mermaid.ink/svg/{encoded}", "-o", str(svg_path)],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        else:
            subprocess.run(
                [
                    *command_prefix,
                    "-i",
                    str(source_path),
                    "-o",
                    str(svg_path),
                    "-b",
                    "transparent",
                    "-t",
                    "neutral",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        replacement = (
            f'<img class="mermaid-rendered" src="mermaid/{svg_path.name}" '
            f'alt="Mermaid diagram {index}">'
        )
        replacements.append((match.start(), match.end(), replacement))

    for start, end, replacement in reversed(replacements):
        source = source[:start] + replacement + source[end:]
    document.write_text(source, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="AlgoTrendy docs/user directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True, help="40-character source commit SHA")
    parser.add_argument("--source-repository", default="KenyBoi/AlgoTrendy-v6")
    parser.add_argument("--pandoc")
    parser.add_argument("--mmdc", help="Mermaid CLI executable; defaults to mmdc or pinned npx package")
    parser.add_argument(
        "--mermaid-ink",
        action="store_true",
        help="render diagrams through mermaid.ink; sends diagram source to that service",
    )
    parser.add_argument("--chrome", help="Chrome executable used for deterministic PDF export")
    args = parser.parse_args()

    if not SHA_RE.fullmatch(args.source_revision):
        parser.error("--source-revision must be a 40-character lowercase commit SHA")

    source_root = args.source_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = [source_root / name for name in SOURCE_FILES]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        parser.error(f"missing manual source files: {', '.join(missing)}")

    artifact = output_dir / "AlgoTrendy-User-Manual.pdf"
    html = output_dir / "AlgoTrendy-User-Manual.html"
    artifact.unlink(missing_ok=True)
    html.unlink(missing_ok=True)
    assets = source_root / "assets"
    if assets.is_dir():
        shutil.copytree(assets, output_dir / "assets", dirs_exist_ok=True)
    css = Path(__file__).with_name("manual.css").resolve()
    pandoc = executable(args.pandoc, "pandoc")
    chrome = args.chrome or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not Path(chrome).is_file():
        raise SystemExit(f"Chrome executable not found: {chrome}")

    subprocess.run(
        [
            pandoc,
            "-f",
            "gfm",
            "--standalone",
            "--toc",
            "--toc-depth=3",
            "--metadata",
            "title=AlgoTrendy User Manual",
            "--metadata",
            "author=AlgoTrendy",
            "--css",
            str(css),
            "--resource-path",
            f"{source_root.parent}:{source_root}",
            *(str(path) for path in sources),
            "-o",
            str(html),
        ],
        check=True,
    )
    render_mermaid_blocks(html, output_dir, args.mmdc, args.mermaid_ink)

    with tempfile.TemporaryDirectory(prefix="algotrendy-chrome-") as profile:
        process = subprocess.Popen(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-default-apps",
                "--disable-extensions",
                "--no-first-run",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={artifact}",
                f"file://{quote(str(html))}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 120
        last_size = -1
        stable_polls = 0
        while time.monotonic() < deadline:
            current_size = artifact.stat().st_size if artifact.exists() else 0
            if current_size > 0 and current_size == last_size:
                stable_polls += 1
            else:
                stable_polls = 0
            if stable_polls >= 3:
                process.terminate()
                break
            if process.poll() is not None:
                if current_size > 0:
                    break
                raise SystemExit(f"Chrome PDF export failed with exit code {process.returncode}")
            last_size = current_size
            time.sleep(0.5)
        else:
            process.kill()
            raise SystemExit("Chrome PDF export timed out")
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    manifest = {
        "artifact": artifact.name,
        "source_repository": args.source_repository,
        "source_revision": args.source_revision,
        "sha256": sha256(artifact),
    }
    (output_dir / "AlgoTrendy-User-Manual.manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
