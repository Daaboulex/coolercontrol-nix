from setuptools import setup

setup(
    name="coolerctl",
    version="0.1.0",
    py_modules=["coolerctl"],
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
