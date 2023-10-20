# coding: utf-8

"""
Base class definitions for adapters and the overarching data provider for cached retrieval.
"""

from __future__ import annotations


__all__ = ["Adapter", "Materialized", "DataProvider"]


import os
import re
import json
import shutil
from datetime import datetime, timezone
from contextlib import contextmanager
from abc import ABCMeta, abstractmethod, abstractproperty

import order.settings as settings
from order.types import Any, Sequence, Generator
from order.util import create_hash


class AdapterMeta(ABCMeta):
    """
    Metaclass for :py:class:`Adapter` classes providing fast subclass lookup and collision handling.
    """

    adapters: dict[str, "AdapterMeta"] = {}

    def __new__(
        meta_cls,
        class_name: str,
        bases: tuple[type],
        class_dict: dict[str, Any],
    ) -> "AdapterMeta":
        cls = type.__new__(meta_cls, class_name, bases, class_dict)

        # check if the class was registered previously
        if meta_cls.has_cls(cls.name):
            raise ValueError(
                f"cannot register adapter {cls}, name '{cls.name}' previously used by "
                f"{meta_cls.adapters[cls.name]}",
            )

        # store class by name
        if getattr(cls, "_name", "") != "base":
            meta_cls.adapters[cls.name] = cls

        return cls

    @classmethod
    def has_cls(cls, name: str) -> bool:
        return name in cls.adapters

    @classmethod
    def get_cls(cls, name: str) -> "AdapterMeta":
        if not cls.has_cls(name):
            raise KeyError(f"unknown adapter '{name}'")

        return cls.adapters[name]


class Materialized(dict):
    """
    Container for materialized values returned by :py:meth:`Adapter.retrieve_data`.
    """


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
    def retrieve_data(self) -> Materialized:
        # must be implemented by subclasses
        return

    def get_cache_key(self, **kwargs) -> tuple:
        return tuple(
            (
                key,
                self.get_cache_key(**kwargs[key]) if isinstance(kwargs[key], dict) else kwargs[key],
            )
            for key in sorted(kwargs)
        )

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
    Interface between data locations plus caches and :py:class:`Adapter` instances.
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
            cls.__instance = cls(
                data_location=settings.data_location,
                cache_directory=settings.cache_directory,
                readonly_cache_directories=settings.readonly_cache_directories,
                clear_cache=settings.clear_cache,
            )

        return cls.__instance

    def __init__(
        self,
        *,
        data_location: str,
        cache_directory: str,
        readonly_cache_directories: Sequence[str] = (),
        clear_cache: bool = False,
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

        # clear the cache initially
        if clear_cache and os.path.exists(self.cache_directory):
            shutil.rmtree(self.cache_directory)

    @contextmanager
    def materialize(
        self,
        adapter_model: "AdapterModel" | dict[str, Any],
        adapter_kwargs: dict[str, Any] | None = None,
    ) -> Generator[Materialized, None, None]:
        if not isinstance(adapter_model, AdapterModel):
            adapter_model = AdapterModel(**adapter_model)

        # get the adapter class and instantiate it
        adapter = AdapterMeta.get_cls(adapter_model.adapter)()

        # merge kwargs
        adapter_kwargs = {**adapter_model.arguments, **(adapter_kwargs or {})}

        # when cached, read the cached object instead
        readable_path, writable_path, cached = self.check_cache(adapter, adapter_kwargs)
        if cached:
            yield self.read_cache(readable_path)
            return

        # in cache-only mode, this point should not be reached
        if settings.cache_only:
            raise Exception(f"adapter '{adapter.name}' cannot be evaluated in cache-only mode")

        # invoke the adapter
        args = (self.data_location,) if adapter.needs_data_location else ()
        materialized = adapter.retrieve_data(*args, **adapter_kwargs)

        # complain when the return value is not a materialized container
        if not isinstance(materialized, Materialized):
            raise TypeError(
                f"retrieve_data of adapter '{adapter_model.adapter}' must return a Materialized "
                f"instance, but got '{materialized}'",
            )

        # yield the materialized data and cache it if the receiving context did not raise
        try:
            yield materialized
        except self.SkipCaching:
            return

        # cache it
        if writable_path:
            self.write_cache(writable_path, materialized)

    def check_cache(
        self,
        adapter: Adapter,
        adapter_kwargs: dict[str, Any],
        lifetime: int = 86400,  # TODO: let adapter or main settings control this
    ) -> [str, str, bool]:
        # create a unique hash
        h = create_hash((
            os.path.realpath(self.data_location),
            adapter.get_cache_key(**adapter_kwargs),
        ))

        # helper to find a cached file in a directory with the largest timestamp and to invalidate
        # too old ones
        cre = re.compile(rf"^{h}(|_\d+)\.json$")

        def find(directory: str, ts: int, invalidate: bool) -> str | None:
            files = {
                int(m.group(1)[1:] or 0): os.path.join(directory, elem)
                for elem in os.listdir(directory)
                if (m := cre.match(elem))
            }

            # return none when no cached files were found
            if not files:
                return None

            # pick the file with the longest remaining lifetime
            best_ts = 0 if 0 in files else max((_ts for _ts in files if _ts >= ts), default=-1)

            # invalidate all other files
            if invalidate:
                for _ts, path in files.items():
                    if _ts != best_ts:
                        try:
                            os.remove(path)
                            print("invalidated", path)
                        except:
                            pass

            return files[best_ts] if best_ts >= 0 else None

        # get a utc timestamp
        ts = round(datetime.now(timezone.utc).timestamp())

        # check the writable default cache directory
        writable_path = find(self.cache_directory, ts, True)
        if writable_path:
            return writable_path, writable_path, True

        # create a writable path in the default cache directory
        ts_postfix = "" if lifetime <= 0 else f"_{ts + lifetime}"
        writable_path = os.path.join(self.cache_directory, f"{h}{ts_postfix}.json")

        # check readable directories
        for readonly_cache_directory in self.readonly_cache_directories:
            readable_path = find(readonly_cache_directory, ts, False)
            if readable_path:
                return readable_path, writable_path, True

        return writable_path, writable_path, False

    def write_cache(self, path: str, materialized: Materialized) -> None:
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        with open(path, "w") as f:
            json.dump(materialized, f)

    def read_cache(self, path: str) -> Materialized:
        with open(path, "r") as f:
            return Materialized(json.load(f))


# trailing imports
from order.models.base import AdapterModel
