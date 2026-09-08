from enum import Enum

from .errors import UnsupportedPlatformError


def _unsupported(*args, **kwargs):
    raise UnsupportedPlatformError("vdd")


class VddStatus(Enum):
    OK = "ok"
    NOT_INSTALLED = "not_installed"
    ACCESS_DENIED = "access_denied"
    ERROR = "error"


class VddError(RuntimeError):
    pass


VddProbeResult = None
VirtualDisplay = _unsupported
probe = _unsupported
remove_display_index = _unsupported
VDD_SETTLE_SECONDS = 1.5
