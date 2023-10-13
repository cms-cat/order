# coding: utf-8

from __future__ import annotations


__all__ = ["CopyMixin"]


from order.types import Any
from order.models.base import Model


class CopyMixin(Model):
    """
    TODO.
    """

    # shallow specs:
    # set_none
    # re_copy
    # field_default (default if not PydanticUndefined, otherwise default_factory())
    # custom: e.g. run setup

    # deep specs:
    # set_none
    # field_default
    # custom: e.g. re-add to index to overwrite duplicate copy, see datasets

    # create a way to have specs apply to both shallow and deep copies, or to just one!

    # also, there should be an easy way to inject conditions for applying specs in the first place,
    # such as laziness checks, which are done on the corresponding lazy attribute to avoid
    # materialization, see e.g. DatasetInfo.lfns

    def __copy__(self) -> "CopyMixin":
        return super().__copy__()

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> "CopyMixin":
        return super().__deepcopy__(memo=memo)
