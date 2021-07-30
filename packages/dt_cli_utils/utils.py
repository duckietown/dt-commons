def str_to_bool(value) -> bool:
    value = value.lower()
    if value in ["y", "yes", "t", "true", "on", "1"]:
        return True
    elif value in ["n", "no", "f", "false", "off", "0"]:
        return False
    else:
        raise ValueError(f"Invalid truth value {value!r}.")
