import functools
from typing import TYPE_CHECKING, Annotated, Any, Self

import pint
import pydantic
from loguru import logger
from pydantic_core import CoreSchema, core_schema

from common_libs.registries import Registry

ureg = pint.get_application_registry()

if TYPE_CHECKING:
    from numbers import Number

    from pint.util import UnitsContainer
    from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue

    Q_ = pint.UnitRegistry.Quantity
else:
    Q_ = ureg.Quantity


__all__ = [
    "Q_",
    "PField",
    "PintQuantityType",
    "PintUnitType",
    "dreg",
    "ureg",
]


class _PintQuantity:
    """A custom Pydantic type that handles Pint units with additional validation."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: "GetCoreSchemaHandler"
    ) -> CoreSchema:
        """Define the core schema for Pydantic validation."""

        def validate_pint(
            input_value: "str | Number",
        ) -> "pint.Quantity | str | Number":
            try:
                return Q_(input_value)
            except pint.errors.UndefinedUnitError as e:
                msg = f"Invalid unit or quantity: {e}"
                raise ValueError(msg) from e
            except pint.errors.OffsetUnitCalculusError:
                return input_value

        return core_schema.no_info_plain_validator_function(
            validate_pint,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: f"{x}", return_schema=core_schema.str_schema()
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: CoreSchema, handler: "GetJsonSchemaHandler"
    ) -> "JsonSchemaValue":
        """Define JSON schema for documentation and validation."""
        return {"type": "string", "description": "Pint Quantity with optional unit"}


class _PintUnit:
    """A custom Pydantic type that handles Pint units with additional validation."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: "GetCoreSchemaHandler"
    ) -> CoreSchema:
        """Define the core schema for Pydantic validation."""

        def validate_str(input_value: str) -> pint.Unit:
            try:
                return pint.Unit(input_value)
            except pint.errors.UndefinedUnitError as e:
                msg = f"Invalid unit: {e}"
                raise ValueError(msg) from None

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_str),
            ]
        )

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(pint.Unit),
                from_str_schema,
            ]
        )


class _PintDimensionality:
    """A custom Pydantic type that handles Pint dimensionality with additional validation."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: "GetCoreSchemaHandler"
    ) -> CoreSchema:
        """Define the core schema for Pydantic validation."""

        def validate_str(input_value: str) -> pint.util.UnitsContainer:
            return dreg.get(input_value)

        from_str_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(validate_str),
            ]
        )

        return core_schema.union_schema(
            [
                core_schema.is_instance_schema(pint.util.UnitsContainer),
                from_str_schema,
            ]
        )


def _get_dimensionality(value: str) -> pint.util.UnitsContainer:
    return ureg.get_dimensionality(value)


dreg = Registry[pint.util.UnitsContainer]()
logger.debug("Registering dimensionality units")
dreg.register("length", _get_dimensionality("inch"))
dreg.register("time", _get_dimensionality("second"))
dreg.register("mass", _get_dimensionality("gram"))
dreg.register("temperature", _get_dimensionality("kelvin"))
dreg.register("angle", _get_dimensionality("radian"))
dreg.register("electric_current", _get_dimensionality("ampere"))
dreg.register("luminous_intensity", _get_dimensionality("candela"))
dreg.register("amount_of_substance", _get_dimensionality("mole"))
dreg.register("volume", _get_dimensionality("liter"))
dreg.register("area", _get_dimensionality("acre"))
dreg.register("speed", _get_dimensionality("mph"))
logger.debug("Dimensionality units registered")


PintQuantityType = Annotated[pint.Quantity, _PintQuantity]
PintUnitType = Annotated[pint.Unit, _PintUnit]
PintDimensionalityType = Annotated[pint.util.UnitsContainer, _PintDimensionality]


class DimensionalityError(ValueError):
    def __init__(self, value, expected_dimensionality):
        self.value = value
        self.expected_dimensionality = expected_dimensionality
        super().__init__(
            f'Dimensionality of "{value:P}" does not match expected "{expected_dimensionality}"'
        )


def is_dimensionality(value: str | Q_, dimensionality: "UnitsContainer") -> bool:
    q_value = Q_(value) if not isinstance(value, Q_) else value

    assert not isinstance(dimensionality, str), "dimensionality should not be a string"
    if q_value.u.dimensionality != dimensionality:
        raise DimensionalityError(q_value, dimensionality)
    return True


class _PFieldDefinition(pydantic.BaseModel):
    dimensionality: PintDimensionalityType | None = None
    default_unit: PintUnitType | None = None

    @pydantic.model_validator(mode="after")
    def check_compatibility(self) -> Self:
        if self.dimensionality is not None and self.default_unit is not None:
            if self.default_unit.dimensionality != self.dimensionality:
                msg = "Default unit must have the same dimensionality as the field"
                raise ValueError(msg)
        return self


def validate_quantity(
    value: Q_,
    *,
    default_unit: pint.Unit | None = None,
    dimensionality: pint.util.UnitsContainer | None = None,
) -> Q_:
    if value.dimensionless:
        if default_unit is not None:
            value = Q_(value.m, default_unit)
        else:
            msg = "Dimensionless quantity requires a default unit"
            raise ValueError(msg)

    if dimensionality is not None:
        is_dimensionality(value, dimensionality)

    return value


def PField(  # noqa: N802
    dimensionality: PintDimensionalityType | None = None,
    default_unit: PintUnitType | None = None,
):
    """Generate a Pydantic AfterValidator for a Pint Quantity field."""
    definitions = _PFieldDefinition(
        dimensionality=dimensionality, default_unit=default_unit
    )
    dimensionality = definitions.dimensionality
    default_unit = definitions.default_unit

    validation_func = functools.partial(
        validate_quantity, default_unit=default_unit, dimensionality=dimensionality
    )

    return pydantic.AfterValidator(validation_func)
