"""Create formatted truth tables for SymPy boolean expressions."""

from itertools import product

from sympy import Symbol


def logic_evaluator(expression, variables=None):
    """Return a truth table for a SymPy symbolic boolean expression.

    Args:
        expression: A SymPy boolean expression, such as ``(A & B) | ~C``.
        variables: Optional iterable that fixes the input-column order. When
            omitted, variables are collected from the expression by name.
    """
    if variables is None:
        variables = sorted(expression.atoms(Symbol), key=lambda symbol: symbol.name)
    else:
        variables = list(variables)

    if len(set(variables)) != len(variables):
        raise ValueError("variables must not contain duplicates")

    expression_label = str(expression).replace("&", "AND").replace("|", "OR")
    labels = [str(variable) for variable in variables] + [expression_label]
    rows = []
    for values in product((False, True), repeat=len(variables)):
        assignment = dict(zip(variables, values))
        result = expression.subs(assignment)
        rows.append([int(value) for value in values] + [int(bool(result))])

    widths = [
        max(len(label), *(len(str(row[index])) for row in rows))
        for index, label in enumerate(labels)
    ]
    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    header = "| " + " | ".join(
        label.center(width) for label, width in zip(labels, widths)
    ) + " |"
    body = [
        "| " + " | ".join(
            str(value).center(width) for value, width in zip(row, widths)
        ) + " |"
        for row in rows
    ]
    return "\n".join([separator, header, separator, *body, separator])


if __name__ == "__main__":
    from sympy import symbols

    A, B, C = symbols("A B C")
    expression = (A & ~B) | (~B & ~C) | (~A & B & C)
    print(logic_evaluator(expression))
