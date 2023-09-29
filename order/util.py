# coding: utf-8

"""
Helpful utilities.
"""

from __future__ import annotations


__all__ = ["no_value", "create_hash", "DotAccessProxy"]


import hashlib
from typing import Any, Callable


#: Unique object denoting *no value*.
no_value = object()


def create_hash(inp: Any, l: int = 10, algo: str = "sha256", to_int: bool = False) -> str | int:
    """
    Takes an arbitrary input *inp* and creates a hexadecimal string hash based on an algorithm
    *algo*. For valid algorithms, see python's hashlib. *l* corresponds to the maximum length of the
    returned hash and is limited by the length of the hexadecimal representation produced by the
    hashing algorithm. When *to_int* is *True*, the decimal integer representation is returned.
    """
    h = getattr(hashlib, algo)(str(inp).encode("utf-8")).hexdigest()[:l]
    return int(h, 16) if to_int else h


class DotAccessProxy(object):
    """
    Proxy object that provides simple attribute access to values that are retrieved by a *getter*
    and optionally set through a *setter*. Example:

    .. code-block:: python

        my_dict = {"foo": 123}

        proxy = DotAccessProxy(my_dict.__getattr__)
        proxy.foo
        # -> 123
        proxy.bar
        # -> AttributeError

        proxy = DotAccessProxy(my_dict.get)
        proxy.foo
        # -> 123
        proxy.bar
        # -> None

        proxy = DotAccessProxy(my_dict.get, my_dict.__setitem__)
        proxy.foo
        # -> 123
        proxy.bar
        # -> None
        proxy.bar = 99
        proxy.bar
        # -> 99
    """

    def __init__(
        self,
        getter: Callable[[str], Any],
        setter: Callable[[str, Any], None] | None = None,
    ) -> None:
        super().__init__()

        self._getter = getter
        self._setter = setter

    def __call__(self, *args, **kwargs):
        return self._getter(*args, **kwargs)

    def __getattr__(self, attr: str) -> Any:
        if attr.startswith("__") or attr in ("_getter", "_setter"):
            return super().__getattr__(attr)

        try:
            return self._getter(attr)
        except KeyError as e:
            raise AttributeError(*e.args)

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr.startswith("__") or attr in ("_getter", "_setter"):
            super().__setattr__(attr, value)
            return

        if self._setter is None:
            raise Exception(
                f"cannot set attribute '{attr}', not setter defined on {self.__class__.__name__}",
            )
        self._setter(attr, value)
