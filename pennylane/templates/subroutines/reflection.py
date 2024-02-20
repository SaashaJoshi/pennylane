# Copyright 2018-2024 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This submodule contains the template for the Reflection operation.
"""

import numpy as np
import pennylane as qml
from pennylane.operation import Operation
from pennylane.ops import SymbolicOp


class Reflection(SymbolicOp, Operation):
    r"""An operation that applies a reflection along a state :math:`|\Psi\rangle`.
    This operator is useful in algorithms such as `amplitude amplification <https://arxiv.org/abs/quant-ph/0005055>`__
    or `oblivious amplitude amplification <https://arxiv.org/abs/1312.1414>`__.

    Given an :class:`~.Operator` :math:`U` such that :math:`|\Psi\rangle = U|0\rangle`,  and a reflection angle :math:`\alpha`,
    this template creates the operation:

    .. math::

        \text{Reflection}(U, \alpha) = -I + (1 - e^{i\alpha}) |\Psi\rangle \langle \Psi|


    Args:
        U (Operator): The operator that generates the state :math:`|\Psi\rangle`.
        alpha (float): the reflection angle. Default is :math:`\pi`.
        reflection_wires (Any or Iterable[Any]): Subsystem of wires on which to reflect. The default is None and the reflection will be applied on the U wires.

    **Example**

    This example shows how to apply the reflection :math:`-I` + 2|+\rangle \langle +|` to the state :math:`|1\rangle`.

    .. code-block::

        @qml.prod
        def generator(wires):
            qml.Hadamard(wires=wires)

        U = generator(wires=0)

        dev = qml.device('default.qubit')

        @qml.qnode(dev)
        def circuit():

            # Initialize to the state |1>
            qml.qml.PauliX(wires=0)

            # Apply the reflection
            qml.Reflection(U)

            return qml.state()

        circuit()


    .. details::
        :title: Theory

        The operator is built as follows:

        .. math::

            \text{Reflection}(U, \alpha) = -I + (1 - e^{i\alpha}) |\Psi\rangle \langle \Psi| = U(-I + (1 - e^{i\alpha}) |0\rangle \langle 0|)U^{\dagger}.

        The central block is obtained through a PhaseShift controlled operator.

        In the case of specifying the reflection wires,  the operator would have the following expression.

        .. math::

            U(I - (1 - e^{i\alpha}) |0\rangle^{\otimes m} \langle 0|^{\otimes m}\otimes I^{n-m})U^{\dagger},

        where :math:`m` is the number of reflection wires and :math:`n` is the total number of wires.

    """

    def __init__(self, U, alpha=np.pi, reflection_wires=None, id=None):
        if reflection_wires is None:
            reflection_wires = U.wires

        if not set(reflection_wires).issubset(set(U.wires)):
            raise ValueError("The reflection wires must be a subset of the operation wires.")

        self.hyperparameters["reflection_wires"] = reflection_wires
        self.hyperparameters["alpha"] = alpha
        self.hyperparameters["U"] = U

        self._name = "Reflection"

        super().__init__(base=U, id=id)

    @property
    def has_matrix(self):
        """True if the operation has a defined matrix representation."""
        return False

    @property
    def U(self):
        """The generator operation."""
        return self.parameters["U"]

    @property
    def alpha(self):
        """The alpha angle for the operation."""
        return self.parameters["alpha"]

    @property
    def reflection_wires(self):
        """The reflection wires for the operation."""
        return self.parameters["reflection_wires"]

    # pylint:disable=arguments-differ
    @staticmethod
    def compute_decomposition(*_, U, alpha, reflection_wires, **__):
        wires = qml.wires.Wires(reflection_wires)

        ops = []

        ops.append(qml.GlobalPhase(np.pi))
        ops.append(qml.adjoint(U))

        if len(wires) > 1:
            ops.append(qml.PauliX(wires=wires[-1]))
            ops.append(
                qml.ctrl(
                    qml.PhaseShift(alpha, wires=wires[-1]),
                    control=wires[:-1],
                    control_values=[0] * (len(wires) - 1),
                )
            )
            ops.append(qml.PauliX(wires=wires[-1]))

        else:
            ops.append(qml.PauliX(wires=wires))
            ops.append(qml.PhaseShift(alpha, wires=wires))
            ops.append(qml.PauliX(wires=wires))

        ops.append(U)

        return ops
