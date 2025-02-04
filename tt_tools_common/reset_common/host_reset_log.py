# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains functions used to generate host logs that are compatible with elasticsearch.
"""

from __future__ import annotations
import json
import base64
import inspect
import datetime
from pathlib import Path

try:
    # Try the newer v2 pydantic and use that first
    from pydantic.v1 import BaseModel
    from pydantic.v1.fields import Field
except:
    # Assume we are on v1 and give that a go
    from pydantic import BaseModel
    from pydantic.fields import Field


from typing import Any, Union, List, TypeVar, Generic


class Long(int): ...


class Keyword(str): ...


class Text(str): ...


class Date(datetime.datetime):
    @classmethod
    def build(cls, format: str):
        cls.format = format

    @classmethod
    def get_mapping(cls):
        return {"type": "date", "format": cls.format}


def optional(*fields):
    """Decorator function used to modify a pydantic model's fields to all be optional.
    Alternatively, you can  also pass the field names that should be made optional as arguments
    to the decorator.
    Taken from https://github.com/samuelcolvin/pydantic/issues/1223#issuecomment-775363074
    """

    def dec(_cls):
        for field in fields:
            _cls.__fields__[field].required = False
            _cls.__fields__[field].default = None
        return _cls

    if fields and inspect.isclass(fields[0]) and issubclass(fields[0], BaseModel):
        cls = fields[0]
        fields = cls.__fields__
        return dec(cls)

    return dec


def type_to_mapping(type: Any):
    """Converts a python type to an elasticsearch mapping type"""

    if issubclass(type, float):
        return {"type": "float"}
    elif issubclass(type, bool):
        return {"type": "boolean"}
    elif issubclass(type, Long):
        return {"type": "long"}
    elif issubclass(type, int):
        return {"type": "integer"}
    elif issubclass(type, bytes):
        return {"type": "binary"}
    elif issubclass(type, Keyword):
        return {"type": "keyword"}
    elif issubclass(type, Text):
        return {"type": "text"}
    elif issubclass(type, str):
        return {"type": "text", "fields": {"keyword": {"type": "keyword"}}}
    elif issubclass(type, Date):
        return type.get_mapping()
    elif issubclass(type, datetime.date):
        return {"type": "date", "format": "strict_date_optional_time||epoch_millis"}
    elif issubclass(type, ElasticModel):
        return {"type": "object", "properties": type.get_mapping()}
    else:
        raise NotImplementedError(f"Have not implemented mapping support for {type}")


def field_to_mapping(info: Field):
    """Converts a pydantic field to an elasticsearch mapping type"""
    try:
        # print(info.outer_type_, type(info.outer_type_))
        if (
            hasattr(info.outer_type_, "__origin__")
            and info.outer_type_.__origin__ == Nested
        ):
            inner = type_to_mapping(info.type_)
            if inner.get("type", None) == "object":
                inner["type"] = "nested"
            else:
                inner = {"type": "nested", "properties": inner}
            return inner
        else:
            return type_to_mapping(info.type_)
    except NotImplementedError as exc:
        raise NotImplementedError(
            f"Have not implemented mapping support for {info}"
        ) from exc


def json_load_bytes(obj):
    """Converts a json object to bytes"""
    if "__type__" in obj:
        if obj["__type__"] == "bytes":
            return base64.b64decode(obj["bytes"].encode("ascii"))
    return obj


class ElasticModel(BaseModel):
    """Base class for models that are compatible with elasticsearch"""

    @classmethod
    def get_mapping(cls):
        mapping = {}
        for name, info in cls.__fields__.items():
            mapping[name] = field_to_mapping(info)

        return mapping

    # Will add the ability to save to elasticsearch as needed
    # def save(self, index: str):
    #     es.index(index=index, document=self.json())


T = TypeVar("T", bound=ElasticModel)


class Nested(list, Generic[T]): ...


@optional
class PciResetDeviceInfo(ElasticModel):
    """Model for storing information about a PCI reset device"""

    pci_index: List[int]


@optional
class MoboReset(ElasticModel):
    """Model for storing information about a mobo reset"""

    #  allow for either an int or None
    nb_host_pci_idx: Union[List[int], None]
    mobo: str
    credo: List[str]
    disabled_ports: List[str]


@optional
class HostResetLog(ElasticModel):
    """Model for storing information about a host reset log"""

    time: datetime.datetime
    host_name: str
    gs_tensix_reset: PciResetDeviceInfo
    wh_link_reset: PciResetDeviceInfo
    re_init_devices: bool
    wh_mobo_reset: List[MoboReset]
    disable_serial_report: bool
    disable_sw_version_report: bool

    def save_as_json(self, fname: Union[str, Path]):
        with open(fname, "w") as f:
            raw_json = self.json(exclude_none=False)
            reloaded_json = json.loads(raw_json)
            json.dump(reloaded_json, f, indent=4)
