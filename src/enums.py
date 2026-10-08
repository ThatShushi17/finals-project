
from enum import Enum

class Position(Enum):
	"""Enum for 9-point positioning grid (anchor/dock)."""
	TOP_LEFT = ("left", "top")
	TOP_CENTER = ("center", "top")
	TOP_RIGHT = ("right", "top")
	CENTER_LEFT = ("left", "center")
	CENTER = ("center", "center")
	CENTER_RIGHT = ("right", "center")
	BOTTOM_LEFT = ("left", "bottom")
	BOTTOM_CENTER = ("center", "bottom")
	BOTTOM_RIGHT = ("right", "bottom")