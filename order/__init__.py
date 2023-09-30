# coding: utf-8
# flake8: noqa

"""
Pythonic class collection to structure and access CMS metadata.
"""


__all__ = [
    "Settings",
    "Lazy", "Model",
    "AdapterModel", "Adapter", "Materialized", "DataProvider",
    "UniqueObject", "LazyUniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
    "GenOrder", "DatasetInfo", "Dataset", "LazyDataset", "DatasetIndex",
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
from order.adapters.base import AdapterModel, Adapter, Materialized, DataProvider
from order.models.base import Model
from order.models.unique import (
    UniqueObject, LazyUniqueObject, UniqueObjectIndex, DuplicateObjectException,
    DuplicateNameException, DuplicateIdException,
)
from order.models.dataset import GenOrder, DatasetInfo, Dataset, LazyDataset, DatasetIndex
from order.models.campaign import Campaign

# import adapters to trigger their registration
import order.adapters.order
import order.adapters.das
# import order.adapters.dbs
# import order.adapters.xsdb
