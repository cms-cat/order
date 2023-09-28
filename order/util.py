# coding: utf-8
from __future__ import annotations

"""
Helpful utilities.
"""

from __future__ import annotations


__all__ = ["no_value", "create_hash"]

from typing import Any, Dict


import hashlib
import requests
from order.settings import Settings 

#: Unique object denoting *no value*.
no_value = object()


def create_hash(inp: Any, l: int = 10, algo: str = "sha256", to_int: bool = False) -> str | int:
    """
    Takes an arbitrary input *inp* and creates a hexadecimal string hash based on an algorithm
    *algo*. For valid algorithms, see python's hashlib. *l* corresponds to the maximum length of the
    returned hash and is limited by the length of the hexadecimal representation produced by the
    hashing algorithm. When *to_int* is *True*, the decimal integer representation is returned.
    """
    h = getattr(hashlib, algo)(str(inp).encode("utf-8")).hexdigest()[:l]
    return int(h, 16) if to_int else h



def query_dbs(dataset_key: str, dbs_instance: str = "prod/global") -> Dict[str, Any]:
    proxy = Settings.instance().get_cms_cert()
    
    resource = f"https://cmsweb.cern.ch:8443/dbs/{dbs_instance}/DBSReader/files?dataset={dataset_key}&detail=True"
    r = requests.get(
                resource,
                cert=proxy,
                verify=False,
            )
    filesjson = r.json()
    return filesjson
