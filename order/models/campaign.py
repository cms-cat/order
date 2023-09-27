# coding: utf-8

from __future__ import annotations


__all__ = ["Campaign"]


from typing import Union
from pydantic import BaseModel

from order.adapters.base import AdapterData, DataProvider


class MyModel(BaseModel, validate_assignment=True):

    pass


class GT(BaseModel):

    gt: str


class Campaign(MyModel):
    """
    TODO:
        - read lazy_ecm from "ecm" in json
        - write lazy_ecm to "ecm" in json
        - prevent programmatic access to lazy_ecm
    """

    id: int
    name: str
    tier: str
    lazy_ecm: Union[int, AdapterData]
    recommended_gt: GT

    @property
    def ecm(self) -> float:
        if isinstance(self.lazy_ecm, AdapterData):
            self.lazy_ecm = DataProvider.instance().get_data(self.lazy_ecm)
        return self.lazy_ecm

    @ecm.setter
    def ecm(self, ecm: Union[int, AdapterData]) -> None:
        self.lazy_ecm = ecm
