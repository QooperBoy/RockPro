"""Read-only scene inventory; independent of the skeleton mutation workflow."""

from .reader import ReadLimits, normalize_bbox, read_parts

__all__ = ["ReadLimits", "normalize_bbox", "read_parts"]
