# coding: utf-8

"""
Container for global settings.
"""

from __future__ import annotations


__all__ = ["Settings"]


import os
import re

from order.types import T
from order.util import no_value


# update env variables
_on_gh = bool(os.getenv("GITHUB_ACTION"))
_on_rtd = bool(os.getenv("READTHEDOCS"))
if _on_gh or _on_rtd:
    os.environ.setdefault("ORDER_DATA_LOCATION", os.getcwd())
    os.environ["ORDER_COLORS"] = "False"


class Settings(object):

    __instance = None

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def get_env(cls, name: str, default: T = no_value) -> T:
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
    def get_user_proxy(cls) -> str:
        return cls.get_env("X509_USER_PROXY", f"/tmp/x509up_u{os.getuid()}")

    @classmethod
    def get_colors(cls) -> bool:
        return cls.flag_to_bool(cls.get_env("ORDER_COLORS", True))

    def __init__(self):
        super().__init__()

        # get all settings
        self.data_location: str = self.get_data_location()
        self.cache_directory: str = self.get_cache_directory()
        self.readonly_cache_directories: list[str] = self.get_readonly_cache_directories()
        self.clear_cache: bool = self.get_clear_cache()
        self.cache_only: bool = self.get_cache_only()
        self.user_proxy: str = self.get_user_proxy()
        self.colors: bool = self.get_colors()


# register convenience functions on module-level
inst = Settings.instance()
for attr, value in inst.__dict__.items():
    if attr.startswith("_"):
        continue
    locals()[attr] = value
