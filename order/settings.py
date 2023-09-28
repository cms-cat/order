# coding: utf-8

"""
Container for global settings.
"""

from __future__ import annotations


__all__ = ["Settings"]


import os
import re
from typing import Any

from order.util import no_value


class Settings(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def get_env(cls, name: str, default: Any = no_value) -> Any:
        if name not in os.environ:
            if default != no_value:
                return default
            raise Exception(f"undefined environment variable '{name}'")
        return os.environ[name]

    @classmethod
    def flag_to_bool(cls, flag: bool | int | str) -> bool:
        if isinstance(flag, int):
            return bool(flag)
        if isinstance(flag, bool):
            return flag

        _flag = str(flag).lower()
        if _flag in ("false", "no", "0"):
            return False
        if _flag in ("true", "yes", "1"):
            return True

        raise ValueError(f"cannot interpret '{flag}' as bool")

    @classmethod
    def get_data_location(cls) -> str:
        loc = cls.get_env("ORDER_DATA_LOCATION")
        scheme = re.match(r"^(\w+)\:\/\/(.*)$", loc)
        if not scheme:
            loc = f"file://{loc}"
        return loc

    @classmethod
    def get_cache_directory(cls) -> str:
        return cls.get_env("ORDER_CACHE_DIRECTORY", os.path.join(os.getcwd(), ".order_cache"))

    @classmethod
    def get_readonly_cache_directories(cls) -> list[str]:
        dirs = cls.get_env("ORDER_READONLY_CACHE_DIRECTORIES", [])
        if dirs:
            dirs = [d.strip() for d in dirs.split(",")]
        return dirs

    @classmethod
    def get_clear_cache(cls) -> bool:
        return cls.flag_to_bool(cls.get_env("ORDER_CLEAR_CACHE", False))

    @classmethod
    def get_cache_only(cls) -> bool:
        return cls.flag_to_bool(cls.get_env("ORDER_CACHE_ONLY", False))

    @classmethod
    def get_cms_cert(cls) -> str:
        return cls.get_env("X509_USER_PROXY")
    
    def __init__(self):
        super().__init__()

        # get all settings
        self.data_location: str = self.get_data_location()
        self.cache_directory: str = self.get_cache_directory()
        self.readonly_cache_directories: list[str] = self.get_readonly_cache_directories()
        self.clear_cache = self.get_clear_cache()
        self.cache_only = self.get_cache_only()
