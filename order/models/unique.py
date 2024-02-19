# coding: utf-8

"""
Models definitions of unique objects and an index container to access them.
"""

from __future__ import annotations

__all__ = [
    "UniqueObject", "LazyUniqueObject", "UniqueObjectIndex",
    "DuplicateObjectException", "DuplicateNameException", "DuplicateIdException",
]

from abc import abstractmethod
from contextlib import contextmanager

from pydantic import Field, field_validator

from order.types import (
    ClassVar, Any, T, List, Union, Generator, GeneratorType, PositiveStrictInt, NonEmptyStrictStr,
    KeysView, Lazy, Callable,
)
from order.models.base import Model, AdapterModel
from order.adapters.base import DataProvider
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

    id: PositiveStrictInt = Field(frozen=True)
    name: NonEmptyStrictStr = Field(frozen=True)

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
            return self is other

        # additional, dynamic checks
        eq = self.__eq_extra__(other)
        if eq is not None:
            return eq

        return False

    def __eq_extra__(self, other: Any) -> bool | None:
        """
        Hook to define additional equality checks with respect to *other*. *None* should be returned
        in case no decision could be made.
        """
        return None

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

    def __repr_circular__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, id={self.id})"


class WrapsUniqueClass(Model):

    class_name: NonEmptyStrictStr = Field(frozen=True)

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
        self._cls: UniqueObjectMeta = UniqueObjectMeta.get_unique_cls(self.class_name)

    @property
    def cls(self) -> UniqueObjectMeta:
        return self._cls


class UniqueObject(UniqueObjectBase, metaclass=UniqueObjectMeta):

    AUTO_ID: ClassVar[str] = "+"

    lazy_cls: ClassVar[UniqueObjectBase] = None

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

    def __eq_extra__(self, other: Any) -> bool | None:
        extra = super().__eq_extra__(other)
        if extra is not None:
            return extra

        if self.lazy_cls and isinstance(other, self.lazy_cls):
            return self.name == other.name and self.id == other.id

        return None


class LazyUniqueObject(UniqueObjectBase, WrapsUniqueClass):

    adapter: AdapterModel

    @classmethod
    @abstractmethod
    def create_lazy_dict(cls) -> dict[str, Any]:
        # must be implemented by subclasses
        ...

    @classmethod
    def create(cls, *args, **kwargs) -> "LazyUniqueObject":
        return cls(**cls.create_lazy_dict(*args, **kwargs))

    def __eq_extra__(self, other: Any) -> bool | None:
        extra = super().__eq_extra__(other)
        if extra is not None:
            return extra

        if isinstance(other, self.cls):
            return self.name == other.name and self.id == other.id

        return None

    @contextmanager
    def materialize(self, index: "UniqueObjectIndex") -> Generator[UniqueObject, None, None]:
        with DataProvider.instance().materialize(self.adapter) as materialized:
            # complain when the adapter did not provide a value for this attribute
            if self.adapter.key not in materialized:
                raise KeyError(
                    f"adapter '{self.adapter.name}' did not provide field "
                    f"'{self.adapter.key}' required to materialize '{self!r}'",
                )

            # create the materialized instance
            inst = self.cls(**materialized[self.adapter.key])

            yield inst


