# coding: utf-8

from __future__ import annotations


__all__ = ["DASDatasetAdapter"]


from order.adapters.base import Adapter, Materialized


class DASDatasetAdapter(Adapter):

    name = "das_dataset"

    def retrieve_data(self, *, keys: list[str]) -> Materialized:
        if keys[0].startswith("/SCALE"):
            return Materialized(n_events=1, n_files=1)
        return Materialized(n_events=5_000_000, n_files=12)


class DASLFNsAdapter(Adapter):

    name = "das_lfns"

    def retrieve_data(self, *, keys: list[str]) -> Materialized:
        if keys[0].startswith("/SCALE"):
            return Materialized(lfns=["/SCALE/b/NANOAODSIM"])
        return Materialized(lfns=["/a/b/NANOAODSIM"])
