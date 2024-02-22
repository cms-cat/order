# coding: utf-8

from __future__ import annotations

__all__ = ["Uncertainty", "LazyUncertainty", "UncertaintyIndex"]

from pydantic import Field, field_validator

from order.types import (
    Union, List, Dict, NonEmptyStrictStr, PositiveStrictInt,
    PositiveStrictFloat, Lazy, ClassVar, Any
)

from order.models.base import Model, AdapterModel
from order.models.unique import UniqueObjectBase, UniqueObject, LazyUniqueObject, UniqueObjectIndex

from typing import ClassVar


class UncertaintyIndex(UniqueObjectIndex):
    
        class_name: NonEmptyStrictStr = Field(default="Uncertainty", frozen=True)
        objects: Lazy[List[Union["LazyUncertainty", "Uncertainty"]]] = Field(default_factory=list, repr=False)


class LazyUncertainty(LazyUniqueObject):

    class_name: NonEmptyStrictStr = Field(default="Uncertainty", frozen=True)

    @classmethod
    def create_lazy_dict(cls, name: str, id: int) -> dict:
        return {
            "name": name,
            "id": id,
            "class_name": "Uncertainty",
            "adapter": {
                "adapter": "order_uncertainty",
                "key": "uncertainty",
                "arguments": {
                    "uncertainty_name": name,
                },
            },
        }


class UncertaintyMeta(type(UniqueObject)):

    _classes = {}
    
    def __new__(metacls, cls_name, bases, cls_dict):    
        # Define the new type
        cls = super().__new__(metacls, cls_name, bases, cls_dict)
        # Store the new type in the _classes dictionary
        if hasattr(cls, "class_label"):
            if hasattr(bases[0], "class_label"):
                metacls._classes["_".join([bases[0].class_label, cls.class_label])] = cls
            else:
                metacls._classes[cls.class_label] = cls
        print(metacls._classes)
        # Save the class in the class cache of all the base classes
        return cls


    def get_class(cls, class_label:str):
        '''This function splits the class_label using _ and look for the
        closest match in the available classes dict'''
        breakpoint()
        toks = class_label.split("_")
        for i in range(len(toks), 0, -1):
            label = "_".join(toks[:i])
            if label in cls._classes:
                return cls._classes[label]
        # If no match is found, raise exception
        raise ValueError(f"Uncertainty class label {class_label} not found in {cls._classes.keys()}")

 

class Uncertainty(UniqueObject, metaclass=UncertaintyMeta):
    '''Model that represents an uncertainty and its splitting/parent.
    The uncertainty_type is a string that connects the data format
    to a specific behaviour class'''

    class_label: ClassVar[str] = "syst"

    description: NonEmptyStrictStr = Field(default="", description="Description of the uncertainty")
  
    @classmethod
    def create(cls, uncertainty_type:str, **kwargs) -> Uncertainty:
        '''Create a new uncertainty of the given type'''
        cls = cls.get_class(uncertainty_type)
        return cls(**kwargs)

    
    
class ExperimentalUncertainty(Uncertainty):
    '''Model that represents an experimental uncertainty'''
    class_label: ClassVar[str] = "exp"
    pog : NonEmptyStrictStr = Field(default="", description="POG that provides the uncertainty")
    
    pass


class TheoryUncertainty(Uncertainty):
    '''Model that represents an experimental uncertainty'''
    class_label: ClassVar[str] = "theory"
    generator: NonEmptyStrictStr = Field(default="", description="Generator that provides the uncertainty")

    pass
