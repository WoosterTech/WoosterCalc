# ruff: noqa: S311
import abc
import colorsys
import random
from decimal import Decimal
from typing import Annotated, Any, Literal, Self, overload

from annotated_types import Ge, Le
from pydantic import BaseModel, Field, model_validator
from pydantic_extra_types.color import COLORS_BY_VALUE
from pydantic_extra_types.color import Color as NamedColor
from rich import print as rprint
from rich.text import Text
from scipy.spatial import distance
from scipy.stats import circmean

HEX_REGEX = r"^#[0-9a-fA-F]{6}$"
RGB_REGEX = r"^\((\d{1,3}), (\d{1,3}), (\d{1,3})\)$"
HSL_REGEX = r"^\((\d{1,3}), (\d{1,3})%, (\d{1,3})%\)$"


class ColorType(BaseModel, abc.ABC):
    value: Any

    @overload
    @classmethod
    def create(cls, *args, input_type="name") -> "CSSColor": ...
    @overload
    @classmethod
    def create(cls, *args, input_type="hex") -> "HexColor": ...
    @overload
    @classmethod
    def create(cls, *args, input_type="hsl") -> "HSLColor": ...
    @overload
    @classmethod
    def create(cls, arg: tuple[int, int, int], input_type="rgb") -> "RGBColor": ...
    @overload
    @classmethod
    def create(cls, *args, input_type="rgb") -> "RGBColor": ...
    @classmethod
    def create(
        cls, *args, input_type: Literal["name", "hex", "hsl", "rgb"] = "name"
    ) -> "ColorType":
        match input_type:
            case "name":
                return cls.from_name(*args)
            case "hex":
                return cls.from_hex(*args)
            case "hsl":
                return cls.from_hsl(*args)
            case "rgb":
                if isinstance(args[0], tuple):
                    return cls.from_rgb(*args[0])
                return cls.from_rgb(*args)
            case _:
                msg = f"Invalid input type: {input_type}"
                raise ValueError(msg)

    @classmethod
    def from_name(cls, name: str) -> "CSSColor":
        return CSSColor(value=name)

    @classmethod
    def from_hex(cls, hex_value: str) -> "HexColor":
        return HexColor(value=hex_value)

    @classmethod
    def from_hsl(cls, hue: int, saturation: Decimal, lightness: Decimal) -> "HSLColor":
        return HSLColor(value=(hue, saturation, lightness))

    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int) -> "RGBColor":
        return RGBColor(value=(red, green, blue))

    @abc.abstractmethod
    def as_hex(self) -> "HexColor":
        pass

    @abc.abstractmethod
    def _rgb_tuple(self) -> tuple[int, int, int]:
        pass

    @abc.abstractmethod
    def as_rgb(self) -> "RGBColor":
        pass

    @abc.abstractmethod
    def as_hsl(self) -> "HSLColor":
        pass

    def as_css(self) -> "CSSColor":
        return COLORS_BY_VALUE.get(self._rgb_tuple())

    def distance(
        self, other: "ColorType", match_type: Literal["hsl", "rgb"] = "hsl"
    ) -> Decimal:
        match match_type:
            case "hsl":
                func = self.hsl_distance
            case "rgb":
                msg = "RGB distance not implemented"
                raise NotImplementedError(msg)
        return Decimal(func(other))

    def hsl_distance(self, color2: "ColorType") -> float:
        return distance.euclidean(self.as_hsl().value, color2.as_hsl().value)

    def hsl_mean(self, other: "ColorType") -> "HSLColor":
        return hsl_mean(self, other)

    def __str__(self) -> str:
        return f"{self.value}"


def hsl_mean(*colors: ColorType) -> "HSLColor":
    """Calculate the mean color of a list of colors in HSL space."""
    hsl_values = [color.as_hsl().value for color in colors]
    h_mean = int(circmean([h for h, _, _ in hsl_values], high=360, low=0))
    s_mean = sum(s for _, s, _ in hsl_values) / len(hsl_values)
    l_mean = sum(li for _, _, li in hsl_values) / len(hsl_values)
    return HSLColor(value=(h_mean, s_mean, l_mean))


def _random_int(value1: float | Decimal, value2: float | Decimal) -> int:
    return random.randint(int(min(value1, value2)), int(max(value1, value2)))


def random_hsl_between(
    color1: ColorType,
    color2: ColorType,
    t: Annotated[float, Ge(0), Le(1)] | None = None,
) -> "HSLColor":
    """Return a random HSL color between two other colors."""
    h1, s1, l1 = color1.as_hsl().value
    h2, s2, l2 = color2.as_hsl().value
    h = _random_int(h1, h2)
    s = _random_int(s1, s2)
    li = _random_int(l1, l2)
    return HSLColor(value=(h, s, li))


class CSSColor(ColorType):
    value: NamedColor

    def as_hex(self) -> "HexColor":
        return HexColor(value=self.value.as_hex(format="long"))

    def _rgb_tuple(self) -> tuple[int, int, int]:
        return self.value.as_rgb_tuple()

    def as_rgb(self) -> "RGBColor":
        return RGBColor(value=self.value.as_rgb_tuple())

    def as_hsl(self) -> "HSLColor":
        return HSLColor(value=self.value.as_hsl_tuple())

    def as_css(self) -> Self:
        return self

    # def __str__(self) -> str:
    #     return f"CSSColor(value={self.value})"


