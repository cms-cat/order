# coding: utf-8
# flake8: noqa

"""
Pythonic class collection to structure and access CMS metadata.
"""


__all__ = ["AdapterData", "Adapter", "DataProvider"]


# package infos
from order.__meta__ import (
    __doc__, __author__, __email__, __copyright__, __credits__, __contact__, __license__,
    __status__, __version__,
)

# provisioning imports
from order.adapters.base import AdapterData, Adapter, DataProvider
import order.adapters.order
import order.adapters.xsdb
