import os
import socket
import logging
import netifaces
import requests

from dt_robot_utils import RobotHardware, get_robot_hardware
from .constants import DeviceHardwareBrand, DEVICE_ID_IFACE, STATS_DIR

# create logger
logging.basicConfig()
logger = logging.getLogger(os.environ.get('DT_MODULE_TYPE', 'module') + '.device')
logger.setLevel(logging.INFO)
if 'DEBUG' in os.environ and os.environ['DEBUG'].lower() in ['true', 'yes', '1']:
    logger.setLevel(logging.DEBUG)


def get_device_id() -> str:
    hw: RobotHardware = get_robot_hardware()
    if hw is RobotHardware.VIRTUAL:
        # virtual robots do not use network interfaces to figure out their ID but a generated random MAC
        eth0_mac_fpath: str = os.path.join(STATS_DIR, "MAC", "eth0")
        if not os.path.exists(eth0_mac_fpath):
            raise FileNotFoundError(f"Device ID file '{eth0_mac_fpath}' not found.")
        with open(eth0_mac_fpath, "rt") as fin:
            mac = fin.read()
    else:
        try:
            addresses = netifaces.ifaddresses(DEVICE_ID_IFACE)
        except ValueError:
            msg = f"Network interface '{DEVICE_ID_IFACE}' not found. Device ID cannot be computed."
            logger.error(msg)
            raise ValueError(msg)
        # read MAC address
        try:
            mac = addresses[netifaces.AF_LINK][0]['addr']
        except KeyError:
            msg = f"No MAC address found on '{DEVICE_ID_IFACE}'. Cannot compute unique device ID."
            logger.error(msg)
            raise ValueError(msg)
    # turn MAC into a unique ID
    device_id = mac.replace(':', '').strip()
    # make sure we have a valid MAC address
    if len(device_id) != 12:
        msg = f"Invalid MAC address '{mac}'. Cannot compute unique device ID."
        logger.error(msg)
        raise ValueError(msg)
    # ---
    return device_id


def get_device_hostname() -> str:
    return socket.gethostname()


def get_device_hardware_brand() -> DeviceHardwareBrand:
    hw = os.environ.get('ROBOT_HARDWARE', 'UNKNOWN')
    if hw == 'raspberry_pi':
        return DeviceHardwareBrand.RASPBERRY_PI
    if hw == 'raspberry_pi_64':
        return DeviceHardwareBrand.RASPBERRY_PI_64
    elif hw == 'jetson_nano':
        return DeviceHardwareBrand.JETSON_NANO
    elif hw == 'virtual':
        return DeviceHardwareBrand.VIRTUAL
    # ---
    return DeviceHardwareBrand.UNKNOWN


def _device_trigger(trigger: str, quiet: bool = True) -> bool:
    hostname = get_device_hostname()
    url = f"http://{hostname}.local/health/trigger/{trigger}"
    # ---
    try:
        data = requests.get(url).json()
        assert data['status'] == 'needs-confirmation'
        assert 'token' in data
        token = data['token']
        url += f"?token={token}"
        data = requests.get(url).json()
        assert data['status'] == 'ok'
    except BaseException as e:
        if quiet:
            logger.error(str(e))
            return False
        else:
            raise e
    # ---
    return True


def shutdown_device(quiet: bool = True) -> bool:
    return _device_trigger('shutdown', quiet=quiet)


def reboot_device(quiet: bool = True) -> bool:
    return _device_trigger('reboot', quiet=quiet)
