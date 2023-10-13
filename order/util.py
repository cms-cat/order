# coding: utf-8

"""
Helpful utilities.
"""

from __future__ import annotations


__all__ = [
    "no_value", "has_attr", "colored", "maybe_colored", "uncolored", "create_hash", "validated",
    "DotAccessProxy", "Repr",
]


import os
import sys
import re
import random
import hashlib
import functools
from collections import deque

try:
    import ipykernel
    import ipykernel.iostream
except ImportError:
    ipykernel = None

from order.types import Any, Callable
import order.settings as settings


#: Unique object denoting *no value*.
no_value = object()


def has_attr(obj: Any, attr: str, placeholder: Any = no_value) -> bool:
    """
    Safer version of :py:func:`hasattr` that includes attributes dynamically provided by hooks such
    as ``__getattr__``.
    """
    return getattr(obj, attr, placeholder) != placeholder


# terminal codes for colors
colors = {
    "default": 39,
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "light_gray": 37,
    "dark_gray": 90,
    "light_red": 91,
    "light_green": 92,
    "light_yellow": 93,
    "light_blue": 94,
    "light_magenta": 95,
    "light_cyan": 96,
    "white": 97,
}

# terminal codes for backgrounds
backgrounds = {
    "default": 49,
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "light_gray": 47,
    "dark_gray": 100,
    "light_red": 101,
    "light_green": 102,
    "light_yellow": 103,
    "light_blue": 104,
    "light_magenta": 105,
    "light_cyan": 106,
    "white": 107,
}

# terminal codes for styles
styles = {
    "default": 0,
    "bright": 1,
    "dim": 2,
    "underlined": 4,
    "blink": 5,
    "inverted": 7,
    "hidden": 8,
}


def colored(
    msg: str,
    color: str | int | None = None,
    background: str | int | None = None,
    style: str | int | None = None,
    force: bool = False,
) -> str:
    """
    Return the colored version of a string *msg*. For *color*, *background* and *style* options, see
    https://misc.flogisoft.com/bash/tip_colors_and_formatting. They can also be explicitely set to
    ``"random"`` to get a random value. Unless *force* is *True*, the *msg* string is returned
    unchanged in case the output is neither a tty nor an IPython output stream.
    """
    if not force:
        tty = False
        ipy = False

        try:
            tty = os.isatty(sys.stdout.fileno())
        except:
            pass

        if not tty and ipykernel is not None:
            ipy = isinstance(sys.stdout, ipykernel.iostream.OutStream)

        if not tty and not ipy:
            return msg

    # get the color
    if color == "random":
        color = random.choice(list(colors.values()))
    else:
        color = colors.get(color, colors["default"])

    # get the background
    if background == "random":
        background = random.choice(list(backgrounds.values()))
    else:
        background = backgrounds.get(background, backgrounds["default"])

    # get multiple styles
    if not isinstance(style, (tuple, list, set)):
        style = (style,)
    style_values = list(styles.values())
    style = ";".join(
        str(random.choice(style_values) if s == "random" else styles.get(s, styles["default"]))
        for s in style
    )

    return f"\033[{style};{background};{color}m{msg}\033[0m"


def maybe_colored(msg: str, *args, **kwargs) -> str:
    """
    Returns a colored representation of *msg* using :py:func:`colored` if the global settings allow
    coloring, and the unchanged *msg* otherwise.
    """
    return colored(msg, *args, **kwargs) if settings.colors else msg


# compiled regular expression for removing all terminal style codes
uncolor_cre = re.compile(r"(\x1B\[[0-?]*[ -/]*[@-~])")


def uncolored(s: str) -> str:
    """
    Removes all terminal style codes from a string *s* and returns it.
    """
    return uncolor_cre.sub("", s)


def create_hash(inp: Any, l: int = 10, algo: str = "sha256", to_int: bool = False) -> str | int:
    """
    Takes an arbitrary input *inp* and creates a hexadecimal string hash based on an algorithm
    *algo*. For valid algorithms, see python's hashlib. *l* corresponds to the maximum length of the
    returned hash and is limited by the length of the hexadecimal representation produced by the
    hashing algorithm. When *to_int* is *True*, the decimal integer representation is returned.
    """
    h = getattr(hashlib, algo)(str(inp).encode("utf-8")).hexdigest()[:l]
    return int(h, 16) if to_int else h


