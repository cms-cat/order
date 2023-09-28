# coding: utf-8

"""
Custom base models and types for lazy evaluation.
"""

from __future__ import annotations


__all__ = ["Lazy", "Model"]


import re
from typing import Union, Any

from pydantic import BaseModel, Field, ConfigDict
from pydantic.fields import FieldInfo

from order.adapters.base import AdapterData, DataProvider


class Lazy(object):

    @classmethod
    def __class_getitem__(cls, types):
        if not isinstance(types, tuple):
            types = (types,)
        return Union[types + (AdapterData,)]


class ModelMeta(type(BaseModel)):
    """
    TODO:
        - cast to proper type after adapter materialization (validation is done though)
        - prevent caching in data provider when validation failed?
    """

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
        def fget(self) -> float:
            value = getattr(self, lazy_attr)
            if isinstance(value, AdapterData):
                value = DataProvider.instance().get_data(value)
                setattr(self, lazy_attr, value)
            return value

        # we need a valid type hint for the setter so create the function dynamically
        fset_type = f"Lazy[{', '.join(type_names)}]"
        locals_ = {}
        exec(
            f"def fset(self, value: {fset_type}) -> None: setattr(self, \"{lazy_attr}\", value)",
            globals(),
            locals_,
        )
        fset = locals_["fset"]

        classdict[attr] = property(fget=fget, fset=fset)


class Model(BaseModel, metaclass=ModelMeta):

    def __repr_args__(self):
        yield from super().__repr_args__()

        for attr, lazy_attr in self._lazy_attrs:
            value = getattr(self, lazy_attr)
            yield attr, f"lazy({value.name})" if isinstance(value, AdapterData) else value
