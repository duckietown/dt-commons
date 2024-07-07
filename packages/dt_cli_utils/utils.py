import logging
from typing import Optional


def str_to_bool(value) -> bool:
    value = value.lower()
    if value in ["y", "yes", "t", "true", "on", "1"]:
        return True
    elif value in ["n", "no", "f", "false", "off", "0"]:
        return False
    else:
        raise ValueError(f"Invalid truth value {value!r}.")


def install_colored_logs(logger: Optional[logging.Logger] = None, level: int = None):
    import coloredlogs
    if logger is None and level is None:
        raise ValueError("Either 'logger' or 'level' must be provided")
    # NOTE: This is kinda weird, but it seems that the coloredlogs library has
    #       some issues: https://github.com/xolox/python-coloredlogs/issues/18
    # get the current root logger level
    logLevel = logging.getLogger().getEffectiveLevel()
    # install the coloredlogs on our logger and with our level
    coloredlogs.install(level=level or logger.level, logger=logger)
    # restore the root logger level
    logging.getLogger().setLevel(logLevel)
