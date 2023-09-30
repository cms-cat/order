# coding: utf-8

"""
Campaign definition.
"""

from __future__ import annotations


__all__ = ["GT", "Campaign"]


from order.types import Lazy, Field
from order.models.base import Model
from order.models.dataset import DatasetIndex


class GT(Model):

    gt: str


class Campaign(Model):

    id: int
    name: str
    tier: Lazy[str]
    ecm: Lazy[float]
    recommended_gt: GT
    datasets: DatasetIndex = Field(default_factory=DatasetIndex)
