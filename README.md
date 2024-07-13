<h1 align="center" style="border-bottom: none; text-align: center;">SGHI Commons</h1>
<h3 align="center" style="text-align: center;">Collection of useful Python utilities.</h3>

<div align="center">

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fgithub.com%2Fsavannahghi%2Fsghi-commons%2Fraw%2Fdevelop%2Fpyproject.toml&logo=python&labelColor=white)
[![Checked with pyright](https://microsoft.github.io/pyright/img/pyright_badge.svg)](https://microsoft.github.io/pyright/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Semantic Release: conventionalcommits](https://img.shields.io/badge/semantic--release-conventionalcommits-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
[![GitHub License](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/savannahghi/sghi-commons/blob/develop/LICENSE)

</div>

<div align="center">

[![CI](https://github.com/savannahghi/sghi-commons/actions/workflows/ci.yml/badge.svg)](https://github.com/savannahghi/sghi-commons/actions/workflows/ci.yml)
[![Coverage Status](https://img.shields.io/coverallsCoverage/github/savannahghi/sghi-commons?branch=develop&logo=coveralls&link=https%3A%2F%2Fcoveralls.io%2Fgithub%2Fsavannahghi%2Fsghi-commons%3Fbranch%3Ddevelop)](https://coveralls.io/github/savannahghi/sghi-commons?branch=develop)

</div>

---

A collection of utilities and reusable components used throughout our Python
projects. They include:

- Utilities for working with resources that require freeing or cleanup after use.
- Components and utilities for defining retry policies, allowing applications to retry operations that might fail due to transient errors.
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
