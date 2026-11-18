"""
Access to the robot-level calibration files stored on the robot under
``/data/config/calibrations/<calibration>/``.

Each calibration folder holds a ``default.yaml`` (written when the robot is initialized) and,
optionally, a ``<robot_name>.yaml`` override produced by a calibration procedure. The robot-specific
file wins when present.

The ``robot`` calibration carries the physical parameters shared by several nodes (kinematics,
odometry, state estimation): wheel baseline, wheel radius and encoder resolution.
"""
import dataclasses
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import yaml

CALIBRATIONS_DIR: str = "/data/config/calibrations"
ROBOT_PARAMS_CALIBRATION: str = "robot"

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RobotParams:
    """Physical parameters of the robot, see ``/data/config/calibrations/robot/``."""
    # [m] distance between the two wheels
    wheel_baseline: float = 0.1
    # [m] wheel radius
    wheel_radius: float = 0.0318
    # [ticks] encoder ticks per wheel revolution
    encoder_resolution: int = 135


DEFAULT_ROBOT_PARAMS: RobotParams = RobotParams()


def get_calibration_file(calibration: str, robot_name: Optional[str] = None) -> Optional[str]:
    """
    Returns the path of the calibration file to use for ``calibration``:
    ``<robot_name>.yaml`` if it exists, otherwise ``default.yaml`` if it exists, otherwise ``None``.
    ``robot_name`` defaults to the ``VEHICLE_NAME`` environment variable.
    """
    folder = os.path.join(CALIBRATIONS_DIR, calibration)
    robot_name = robot_name or os.environ.get("VEHICLE_NAME")
    candidates = []
    if robot_name:
        candidates.append(os.path.join(folder, f"{robot_name}.yaml"))
    candidates.append(os.path.join(folder, "default.yaml"))
    for fpath in candidates:
        if os.path.isfile(fpath):
            return fpath
    return None


def load_calibration(calibration: str, robot_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads the calibration file selected by :func:`get_calibration_file` as a dictionary.
    Returns an empty dictionary (with a warning) when no file is found.
    """
    fpath = get_calibration_file(calibration, robot_name)
    if fpath is None:
        _logger.warning(f"No '{calibration}' calibration file found under {CALIBRATIONS_DIR}/{calibration}/, "
                        f"using built-in defaults.")
        return {}
    with open(fpath, "rt") as fin:
        data = yaml.safe_load(fin) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Calibration file {fpath} must contain a mapping, found {type(data).__name__}.")
    return data


def get_robot_params(robot_name: Optional[str] = None) -> RobotParams:
    """
    Returns the robot-level physical parameters, reading ``/data/config/calibrations/robot/``.
    Keys missing from the file fall back to :data:`DEFAULT_ROBOT_PARAMS`.
    """
    data = load_calibration(ROBOT_PARAMS_CALIBRATION, robot_name)
    fields = {f.name: f for f in dataclasses.fields(RobotParams)}
    unknown = sorted(set(data) - set(fields))
    if unknown:
        _logger.warning(f"Ignoring unknown robot parameters {unknown} in the '{ROBOT_PARAMS_CALIBRATION}' calibration.")
    values = {name: field.type(data[name]) for name, field in fields.items() if name in data}
    return RobotParams(**values)
