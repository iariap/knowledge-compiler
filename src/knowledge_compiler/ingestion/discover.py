from pathlib import Path


def discover_files(root: Path, include_extensions: tuple[str, ...]) -> list[Path]:
    normalized_extensions = {extension.lower() for extension in include_extensions}
    discovered = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower().lstrip(".") in normalized_extensions
    ]
    return sorted(discovered)
