<h1 align="center" style="border-bottom: none; text-align: center;">SGHI Commons</h1>
<h3 align="center" style="text-align: center;">Collection of useful Python utilities.</h3>
<p align="center" style="text-align: center;">
    <img alt="Python Version from PEP 621 TOML" src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fgithub.com%2Fsavannahghi%2Fsghi-commons%2Fraw%2Fdevelop%2Fpyproject.toml&logo=python&labelColor=white"/>
    <a href="https://microsoft.github.io/pyright/">
        <img alt="Checked with pyright" src="https://microsoft.github.io/pyright/img/pyright_badge.svg">
    </a>
    <a href="https://github.com/astral-sh/ruff">
        <img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json">
    </a>
    <a href="https://github.com/pre-commit/pre-commit">
        <img alt="pre-commit" src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white">
    </a>
    <a href="https://github.com/semantic-release/semantic-release">
        <img alt="Semantic Release: conventionalcommits" src="https://img.shields.io/badge/semantic--release-conventionalcommits-e10079?logo=semantic-release"/>
    </a>
    <a href="https://github.com/savannahghi/sghi-commons/blob/develop/LICENSE">
        <img alt="GitHub License" src="https://img.shields.io/badge/License-MIT-blue.svg">
    </a>
</p>
<p align="center" style="text-align: center;">
    <a href="https://github.com/savannahghi/sghi-commons/actions/workflows/ci.yml">
        <img alt="CI" src="https://github.com/savannahghi/sghi-commons/actions/workflows/ci.yml/badge.svg">
    </a>
    <a href="https://coveralls.io/github/savannahghi/sghi-commons?branch=develop">
        <img alt="Coverage Status" src="https://img.shields.io/coverallsCoverage/github/savannahghi/sghi-commons?branch=develop&logo=coveralls&link=https%3A%2F%2Fcoveralls.io%2Fgithub%2Fsavannahghi%2Fsghi-commons%3Fbranch%3Ddevelop">
    </a>
</p>

---

A collection of utilities and reusable components used throughout our Python
projects. They include:

- Utilities for working with resources that require freeing or cleanup after use.
- Components for defining and accessing application configurations.
- A registry component for storing key-value pairs.
- A signal dispatcher inspired by [PyDispatch](https://grass.osgeo.org/grass83/manuals/libpython/pydispatch.html) and [Django Dispatch](https://docs.djangoproject.com/en/dev/topics/signals/).

## Contribute

Clone the project and run the following command to install dependencies:

```bash
pip install -e .[dev,test,docs]
```

Set up pre-commit hooks:
```bash
pre-commit install
```

## License

[MIT License](https://github.com/savannahghi/sghi-commons/blob/main/LICENSE)

Copyright (c) 2023, Savannah Informatics Global Health Institute
