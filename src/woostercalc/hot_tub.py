from decimal import Decimal
from typing import Annotated, Any, ClassVar, Self

from pydantic import BaseModel, GetCoreSchemaHandler, model_validator
from pydantic_core import CoreSchema, core_schema

# from typing_extensions import Self
from woostercalc import Q_


class _PydanticGallon:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate_from_number(value: float | int | Decimal) -> Q_:
            return Q_(value, "gallon")

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(Q_),
                core_schema.no_info_plain_validator_function(validate_from_number),
            ]
        )


class _PydanticPPM:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate_from_number(value: float | int | Decimal) -> Q_:
            return Q_(value, "ppm")

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(Q_),
                core_schema.no_info_plain_validator_function(validate_from_number),
            ]
        )


class _PydanticQuantity:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        def validate_from_number(value: float | int | Decimal) -> Q_:
            return Q_(value)

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(Q_),
                core_schema.no_info_plain_validator_function(validate_from_number),
            ]
        )


Quantity = Annotated[Q_, _PydanticQuantity]
Gallon = Annotated[Q_, _PydanticGallon]
PPM = Annotated[Q_, _PydanticPPM]


class HotTub(BaseModel):
    volume: ClassVar[Gallon]


class SaluSpa(HotTub):
    volume = Q_(242, "gallon")


class ValueRange(BaseModel):
    minimum: Quantity
    maximum: Quantity
    nominal: Quantity

    @model_validator(mode="after")
    def validate_nominal(self) -> Self:
        if not self.in_range(self.nominal):
            raise ValueError("Nominal value must be within the range")
        return self

    def in_range(self, value: Quantity) -> bool:
        return self.minimum <= value <= self.maximum


chemcials = {
    "pH": ValueRange(
        minimum=Q_(7.2, "dimensionless"),
        maximum=Q_(7.8, "dimensionless"),
        nominal=Q_(7.5, "dimensionless"),
    ),
}


class Measurements(BaseModel):
    tub: HotTub
    ph: Quantity
    total_hardness: PPM


class Chemical(BaseModel):
    name: ClassVar[str]


if __name__ == "__main__":
    my_range = ValueRange(
        minimum=Q_(1, "gallon"), maximum=Q_(10, "gallon"), nominal=Q_(8, "pint")
    )
    print(my_range.nominal)
