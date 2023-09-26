# coding: utf-8

from __future__ import annotations

import os
import glob
from typing import Any

import yaml

from order.adapters.base import Adapter


class DatasetsAdapter(Adapter):

    name = "order_datasets"

    def get_cache_key(self, *, campaign_name: str) -> tuple:
        return (campaign_name,)

    def retrieve_data(self, data_location: str, *, campaign_name: str) -> dict[str, Any]:
        # only supporting local evaluation for now
        if not data_location.startswith("file://"):
            raise NotImplementedError(f"data location {data_location} not handled by {self}")

        # read yaml files in the datasets directory
        dataset_dir = os.path.join(
            data_location.replace("file://", ""),
            "datasets",
            campaign_name,
        )
        datasets = {}
        for path in glob.glob(os.path.join(dataset_dir, "*.yaml")):
            with open(path, "r") as f:
                data = yaml.full_load(f)
            if "name" not in data:
                raise KeyError(f"no field 'name' defined in dataset yaml file {path}")
            datasets[data["name"]] = data

        return datasets
