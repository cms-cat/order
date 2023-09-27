# coding: utf-8

from __future__ import annotations


__all__ = ["Campaign"]


from typing import Union, Any
from pydantic import BaseModel, Field

from order.adapters.base import AdapterData, DataProvider


BaseModelMeta = type(BaseModel)


class MyMeta(BaseModelMeta):

    def __new__(metacls, classname: str, bases: tuple, classdict: dict[str, Any]):
        # check for union types with adapters
        # if classname == "Campaign":
        #     from IPython import embed; embed()

        def fget(inst):
            return 1234567

        def fset(inst, value):
            inst.id = value

        classdict["ecm"] = property(fget=fget, fset=fset)

        # create the class
        cls = BaseModelMeta.__new__(metacls, classname, bases, classdict)  # TODO: use super()

        return cls


class MyModel(BaseModel, metaclass=MyMeta):  #, validate_assignment=True):  # TODO: add to meta

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
    lazy_ecm: Union[int, AdapterData] = Field(
        alias="ecm",
        serialization_alias="ecm",
    )
    recommended_gt: GT

    # @property
    # def ecm(self) -> float:
    #     if isinstance(self.lazy_ecm, AdapterData):
    #         self.lazy_ecm = DataProvider.instance().get_data(self.lazy_ecm)
    #     return self.lazy_ecm

    # @ecm.setter
    # def ecm(self, ecm: Union[int, AdapterData]) -> None:
    #     self.lazy_ecm = ecm
