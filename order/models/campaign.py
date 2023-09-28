# coding: utf-8

"""
Campaign definition.
"""


from __future__ import annotations


__all__ = ["GT", "Campaign"]


from order.models.base import Model, Lazy


class GT(Model):

    gt: str


class Campaign(Model):

    id: int
    name: str
    tier: str
    ecm: Lazy[float]
    recommended_gt: GT
