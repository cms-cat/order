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
