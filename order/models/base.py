# coding: utf-8

"""
Custom base models and types for lazy evaluation.
"""

from __future__ import annotations


__all__ = ["Lazy", "Model"]


import re
from typing import Union, Any, _AnnotatedAlias as AnnotatedType

from typing_extensions import Annotated
from pydantic import BaseModel, Field, Strict, ConfigDict
from pydantic.fields import FieldInfo

from order.adapters.base import AdapterModel, DataProvider
from order.util import no_value


class Lazy(object):

    @classmethod
    def __class_getitem__(cls, types):
        if not isinstance(types, tuple):
            types = (types,)
        return Union[tuple(map(cls.make_strict, types)) + (AdapterModel,)]

    @classmethod
    def make_strict(cls, type_: type) -> AnnotatedType:
        # some types cannot be strict
        if not cls.can_make_strict(type_):
            return type_

        # when not decorated with strict meta data, just create a new strict tyoe
        if (
            not isinstance(type_, AnnotatedType) or
            not any(isinstance(m, Strict) for m in getattr(type_, "__metadata__", []))
        ):
            return Annotated[type_, Strict()]

        # when already strict, return as is
        metadata = type_.__metadata__
        if all(m.strict for m in metadata if isinstance(m, Strict)):
            return type_

        # at this point, strict metadata exists but it is actually disabled,
        # so replace it in metadata and return a new annotated type
        metadata = [
            (Strict() if isinstance(m, Strict) else m)
            for m in metadata
        ]
        return Annotated[(*type_.__args__, *metadata)]

    @classmethod
    def can_make_strict(cls, type_: type) -> bool:
        if type_.__dict__.get("_name") in ("Dict", "List"):
            return False

        return True


class ModelMeta(type(BaseModel)):

    def __new__(metacls, classname: str, bases: tuple, classdict: dict[str, Any]) -> "ModelMeta":
        # convert "Lazy" annotations to proper fields and add access properties
        lazy_attrs = []
        for attr, type_str in list(classdict.get("__annotations__", {}).items()):
            type_names = metacls.parse_lazy_annotation(type_str)
            if type_names:
                metacls.register_lazy_attr(attr, type_names, classname, classdict)
                lazy_attrs.append(attr)

        # store names of lazy attributes
        classdict["_lazy_attrs"] = [(attr, metacls.get_lazy_attr(attr)) for attr in lazy_attrs]

        # enable assignment validation
        classdict["model_config"] = model_config = classdict.get("model_config") or ConfigDict()
        if not isinstance(model_config, dict):
            raise TypeError(
                "class attribute 'model_config' should be empty or a ConfigDict, "
                f"but got {model_config}",
            )
        model_config["validate_assignment"] = True

        # create the class
        cls = super().__new__(metacls, classname, bases, classdict)

        return cls

    @classmethod
    def parse_lazy_annotation(metacls, type_str: str) -> list[str] | None:
        m = re.match(r"^Lazy\[(.+)\]$", type_str)
        return m and [s.strip() for s in m.group(1).split(",")]

    @classmethod
    def get_lazy_attr(metacls, attr: str) -> str:
        return f"lazy_{attr}"

    @classmethod
    def register_lazy_attr(
        metacls,
        attr: str,
        type_names: list[str],
        classname: str,
        classdict: dict[str, Any],
    ) -> None:
        # if a field already exist, get it
        field = classdict.get(attr)
        if field is not None and not isinstance(field, FieldInfo):
            raise TypeError(
                f"class attribute '{attr}' should be empty or a Field, but got {field}",
            )
        classdict.pop(attr, None)

        # exchange the annotation with the lazy one
        lazy_attr = metacls.get_lazy_attr(attr)
        classdict["__annotations__"][lazy_attr] = classdict["__annotations__"].pop(attr)

        # add a field for the lazy attribute with aliases
        _field = Field(alias=attr, serialization_alias=attr, repr=False)
        field = FieldInfo.merge_field_infos(field, _field) if field else _field
        classdict[lazy_attr] = field

        # add a property for the original attribute
        def fget(self):
            value = getattr(self, lazy_attr)

            # when the value is (already) materialized, just return it
            if not isinstance(value, AdapterModel):
                return value

            # at this point, we must materialize the value through the adapter
            # and assign all resulting lazy attributes
            adapter_model = value
            value = no_value
            with DataProvider.instance().materialize(adapter_model) as materialized:
                # loop through known lazy attributes and check which of them is assigned a
                # materialized value
                for attr_, lazy_attr_ in self._lazy_attrs:
                    # the adapter model must be compatible that the called one
                    adapter_model_ = getattr(self, lazy_attr_)
                    if not adapter_model.compare_signature(adapter_model_):
                        continue

                    # complain when the adapter did not provide a value for this attribute
                    if adapter_model_.key not in materialized:
                        raise KeyError(
                            f"adapter '{adapter_model.name}' did not provide field "
                            f"'{adapter_model_.key}' as required by attribute '{attr_}'",
                        )

                    # set the value
                    setattr(self, lazy_attr_, materialized[adapter_model_.key])

                    # assign it to the return value for the requested attribute
                    if attr_ == attr:
                        value = getattr(self, lazy_attr_)

            # complain if the return value was not set
            if value == no_value:
                raise RuntimeError(
                    f"adapter referred to by '{adapter_model}' did not materialize value "
                    f"for field '{attr}'",
                )

            return value

        # we need a valid type hint for the setter so create the function dynamically
        fset_type = f"Lazy[{', '.join(type_names)}]"
        locals_ = {}
        exec(
            f"def fset(self, value: {fset_type}) -> None: setattr(self, '{lazy_attr}', value)",
            globals(),
            locals_,
        )
        fset = locals_["fset"]

        classdict[attr] = property(fget=fget, fset=fset)


class Model(BaseModel, metaclass=ModelMeta):
    """
    Base model for all order entities.
    """

    def __repr_args__(self):
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__()

        for attr, lazy_attr in self._lazy_attrs:
            value = getattr(self, lazy_attr)
            yield attr, f"lazy({value.name})" if isinstance(value, AdapterModel) else value
