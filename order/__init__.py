# coding: utf-8
# flake8: noqa

"""
Pythonic class collection to structure and access CMS metadata.
"""


__all__ = [
    "Settings",
    "Lazy", "Model",
    "AdapterModel", "Adapter", "Materialized", "DataProvider",
    "UniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
]


# package infos
from order.__meta__ import (
    __doc__, __author__, __email__, __copyright__, __credits__, __contact__, __license__,
    __status__, __version__,
)

# provisioning imports
from order.settings import Settings
from order.models.base import Lazy, Model
from order.models.unique import (
    UniqueObject, UniqueObjectIndex, DuplicateObjectException, DuplicateNameException,
    DuplicateIdException,
)
from order.adapters.base import AdapterModel, Adapter, Materialized, DataProvider

# import adapters to trigger their registration
import order.adapters.order
import order.adapters.dbs
import order.adapters.xsdb
