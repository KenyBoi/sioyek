# AlgoTrendy manual integration

This directory contains the reader-side integration for the maintained AlgoTrendy
operator manual. The manual content remains owned by `KenyBoi/AlgoTrendy-v6`
under `docs/user/`; this fork only supplies reader configuration and packaging
helpers.

## Artifact contract

The launcher accepts a generated PDF and a JSON provenance manifest. The manifest
must contain:

```json
{
  "artifact": "AlgoTrendy-User-Manual.pdf",
  "source_repository": "KenyBoi/AlgoTrendy-v6",
  "source_revision": "<40-character commit SHA>",
  "sha256": "<64 lowercase hexadecimal characters>"
}
```

The launcher refuses to open a missing file or a checksum mismatch. It never
downloads a moving `latest` URL and never executes selected PDF text.

## Rebuild the artifact

From a checkout of the AlgoTrendy repository:

```sh
python3 /path/to/sioyek/integrations/algotrendy/build_manual.py \
  --source-root /path/to/AlgoTrendy-v6/docs/user \
  --output-dir /path/to/algotrendy-manual \
  --source-revision "$(git -C /path/to/AlgoTrendy-v6 rev-parse HEAD)"
```

The builder uses an explicit source-page allowlist, renders Mermaid fences with
pinned Mermaid CLI `11.16.0`, and emits the PDF plus its manifest together. If
the local CLI is unavailable, `--mermaid-ink` is an explicit fallback that sends
diagram source to mermaid.ink; use it only for approved non-sensitive manuals.
Do not replace the revision with a mutable branch or `latest` URL.

## UX/UI direction

The PDF theme follows the AlgoTrendy graphite design system: compact analytical
hierarchy, thin separators, monospace values, and text labels alongside state
color. Mermaid diagrams and SVG assets are explanatory visuals, not runtime proof.

The recommended web companion is a static documentation site using the same
source files and tokens. Sioyek is the offline, annotation-friendly reader for
the verified PDF artifact.
