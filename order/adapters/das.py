# coding: utf-8

from __future__ import annotations
import requests
from order.settings import Settings

__all__ = ["DASDatasetAdapter"]


from order.adapters.base import Adapter, Materialized


class DASDatasetAdapter(Adapter):

    name = "das_dataset"

    def retrieve_data(self, *, keys: list[str], dbs_instance: str = "prod/global") -> Materialized:
        # Support list of keys since we may have datasets with extensions in stat
        results = {}
        for key in keys:
            resource = f"https://cmsweb.cern.ch:8443/dbs/{dbs_instance}/DBSReader/files?dataset={key}&detail=True"  # noqa
            r = requests.get(
                resource,
                cert=Settings.instance().user_proxy,
                verify=False,
            )
            results[key] = r.json()

        out = {"n_files": 0,
               "n_events": 0,
               "lfns": [],
               "file_size": 0}
               
        for res in results.values():
            for file in res:
                out["n_files"] += 1
                out["n_events"] += file["event_count"]
                out["lfns"].append(file["logical_file_name"])
                out["file_size"] += file["file_size"]
                
        return Materialized(**out)

        
