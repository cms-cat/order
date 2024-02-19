# coding: utf-8
# flake8: noqa

"""
Pythonic class collection to structure and access CMS metadata.
"""


__all__ = [
    "Settings",
    "Lazy",
    "BaseModel", "Model", "AdapterModel",
    "Adapter", "Materialized", "DataProvider",
    "UniqueObject", "LazyUniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
    "ProcessIndex", "Process", "LazyProcess",
    "DatasetIndex", "Dataset", "LazyDataset", "DatasetVariation", "GenOrder",
    "Campaign",
]


# package infos
from order.__meta__ import (
    __doc__, __author__, __email__, __copyright__, __credits__, __contact__, __license__,
    __status__, __version__,
)

# provisioning imports
from order.settings import Settings
from order.types import Lazy
from order.models.base import BaseModel, Model, AdapterModel
from order.adapters.base import Adapter, Materialized, DataProvider
from order.models.unique import (
    UniqueObject, LazyUniqueObject, UniqueObjectIndex, DuplicateObjectException,
    DuplicateNameException, DuplicateIdException,
)
from order.models.process import ProcessIndex, Process, LazyProcess
from order.models.dataset import DatasetIndex, Dataset, LazyDataset, DatasetVariation, GenOrder
from order.models.campaign import Campaign

# import adapters to trigger their registration
import order.adapters.order
import order.adapters.das
# import order.adapters.dbs
# import order.adapters.xsdb

# ipython magics
from order.magics import register_magics
register_magics()
