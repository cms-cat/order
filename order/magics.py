# coding: utf-8

"""
IPython magics.
"""

from __future__ import annotations


__all__ = []


import argparse
import shlex

from order.util import maybe_colored


def create_magics() -> type | None:
    try:
        import IPython.core as ipc
    except ImportError:
        return None

    @ipc.magic.magics_class
    class OrderMagics(ipc.magic.Magics):

        @ipc.magic.line_magic("od.show")
        def show(self, line: str) -> None:
            from order.models.base import BaseModel

            err = lambda msg: print(f"{maybe_colored('od.show', color='red')}: {msg}")

            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument("attr")
            parser.add_argument("flags", nargs="*")
            args = parser.parse_args(shlex.split(line))

            # get the model
            model = get_ipython().ev(args.attr)  # noqa
            if not isinstance(model, BaseModel):
                err(f"not a model instance: {model}")
                return

            # build arguments
            kwargs = {}
            known_flags = BaseModel._model_show_flags
            for flag in args.flags:
                if flag in known_flags:
                    kwargs[flag] = True
                else:
                    err(f"unknown flag: {flag}")
                    err(f"known flags: {', '.join(known_flags)}")

            # show the model
            model.model_show(**kwargs)

    return OrderMagics


def register_magics(*args, **kwargs) -> None:
    """
    Registers order-related IPython magic methods, forwarding all *args* and *kwargs* to
    :py:func:`create_magics`.

    - ``%od.show``: Calls :py:func:`BaseModel.model_show` of a model. When provided, additional
        flags "verbose" and "adapters" are considered *True* and forwarded as keyword arguments.
    """
    ipy = None
    magics = None

    try:
        ipy = get_ipython()
    except NameError:
        # print("no running notebook kernel found")
        pass

    # create the magics
    if ipy:
        magics = create_magics(*args, **kwargs)

    # register them
    if ipy and magics:
        ipy.register_magics(magics)
