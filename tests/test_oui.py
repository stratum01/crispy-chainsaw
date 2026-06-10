from oui import lookup_vendor


def test_lookup_known_vendor(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text(
        "00-00-0C   (hex)\t\tCisco Systems, Inc\n"
        "00-50-56   (hex)\t\tVMware, Inc.\n"
    )
    assert lookup_vendor("00:00:0c:11:22:33", str(oui_file)) == "Cisco Systems, Inc"


def test_lookup_case_insensitive(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text("00-50-56   (hex)\t\tVMware, Inc.\n")
    assert lookup_vendor("00:50:56:aa:bb:cc", str(oui_file)) == "VMware, Inc."


def test_lookup_unknown_returns_none(tmp_path):
    oui_file = tmp_path / "oui.txt"
    oui_file.write_text("00-00-0C   (hex)\t\tCisco Systems, Inc\n")
    assert lookup_vendor("ff:ff:ff:11:22:33", str(oui_file)) is None
