# coding: utf-8

from __future__ import annotations


__all__ = ["ProcessIndex", "Process", "LazyProcess"]


from pydantic import Field

from order.types import (
    Union, List, Dict, NonEmptyStrictStr, Lazy, ClassVar, StrictFloat,
)
from order.util import has_attr
from order.models.unique import UniqueObjectBase, UniqueObject, LazyUniqueObject, UniqueObjectIndex


class ProcessIndex(UniqueObjectIndex):

    class_name: NonEmptyStrictStr = Field(default="Process", frozen=True)
    objects: Lazy[List[Union["LazyProcess", "Process"]]] = Field(default_factory=list, repr=False)


class LazyProcess(LazyUniqueObject):

    class_name: NonEmptyStrictStr = Field(default="Process", frozen=True)

    @classmethod
    def create_lazy_dict(cls, name: str, id: int) -> dict:
        return {
            "name": name,
            "id": id,
            "class_name": "Process",
            "adapter": {
                "adapter": "order_process",
                "key": "process",
                "arguments": {
                    "process_name": name,
                },
            },
        }


class Process(UniqueObject):

    # TODO: lazy cross sections dicts (to reference other cross sections)
    #       and lazy values (to talk to databases) that materialize into scinum.Number objects
    cross_section: Dict[StrictFloat, Dict[str, StrictFloat]] = Field(
        default_factory=dict,
        frozen=True,
    )
    processes: ProcessIndex = Field(
        default_factory=ProcessIndex,
        frozen=True,
    )
    parent_processes: ProcessIndex = Field(
        default_factory=ProcessIndex,
        frozen=True,
        # exclude from exports to avoid circular references
        exclude=True,
    )

    lazy_cls: ClassVar[UniqueObjectBase] = LazyProcess

    def _setup_objects(self: Process) -> None:
        super()._setup_objects()

        # setup the processes and parent_processes indices
        self._setup_processes()
        self._setup_parent_processes()

    def _setup_processes(self) -> None:
        if not has_attr(self, "processes"):
            return

        # reset internal indices
        self.processes._reset_indices()

        # register callbacks
        self.processes.set_callbacks(
            materialize=self._process_materialize_callback,
            add=self._process_add_callback,
            remove=self._process_remove_callback,
        )

        # initially invoke the "add" callback for all objects in the index
        for process in self.processes.objects:
            self._process_add_callback(process)

    def _setup_parent_processes(self) -> None:
        if not has_attr(self, "parent_processes"):
            return

        # reset internal indices
        self.parent_processes._reset_indices()

        # register callbacks
        self.parent_processes.set_callbacks(
            materialize=self._parent_process_materialize_callback,
            add=self._parent_process_add_callback,
            remove=self._parent_process_remove_callback,
        )

        # initially invoke the "add" callback for all objects in the index
        for parent_process in self.parent_processes.objects:
            self._parent_process_add_callback(parent_process)

    def _process_materialize_callback(self, process: "Process") -> None:
        process.parent_processes.add(self, overwrite=True)

    def _parent_process_materialize_callback(self, parent_process: "Process") -> None:
        parent_process.processes.add(self, overwrite=True)

    def _process_add_callback(self, process: LazyProcess | "Process") -> None:
        if isinstance(process, Process) and has_attr(process, "parent_processes"):
            process.parent_processes.add(self, overwrite=True, skip_callback=True)

    def _parent_process_add_callback(self, parent_process: LazyProcess | "Process") -> None:
        if isinstance(parent_process, Process) and has_attr(parent_process, "processes"):
            parent_process.processes.add(self, overwrite=True, skip_callback=False)

    def _process_remove_callback(self, process: LazyProcess | "Process") -> None:
        if isinstance(process, Process) and has_attr(process, "parent_processes"):
            process.parent_processes.remove(self, skip_callback=True)

    def _parent_process_remove_callback(self, parent_process: LazyProcess | "Process") -> None:
        if isinstance(parent_process, Process) and has_attr(parent_process, "processes"):
            parent_process.processes.remove(self, skip_callback=False)


# rebuild models that contained forward type declarations
ProcessIndex.model_rebuild()
