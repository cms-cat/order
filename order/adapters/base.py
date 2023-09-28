# coding: utf-8

"""
Base class definitions for adapters and the overarching data provider for cached retrieval.
"""

from __future__ import annotations


__all__ = ["AdapterData", "Adapter", "DataProvider"]


import os
import re
import json
from contextlib import contextmanager
from abc import ABCMeta, abstractmethod, abstractproperty
from typing import Any, Sequence, Dict

from pydantic import BaseModel

from order.settings import Settings
from order.util import create_hash


class AdapterData(BaseModel):

    adapter: str
    arguments: Dict[str, Any]

    @property
    def name(self) -> str:
        return self.adapter


class AdapterMeta(ABCMeta):
    """
    Metaclass for :py:class:`Adapter` classes providing fast subclass lookup and collision handling.
    """

    adapters: dict[str, "AdapterMeta"] = {}

    def __new__(
        metacls,
        classname: str,
        bases: tuple[type],
        classdict: dict[str, Any],
    ) -> "AdapterMeta":
        cls = type.__new__(metacls, classname, bases, classdict)

        # check if the class was registered previously
        if metacls.has_cls(cls.name):
            raise ValueError(
                f"cannot register adapter {cls}, name '{cls.name}' previously used by "
                f"{metacls.adapters[cls.name]}",
            )

        # store class by name
        if getattr(cls, "_name", "") != "base":
            metacls.adapters[cls.name] = cls

        return cls

    @classmethod
    def has_cls(cls, name: str) -> bool:
        return name in cls.adapters

    @classmethod
    def get_cls(cls, name: str) -> "AdapterMeta":
        if not cls.has_cls(name):
            raise KeyError(f"unknown adapter '{name}'")
        return cls.adapters[name]


class Adapter(object, metaclass=AdapterMeta):
    """
    Abstract base class for all adapters.
    """

    # temporary attribute used during class registration
    _name = "base"

    # whether the retrieve_data method needs the data_location as its first positional argument
    needs_data_location = False

    @abstractproperty
    def name(self) -> str:
        # must be implemented by subclasses
        return ""

    @abstractmethod
    def get_cache_key(self, **kwargs) -> tuple:
        # must be implemented by subclasses
        return ()

    @abstractmethod
    def retrieve_data(self) -> Any:
        # must be implemented by subclasses
        return

    @classmethod
    def location_is_local(cls, data_location: str) -> bool:
        return data_location.startswith("file://")

    @classmethod
    def location_is_remote(cls, data_location: str) -> bool:
        return data_location.startswith(("http://", "https://"))

    @classmethod
    def remove_scheme(cls, data_location: str) -> str:
        return re.sub(r"^(\w+)\:\/\/", "", data_location)


# remove temporary _name attribute
del Adapter._name


class DataProvider(object):
    """
    Interface between data locations plus caches and :py:class:`Adapter`'s.
    """

    __instance = None

    class SkipCaching(Exception):
        """
        Special exception type that can be thrown within the :py:meth:`DataProvider.get_data`
        context to instruct it to skip caching.
        """

    @classmethod
    def instance(cls) -> "DataProvider":
        """
        Singleton constructor and getter.
        """
        if cls.__instance is None:
            settings = Settings.instance()
            cls.__instance = cls(
                data_location=settings.data_location,
                cache_directory=settings.cache_directory,
                readonly_cache_directories=settings.readonly_cache_directories,
            )

        return cls.__instance

    def __init__(
        self,
        data_location: str,
        cache_directory: str,
        readonly_cache_directories: Sequence[str] = (),
    ) -> None:
        super().__init__()

        # expansion helper
        expand = lambda path: os.path.expandvars(os.path.expanduser(str(path)))

        # store attributes
        self.data_location: str = expand(data_location)
        self.cache_directory: str = expand(cache_directory)
        self.readonly_cache_directories: list[str] = list(map(expand, readonly_cache_directories))

        # cache_directory must not be in read_cache
        if self.cache_directory in self.readonly_cache_directories:
            raise ValueError(
                f"cache_directory '{self.cache_directory}' must not be in "
                "readonly_cache_directories",
            )

    @contextmanager
    def get_data(self, adapter_data: AdapterData | dict[str, Any]) -> None:
        if not isinstance(adapter_data, AdapterData):
            adapter_data = AdapterData(**adapter_data)

        # get the adapter class and instantiate it
        adapter = AdapterMeta.get_cls(adapter_data.name)()

        # determine the basename of the cache file (if existing)
        h = (
            os.path.realpath(self.data_location),
            adapter.get_cache_key(**adapter_data.arguments),
        )
        cache_name = f"{create_hash(h)}.json"

        # when cached, read the cached object instead
        readable_path, writable_path, cached = self.check_cache(cache_name)
        if cached:
            return self.read_cache(readable_path)

        # in cache-only mode, this point should not be reached
        if Settings.instance().cache_only:
            raise Exception(f"adapter '{adapter.name}' cannot be evaluated in cache-only mode")

        # invoke the adapter
        args = (self.data_location,) if adapter.needs_data_location else ()
        data = adapter.retrieve_data(*args, **adapter_data.arguments)

        # yield the materialized data and cache it if the receiving context did not raise
        try:
            yield data
        except Exception as e:
            if isinstance(e, self.SkipCaching):
                return
            raise e

        # cache it
        if writable_path:
            self.write_cache(writable_path, data)

    def check_cache(self, cache_name: str) -> [str, str, bool]:
        # check the writable (default) cache directory
        writable_path = os.path.join(self.cache_directory, cache_name)
        if os.path.exists(writable_path):
            return writable_path, writable_path, True

        for readonly_cache_directory in self.readonly_cache_directories:
            readable_path = os.path.join(readonly_cache_directory, cache_name)
            if os.path.exists(readable_path):
                return readable_path, writable_path, True

        return writable_path, writable_path, False

    def write_cache(self, path: str, data: Any) -> None:
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(path, "w") as f:
            json.dump(data, f)

    def read_cache(self, path: str) -> Any:
        with open(path, "r") as f:
            return json.load(f)
