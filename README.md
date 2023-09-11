# SGHI Commons

[![pyversion](https://camo.githubusercontent.com/64bafa7ada773716674e93fd8fbaa3f681e1748865cdcb47cc373579079b767f/68747470733a2f2f696d672e736869656c64732e696f2f707970692f707976657273696f6e732f7365747570746f6f6c732e737667)](https://camo.githubusercontent.com/64bafa7ada773716674e93fd8fbaa3f681e1748865cdcb47cc373579079b767f/68747470733a2f2f696d672e736869656c64732e696f2f707970692f707976657273696f6e732f7365747570746f6f6c732e737667)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A collection of utilities and reusable components used throughout our Python
projects. They include:

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
