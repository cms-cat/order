# coding: utf-8

"""
Custom type definitions and shorthands to simplify imports of types that are spread across multiple
packages.
"""

from __future__ import annotations


__all__ = []


# warn when imported while _in_ this directory
import os
thisdir = os.path.dirname(os.path.abspath(__file__))
if os.path.realpath(thisdir) == os.path.realpath(os.getcwd()):
    msg = """
NOTE: you are running a python interpreter inside the "order" source directory which
      is highly discouraged as it leads to unintended local imports in builtin packages
"""
    print(msg, flush=True)


import re
from collections.abc import KeysView, ValuesView  # noqa
from typing import (  # noqa
    Any, Union, TypeVar, ClassVar, List, Tuple, Sequence, Set, Dict, Callable, Iterable, Generator,
)
from types import GeneratorType  # noqa

from typing_extensions import Annotated, _AnnotatedAlias as AnnotatedType  # noqa
from annotated_types import Ge, Len  # noqa
from pydantic import Strict, StrictInt, StrictFloat, StrictStr, StrictBool  # noqa
from pydantic.fields import FieldInfo  # noqa


#: Strict positive integer.
PositiveStrictInt = Annotated[StrictInt, Ge(0)]

#: Strict non-empty string.
NonEmptyStrictStr = Annotated[StrictStr, Len(min_length=1)]

#: Generic type variable, more stringent than Any.
T = TypeVar("T")


class Lazy(object):
    """
    Annotation factory that adds :py:class:`AdapterModel` to the metadata of the returned annotated
    type.
    """

    @classmethod
    def __class_getitem__(cls, types: tuple[type]) -> type:
        from order.models.base import AdapterModel

        if not isinstance(types, tuple):
            types = (types,)
        return Union[tuple(map(cls.make_strict, types)) + (AdapterModel,)]

    @classmethod
    def parse_annotation(cls, type_str: str) -> list[str] | None:
        m = re.match(r"^Lazy\[(.+)\]$", type_str)
        return m and [s.strip() for s in m.group(1).split(",")]

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
        if (
            getattr(type_, "__dict__", None) is not None and
            type_.__dict__.get("_name") in ("Dict", "List")
        ):
            return False

        return True
