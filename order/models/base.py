# coding: utf-8

"""
Custom base models and types for lazy evaluation.
"""

from __future__ import annotations


__all__ = ["BaseModel", "Model", "AdapterModel"]


from contextlib import contextmanager

from pydantic import BaseModel as PDBaseModel, ConfigDict, Field

from order.types import (
    Any, Generator, GeneratorType, FieldInfo, Lazy, NonEmptyStrictStr, StrictStr, Dict, Tuple,
    ClassVar,
)
from order.util import no_value, has_attr, maybe_colored, Repr


class ModelMeta(type(PDBaseModel)):

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
            if not has_attr(base, "_lazy_attrs"):
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
        from order.adapters.base import DataProvider

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


class BaseModel(PDBaseModel):

    _model_show_flags: ClassVar[Tuple[str]] = ("verbose", "adapters")

    def __init__(self: BaseModel, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # flag that is True for the duration of the model_copy base call to better control __copy__
        # and __deepcopy__ depending on whether mode_copy or another object triggered the copy
        self._copy_triggered_by_model = False

        # setup objects
        self._setup_objects()

    def _setup_objects(self) -> None:
        """
        A custom hook to setup objects like indices and references that get invoked in certain
        events, such as during initialization, or after deserialization and copying.
        """
        return

    @contextmanager
    def _unfreeze_field(self, name: str) -> Generator[None, None, None]:
        # get current settings
        field = self.model_fields.get(name)
        frozen = getattr(field, "frozen", no_value)
        validate_assignment = getattr(self.model_config, "validate_assignment", no_value)

        # update settings
        if field:
            field.frozen = False
        self.model_config["validate_assignment"] = False

        try:
            yield

        finally:
            # change back settings
            if field:
                if frozen == no_value:
                    delattr(field, "frozen")
                else:
                    field.frozen = frozen
            if validate_assignment == no_value:
                del self.model_config["validate_assignment"]
            else:
                self.model_config["validate_assignment"] = validate_assignment

    def __repr_name__(self) -> str:
        return maybe_colored(super().__repr_name__(), color="light_green")

    def __repr_str__(self, join_str: str, *, verbose: bool = False, adapters: bool = False) -> str:
        return join_str.join(
            (
                repr(v)
                if f is None
                else (
                    f"{maybe_colored(f, color='light_blue')}={v!r}"
                    if adapters or not isinstance(v, AdapterModel)
                    else f"{maybe_colored(f, color='light_blue')}={self.__repr_adapter__(v)!r}"
                )
            )
            for f, v in self.__repr_args__(verbose=verbose, adapters=adapters)
        )

    def __repr_args__(self, *, verbose: bool = False, adapters: bool = False) -> GeneratorType:
        yield from super().__repr_args__()

    def __repr_adapter__(self, adapter_model: "AdapterModel") -> str | Repr:
        # wrap into a Repr object so that potential color codes are not escaped
        r = f"lazy:{adapter_model.adapter}.{adapter_model.key}"
        return Repr(maybe_colored(r, color="light_magenta"))

    def __repr_circular__(self) -> str:
        return self.__class__.__name__

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> "BaseModel":
        # set the copy flag since model_copy triggered the copy
        orig_copy_flag = self._copy_triggered_by_model
        self._copy_triggered_by_model = True

        # super call
        copied = super().model_copy(update=update, deep=deep)

        # reset the copy flag of _this_ and the copied instance
        copied._copy_triggered_by_model = orig_copy_flag
        self._copy_triggered_by_model = orig_copy_flag

        # the copied instance already contains updated variables, but pydantic does not re-validate
        # them, so we need to do this manually here
        if update:
            for f, v in update.items():
                with copied._unfreeze_field(f):
                    setattr(copied, f, v)

        # setup objects
        copied._setup_objects()

        return copied

    def model_show(
        self,
        *,
        verbose: bool = False,
        adapters: bool = False,
        indent: int = 2,
        _memo: dict[int, Any] | None = None,
        _name_prefix: str = "",
        _ind: str = "",
    ) -> None:
        """ model_show(*, verbose: bool = False, adapters : bool = False, indent: int = 2) -> None
        Prints a full representation of this object. When *verbose* is *True*, more information is
        shown, depending on the model implementation. Unless *adapters* is *True*,
        :py:class:`AdapterModel`'s are shown abbreviated. The indentation level can be controlled
        via *indent*.
        """
        # type formatters
        col_key = lambda v: maybe_colored(v, color="light_blue")
        col_str = lambda v: maybe_colored(repr(v), color="light_yellow")
        col_num = lambda v: maybe_colored(v, color="light_red")
        col_cir = lambda v: maybe_colored(f"{v} (circular)", color="light_cyan")

        # avoid recursions using the memo object
        if _memo is None:
            _memo = {}
        elif _memo.get(id(self)):
            print(f"{_ind}{_name_prefix}{col_cir(self.__repr_circular__())}")
            return
        _memo[id(self)] = True

        def show(name_prefix: str | None, value: Any, ind: str):
            if isinstance(value, BaseModel) and (adapters or not isinstance(value, AdapterModel)):
                return value.model_show(
                    verbose=verbose,
                    adapters=adapters,
                    indent=indent,
                    _memo=_memo,
                    _name_prefix="" if name_prefix is None else f"{col_key(name_prefix)}: ",
                    _ind=ind,
                )

            prefix = ind if name_prefix is None else f"{ind}{col_key(name_prefix)}: "

            if isinstance(value, AdapterModel):
                print(f"{prefix}{self.__repr_adapter__(value)}")

            elif isinstance(value, (list, tuple, set)):
                o, c = "[", "]"
                if isinstance(value, tuple):
                    o, c = "(", ")"
                elif isinstance(value, set):
                    o, c = "{", "}"
                print(f"{prefix}{o}")
                for _value in value:
                    show(None, _value, ind + indent * " ")
                print(f"{ind}{c}")

            elif isinstance(value, dict):
                o, c = "{", "}"
                print(f"{prefix}{o}")
                for _key, _value in value.items():
                    show(_key, _value, ind + indent * " ")
                print(f"{ind}{c}")

            elif isinstance(value, str):
                print(f"{prefix}{col_str(value)}")

            elif isinstance(value, (int, float)):
                print(f"{prefix}{col_num(value)}")

            else:
                print(f"{prefix}{value!r}")

        print(f"{_ind}{_name_prefix}{self.__repr_name__()}(")
        for a, v in self.__repr_args__(verbose=verbose, adapters=adapters):
            show(a, v, _ind + indent * " ")
        print(f"{_ind})")


class AdapterModel(BaseModel):

    adapter: NonEmptyStrictStr
    key: StrictStr
    arguments: Dict[NonEmptyStrictStr, Any] = Field(default_factory=dict)

    def compare_signature(self, other: "AdapterModel") -> bool:
        return (
            isinstance(other, AdapterModel) and
            other.adapter == self.adapter and
            other.arguments == self.arguments
        )


class Model(BaseModel, metaclass=ModelMeta):
    """
    Base model for all order entities.
    """

    def __repr_args__(self, *, verbose: bool = False, adapters: bool = False) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__(verbose=verbose, adapters=adapters)

        for attr, lazy_attr in self._lazy_attrs.items():
            # skip when field was originally skipped
            orig_field = self.__orig_fields__.get(attr)
            if orig_field and not orig_field.repr:
                continue

            # prepare the string representation of the value
            value = getattr(self, lazy_attr)
            if not adapters and isinstance(value, AdapterModel):
                value = self.__repr_adapter__(value)

            yield attr, value
