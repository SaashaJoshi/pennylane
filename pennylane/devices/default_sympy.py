# Copyright 2018-2023 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This module contains the SymPy device"""
from typing import Callable, Optional, Sequence, Tuple, Union, Iterable

import pennylane as qml
from pennylane import DeviceError
from pennylane.tape import QuantumTape
from pennylane.devices import Device, DefaultExecutionConfig, ExecutionConfig
from pennylane.transforms.core import TransformProgram, transform
from pennylane.devices.qubit.preprocess import validate_measurements, expand_fn
from pennylane.operation import StatePrep


class DefaultSympy(Device):
    """TODO."""

    name: str = "default.sympy"

    def execute(
        self,
        circuits: Union[QuantumTape, Sequence[QuantumTape]],
        execution_config: ExecutionConfig = DefaultExecutionConfig,
    ):
        return _simulate(circuits) if isinstance(circuits, qml.tape.QuantumScript) else tuple(_simulate(c) for c in circuits)

    def preprocess(
        self,
        execution_config: ExecutionConfig = DefaultExecutionConfig,
    ) -> Tuple[TransformProgram, ExecutionConfig]:
        if execution_config.gradient_method == "adjoint":
            raise DeviceError("The adjoint gradient method is not supported on the default.sympy device")

        program = TransformProgram()

        program.add_transform(_validate_shots)
        program.add_transform(validate_measurements)

        program.add_transform(expand_fn, acceptance_function=_accepted_operator)

        return program, execution_config

    def supports_derivatives(
        self,
        execution_config: Optional[ExecutionConfig] = None,
        circuit: Optional[QuantumTape] = None,
    ) -> bool:
        if execution_config.gradient_method == "backprop" and execution_config.interface == "sympy":
            return True


def _accepted_operator(op: qml.operation.Operator) -> bool:
    """Indicates whether an operation is supported on default.sympy"""
    if isinstance(op, StatePrep) and not isinstance(op, qml.BasisState):
        return False
    return True


def _simulate(circuit: QuantumTape):
    from sympy.physics.quantum.gate import X, Y, Z, CNOT, H, S, SWAP, T, IdentityGate, UGate
    from sympy.physics.quantum.qapply import qapply
    from sympy import Matrix

    _directly_supported_gates = {
        qml.PauliX: X,
        qml.PauliY: Y,
        qml.PauliZ: Z,
        qml.CNOT: CNOT,
        qml.Hadamard: H,
        qml.S: S,
        qml.SWAP: SWAP,
        qml.T: T,
        qml.Identity: IdentityGate,
    }

    prep = None
    if len(circuit) > 0 and isinstance(circuit[0], qml.operation.StatePrepBase):
        prep = circuit[0]

    state = _create_initial_state(circuit.num_wires, prep)

    for op in circuit.operations[bool(prep):]:
        wires = circuit.wires.indices(op.wires)
        if (t := type(op)) in _directly_supported_gates:
            state = qapply(_directly_supported_gates[t](*wires) * state)
        else:
            sympy_mat = Matrix(qml.matrix(op))
            sympy_op = UGate(wires, sympy_mat)
            state = qapply(sympy_op * state)

    from sympy import simplify
    print(simplify(state))

    return 0.0


def _create_initial_state(
    n_wires: int,
    prep_operation: qml.operation.StatePrepBase = None,
):
    from sympy.physics.quantum.qubit import Qubit
    if not prep_operation:
        return Qubit("0" * n_wires)

    assert isinstance(prep_operation, qml.BasisState)
    prep_vals = prep_operation.parameters[0]
    return Qubit("".join(map(str, prep_vals)))


@transform
def _validate_shots(tape: qml.tape.QuantumTape, execution_config: ExecutionConfig = DefaultExecutionConfig) -> (Sequence[qml.tape.QuantumTape], Callable):
    """Validates that no shots are present in the input tape because this is not supported on the
    device."""
    if tape.shots:
        raise DeviceError("The default.sympy device does not support finite-shot execution")
    def null_postprocessing(results):
        """A postprocesing function returned by a transform that only converts the batch of results
        into a result for a single ``QuantumTape``.
        """
        return results[0]

    return [tape], null_postprocessing
