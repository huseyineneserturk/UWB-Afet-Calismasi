"""GitHub deposundaki Markdown içeriklerinden MkDocs kaynak klasörü üretir."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / ".site-src"

ALERT_TITLES = {
    "NOTE": ("note", "Not"),
    "TIP": ("tip", "İpucu"),
    "IMPORTANT": ("important", "Önemli"),
    "WARNING": ("warning", "Uyarı"),
    "CAUTION": ("danger", "Dikkat"),
}


def convert_alerts(markdown: str) -> str:
    """GitHub uyarı bloklarını Material for MkDocs uyarılarına dönüştürür."""

    lines = markdown.splitlines()
    converted: list[str] = []
    index = 0

    while index < len(lines):
        match = re.fullmatch(r">\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*", lines[index])
        if not match:
            converted.append(lines[index])
            index += 1
            continue

        alert_type, title = ALERT_TITLES[match.group(1)]
        body: list[str] = []
        index += 1

        while index < len(lines) and lines[index].startswith(">"):
            body.append(re.sub(r"^>\s?", "", lines[index]))
            index += 1

        converted.append(f'!!! {alert_type} "{title}"')
        converted.extend(f"    {line}" if line else "" for line in body)

    result = "\n".join(converted)
    if markdown.endswith("\n"):
        result += "\n"
    return result


def convert_markdown(source: Path, target: Path) -> None:
    """Bağlantıları site yapısına uyarlar ve Markdown dosyasını yazar."""

    content = source.read_text(encoding="utf-8")
    content = content.replace("README.md", "index.md")
    content = convert_alerts(content)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")


def markdown_target(source: Path, relative_root: Path) -> Path:
    relative = source.relative_to(relative_root)
    if relative.name == "README.md":
        relative = relative.with_name("index.md")
    return SITE_SOURCE / relative


def main() -> None:
    if SITE_SOURCE.exists():
        if SITE_SOURCE.parent != ROOT or SITE_SOURCE.name != ".site-src":
            raise RuntimeError(f"Beklenmeyen geçici klasör: {SITE_SOURCE}")
        shutil.rmtree(SITE_SOURCE)

    SITE_SOURCE.mkdir()

    convert_markdown(ROOT / "README.md", SITE_SOURCE / "index.md")

    for source in sorted((ROOT / "docs").rglob("*.md")):
        target = markdown_target(source, ROOT)
        convert_markdown(source, target)

    shutil.copytree(ROOT / "assets", SITE_SOURCE / "assets")
    shutil.copytree(ROOT / "reports", SITE_SOURCE / "reports")
    shutil.copytree(ROOT / "site-assets", SITE_SOURCE, dirs_exist_ok=True)

    markdown_count = len(list(SITE_SOURCE.rglob("*.md")))
    print(f"Site source prepared: {markdown_count} Markdown pages")


if __name__ == "__main__":
    main()
