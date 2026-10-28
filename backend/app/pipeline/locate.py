from dataclasses import dataclass

from app.pipeline.extract import Word
from app.pipeline.recognizers import Detection, detect_rules


@dataclass(frozen=True)
class Box:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True)
class Finding:
    detection: Detection
    boxes: list[Box]


def build_text(words: list[Word]) -> tuple[str, list[tuple[int, int]]]:
    """Join words with single spaces; return the text and each word's (start, end)."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for i, word in enumerate(words):
        if i > 0:
            pos += 1  # the joining space
        spans.append((pos, pos + len(word.text)))
        pos += len(word.text)
    return " ".join(w.text for w in words), spans


def locate(
    detection: Detection, words: list[Word], spans: list[tuple[int, int]]
) -> list[Box]:
    """Boxes of every word that overlaps the detection (whole words, to be safe)."""
    boxes: list[Box] = []
    for word, (start, end) in zip(words, spans):
        if start < detection.end and end > detection.start:
            boxes.append(Box(word.page, word.x0, word.y0, word.x1, word.y1))
    return boxes


def find_pii(words: list[Word]) -> list[Finding]:
    text, spans = build_text(words)
    return [Finding(d, locate(d, words, spans)) for d in detect_rules(text)]