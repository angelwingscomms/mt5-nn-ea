from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_define_value(raw_value: str, known_values: dict[str, Scalar]) -> Scalar:
    value = raw_value.split("//", 1)[0].strip()
    if value.endswith("f"):
        value = value[:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    safe_names = dict(known_values)
    safe_names.update({"true": True, "false": False})
    return eval(value, {"__builtins__": {}}, safe_names)
