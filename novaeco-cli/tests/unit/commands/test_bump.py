import pytest
from novaeco_cli.commands.bump import compute_new_version


def test_compute_new_version_minor():
    assert compute_new_version("1.2.3", "minor") == "1.3.0"


def test_compute_new_version_patch():
    assert compute_new_version("1.2.3", "patch") == "1.2.4"


def test_compute_new_version_exact():
    assert compute_new_version("1.2.3", "2.0.0") == "2.0.0"


def test_compute_new_version_invalid():
    with pytest.raises(SystemExit):
        compute_new_version("invalid", "patch")
