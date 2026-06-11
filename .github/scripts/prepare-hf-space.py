#!/usr/bin/env python3
import argparse
import os
import shutil
import stat
from pathlib import Path


EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    ".pytest_cache",
    ".venv",
    "hf-docker-space",
    "hf-space",
    "node_modules",
}

EXCLUDED_FILE_NAMES = {
    ".DS_Store",
}


HF_README_FRONT_MATTER = """---
title: AgriPulse Tech
emoji: "\\U0001F33E"
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Smart agriculture with IoT, AI, and drones.
---
"""

AGRI_PULSE_OVERVIEW = """<div align="center">
  <h1>AgriPulse Tech</h1>
  <p><strong>Agri + Pulse: precisely sensing every rhythm of modern agriculture.</strong></p>
  <p><em>Alternative project name: AcroPulse.</em></p>
</div>

## Project Overview

AgriPulse Tech is a pioneering smart agriculture platform that integrates IoT sensors, AI-driven analytics, and drone technology to revolutionize modern farming. By providing real-time data on soil health, crop growth, and weather patterns, the project empowers farmers to optimize resource allocation, maximize yields, and reduce operational costs. It bridges the gap between traditional farming and data-driven precision agriculture.

## Deployment Notes

This Hugging Face Space runs the full Resin Docker application from the repository source. The Space is configured to expose the application on port `7860`.
"""


def ignore_names(directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        path = Path(directory, name)
        if name in EXCLUDED_FILE_NAMES:
            ignored.add(name)
        elif path.is_dir() and name in EXCLUDED_DIR_NAMES:
            ignored.add(name)
    return ignored


def strip_front_matter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return markdown
    return markdown[end + len("\n---\n") :].lstrip()


def prepare_readme(output: Path) -> None:
    readme = output / "README.md"
    original = readme.read_text(encoding="utf-8") if readme.exists() else ""
    original = strip_front_matter(original)
    readme.write_text(
        HF_README_FRONT_MATTER + "\n" + AGRI_PULSE_OVERVIEW + "\n---\n\n" + original,
        encoding="utf-8",
        newline="\n",
    )


def prepare_dockerfile(output: Path) -> None:
    dockerfile = output / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    env_block = """ENV RESIN_LISTEN_ADDRESS=0.0.0.0 \\
  RESIN_PORT=7860 \\
  RESIN_AUTH_VERSION=V1

"""
    if "RESIN_PORT=7860" not in text:
        if "EXPOSE 2260" in text:
            text = text.replace("EXPOSE 2260", env_block + "EXPOSE 7860", 1)
        elif "VOLUME " in text:
            text = text.replace("VOLUME ", env_block + "EXPOSE 7860\nVOLUME ", 1)
        else:
            text = text.rstrip() + "\n\n" + env_block + "EXPOSE 7860\n"
    else:
        text = text.replace("EXPOSE 2260", "EXPOSE 7860")
    dockerfile.write_text(text, encoding="utf-8", newline="\n")


def normalize_shell_scripts(output: Path) -> None:
    for script in output.rglob("*.sh"):
        text = script.read_text(encoding="utf-8")
        script.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8", newline="\n")
        current_mode = script.stat().st_mode
        script.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a Resin source tree for Hugging Face Docker Spaces.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()

    if output.exists():
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source, output, ignore=ignore_names)
    prepare_readme(output)
    prepare_dockerfile(output)
    normalize_shell_scripts(output)

    print(f"Prepared Hugging Face Space bundle at {output}")


if __name__ == "__main__":
    main()
