# coding: utf-8

from __future__ import annotations


__all__ = ["Dataset"]


from typing import List
from order.models.base import Model, Lazy


# class DAS(Model):
#     das_name: str


class File(Model):
    logical_file_name: str
    block_name: str
    check_sum: int
    last_modification_date: int
    file_type: str


class Dataset(Model):

    id: int
    name: str
    das_name: str
    nevents: int
    # pnf: Lazy[List of string]
    files: Lazy[List[File]]
