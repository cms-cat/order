# coding: utf-8

from __future__ import annotations


__all__ = ["GenOrder", "DatasetInfo", "Dataset", "LazyDataset", "DatasetIndex"]


import enum

from pydantic import field_validator

from order.types import Union, List, Dict, Field, NonEmptyStrictStr, PositiveStrictInt, Lazy
from order.models.base import Model
from order.models.unique import UniqueObject, LazyUniqueObject, UniqueObjectIndex


# class File(Model):
#     logical_file_name: str
#     block_name: str
#     check_sum: int
#     last_modification_date: int
#     file_type: str


class GenOrder(enum.Enum):

    unknown: str = "unknown"
    lo: str = "lo"
    nlo: str = "nlo"
    nnlo: str = "nnlo"
    n3lo: str = "n3lo"

    def __str__(self) -> str:
        return self.value


class DatasetInfo(Model):

    keys: List[NonEmptyStrictStr]
    gen_order: NonEmptyStrictStr = Field(default=str(GenOrder.unknown))
    n_files: Lazy[PositiveStrictInt]
    n_events: Lazy[PositiveStrictInt]
    lfns: Lazy[List[NonEmptyStrictStr]]

    @field_validator("gen_order", mode="after")
    @classmethod
    def validate_gen_order(cls, gen_order: str) -> str:
        try:
            return str(GenOrder[gen_order])
        except KeyError:
            raise ValueError(f"unknown gen_order '{gen_order}'")


class Dataset(UniqueObject):

    info: Dict[str, DatasetInfo]

    def __getitem__(self, name: str) -> DatasetInfo:
        return self.get_info(name)

    def get_info(self, name: str) -> DatasetInfo:
        return self.info[name]

    def set_info(self, name: str, info: DatasetInfo) -> None:
        if not isinstance(info, DatasetInfo):
            raise TypeError(f"expected info to be DatasetInfo object, but got '{info}'")
        self.info[name] = info

    @property
    def keys(self) -> list[NonEmptyStrictStr]:
        return self.info["nominal"].keys

    @property
    def gen_order(self) -> GenOrder:
        return self.info["nominal"].gen_order

    @property
    def n_files(self) -> int:
        return self.info["nominal"].n_files

    @property
    def n_events(self) -> int:
        return self.info["nominal"].n_events

    @property
    def lfns(self) -> list[NonEmptyStrictStr]:
        return self.info["nominal"].lfns


class LazyDataset(LazyUniqueObject):

    class_name: NonEmptyStrictStr = Field(default=Dataset)


class DatasetIndex(UniqueObjectIndex):

    class_name: NonEmptyStrictStr = Field(default=Dataset)
    objects: Lazy[List[Union[Dataset, LazyDataset]]] = Field(default_factory=list, repr=False)
