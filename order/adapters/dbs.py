# coding: utf-8

from __future__ import annotations


__all__ = ["DBSAdapter"]


from order.adapters.base import Adapter, Materialized
from order.util import query_dbs


class DBSAdapter(Adapter):

    name = "dbs_adapter"

    def retrieve_data(self, *, dataset_key: str) -> Materialized:
        dbs_out = query_dbs(dataset_key)
        return Materialized(data=dbs_out)
