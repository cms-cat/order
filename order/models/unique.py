# coding: utf-8

"""
Models definitions of unique objects and an index container to access them.
"""

from __future__ import annotations


__all__ = [
    "UniqueObject", "LazyUniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
]


from contextlib import contextmanager

from pydantic import field_validator

from order.types import (
    ClassVar, Any, T, List, Union, GeneratorType, Field, PositiveStrictInt, NonEmptyStrictStr,
    KeysView, Lazy,
)
from order.models.base import Model
from order.adapters.base import AdapterModel, DataProvider
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
        class_dict.setdefault("__annotations__", {})["_max_id"] = "ClassVar[int]"

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


class UniqueObjectBase(Model):

    id: PositiveStrictInt
    name: NonEmptyStrictStr

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

        # TODO: not particularly clean to use a subclass of _this_ class, solve by inheritance
        if (
            (isinstance(other, LazyUniqueObject) and other.cls == self.__class__) or
            (isinstance(self, LazyUniqueObject) and self.cls == other.__class__)
        ):
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

        if isinstance(other, UniqueObjectBase):
            return self.id < other.id

        return False

    def __le__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is lower than or equal to an *other* one.
        *other* can either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id <= other

        if isinstance(other, UniqueObjectBase):
            return self.id <= other.id

        return False

    def __gt__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is greater than an *other* one. *other* can
        either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id > other

        if isinstance(other, UniqueObjectBase):
            return self.id > other.id

        return False

    def __ge__(self, other: Any) -> bool:
        """
        Returns *True* when the id of this instance is greater than or qual to an *other* one.
        *other* can either be an integer or a unique object of the same class.
        """
        if isinstance(other, int):
            return self.id >= other

        if isinstance(other, UniqueObjectBase):
            return self.id >= other.id

        return False


class WrapsUniqueClcass(Model):

    class_name: NonEmptyStrictStr

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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # store a reference to the wrapped class
        self._cls = UniqueObjectMeta.get_unique_cls(self.class_name)

    @property
    def cls(self) -> UniqueObjectMeta:
        return self._cls


class UniqueObject(UniqueObjectBase, metaclass=UniqueObjectMeta):

    AUTO_ID: ClassVar[str] = "+"

    @field_validator("id", mode="before")
    @classmethod
    def evaluate_auto_id(cls, id: str | int) -> int:
        if id == cls.AUTO_ID:
            cls._max_id += 1
            id = cls._max_id
        return id

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # adjust max id class attribute
        if self.id > self.__class__._max_id:
            self.__class__._max_id = self.id


class LazyUniqueObject(UniqueObjectBase, WrapsUniqueClcass):

    adapter: AdapterModel

    @contextmanager
    def materialize(self, index: "UniqueObjectIndex") -> GeneratorType:
        with DataProvider.instance().materialize(self.adapter) as materialized:
            # complain when the adapter did not provide a value for this attribute
            if self.adapter.key not in materialized:
                raise KeyError(
                    f"adapter '{self.adapter.name}' did not provide field "
                    f"'{self.adapter.key}' required to materialize '{self}'",
                )

            # create the materialized instance
            inst = self.cls(**materialized[self.adapter.key])

            yield inst


