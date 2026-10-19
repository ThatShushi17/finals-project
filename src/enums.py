from enum import Enum

class Position(Enum):
	TOP_LEFT = ("left", "top")
	TOP_CENTER = ("center", "top")
	TOP_RIGHT = ("right", "top")
	CENTER_LEFT = ("left", "center")
	CENTER = ("center", "center")
	CENTER_RIGHT = ("right", "center")
	BOTTOM_LEFT = ("left", "bottom")
	BOTTOM_CENTER = ("center", "bottom")
	BOTTOM_RIGHT = ("right", "bottom")

class Cardinal(Enum):
	TOP = "top"
	BOTTOM = "bottom"
	LEFT = "left"
	RIGHT = "right"

class HexFadeCorner(Enum):
	TOP_LEFT = "top_left"
	TOP_RIGHT = "top_right"
	BOTTOM_LEFT = "bottom_left"
	BOTTOM_RIGHT = "bottom_right"

class Axis(Enum):
	VERTICAL = "vertical"
	HORIZONTAL = "horizontal"

class Alignment(Enum):
	START = "start"
	CENTER = "center"
	END = "end"
	SPACE_BETWEEN = "space_between"
	SPACE_AROUND = "space_around"


class Settings(Enum):
	FONT_NORMAL = "font_default"

	FONT_SIZE_NORMAL = "font_size_normal"

class TabStyles(Enum):
	ONE_CONTAINER = "one_container"
	TWO_CONTAINERS = "two_containers"

class TabBackgrounds(Enum):
	MAIN = "main"
	HEX = "hex"
	SOLID = "solid"

class InputTypes(Enum):
	SLIDER = "slider"
	INPUT = "input"
	CHECKBOX = "checkbox"
	DROPDOWN = "dropdown"
	COMPOUND = "compound"
	LIST = "list"

class Accents(Enum):
	BLUE = "blue"
	GREEN = "green"
	ORANGE = "orange"
	PINK = "pink"

# class FontSizes(Enum):
# 	SMALL = 14
# 	REGULAR = 16
# 	MEDIUM = 24
# 	LARGE = 40

# class FontStyles(Enum):
# 	REGULAR = "regular"
# 	BOLD = "bold"
# 	ITALIC = "italic"
# 	BOLD_ITALIC = "bold_italic"

# FONT_TITLE: set[FontStyles | int] = {FontStyles.BOLD, FontSizes.LARGE.value}
# FONT_REGULAR: set[FontStyles | int] = {FontStyles.REGULAR, FontSizes.REGULAR.value}
