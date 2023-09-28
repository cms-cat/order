# coding: utf-8

"""
Cross section data base (XSDB) adapters.
"""

from __future__ import annotations


__all__ = ["XSDBAdapter"]


from order.adapters.base import Adapter, Materialized


class XSDBAdapter(Adapter):

    name = "xsdb"

    def retrieve_data(self, *, foo: int) -> Materialized:
        return Materialized(ecm=foo * 2, data_tier="nano")
