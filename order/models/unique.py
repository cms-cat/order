# coding: utf-8

"""
Models definitions of unique objects and an index container to access them.
"""

from __future__ import annotations


__all__ = [
    "UniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
]


from typing import ClassVar, Any, List, Union
from types import GeneratorType

from pydantic import StrictInt, StrictStr, Field, field_validator
from typing_extensions import Annotated
from annotated_types import Ge, Len

from order.models.base import Model
from order.util import no_value, DotAccessProxy


class UniqueObjectMeta(type(Model)):
    """
    Meta class definition for :py:class:`UniqueObject` that ammends the class dict for newly created
    classes.
    """

    # registered classes mapped to their names
    __unique_classes = {}

    def __new__(
        meta_cls,
        class_name: str,
        bases: tuple,
        class_dict: dict[str, Any],
    ) -> "UniqueObjectMeta":
        # define a separate integer to remember the maximum id
        class_dict.setdefault("_max_id", 0)
        class_dict["__annotations__"]["_max_id"] = "ClassVar[int]"

        # create the class
        cls = super().__new__(meta_cls, class_name, bases, class_dict)

        # remember it
        meta_cls.__unique_classes[class_name] = cls

        return cls

    @classmethod
    def has_unique_cls(meta_cls, name: str) -> bool:
        """
        Returns whether a class named *name* was registered previously.
        """
        return name in meta_cls.__unique_classes

    @classmethod
    def get_unique_cls(meta_cls, name: str) -> "UniqueObjectMeta":
        """
        Returns a previously created class named *name*.
        """
        return meta_cls.__unique_classes[name]


class UniqueObject(Model, metaclass=UniqueObjectMeta):

    id: Annotated[StrictInt, Ge(0)]
    name: Annotated[StrictStr, Len(min_length=1)]

    AUTO_ID: ClassVar[str] = "+"

    @field_validator("id", mode="before")
    @classmethod
    def evaluate_auto_id(cls, id: str | int) -> int:
        if id == cls.AUTO_ID:
            cls._max_id += 1
            id = cls._max_id
        return id

    def __hash__(self) -> int:
        """
        Returns the unique hash of the unique object.
        """
        return hash((hex(id(self)), self.__repr__()))

    def __eq__(self, other: Any) -> bool:
        """
        Compares *other* to this instance. When *other* is a string (integer), the comparison is
        *True* when it matches the *name* (*id*) if this instance. When *other* is a unique object
        as well, the comparison is *True* when *__class__*, *name* and *id* match. All other cases
        evaluate to *False*.
        """
        if isinstance(other, str):
            return self.name == other

        if isinstance(other, int):
            return self.id == other

        if isinstance(other, self.__class__):
            return self.name == other.name and self.id == other.id

        return False

    def __ne__(self, other: Any) -> bool:
        """
        Opposite of :py:meth:`__eq__`.
        """
        return not self.__eq__(other)

    def __lt__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is lower than an *other* one. *other* can either
        be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id < other

        if isinstance(other, self.__class__):
            return self.id < other.id

        return False

    def __le__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is lower than or equal to an *other* one.
        *other* can either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id <= other

        if isinstance(other, self.__class__):
            return self.id <= other.id

        return False

    def __gt__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is greater than an *other* one. *other* can
        either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id > other

        if isinstance(other, self.__class__):
            return self.id > other.id

        return False

    def __ge__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is greater than or qual to an *other* one.
        *other* can either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id >= other

        if isinstance(other, self.__class__):
            return self.id >= other.id

        return False


