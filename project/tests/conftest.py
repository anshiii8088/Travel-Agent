"""Pytest configuration and global test fixtures."""

import pytest

# pytest-asyncio default loop scope configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")

