# backends/linux.py
from backends.base import BaseBackend
from models import WiFiNetwork, BTDevice, GPSLocation


class LinuxBackend(BaseBackend):
    def scan_wifi(self) -> list[WiFiNetwork]:
        raise NotImplementedError("Linux backend: implement using `iw dev <iface> scan`")

    def scan_bluetooth(self) -> list[BTDevice]:
        raise NotImplementedError("Linux backend: implement using hcitool/bluetoothctl")

    def get_location(self) -> GPSLocation | None:
        raise NotImplementedError("Linux backend: implement using gpsd + gpspipe")
