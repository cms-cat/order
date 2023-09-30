# coding: utf-8

"""
Order-internal adapters, mainly used to avoid redundancies inside order-data.
"""

from __future__ import annotations


__all__ = ["OrderAdapter"]


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
        datasets = []
        for path in glob.glob(os.path.join(dataset_dir, "*.yaml")):
            with open(path, "r") as f:
                # allow multiple documents per file
                stream = yaml.load_all(f, Loader=yaml.SafeLoader)
                for i, entry in enumerate(stream):
                    if "name" not in entry:
                        raise AttributeError(
                            f"no field 'name' defined in enty {i} of dataset yaml file {path}",
                        )
                    if "id" not in entry:
                        raise AttributeError(
                            f"no field 'id' defined in enty {i} of dataset yaml file {path}",
                        )
                    datasets.append(
                        self.create_lazy_dataset_dict(campaign_name, entry["name"], entry["id"]),
                    )

        return Materialized(datasets=datasets)

    @classmethod
    def create_lazy_dataset_dict(cls, campaign_name: str, name: str, id: int) -> dict:
        return {
            "name": name,
            "id": id,
            "class_name": "Dataset",
            "adapter": {
                "adapter": "order_dataset",
                "arguments": {
                    "campaign_name": campaign_name,
                    "dataset_name": name,
                },
                "key": "dataset",
            },
        }


class DatasetAdapter(OrderAdapter):

    name = "order_dataset"

    def retrieve_data(
        self,
        data_location: str,
        *,
        campaign_name: str,
        dataset_name: str,
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self}")

        # build the yaml file path
        path = os.path.join(
            self.remove_scheme(data_location),
            "datasets",
            campaign_name,
            f"{dataset_name}.yaml",
        )
        if not os.path.exists(path):
            raise Exception(f"dataset file {path} not existing")

        # open the file and look for the dataset
        with open(path, "r") as f:
            stream = yaml.load_all(f, Loader=yaml.SafeLoader)
            for entry in stream:
                if entry.get("name") == dataset_name:
                    return Materialized(dataset=entry)

        raise Exception(f"no dataset entry with name '{dataset_name}' found in {path}")
