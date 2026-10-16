import pytest
from kit_models import kit_model


@pytest.mark.parametrize("kit,expected", [
    ("KIT400651113", "Standard V4"),
    ("KIT4M00123", "Mini"),
    ("KIT4P00999", "Performance Gen3"),
    ("KITP00042", "Performance Gen2"),
    ("KIT5000001", "Standard V5"),
    ("XYZ0001", "Desconocido"),
])
def test_kit_model(kit, expected):
    assert kit_model(kit) == expected
