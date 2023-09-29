# coding: utf-8

from __future__ import annotations


__all__ = ["DBSFilesAdapter"]


import requests

from order.settings import Settings
from order.adapters.base import Adapter, Materialized


class DBSFilesAdapter(Adapter):

    name = "dbs_files"

    def retrieve_data(self, *, dataset_key: str, dbs_instance: str = "prod/global") -> Materialized:
        resource = f"https://cmsweb.cern.ch:8443/dbs/{dbs_instance}/DBSReader/files?dataset={dataset_key}&detail=True"  # noqa
        r = requests.get(
            resource,
            cert=Settings.instance().user_proxy,
            verify=False,
        )
        return Materialized(data=r.json())
