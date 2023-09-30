# coding: utf-8

"""
Custom base models and types for lazy evaluation.
"""

from __future__ import annotations


__all__ = ["Model"]


from pydantic import BaseModel, ConfigDict

from order.types import Any, GeneratorType, Field, FieldInfo, Lazy
from order.adapters.base import AdapterModel, DataProvider
from order.util import no_value


class ModelMeta(type(BaseModel)):

    def __new__(meta_cls, class_name: str, bases: tuple, class_dict: dict[str, Any]) -> "ModelMeta":
        # convert "Lazy" annotations to proper fields and add access properties
        lazy_attrs = []
        for attr, type_str in list(class_dict.get("__annotations__", {}).items()):
            type_names = Lazy.parse_annotation(type_str)
            if type_names:
                meta_cls.register_lazy_attr(attr, type_names, class_name, bases, class_dict)
                lazy_attrs.append(attr)

        # store names of lazy attributes, considering also bases
        lazy_attrs_dict = {}
        for base in reversed(bases):
            if getattr(base, "_lazy_attrs", None) is None:
                continue
            lazy_attrs_dict.update({
                attr: lazy_attr
                for attr, lazy_attr in base._lazy_attrs.default.items()
                if lazy_attr in base.__fields__
            })
        lazy_attrs_dict.update({attr: meta_cls.get_lazy_attr(attr) for attr in lazy_attrs})
        class_dict["_lazy_attrs"] = lazy_attrs_dict

        # check the model_config
        class_dict["model_config"] = model_config = class_dict.get("model_config") or ConfigDict()
        if not isinstance(model_config, dict):
            raise TypeError(
                "class attribute 'model_config' should be empty or a ConfigDict, "
                f"but got {model_config}",
            )

        # enable default value validation
        model_config["validate_default"] = True

        # enable assignment validation
        model_config["validate_assignment"] = True

        # create the class
        cls = super().__new__(meta_cls, class_name, bases, class_dict)

        # remove non-existing lazy attributes from above added dict after class was created
        for attr, lazy_attr in list(cls._lazy_attrs.default.items()):
            if lazy_attr not in cls.__fields__:
                del cls._lazy_attrs.default[attr]

        return cls

    @classmethod
    def get_lazy_attr(meta_cls, attr: str) -> str:
        return f"lazy_{attr}"

    @classmethod
    def register_lazy_attr(
        meta_cls,
        attr: str,
        type_names: list[str],
        class_name: str,
        bases: tuple,
        class_dict: dict[str, Any],
    ) -> None:
        # if a field already exist, get it
        field = class_dict.get(attr)
        if field is not None and not isinstance(field, FieldInfo):
            raise TypeError(
                f"class attribute '{attr}' should be empty or a Field, but got {field}",
            )
        class_dict.pop(attr, None)

        # store existing fields
        class_dict.setdefault("__orig_fields__", {})[attr] = field

        # exchange the annotation with the lazy one
        lazy_attr = meta_cls.get_lazy_attr(attr)
        class_dict["__annotations__"][lazy_attr] = class_dict["__annotations__"].pop(attr)

        # make sure the field has an alias set and is skipped in repr
        _field = Field(alias=attr, repr=False)
        field = FieldInfo.merge_field_infos(field, _field) if field else _field
        class_dict[lazy_attr] = field

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
                for attr_, lazy_attr_ in self._lazy_attrs.items():
                    # the adapter model must be compatible that the called one
                    adapter_model_ = getattr(self, lazy_attr_)
                    if not adapter_model.compare_signature(adapter_model_):
                        continue

                    # complain when the adapter did not provide a value for this attribute
                    if adapter_model_.key not in materialized:
                        raise KeyError(
                            f"adapter '{adapter_model.adapter}' did not provide field "
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

        class_dict[attr] = property(fget=fget, fset=fset)


class Model(BaseModel, metaclass=ModelMeta):
    """
    Base model for all order entities.
    """

    def __repr_args__(self) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__()

        for attr, lazy_attr in self._lazy_attrs.items():
            # skip when field was originally skipped
            orig_field = self.__orig_fields__.get(attr)
            if orig_field and not orig_field.repr:
                continue

            value = getattr(self, lazy_attr)
            yield attr, f"lazy({value.adapter})" if isinstance(value, AdapterModel) else value