class validated(property):
    """
    Shorthand for a property definition that can be used as a decorator to wrap around a validation
    function. Example:

    .. code-block:: python

         class MyClass(object):

            def __init__(self):
                self._foo: str = None

            @validate
            def foo(self, foo: str) -> str:
                if not isinstance(foo, str):
                    raise TypeError(f"not a string: '{str}'")
                return foo

        myInstance = MyClass()
        myInstance.foo = 123   -> TypeError
        myInstance.foo = "bar" -> ok
        print(myInstance.foo)  -> prints "bar"

    In the exampe above, set/get calls target the instance member ``_foo``, i.e. "_<function_name>".
    The attribute name can be configured by setting *attr*.

    If *setter* (*deleter*) is *True* (the default), a setter (deleter) method is booked as well.
    Prior to updating the member when the setter is called, *fvalidate* is invoked which may
    implement validation checks.

    In case the attribute has not been added before the getter is called, *default* is returned if
    provided. Otherwise, an *AttributeError* might be raised.
    """

    def __init__(
        self,
        fvalidate: Callable[[Any], Any] | None = None,
        setter: bool = True,
        deleter: bool = True,
        default: Any = no_value,
        attr: str | None = None,
    ):
        # store keyword arguments for when used as deferred decorator in __call__
        self._kwargs = {
            "setter": setter,
            "deleter": deleter,
            "default": default,
            "attr": attr,
        }

        # only register the property if fvalidate is set
        if fvalidate is not None:
            self.fvalidate = fvalidate

            # default attribute
            if attr is None:
                attr = f"_{fvalidate.__name__}"

            # call the super constructor with generated methods
            super().__init__(
                functools.wraps(fvalidate)(self._fget(attr, default)),
                self._fset(attr) if setter else None,
                self._fdel(attr) if deleter else None,
            )

    def __call__(self, fvalidate: Callable[[Any], Any]) -> Any:
        return self.__class__(fvalidate, **self._kwargs)

    def _fget(self, attr: str, default: Any) -> Callable:
        """
        Build and returns the property's *fget* method for the attribute *attr*.
        """
        if default == no_value:
            def fget(inst) -> Any:
                return getattr(inst, attr)
        else:
            def fget(inst) -> Any:
                return getattr(inst, attr, default)

        return fget

    def _fset(self, attr: str) -> Callable:
        """
        Build and returns the property's *fdel* method for the attribute *attr*.
        """
        def fset(inst, value: Any) -> None:
            # the setter uses the wrapped function as well
            # to allow for value checks
            value = self.fvalidate(inst, value)
            setattr(inst, attr, value)

        return fset

    def _fdel(self, attr: str) -> Callable:
        """
        Build and returns the property's *fdel* method for the attribute *attr*.
        """
        def fdel(inst) -> None:
            delattr(inst, attr)

        return fdel


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

    Additionally, if a *dir* callable is provided, it is invoked by the internal :py:meth:`__dir__`
    method.
    """

    def __init__(
        self,
        getter: Callable[[str], Any],
        setter: Callable[[str, Any], None] | None = None,
        dir: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        super().__init__()

        self._getter = getter
        self._setter = setter
        self._dir = dir

        # autocompletion of the python interpreter works by running dir(object), followed by
        # getattr(attr) for all attributes returned by the former call, sorted in ascending order;
        # the __getattr__ calls could lead to expensive payloads (e.g. materialization through
        # adapters) that are undesired when just evaluating completion choices; hence, store a set
        # of attributes previously returned by dir() and if an attribute is requested that is in
        # that set, skip the getter invocation
        self._completion_attrs = deque()

    def __call__(self, *args, **kwargs) -> Any:
        return self._getter(*args, **kwargs)

    def __getattr__(self, attr: str) -> Any:
        if attr.startswith("__") or attr in ("_getter", "_setter", "_dir", "_completion_attrs"):
            return super().__getattr__(attr)

        # as described above, when attr was part of a previous dir() call, just return None
        # since the autocompletion check allows all values if no AttributeError is raised
        if self._completion_attrs and attr == self._completion_attrs[0]:
            self._completion_attrs.popleft()
            return None
        self._completion_attrs.clear()

        try:
            return self._getter(attr)
        except KeyError as e:
            raise AttributeError(*e.args)

    def __setattr__(self, attr: str, value: Any) -> None:
        if attr.startswith("__") or attr in ("_getter", "_setter", "_dir", "_completion_attrs"):
            super().__setattr__(attr, value)
            return

        if self._setter is None:
            raise Exception(
                f"cannot set attribute '{attr}', not setter defined on {self.__class__.__name__}",
            )
        self._setter(attr, value)

    def __dir__(self, for_completion: bool = True) -> list[str]:
        # get the list of attributes
        attrs = list(self._dir()) if callable(self._dir) else []

        # make it unique but preserve the order
        attrs = sorted(set(attrs), key=attrs.index)

        # store them when requested for autocompletion
        if for_completion:
            self._completion_attrs.clear()
            self._completion_attrs.extend(sorted(attrs))

        return attrs


class Repr(object):
    """
    Factory for objects with a configurable representation.
    """

    def __init__(self, value: Any) -> None:
        super().__init__()

        self.value = value

    def __repr__(self) -> str:
        return str(self.value)