class UniqueObjectIndex(Model):
    """
    Index of :py:class:`UniqueObject` instances which are - as the name suggests - unique within
    this index, enabling fast lookups by either name or id.

    **Example**

    .. code-block:: python

        idx = UniqueObjectIndex(class_name="UniqueObject")
        foo = idx.add(UniqueObject(name="foo", id=1))
        bar = idx.add(UniqueObject(name="bar", id=2))

        len(idx)
        # -> 2

        idx.get(1) == foo
        # -> True

        idx.add(UniqueObject(name="foo", id=3))
        # -> DuplicateNameException

        idx.add(UniqueObject(name="test", id=1))
        # -> DuplicateIdException

        idx.names()
        # -> ["foo", "bar"]

        idx.ids()
        # -> [1, 2]

    **Members**

    .. py:attribute:: cls

        type: :py:class:`UniqueObjectMeta` (read-only)

        Class of objects hold by this index.

    .. py:attribute:: n

        type: :py:class:`DotAccessProxy` (read-only)

        An object that provides simple attribute access to contained objects via name.
    """

    class_name: Annotated[StrictStr, Len(min_length=1)] = Field(default=UniqueObject)
    objects: List[UniqueObject] = Field(default_factory=lambda: [], repr=False)

    @field_validator("class_name", mode="before")
    @classmethod
    def convert_class_to_name(cls, class_name: str | UniqueObjectMeta) -> str:
        if isinstance(class_name, UniqueObjectMeta):
            class_name = class_name.__name__
        return class_name

    @field_validator("class_name", mode="after")
    @classmethod
    def validate_class_name(cls, class_name: str) -> str:
        # check that the model class is existing
        if not UniqueObjectMeta.has_unique_cls(class_name):
            raise ValueError(f"class '{class_name}' is not a subclass of UniqueObject")
        return class_name

    @field_validator("objects", mode="after")
    @classmethod
    def detect_duplicate_objects(cls, objects: List[UniqueObject]) -> List[UniqueObject]:
        seen_ids, seen_names = set(), set()
        for obj in objects:
            if obj.id in seen_ids:
                raise DuplicateIdException(type(obj), obj.id, cls)
            if obj.name in seen_names:
                raise DuplicateNameException(type(obj), obj.name, cls)
            seen_ids.add(obj.id)
            seen_names.add(obj.name)
        return objects

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # store a reference to the class
        self._cls = UniqueObjectMeta.get_unique_cls(self.class_name)

        # name-based DotAccessProxy
        self._n = DotAccessProxy(self.get)

        # hashmap indices for faster lookups
        self._name_index = {}
        self._id_index = {}

        # sync indices initially
        self._sync_indices()

    def __len__(self) -> int:
        """
        Returns the number of objects in the index.
        """
        return len(self.objects)

    def __contains__(self, obj: Any) -> None:
        """
        Checks if an object is contained in the index. :py:meth:`has` is used internally.
        """
        return self.has(obj)

    def __iter__(self) -> GeneratorType:
        """
        Iterates through the index and yields the contained objects (i.e. the *values*).
        """
        for obj in self.objects:
            yield obj

    def __nonzero__(self):
        """
        Boolish conversion that depends on the number of objects in the index.
        """
        return bool(self.objects)

    def __repr_args__(self) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__()
        yield "objects", len(self)

    @property
    def cls(self) -> UniqueObjectMeta:
        return self._cls

    @property
    def n(self) -> DotAccessProxy:
        return self._n

    def _sync_indices(self, force: bool = False) -> None:
        """
        Synchronizes the two hashmap indices with the actual objects. Unless *force* is *True*, the
        synchronization stops in case the index lengths match the number of objects.
        """
        # when not forcing and all lengths are all identical, do nothing
        if not force and (len(self.objects) == len(self._name_index) == len(self._id_index)):
            return

        # clear indices
        self._name_index.clear()
        self._id_index.clear()

        # populate them
        for obj in self.objects:
            self._name_index[obj.name] = obj
            self._id_index[obj.id] = obj

    def names(self) -> List[str]:
        """
        Returns the names of the contained objects in the index.
        """
        self._sync_indices()
        return list(self._name_index.keys())

    def ids(self) -> List[int]:
        """
        Returns the ids of the contained objects in the index.
        """
        self._sync_indices()
        return list(self._id_index.keys())

    def keys(self):
        """
        Returns the (name, id) pairs of all objects contained in the index.
        """
        self._sync_indices()
        return list(zip(self._name_index.keys(), self._id_index.keys()))

    def values(self):
        """
        Returns all objects contained in the index.
        """
        self._sync_indices()
        return list(self.objects)

    def items(self):
        """
        Returns (name, id, object) 3-tuples of all objects contained in the index
        """
        return list(zip(self.keys(), self.objects))

    def has(self, obj: Any) -> bool:
        """
        Returns whether an object *obj* is contained in the index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name` or a :py:class:`UniqueObject` of type :py:attr:`cls`
        """
        self._sync_indices()

        if isinstance(obj, self.cls):
            obj = obj.name

        if isinstance(obj, str):
            return obj in self._name_index

        if isinstance(obj, id):
            return obj in self._id_index

        return False

    def get(self, obj: Any, default: Any = no_value) -> Union[UniqueObject, Any]:
        """
        Returns an object *obj* contained in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name` or a :py:class:`UniqueObject` of type :py:attr:`cls`. If no object could be
        found, *default* is returned if set. An exception is raised otherwise.
        """
        self._sync_indices()

        obj_orig = obj
        if isinstance(obj, self.cls):
            obj = obj.name

        if isinstance(obj, str):
            if obj in self._name_index:
                return self._name_index[obj]
            if default != no_value:
                return default

        elif isinstance(obj, int):
            if obj in self._id_index:
                return self._id_index[obj]
            if default != no_value:
                return default

        raise ValueError(f"object '{obj_orig}' not known to index '{self}'")

    def get_first(self, default: Any = no_value) -> Union[UniqueObject, Any]:
        """
        Returns the first object of this index. If no object could be found, *default* is returned
        if set. An exception is raised otherwise.
        """
        if not self.objects and default != no_value:
            return default

        return self.objects[0]

    def get_last(self, default: Any = no_value) -> Union[UniqueObject, Any]:
        """
        Returns the last object of this index. If no object could be found, *default* is returned if
        set. An exception is raised otherwise.
        """
        if not self.objects and default != no_value:
            return default

        return self.objects[-1]

    def add(self, obj: UniqueObject, overwrite: bool = False) -> UniqueObject:
        """
        Adds a new object *obj* with type :py:attr:`cls` to the index. When an object with the same
        :py:attr:`name` or :py:attr:`id` already exists and *overwrite* is *False*, an exception is
        raised. Otherwise, the object is overwritten. The added object is returned.
        """
        if not isinstance(obj, self.cls):
            raise TypeError(f"object '{obj}' to add must be of type '{self.cls}'")

        self._sync_indices()

        # handle duplicates
        if obj.name in self._name_index:
            if not overwrite:
                raise DuplicateNameException(self.cls, obj.name, self)
            self.remove(obj)
        if obj.id in self._id_index:
            if not overwrite:
                raise DuplicateIdException(self.cls, obj.id, self)
            self.remove(obj)

        # add to objects and indices
        self.objects.append(obj)
        self._name_index[obj.name] = obj
        self._id_index[obj.id] = obj

        return obj

    def extend(
        self,
        objects: Union["UniqueObjectIndex", List[UniqueObject]],
        overwrite: bool = False,
    ) -> None:
        """
        Adds multiple new *objects* of type :py:attr:`cls` to this index.
        """
        for obj in objects:
            self.add(obj, overwrite=overwrite)

    def index(self, obj: Any) -> int:
        """
        Returns the position of an object *obj* in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name` or a :py:class:`UniqueObject` of type :py:attr:`cls`.
        """
        return self.objects.index(self.get(obj))

    def remove(self, obj: Any) -> bool:
        """
        Remove an object *obj* from the index. *obj* can be an :py:attr:`id`, a :py:attr:`name` or a
        :py:class:`UniqueObject` of type :py:attr:`cls`. *True* is returned in case an object could
        be removed, and *False* otherwise.
        """
        # first, get the object
        obj = self.get(obj, default=None)

        # return when not existing
        if obj is None:
            return False

        # remove from indices and objects
        self._name_index.pop(obj.name)
        self._id_index.pop(obj.id)
        self.objects.remove(obj)

        return True

    def clear(self) -> None:
        """
        Removes all objects from the index.
        """
        del self.objects[:]
        self._sync_indices()


class DuplicateObjectException(Exception):
    """
    Base class for exceptions that are raised when a duplicate of a unique object is encountered.
    """


class DuplicateNameException(DuplicateObjectException):
    """
    An exception which is raised when a duplicate object, identified by its name, is encountered.
    """

    def __init__(
        self,
        cls: UniqueObjectMeta,
        name: str,
        index: UniqueObjectIndex | None = None,
    ) -> None:
        # create the message
        msg = f"duplicate '{cls.__module__}.{cls.__name__}' object with name '{name}' encountered"
        if index is not None:
            msg += f" in {index!r}"

        super().__init__(msg)


class DuplicateIdException(DuplicateObjectException):
    """
    An exception which is raised when a duplicate object, identified by its id, is encountered.
    """

    def __init__(
        self,
        cls: UniqueObjectMeta,
        id: int,
        index: UniqueObjectIndex | None = None,
    ) -> None:
        # create the message
        msg = f"duplicate '{cls.__module__}.{cls.__name__}' object with id '{id}' encountered"
        if index is not None:
            msg += f" in {index!r}"

        super().__init__(msg)
