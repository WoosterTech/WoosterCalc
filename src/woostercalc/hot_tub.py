import enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Generic,
    Literal,
    TypeVar,
)

from common_libs.colors import ColorType, get_color_block, random_hsl_between
from common_libs.pydantic_pint import (
    Q_,
    PField,
    PintQuantityType,
    _get_dimensionality,
    dreg,
)
from pydantic import BaseModel, Field, RootModel, model_validator

if TYPE_CHECKING:
    from decimal import Decimal

dreg.register("concentration", _get_dimensionality("ppm"))

Quantity = PintQuantityType
Volume = Annotated[
    PintQuantityType, PField(dimensionality="volume", default_unit="gallon")
]
Concentration = Annotated[
    PintQuantityType, PField(dimensionality="concentration", default_unit="ppm")
]


class HotTub(BaseModel):
    volume: ClassVar[Volume]


class SaluSpa(HotTub):
    volume = Q_(242, "gallon")


_Q = TypeVar("_Q", bound=Quantity)


class ValueRange(BaseModel, Generic[_Q]):
    minimum: _Q
    maximum: _Q

    @model_validator(mode="before")
    @classmethod
    def from_tuple(cls, value: Any | tuple[_Q, _Q]) -> Any | dict[str, _Q]:
        if isinstance(value, tuple):
            return {"minimum": value[0], "maximum": value[1]}
        return value

    def in_range(self, value: _Q) -> bool:
        return self.minimum <= value <= self.maximum


value_status = Literal["VERY LOW", "LOW", "OK", "IDEAL", "HIGH", "VERY HIGH"]


class TestStripValue(BaseModel, Generic[_Q]):
    value: _Q
    color: ColorType
    description: value_status

    @classmethod
    def create(
        cls, value: _Q, color_rgb: tuple[int, int, int], description: value_status
    ) -> "TestStripValue":
        color = ColorType.from_rgb(*color_rgb)
        return cls(value=value, color=color, description=description)


HardnessColor = TestStripValue[Concentration]

_V = TypeVar("_V", bound=TestStripValue[_Q])


class TestStripWay(RootModel[dict[str, _V]], Generic[_V]):
    @classmethod
    def create(
        cls,
        value_class: type[_V],
        *values: tuple[str, _Q, tuple[int, int, int], value_status],
    ):
        data: dict[str, _V] = {}
        for value in values:
            key = value[0]
            strip_values = value[1:]
            strip_value = value_class.create(*strip_values)
            data[key] = strip_value
        return cls(root=data)

    def match_rgb(self, value: tuple[int, int, int]) -> _V:
        return self.match_color(ColorType.create(value, input_type="rgb"))

    def match_color(self, value: ColorType) -> _V:
        distances: list[tuple[str, Decimal]] = []
        for key, test_strip_value in self.root.items():
            distances.append(
                (key, test_strip_value.color.distance(value, match_type="hsl"))
            )
        return self.root[min(distances, key=lambda x: x[1])[0]]

    def __getitem__(self, key: str) -> _V:
        return self.root[key]

    def __setitem__(self, key: str, value: _V):
        self.root[key] = value


# total_hardness = TestStripWay(
#     root={
#         "A": HardnessColor.create(Q_(0, "ppm"), (76, 116, 166), "VERY LOW"),
#         "B": HardnessColor.create(Q_(100, "ppm"), (116, 121, 174), "LOW"),
#         "C": HardnessColor.create(Q_(250, "ppm"), (122, 106, 166), "IDEAL"),
#         "D": HardnessColor.create(Q_(500, "ppm"), (144, 90, 140), "HIGH"),
#         "E": HardnessColor.create(Q_(1000, "ppm"), (178, 98, 154), "VERY HIGH"),
#     }
# )

total_hardness = TestStripWay[TestStripValue[Concentration]].create(
    TestStripValue[Concentration],
    ("A", Q_(0, "ppm"), (76, 116, 166), "VERY LOW"),
    ("B", Q_(100, "ppm"), (116, 121, 174), "LOW"),
    ("C", Q_(250, "ppm"), (122, 106, 166), "IDEAL"),
    ("D", Q_(500, "ppm"), (144, 90, 140), "HIGH"),
    ("E", Q_(1000, "ppm"), (178, 98, 154), "VERY HIGH"),
)