class HexColor(ColorType):
    value: Annotated[str, Field(..., pattern=r"^#[0-9a-fA-F]{6}$")]

    def as_hex(self) -> "HexColor":
        return self

    def _rgb_tuple(self) -> tuple[int, int, int]:
        return (
            int(self.value[1:3], 16),
            int(self.value[3:5], 16),
            int(self.value[5:7], 16),
        )

    def as_rgb(self) -> "RGBColor":
        return RGBColor(
            value=self._rgb_tuple(),
        )

    def as_hsl(self) -> "HSLColor":
        rgb = self._rgb_tuple()
        h, li, s = colorsys.rgb_to_hls(*[c / 255 for c in rgb])
        return HSLColor(
            value=(
                int(h * 360),
                Decimal(round(s, 2) * 100),
                Decimal(round(li, 2) * 100),
            ),
        )

    # def __str__(self) -> str:
    #     return f"HexColor(value={self.value})"


class RGBColor(ColorType):
    value: Annotated[
        tuple[int, int, int],
        Field(
            ...,
            min_items=3,
            max_items=3,
            description="A tuple of red, green, and blue values",
        ),
    ]

    red: Annotated[int, Field(..., ge=0, le=255)]
    green: Annotated[int, Field(..., ge=0, le=255)]
    blue: Annotated[int, Field(..., ge=0, le=255)]

    @model_validator(mode="before")
    @classmethod
    def populate_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if all(color in data for color in ("red", "green", "blue")):
                if "value" in data:
                    msg = "Cannot specify both 'value' and individual color values"
                    raise ValueError(msg)
                data["value"] = (data["red"], data["green"], data["blue"])
            else:
                data["red"], data["green"], data["blue"] = data["value"]
        return data

    def as_hex(self) -> HexColor:
        return HexColor(value=f"#{self.red:02x}{self.green:02x}{self.blue:02x}")

    def _rgb_tuple(self) -> tuple[int, int, int]:
        return self.value

    def as_rgb(self) -> Self:
        return self

    def as_hsl(self) -> "HSLColor":
        h, li, s = colorsys.rgb_to_hls(*[c / 255 for c in self.value])
        return HSLColor(
            value=(
                int(h * 360),
                Decimal(round(s, 2) * 100),
                Decimal(round(li, 2) * 100),
            ),
        )


NAMED_COLORS = {v: RGBColor(value=k) for k, v in COLORS_BY_VALUE.items()}


class HSLColor(ColorType):
    value: Annotated[
        tuple[int, Decimal, Decimal],
        Field(
            ...,
            min_items=3,
            max_items=3,
            description="A tuple of hue, saturation, and lightness values",
        ),
    ]

    hue: Annotated[int, Field(..., ge=0, le=360)]
    saturation: Annotated[Decimal, Field(..., ge=0, le=100)]
    lightness: Annotated[Decimal, Field(..., ge=0, le=100)]

    @model_validator(mode="before")
    @classmethod
    def populate_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if all(color in data for color in ("hue", "saturation", "lightness")):
                if "value" in data:
                    msg = "Cannot specify both 'value' and individual values"
                    raise ValueError(msg)
                data["value"] = (data["hue"], data["saturation"], data["lightness"])
            else:
                data["hue"], data["saturation"], data["lightness"] = data["value"]
        return data

    def as_hex(self) -> HexColor:
        red, green, blue = self._rgb_tuple()
        return HexColor(value=f"#{red:02x}{green:02x}{blue:02x}")

    def _rgb_tuple(self):
        hls = (
            float(self.hue) / 360,
            float(self.lightness) / 100,
            float(self.saturation) / 100,
        )
        red, green, blue = (int(color * 255) for color in colorsys.hls_to_rgb(*hls))
        return red, green, blue

    def as_rgb(self) -> RGBColor:
        return RGBColor(value=self._rgb_tuple())

    def as_hsl(self) -> Self:
        return self

    def __str__(self):
        return f"{self.hue}, {self.saturation}%, {self.lightness}%"


def get_color_block(color: ColorType, label: str | None = None) -> Text:
    """Return a color block with a label.

    The label will be the hex value of the color if none is provided.

    Args:
        color (ColorType): The color to display
        label (str, optional): The label to display. Defaults to None.

    Returns:
        Text: The color block with the label
    """
    color_hex = color.as_hex().value
    label = label or color_hex
    return Text(f"  {label}  ", style=f"on {color_hex} bold white")


def show_color_block(color: ColorType, label: str | None = None):
    """Display a color block with a label.

    The label will be the hex value of the color if none is provided.

    Args:
        color (ColorType): The color to display
        label (str, optional): The label to display. Defaults to None.
    """
    text = get_color_block(color, label)
    rprint(text)


if __name__ == "__main__":
    from rich.table import Table

    my_table = Table("Input", "Hex", "RGB", "HSL", "CSS", title="Color Conversions")

    color_rows: list[ColorType] = [
        CSSColor(value="black"),
        HexColor(value="#ffffff"),
        RGBColor(value=(216, 191, 216)),
        HSLColor(value=(300, Decimal("24"), Decimal("80"))),
    ]

    black = color_rows[0]

    color_distance = black.distance(color_rows[2])
    rprint(f"Distance between black and (216, 191, 216): {color_distance}")

    def create_row(color: ColorType) -> tuple[str, str, str, str]:  # noqa: D103
        return (
            f"{color}",
            f"{color.as_hex()}",
            f"{color.as_rgb()}",
            f"{color.as_hsl()}",
            f"{color.as_css()}",
        )

    for color in color_rows:
        my_table.add_row(*create_row(color))

    rprint(my_table)

    class TestModel(BaseModel):
        color: ColorType

    my_data = TestModel(color=HexColor(value="#ff0000"))
