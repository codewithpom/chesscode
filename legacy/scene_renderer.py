"""scene_renderer.py — Video format definitions."""

from dataclasses import dataclass


@dataclass
class VideoFormat:
    width: int
    height: int
    name: str


FORMATS = {
    "hd":     VideoFormat(1920, 1080, "hd"),
    "shorts": VideoFormat(1080, 1920, "shorts"),
}