class UniqueObjectIndex(WrapsUniqueClcass):
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

    objects: Lazy[List[Union[UniqueObject, LazyUniqueObject]]] = Field(
        default_factory=lambda: [],
        repr=False,
    )

    @field_validator("lazy_objects", mode="after")
    @classmethod
    def detect_duplicate_objects(
        cls,
        objects: Lazy[list[UniqueObject | LazyUniqueObject]],
    ) -> Lazy[list[UniqueObject | LazyUniqueObject]]:
        # skip adapters
        if isinstance(objects, AdapterModel):
            return objects

        # detect duplicate ids and names
        seen_names, seen_ids = set(), set()
        for obj in objects:
            if obj.name in seen_names:
                raise DuplicateNameException(type(obj), obj.name, cls)
            if obj.id in seen_ids:
                raise DuplicateIdException(type(obj), obj.id, cls)
            seen_ids.add(obj.id)
            seen_names.add(obj.name)

        return objects

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

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
            yield self.get(obj.name)

    def __nonzero__(self):
        """
        Boolish conversion that depends on the number of objects in the index.
        """
        return bool(self.objects)

    def __getitem__(self, obj: Any) -> UniqueObject:
        """
        Shorthand for :py:func:`get` without a default value.
        """
        return self.get(obj)

    def __repr_args__(self) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__()
        yield "len", len(self)

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

    def names(self) -> KeysView:
        """
        Returns the names of the contained objects in the index.
        """
        self._sync_indices()
        return self._name_index.keys()

    def ids(self) -> KeysView:
        """
        Returns the ids of the contained objects in the index.
        """
        self._sync_indices()
        return self._id_index.keys()

    def keys(self) -> GeneratorType:
        """
        Returns the (name, id) pairs of all objects contained in the index.
        """
        self._sync_indices()
        return (tpl for tpl in zip(self.names(), self.ids()))

    def values(self) -> GeneratorType:
        """
        Returns all objects contained in the index.
        """
        self._sync_indices()
        return (obj for obj in self)

    def items(self) -> GeneratorType:
        """
        Returns (name, id, object) 3-tuples of all objects contained in the index
        """
        return (
            ((obj.name, obj.id), obj)
            for obj in self
        )

    def has(self, obj: Any) -> bool:
        """
        Returns whether an object *obj* is contained in the index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name`, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`.
        """
        self._sync_indices()

        if isinstance(obj, self.cls) or (isinstance(obj, LazyUniqueObject) and obj.cls == self.cls):
            obj = obj.name

        if isinstance(obj, str):
            return obj in self._name_index

        if isinstance(obj, id):
            return obj in self._id_index

        return False

    def get(self, obj: Any, default: T = no_value) -> UniqueObject | T:
        """
        Returns an object *obj* contained in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name`, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`. If no object could be found, *default* is returned if set. An
        exception is raised otherwise.
        """
        self._sync_indices()

        name_or_id = obj
        inst_passed = False
        if isinstance(obj, self.cls) or isinstance(obj, LazyUniqueObject) and obj.cls == self.cls:
            name_or_id = obj.name
            inst_passed = True

        _obj = None
        if isinstance(name_or_id, str):
            if name_or_id in self._name_index:
                _obj = self._name_index[name_or_id]

        elif isinstance(name_or_id, int):
            if name_or_id in self._id_index:
                _obj = self._id_index[name_or_id]

        # when an obj was an instance, but the found one is not equal to it, reset the found one
        if _obj is not None and inst_passed and _obj != obj:
            _obj = None

        # prepare and return the found object
        if _obj is not None:
            # materialize when the found object is lazy
            if isinstance(_obj, LazyUniqueObject):
                # remember the position of the object
                idx = self.objects.index(_obj)

                # materializee
                with _obj.materialize(self) as _obj:
                    # add back the materialized object
                    self.objects[idx] = _obj
                    self._name_index[_obj.name] = _obj
                    self._id_index[_obj.id] = _obj

            return _obj

        if default != no_value:
            return default

        raise ValueError(f"object '{obj}' not known to index '{self}'")

    def get_first(self, default: T = no_value) -> UniqueObject | T:
        """
        Returns the first object of this index. If no object could be found, *default* is returned
        if set. An exception is raised otherwise.
        """
        if not self.objects and default != no_value:
            return default

        return self.get(self.objects[0].name)

    def get_last(self, default: T = no_value) -> UniqueObject | T:
        """
        Returns the last object of this index. If no object could be found, *default* is returned if
        set. An exception is raised otherwise.
        """
        if not self.objects and default != no_value:
            return default

        return self.get(self.objects[-1].name)

    def add(
        self,
        obj: UniqueObject | LazyUniqueObject,
        overwrite: bool = False,
    ) -> UniqueObject | LazyUniqueObject:
        """
        Adds *obj*, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`, to the index. When an object with the same :py:attr:`name` or
        :py:attr:`id` already exists and *overwrite* is *False*, an exception is raised. Otherwise,
        the object is overwritten. The added object is returned.
        """
        if isinstance(obj, LazyUniqueObject):
            # unique object type of the lazy object and this index must match
            if self.cls != obj.cls:
                raise TypeError(
                    f"LazyUniqueObject '{obj}' must materialize into '{self.cls}' instead of "
                    f"'{obj.cls}'",
                )
        elif not isinstance(obj, self.cls):
            # type of the object must match that of the index
            raise TypeError(f"object '{obj}' to add must be of type '{self.cls}'")

        self._sync_indices()

        # handle duplicates
        if obj.name in self._name_index:
            if not overwrite:
                raise DuplicateNameException(self.cls, obj.name, self)
            self.remove(obj.name)
        if obj.id in self._id_index:
            if not overwrite:
                raise DuplicateIdException(self.cls, obj.id, self)
            self.remove(obj.id)

        # add to objects and indices
        self.objects.append(obj)
        self._name_index[obj.name] = obj
        self._id_index[obj.id] = obj

        return obj

    def extend(
        self,
        objects: "UniqueObjectIndex" | list[UniqueObject | LazyUniqueObject],
        overwrite: bool = False,
    ) -> None:
        """
        Adds multiple new *objects* of type :py:attr:`cls` to this index. See :py:meth:`add` for
        more info.
        """
        # when objects is an index, do not materialize its objects via the normal iterator
        gen = objects.objects if isinstance(objects, UniqueObjectIndex) else objects
        for obj in gen:
            self.add(obj, overwrite=overwrite)

    def index(self, obj: Any) -> int:
        """
        Returns the position of an object *obj* in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name`, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`.
        """
        return self.objects.index(self.get(obj))

    def remove(self, obj: Any) -> bool:
        """
        Remove an object *obj* from the index. *obj* can be an :py:attr:`id`, a :py:attr:`name`, a
        :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that wraps a type
        :py:attr:`cls`. *True* is returned in case an object could be removed, and *False*
        otherwise.
        """
        self._sync_indices()

        name_or_id = obj
        inst_passed = False
        if isinstance(obj, self.cls) or isinstance(obj, LazyUniqueObject) and obj.cls == self.cls:
            name_or_id = obj.name
            inst_passed = True

        _obj = None
        if isinstance(name_or_id, str):
            if name_or_id in self._name_index:
                _obj = self._name_index[name_or_id]

        elif isinstance(name_or_id, int):
            if name_or_id in self._id_index:
                _obj = self._id_index[name_or_id]

        # when an obj was an instance, but the found one is not equal to it, reset the found one
        if _obj is not None and inst_passed and _obj != obj:
            _obj = None

        # do nothing if no object was found, or if it does not exactly match the passed one
        if _obj is None:
            return False

        # remove from indices and objects
        self._name_index.pop(_obj.name)
        self._id_index.pop(_obj.id)
        self.objects.remove(_obj)

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
