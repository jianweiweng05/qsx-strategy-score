import shutil
import subprocess
from pathlib import Path

import pytest


def test_chrome_uses_nullable_shared_core_contract():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for the shipped Chrome client contract check")
    test = Path(__file__).with_suffix(".cjs")
    result = subprocess.run([node, str(test)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
