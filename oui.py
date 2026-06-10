from pathlib import Path

_DEFAULT_OUI_PATH = Path(__file__).parent / "data" / "oui.txt"
_cache: dict[str, str | None] = {}


def lookup_vendor(mac: str, oui_path: str | None = None) -> str | None:
    path = oui_path or str(_DEFAULT_OUI_PATH)
    prefix = mac.upper().replace(":", "-")[:8]
    if prefix in _cache:
        return _cache[prefix]
    vendor = _parse_oui_file(path, prefix)
    _cache[prefix] = vendor
    return vendor


def _parse_oui_file(path: str, prefix: str) -> str | None:
    try:
        with open(path) as f:
            for line in f:
                if "(hex)" in line and line.upper().startswith(prefix):
                    return line.split("\t\t", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None
