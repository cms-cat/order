# coding: utf-8

"""
Campaign definition.
"""


from __future__ import annotations
from typing import Dict


__all__ = ["GT", "Campaign"]


from typing import Dict

from order.models.base import Model, Lazy
from order.models.dataset import Dataset


class GT(Model):

    gt: str


class Campaign(Model):

    id: int
    name: str
    tier: Lazy[str]
    ecm: Lazy[float]
    recommended_gt: GT
    dataset: Lazy[Dict[str,Dataset]]
