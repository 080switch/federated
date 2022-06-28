# Copyright 2019, The TensorFlow Federated Authors.
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

import asyncio

from absl.testing import absltest
import tensorflow as tf

from tensorflow_federated.python.common_libs import structure
from tensorflow_federated.python.core.impl.executors import eager_tf_executor
from tensorflow_federated.python.core.impl.executors import executor_test_utils
from tensorflow_federated.python.core.impl.tensorflow_context import tensorflow_computation


class TracingExecutorTest(absltest.TestCase):

  def test_simple(self):
    ex = executor_test_utils.TracingExecutor(
        eager_tf_executor.EagerTFExecutor())

    @tensorflow_computation.tf_computation(tf.int32)
    def add_one(x):
      return tf.add(x, 1)

    async def _make():
      v1 = await ex.create_value(add_one)
      v2 = await ex.create_value(10, tf.int32)
      v3 = await ex.create_call(v1, v2)
      v4 = await ex.create_struct(structure.Struct([('foo', v3)]))
      v5 = await ex.create_selection(v4, 0)
      return await v5.compute()

    result = asyncio.run(_make())
    self.assertEqual(result.numpy(), 11)

    expected_trace = [('create_value', add_one, 1),
                      ('create_value', 10, tf.int32, 2),
                      ('create_call', 1, 2, 3),
                      ('create_struct', structure.Struct([('foo', 3)]), 4),
                      ('create_selection', 4, 0, 5), ('compute', 5, result)]

    self.assertLen(ex.trace, len(expected_trace))
    for x, y in zip(ex.trace, expected_trace):
      self.assertEqual(x, y)


if __name__ == '__main__':
  absltest.main()
