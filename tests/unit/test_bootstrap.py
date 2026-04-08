from WorkAI import __version__


def test_package_version_is_bootstrap_dev() -> None:
    assert __version__ == "2.0.0-dev"
