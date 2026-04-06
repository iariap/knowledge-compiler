"""Extract plain text from HTML using the standard library only."""

from html.parser import HTMLParser


class _HTMLToText(HTMLParser):
    """Collect visible text; skip script and style contents."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in ("script", "style"):
            self._skip_depth += 1
        elif tag.lower() in ("br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag.lower() in ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        self._parts.append(data)


def html_to_plain_text(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html)
    parser.close()
    raw = "".join(parser._parts)
    lines = [line.strip() for line in raw.splitlines()]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed.strip()
