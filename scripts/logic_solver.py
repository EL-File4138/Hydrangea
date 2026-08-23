"""Derive simplified boolean expressions from a truth table."""

from sympy import simplify_logic, symbols
from sympy.logic import SOPform


def logic_solver(truth_table, variables, outputs):
    """Return simplified SOP expressions for every truth-table output.

    Use ``1`` for a minterm, ``0`` for an off-set value, and ``-1`` for a
    don't-care value. Each row must contain values for ``variables`` followed
    by values for ``outputs``.
    """
    variables = tuple(variables)
    outputs = tuple(outputs)
    if not variables:
        raise ValueError("at least one input variable is required")
    if not outputs:
        raise ValueError("at least one output is required")

    rows = [list(row) for row in truth_table]
    expected_width = len(variables) + len(outputs)
    if any(len(row) != expected_width for row in rows):
        raise ValueError("each row must contain every input and output value")
    if any(value not in (0, 1, -1) for row in rows for value in row):
        raise ValueError("truth-table values must be 0, 1, or -1")

    expressions = {}
    for offset, output in enumerate(outputs):
        output_index = len(variables) + offset
        minterms = [row[: len(variables)] for row in rows if row[output_index] == 1]
        dontcares = [row[: len(variables)] for row in rows if row[output_index] == -1]
        expressions[output] = simplify_logic(SOPform(variables, minterms, dontcares))

    return expressions


if __name__ == "__main__":
    variables = symbols("A:D")
    outputs = ["a"]
    truth_table = [
        [0, 0, 0, 0, -1],
        [0, 0, 0, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 1, 1],
        [0, 1, 0, 0, 0],
        [0, 1, 0, 1, 1],
        [0, 1, 1, 0, 0],
        [0, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 1, 0],
        [1, 0, 1, 0, 1],
        [1, 0, 1, 1, 0],
        [1, 1, 0, 0, 1],
        [1, 1, 0, 1, -1],
        [1, 1, 1, 0, -1],
        [1, 1, 1, 1, -1],
    ]
    print(logic_solver(truth_table, variables, outputs))
