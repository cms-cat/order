# coding: utf-8

"""
Campaign definition.
"""

from __future__ import annotations


__all__ = ["Campaign"]


from pydantic import Field

from order.types import Lazy, NonEmptyStrictStr, StrictFloat, Any
from order.util import has_attr
from order.models.unique import UniqueObject
from order.models.dataset import DatasetIndex, Dataset, LazyDataset


class Campaign(UniqueObject):

    tier: Lazy[NonEmptyStrictStr]
    ecm: Lazy[StrictFloat]
    recommended_global_tag: NonEmptyStrictStr
    datasets: DatasetIndex = Field(default_factory=DatasetIndex, frozen=True)

    def _setup_objects(self: Campaign) -> None:
        super()._setup_objects()

        # setup the datasets index
        self._setup_datasets()

    def _setup_datasets(self) -> None:
        if not has_attr(self, "datasets"):
            return

        # reset internal indices
        self.datasets._reset_indices()

        # register callbacks
        self.datasets.set_callbacks(
            materialize=self._dataset_materialize_callback,
            add=self._dataset_add_callback,
            remove=self._dataset_remove_callback,
        )

        # register arguments to be passed to lazy object creation
        self.datasets.set_lazy_object_kwargs(campaign_name=self.name)

        # initially invoke the "add" callback for all objects in the index
        for dataset in self.datasets.objects:
            self._dataset_add_callback(dataset)

    def __copy__(self) -> Campaign:
        copied = super().__copy__()

        # drop references to datasets for consistency as they still point to the original campaign
        with copied._unfreeze_field("datasets"):
            copied.datasets = copied.model_fields["datasets"].default_factory()

        # setup objects if not triggered by model_copy
        if not self._copy_triggered_by_model:
            copied._setup_objects()

        return copied

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Campaign:
        copied = super().__deepcopy__(memo=memo)

        # setup objects if not triggered by model_copy
        if not self._copy_triggered_by_model:
            copied._setup_objects()

        return copied

    def _dataset_materialize_callback(self, dataset: Dataset) -> None:
        dataset.campaign = self

    def _dataset_add_callback(self, dataset: LazyDataset | Dataset) -> None:
        if isinstance(dataset, Dataset):
            dataset.campaign = self

    def _dataset_remove_callback(self, dataset: LazyDataset | Dataset) -> None:
        if isinstance(dataset, Dataset):
            dataset.campaign = None
