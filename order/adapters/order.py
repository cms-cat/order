# coding: utf-8

"""
Order-internal adapters, mainly used to avoid redundancies inside order-data.
"""

from __future__ import annotations


__all__ = ["DatasetsAdapter"]


import os
import glob

import yaml

from order.adapters.base import Adapter, Materialized


class OrderAdapter(Adapter):

    # order adapters need to DataProvider's data_location in retrieve_data
    needs_data_location = True


class DatasetsAdapter(OrderAdapter):

    name = "order_datasets"

    def retrieve_data(
        self,
        data_location: str,
        *,
        campaign_name: str,
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self}")

        # build the directory in which to look for dataset files
        dataset_dir = os.path.join(self.remove_scheme(data_location), "datasets", campaign_name)

        # read yaml files in the datasets directory
        datasets = {}
        for path in glob.glob(os.path.join(dataset_dir, "*.yaml")):
            with open(path, "r") as f:
                # allow multiple documents per file
                for data in yaml.load_all(f, Loader=yaml.SafeLoader):
                    if "name" not in data:
                        raise KeyError(f"no field 'name' defined in dataset yaml file {path}")
                    datasets[data["name"]] = data

        return Materialized(datasets=datasets)