total_chlorine = TestStripWay[TestStripValue[Concentration]].create(
    TestStripValue[Concentration],
    ("A", Q_(0, "ppm"), (255, 247, 193), "VERY LOW"),
    ("B", Q_(1, "ppm"), (251, 247, 205), "IDEAL"),
    ("C", Q_(3, "ppm"), (234, 243, 201), "IDEAL"),
    ("D", Q_(5, "ppm"), (203, 229, 200), "HIGH"),
    ("E", Q_(10, "ppm"), (172, 215, 191), "VERY HIGH"),
)

free_chlorine = TestStripWay[TestStripValue[Concentration]].create(
    TestStripValue[Concentration],
    ("A", Q_(0, "ppm"), (255, 250, 227), "VERY LOW"),
    ("B", Q_(1, "ppm"), (246, 229, 221), "IDEAL"),
    ("C", Q_(3, "ppm"), (205, 177, 209), "IDEAL"),
    ("D", Q_(5, "ppm"), (172, 121, 182), "HIGH"),
    ("E", Q_(10, "ppm"), (142, 69, 151), "VERY HIGH"),
)

ph_strip = TestStripWay[TestStripValue[Quantity]].create(
    TestStripValue[Quantity],
    ("A", Q_(6.2, ""), (239, 175, 96), "VERY LOW"),
    ("B", Q_(6.8, ""), (243, 144, 82), "LOW"),
    ("C", Q_(7.2, ""), (225, 104, 51), "OK"),
    ("D", Q_(7.8, ""), (222, 101, 94), "HIGH"),
    ("E", Q_(8.4, ""), (228, 50, 92), "VERY HIGH"),
)


class ValueDefinition(BaseModel):
    values: enum.Enum


class Measurements(BaseModel):
    tub: HotTub
    ph: Annotated[Quantity, Field(alias="pH")]
    total_hardness: Concentration
    total_chlorine: Concentration
    free_chlorine: Concentration
    total_alkalinity: Concentration

    @classmethod
    def from_rgb_values(cls, ph_rgb: tuple[int, int, int], *args: tuple[int, int, int]):
        pass


class Chemical(BaseModel):
    name: ClassVar[str]


special_cased_words = {"ph": "pH"}


def title_case(value: str) -> str:
    """Convert a string to title case, with special cases."""
    if value.lower() in special_cased_words:
        return special_cased_words[value.lower()]
    return value.title()


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()

    table = Table(
        "Value",
        "Observed Color",
        "Closest Match",
        "Value",
        "Status",
        title="Test Strip Values",
    )

    observed_hardnesses = [
        ColorType.create((113, 71, 110), input_type="rgb"),
        ColorType.create((111, 82, 190), input_type="rgb"),
    ]

    def add_table_row(  # noqa: D103
        label: str, observed_rgb: tuple[int, int, int], test_strip: TestStripWay
    ):
        observed_color = ColorType.create(observed_rgb, input_type="rgb")
        test_strip_value = test_strip.match_color(observed_color)
        table.add_row(
            title_case(label),
            get_color_block(observed_color),
            get_color_block(test_strip_value.color),
            str(test_strip_value.value),
            test_strip_value.description,
        )

    random_hardness_color = (
        random_hsl_between(total_hardness["A"].color, total_hardness["E"].color)
        .as_rgb()
        .value
    )
    random_total_chlorine = (
        random_hsl_between(total_chlorine["A"].color, total_chlorine["E"].color)
        .as_rgb()
        .value
    )
    random_ph = (
        random_hsl_between(ph_strip["A"].color, ph_strip["E"].color).as_rgb().value
    )
    console.print(ph_strip["A"].color.distance(ph_strip["E"].color, match_type="hsl"))
    add_table_row("total hardness", random_hardness_color, total_hardness)
    add_table_row("total chlorine", random_total_chlorine, total_chlorine)
    add_table_row("ph", random_ph, ph_strip)

    console.print(table)
