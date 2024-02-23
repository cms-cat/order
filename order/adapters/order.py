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
from order.models.dataset import LazyDataset
from order.models.process import LazyProcess
from order.models.uncertainty import LazyUncertainty

class OrderAdapter(Adapter):

    # order adapters need to DataProvider's data_location in retrieve_data
    needs_data_location = True


class CampaignAdapter(OrderAdapter):

    name = "order_campaign"

    def retrieve_data(
        self,
        data_location: str,
        *,
        campaign_name: str,
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the yaml file path
        path = os.path.join(
            self.remove_scheme(data_location),
            "campaigns",
            f"{campaign_name}.yaml",
        )
        if not os.path.exists(path):
            raise FileNotFoundError(f"campaign file {path} does not exist")

        # open the file and look for the campaign
        with open(path, "r") as f:
            stream = yaml.load_all(f, Loader=yaml.SafeLoader)
            for entry in stream:
                if entry.get("name") == campaign_name:
                    return Materialized(campaign=entry)
                # only one campaign per file allowed
                break

        raise Exception(f"no campaign entry with name '{campaign_name}' found in {path}")


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
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the directory in which to look for dataset files
        dataset_dir = os.path.join(self.remove_scheme(data_location), "datasets", campaign_name)

        # read yaml files in the datasets directory
        datasets = []
        paths = glob.glob(os.path.join(dataset_dir, "*.yaml"))
        for path in paths:
            with open(path, "r") as f:
                # allow multiple documents per file
                stream = yaml.load_all(f, Loader=yaml.SafeLoader)
                for i, entry in enumerate(stream):
                    if "name" not in entry:
                        raise AttributeError(
                            f"no field 'name' defined in entry {i} of dataset yaml file {path}",
                        )
                    if "id" not in entry:
                        raise AttributeError(
                            f"no field 'id' defined in entry {i} of dataset yaml file {path}",
                        )
                    datasets.append(
                        LazyDataset.create_lazy_dict(campaign_name, entry["name"], entry["id"]),
                    )

        return Materialized(datasets=datasets)


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
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the yaml file path
        path = os.path.join(
            self.remove_scheme(data_location),
            "datasets",
            campaign_name,
            f"{dataset_name}.yaml",
        )
        if not os.path.exists(path):
            raise Exception(f"dataset file {path} does not exist")

        # open the file and look for the dataset
        with open(path, "r") as f:
            stream = yaml.load_all(f, Loader=yaml.SafeLoader)
            for entry in stream:
                if entry.get("name") == dataset_name:
                    return Materialized(dataset=entry)

        raise Exception(f"no dataset entry with name '{dataset_name}' found in {path}")


class ProcessesAdapter(OrderAdapter):

    name = "order_processes"

    def retrieve_data(
        self,
        data_location: str,
        *,
        process_names: list[str],
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the directory in which to look for process files
        process_dir = os.path.join(self.remove_scheme(data_location), "processes")

        # read yaml files in the process directory
        processes = []
        paths = sum(
            (glob.glob(os.path.join(process_dir, f"{name}.yaml")) for name in process_names),
            [],
        )
        for path in sorted(set(paths), key=paths.index):
            if not os.path.exists(path):
                raise Exception(f"process file {path} does not exist")

            with open(path, "r") as f:
                # allow multiple documents per file
                stream = yaml.load_all(f, Loader=yaml.SafeLoader)
                for i, entry in enumerate(stream):
                    if "name" not in entry:
                        raise AttributeError(
                            f"no field 'name' defined in entry {i} of process yaml file {path}",
                        )
                    if "id" not in entry:
                        raise AttributeError(
                            f"no field 'id' defined in entry {i} of process yaml file {path}",
                        )
                    processes.append(LazyProcess.create_lazy_dict(entry["name"], entry["id"]))

        return Materialized(processes=processes)


class ProcessAdapter(OrderAdapter):

    name = "order_process"

    def retrieve_data(
        self,
        data_location: str,
        *,
        process_name: str,
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the yaml file path
        path = os.path.join(
            self.remove_scheme(data_location),
            "processes",
            f"{process_name}.yaml",
        )
        if not os.path.exists(path):
            raise Exception(f"process file {path} does not exist")

        # open the file and look for the process
        with open(path, "r") as f:
            stream = yaml.load_all(f, Loader=yaml.SafeLoader)
            for entry in stream:
                if entry.get("name") == process_name:
                    return Materialized(process=entry)

        raise Exception(f"no process entry with name '{process_name}' found in {path}")



class uncertaintiesAdapter(OrderAdapter):
    name ="order_uncertainties"
    def retrieve_data(
            self,
            data_location: str,
            *,
            directories: list[str]                    
    ) -> Materialized:
        # only supporting local evaluation for now
        if not self.location_is_local(data_location):
            raise NotImplementedError(f"non-local location {data_location} not handled by {self!r}")

        # build the yaml file path.
        # We need to find the directory by looking at the deepest existent
        # directory of the uncertainty_type hierarchy.
        uncertainties = []
        basepath = os.path.join(self.remove_scheme(data_location), "uncertainties")
        for directory in directories:
            # loop over all file in the directory
            for file in os.listdir(os.path.join(basepath, directory)):
                if os.path.isfile(os.path.join(basepath, directory, file)):
                    #load the file and loop over entities
                    with open(os.path.join(basepath, directory, file), "r") as f:
                        stream = yaml.load_all(f, Loader=yaml.SafeLoader)
                        for entry in stream:
                            uncertainties.append(LazyUncertainty.create_lazy_dict(
                                entry["name"], entry["id"],
                                entry["uncertainty_type"], os.path.join(directory,file)))
        
        return Materialized(uncertainties=uncertainties)