class UniqueObjectIndex(WrapsUniqueClass):
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

    objects: Lazy[List[Union[LazyUniqueObject, UniqueObject]]] = Field(
        default_factory=list,
        repr=False,
    )

    @field_validator("lazy_objects", mode="after")
    @classmethod
    def detect_duplicate_objects(
        cls,
        objects: Lazy[list[LazyUniqueObject | UniqueObject]],
    ) -> Lazy[list[LazyUniqueObject | UniqueObject]]:
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

        # hashmap indices for faster lookups
        self._name_index: dict[str, LazyUniqueObject | UniqueObject] = {}
        self._id_index: dict[int, LazyUniqueObject | UniqueObject] = {}

        # name-based DotAccessProxy
        self._n: DotAccessProxy = DotAccessProxy(self.get, dir=lambda: self._name_index.keys())

        # callbacks registered for certain events
        self._after_add: Callable | None = None
        self._after_remove: Callable | None = None
        self._after_materialize: Callable | None = None

        # attributes to be passed to the lazy object constructor in add()
        self._lazy_object_kwargs: dict[str, Any] = {}

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

    def __nonzero__(self) -> bool:
        """
        Boolish conversion that depends on the number of objects in the index.
        """
        return bool(self.objects)

    def __getitem__(self, obj: Any) -> UniqueObject:
        """
        Shorthand for :py:func:`get` without a default value.
        """
        return self.get(obj)

    def __repr_args__(self, verbose: bool = False, adapters: bool = False) -> GeneratorType:
        """
        Yields all key-values pairs to be injected into the representation.
        """
        yield from super().__repr_args__(verbose=verbose, adapters=adapters)

        yield "len", len(self)

        if verbose:
            yield "objects", self.objects

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

    def _reset_indices(self) -> None:
        """
        Fully resets the two hashmaps and synchronizes them back to :py:attr:`objects`.
        """
        self._name_index: dict[str, LazyUniqueObject | UniqueObject] = {}
        self._id_index: dict[int, LazyUniqueObject | UniqueObject] = {}
        self._sync_indices()

    def set_callbacks(
        self,
        materialize: Callable | None = None,
        add: Callable | None = None,
        remove: Callable | None = None,
    ) -> None:
        """
        Registers callbacks invoked after :py:meth:`materialize`, py:meth:`add` and
        py:meth:`remove`.
        """
        self._after_materialize = materialize
        self._after_add = add
        self._after_remove = remove

    def set_lazy_object_kwargs(self, **kwargs) -> None:
        """
        Registers keyword arguments *kwargs* that are used for the lazy object creation in
        :py:meth:`add`.
        """
        self._lazy_object_kwargs.clear()
        self._lazy_object_kwargs.update(kwargs)

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

        # instance
        if isinstance(obj, self.cls):
            return self._name_index.get(obj.name) is obj

        # lazy instance
        if isinstance(obj, LazyUniqueObject) and obj.cls == self.cls:
            return obj.name in self._name_index and obj.id in self._id_index

        # name
        if isinstance(obj, str):
            return obj in self._name_index

        # id
        if isinstance(obj, int):
            return obj in self._id_index

        return False

    def get(
        self,
        obj: Any,
        default: T = no_value,
        skip_callback: bool = False,
    ) -> UniqueObject | T:
        """
        Returns an object *obj* contained in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name`, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`. If no object could be found, *default* is returned if set. An
        exception is raised otherwise.

        After successful materialization, the :py:func:`_after_materialize` callback is invoked
        unless *skip_callback* is *True*.
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

                # materialize
                with _obj.materialize(self) as _obj:
                    # add back the materialized object
                    self.objects[idx] = _obj
                    self._name_index[_obj.name] = _obj
                    self._id_index[_obj.id] = _obj

                # invoke the materialization callback
                if not skip_callback and callable(self._after_materialize):
                    self._after_materialize(_obj)

            return _obj

        if default != no_value:
            return default

        raise ValueError(f"object '{obj}' not known to index '{self!r}'")

    def get_first(self, default: T = no_value) -> UniqueObject | T:
        """
        Returns the first object of this index. If no object could be found, *default* is returned
        if set. An exception is raised otherwise.
        """
        if self.objects:
            return self.get(self.objects[0].name)

        if default != no_value:
            return default

        raise Exception(f"cannot return first object, '{self!r}' is empty")

    def get_last(self, default: T = no_value) -> UniqueObject | T:
        """
        Returns the last object of this index. If no object could be found, *default* is returned if
        set. An exception is raised otherwise.
        """
        if self.objects:
            return self.get(self.objects[-1].name)

        if default != no_value:
            return default

        raise Exception(f"cannot return last object, '{self!r}' is empty")

    def add(
        self,
        *args,
        overwrite: bool = False,
        skip_callback: bool = False,
        **kwargs,
    ) -> LazyUniqueObject | UniqueObject:
        """
        Adds *obj*, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`, to the index. When an object with the same :py:attr:`name` or
        :py:attr:`id` already exists and *overwrite* is *False*, an exception is raised. Otherwise,
        the object is overwritten. The added object is returned.

        After successful materialization, the :py:func:`_after_add` callback is invoked unless
        *skip_callback* is *True*.
        """
        if args and (len(args) != 1 or kwargs):
            raise ValueError(
                f"add() of {self!r} expects either a single positional argument or keyword "
                f"arguments, but got args={args} and kwargs={kwargs}",
            )

        # get or create the object
        if len(args) == 1:
            obj = args[0]

            # type checks
            if isinstance(obj, LazyUniqueObject):
                # unique object type of the lazy object and this index must match
                if self.cls != obj.cls:
                    raise TypeError(
                        f"LazyUniqueObject '{obj!r}' must materialize into '{self.cls}' instead of "
                        f"'{obj.cls}'",
                    )
            elif not isinstance(obj, self.cls):
                # type of the object must match that of the index
                raise TypeError(f"object '{obj}' to add must be of type '{self.cls}'")

        elif self.cls.lazy_cls and set(kwargs) == {"name", "id"}:
            # create a lazy object when the lazy class is known and only name and id are given
            obj = self.cls.lazy_cls.create(**{**kwargs, **self._lazy_object_kwargs})

        else:
            # create a normal object
            obj = self.cls(**kwargs)

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

        # invoke the add callback
        if not skip_callback and callable(self._after_add):
            self._after_add(obj)

        return obj

    def extend(
        self,
        objects: "UniqueObjectIndex" | list[LazyUniqueObject | UniqueObject],
        overwrite: bool = False,
        skip_callback: bool = False,
    ) -> None:
        """
        Adds multiple new *objects* of type :py:attr:`cls` to this index. See :py:meth:`add` for
        more info.
        """
        # when objects is an index, do not materialize its objects via the normal iterator
        gen = objects.objects if isinstance(objects, UniqueObjectIndex) else objects
        for obj in gen:
            self.add(obj, overwrite=overwrite, skip_callback=skip_callback)

    def index(self, obj: Any) -> int:
        """
        Returns the position of an object *obj* in this index. *obj* can be an :py:attr:`id`, a
        :py:attr:`name`, a :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that
        wraps a type :py:attr:`cls`.
        """
        return self.objects.index(self.get(obj))

    def remove(self, obj: Any, skip_callback: bool = False) -> bool:
        """
        Remove an object *obj* from the index. *obj* can be an :py:attr:`id`, a :py:attr:`name`, a
        :py:class:`UniqueObject` of type or a :py:class:`LazyUniqueObject` that wraps a type
        :py:attr:`cls`. *True* is returned in case an object could be removed, and *False*
        otherwise.

        After successful materialization, the :py:func:`_after_remove` callback is invoked unless
        *skip_callback* is *True*.
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

        # invoke the remove callback
        if not skip_callback and callable(self._after_add):
            self._after_remove(obj)

        return True

    def clear(self) -> None:
        """
        Removes all objects from the index. See :py:meth:`remove` for more info.
        """
        for obj in list(self.objects):
            self.remove(obj)


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
