from setuptools import setup

setup(
    name="coolerctl",
    version="0.1.0",
    # setup.py lives inside the package dir; Nix copies it as build root,
    # so "." correctly points to the package source files.
    packages=["coolerctl"],
    package_dir={"coolerctl": "."},
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
    ],
    entry_points={
        "console_scripts": [
            "coolerctl=coolerctl:main",
        ],
    },
    python_requires=">=3.10",
    description="CLI for CoolerControl daemon REST API",
    license="GPL-3.0",
)
