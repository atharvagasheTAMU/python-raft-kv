"""Setup script for python-raft-kv package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="python-raft-kv",
    version="0.1.0",
    description="A distributed key-value store in Python using Raft consensus",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Atharva Agashe",
    author_email="agashe2209@gmail.com",
    url="https://github.com/atharvagasheTAMU/python-raft-kv",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "raft-kv-start=python_kv.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "python_kv": [
            "../raft-bridge/*.go",
            "../raft-bridge/go.mod",
            "../raft-bridge/go.sum",
            "../raft/*.go",
            "../raft/go.mod",
            "../raft/go.sum",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
    ],
)

