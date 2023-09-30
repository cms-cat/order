# coding: utf-8

"""
Campaign definition.
"""

from __future__ import annotations


__all__ = ["Campaign"]


from order.types import Lazy, NonEmptyStrictStr, StrictFloat, Field
from order.models.unique import UniqueObject
from order.models.dataset import DatasetIndex


class Campaign(UniqueObject):

    tier: Lazy[NonEmptyStrictStr]
    ecm: Lazy[StrictFloat]
    recommended_global_tag: NonEmptyStrictStr
    datasets: DatasetIndex = Field(default_factory=DatasetIndex)
