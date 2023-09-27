# coding: utf-8

"""
Cross section data base (XSDB) adapters.
"""

from __future__ import annotations


__all__ = ["XSDBAdapter"]


from order.adapters.base import Adapter


class XSDBAdapter(Adapter):

    name = "xsdb"

    def get_cache_key(self, *, foo: str) -> tuple:
        return (foo,)

    def retrieve_data(self, *, foo: str) -> float:
        return foo * 2.0
