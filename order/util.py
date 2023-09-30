# coding: utf-8

"""
Helpful utilities.
"""

from __future__ import annotations


__all__ = ["no_value", "colored", "uncolored", "create_hash", "DotAccessProxy"]


import os
import sys
import re
import random
import hashlib

try:
    import ipykernel
    import ipykernel.iostream
except ImportError:
    ipykernel = None

from order.types import Any, Callable


#: Unique object denoting *no value*.
no_value = object()


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


def colored(msg, color=None, background=None, style=None, force=False):
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


# compiled regular expression for removing all terminal style codes
uncolor_cre = re.compile(r"(\x1B\[[0-?]*[ -/]*[@-~])")


def uncolored(s):
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

    def __call__(self, *args, **kwargs) -> Any:
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
