# coding: utf-8

from __future__ import annotations


__all__ = ["DatasetIndex", "Dataset", "LazyDataset", "DatasetVariation", "GenOrder"]


import enum
import copy

from pydantic import Field, field_validator

from order.types import (
    Union, List, Dict, NonEmptyStrictStr, PositiveStrictInt, Lazy, ClassVar, GeneratorType, Any,
)
from order.util import has_attr, validated
from order.models.base import Model
from order.models.unique import UniqueObjectBase, UniqueObject, LazyUniqueObject, UniqueObjectIndex
# from order.models.mixins import CopyMixin


class DatasetIndex(UniqueObjectIndex):

    class_name: NonEmptyStrictStr = Field(default="Dataset", frozen=True)
    objects: Lazy[List[Union["LazyDataset", "Dataset"]]] = Field(default_factory=list, repr=False)


class LazyDataset(LazyUniqueObject):

    class_name: NonEmptyStrictStr = Field(default="Dataset", frozen=True)

    @classmethod
    def create_lazy_dict(cls, campaign_name: str, name: str, id: int) -> dict:
        return {
            "name": name,
            "id": id,
            "class_name": "Dataset",
            "adapter": {
                "adapter": "order_dataset",
                "key": "dataset",
                "arguments": {
                    "campaign_name": campaign_name,
                    "dataset_name": name,
                },
            },
        }


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


class DatasetVariation(Model):

    keys: List[NonEmptyStrictStr] = Field(frozen=True)
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

    def __copy__(self) -> "DatasetVariation":
        inst = super().__copy__()

        # shallow copy of keys
        with self._unfreeze_field("keys"):
            inst.keys = copy.copy(inst.keys)

        # shallow copy of the lfns if not materialized yet
        if isinstance(inst.lazy_lfns, list):
            inst.lfns = copy.copy(inst.lfns)

        return inst


class Dataset(UniqueObject):

    variations: Dict[str, DatasetVariation] = Field(frozen=True)

    lazy_cls: ClassVar[UniqueObjectBase] = LazyDataset

    @validated(default=None)
    def campaign(self, campaign: "Campaign" | None) -> "Campaign":
        # do nothing when the previous campaign matches the new one
        if campaign == self.campaign:
            return campaign

        # deregister from previous campaign
        if self.campaign:
            self.campaign.datasets.remove(self, skip_callback=True)

        # None case
        if campaign is None:
            return campaign

        # type check
        if not isinstance(campaign, Campaign):
            raise TypeError(f"expected Campaign object, but got '{campaign}'")

        # add to the index if not already in there
        if self not in campaign.datasets:
            campaign.datasets.add(self, skip_callback=True)

        return campaign

    def __copy__(self) -> "Dataset":
        copied = super().__copy__()

        # shallow copy the variations dict
        with copied._unfreeze_field("variations"):
            copied.variations = copy.copy(copied.variations)

        # drop the campaign reference
        copied.campaign = None

        # setup objects if not triggered by model_copy
        if not self._copy_triggered_by_model:
            copied._setup_objects()

        return copied

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Dataset:
        copied = super().__deepcopy__(memo=memo)

        # setup objects if not triggered by model_copy
        if not self._copy_triggered_by_model:
            copied._setup_objects()

        return copied

    def model_copy(self, *args, **kwargs) -> "Dataset":
        copied = super().model_copy(*args, **kwargs)

        # since campaign is not a proper field, a duplicate of the copied instance is added to the
        # campaign's dataset index, so replace it
        if has_attr(getattr(copied, "campaign", None), "datasets"):
            copied.campaign._setup_datasets()
            copied.campaign.datasets.add(copied, overwrite=True)

        return copied

    def __getitem__(self, name: str) -> DatasetVariation:
        return self.get_info(name)

    def __repr_args__(self, verbose: bool = False, adapters: bool = False) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__(verbose=verbose, adapters=adapters)

        if self.campaign:
            yield "campaign", self.campaign.name

    def get_variation(self, name: str) -> DatasetVariation:
        return self.variations[name]

    def set_variation(self, name: str, variation: DatasetVariation) -> None:
        if not isinstance(variation, DatasetVariation):
            raise TypeError(
                f"expected variation to be a DatasetVariation object, but got '{variation}'",
            )

        self.variations[name] = variation

    @property
    def keys(self) -> list[NonEmptyStrictStr]:
        return self.variations["nominal"].keys

    @property
    def gen_order(self) -> GenOrder:
        return self.variations["nominal"].gen_order

    @property
    def n_files(self) -> int:
        return self.variations["nominal"].n_files

    @property
    def n_events(self) -> int:
        return self.variations["nominal"].n_events

    @property
    def lfns(self) -> list[NonEmptyStrictStr]:
        return self.variations["nominal"].lfns


# trailing imports
from order.models.campaign import Campaign

# rebuild models that contained forward type declarations
DatasetIndex.model_rebuild()
Dataset.model_rebuild()
