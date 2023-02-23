# Copyright 2021, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for testing the program library."""

from collections.abc import Iterable, Iterator
import contextlib
import sys
from typing import NamedTuple
import warnings

import attrs
import tensorflow as tf
import tree

from tensorflow_federated.python.core.impl.types import computation_types
from tensorflow_federated.python.program import value_reference


class TestMaterializableValueReference(
    value_reference.MaterializableValueReference
):
  """A test implementation of `tff.program.MaterializableValueReference`."""

  def __init__(self, value: value_reference.MaterializedValue):
    if isinstance(value, bool):
      self._type_signature = computation_types.TensorType(tf.bool)
    elif isinstance(value, int):
      self._type_signature = computation_types.TensorType(tf.int32)
    elif isinstance(value, str):
      self._type_signature = computation_types.TensorType(tf.string)
    elif isinstance(value, tf.data.Dataset):
      self._type_signature = computation_types.SequenceType(tf.int32)
    else:
      raise NotImplementedError(f'Unexpected type found: {type(value)}.')
    self._value = value

  @property
  def type_signature(self) -> value_reference.MaterializableTypeSignature:
    return self._type_signature

  async def get_value(self) -> value_reference.MaterializedValue:
    return self._value

  def __eq__(self, other: object) -> bool:
    if self is other:
      return True
    elif not isinstance(other, TestMaterializableValueReference):
      return NotImplemented
    if self._type_signature != other._type_signature:
      return False
    if self._type_signature.is_sequence():
      return list(self._value) == list(other._value)
    else:
      return self._value == other._value


class TestNamedTuple1(NamedTuple):
  a: bool
  b: int
  c: str
  d: value_reference.MaterializableValueReference


class TestNamedTuple2(NamedTuple):
  a: int


class TestNamedTuple3(NamedTuple):
  x: TestNamedTuple1
  y: TestNamedTuple2


@attrs.define
class TestAttrs1:
  a: bool
  b: int
  c: str
  d: value_reference.MaterializableValueReference


@attrs.define
class TestAttrs2:
  a: int


@attrs.define
class TestAttrs3:
  x: TestAttrs1
  y: TestAttrs2


def assert_types_equal(a: object, b: object) -> None:
  def _assert_type_equal(a: object, b: object) -> None:
    if not isinstance(a, type(b)):
      raise AssertionError(f'{type(a)} != {type(b)}')

  try:
    tree.map_structure(_assert_type_equal, a, b)
  except (TypeError, ValueError) as e:
    raise AssertionError(
        "The two structures don't have the same nested structure."
    ) from e


@contextlib.contextmanager
def assert_not_warns(
    category: type[Warning],
) -> Iterator[Iterable[warnings.WarningMessage]]:
  """Yields a context manager used to test if a warning is not triggered."""

  # The `__warningregistry__`'s need to be in a pristine state for tests to
  # work properly. This code replicates the standard library implementation of
  # `TestCase.assertWarns`. See
  # https://github.com/python/cpython/blob/main/Lib/unittest/case.py for more
  # information.
  for v in list(sys.modules.values()):
    if getattr(v, '__warningregistry__', None):
      v.__warningregistry__ = {}

  with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always', category=category)
    yield w
    for warning in w:
      if issubclass(warning.category, category):
        raise AssertionError(f'Warned `{category.__name__}` unexpectedly.')
