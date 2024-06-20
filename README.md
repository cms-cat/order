<!-- marker-before-logo -->

<p align="center">
  <a href="https://github.com/cms-cat/order">
    <img src="https://media.githubusercontent.com/media/cms-cat/order/master/assets/logo240.png" />
  </a>
</p>

<!-- marker-after-logo -->

<!-- marker-before-badges -->

<p align="center">
  <a href="http://cms-order.readthedocs.io/en/latest">
    <img alt="Documentation status" src="https://readthedocs.org/projects/cms-order/badge/?version=latest" />
  </a>
  <img alt="Python version" src="https://img.shields.io/badge/Python-%E2%89%A53.7-blue" />
  <a href="https://pypi.python.org/pypi/order">
    <img alt="Package version" src="https://img.shields.io/pypi/v/order.svg?style=flat" />
  </a>
  <a href="https://github.com/cms-cat/order/blob/master/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/cms-cat/order.svg" />
  </a>
  <a href="https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml">
    <img alt="Lint and test" src="https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml/badge.svg" />
  </a>
  <a href="https://codecov.io/gh/cms-cat/order">
    <img alt="Code coverge" src="https://codecov.io/gh/cms-cat/order/branch/master/graph/badge.svg?token=JF7BVTNB2Y" />
  </a>
  <a href="https://colab.research.google.com/github/cms-cat/order/blob/master/examples/intro.ipynb">
    <img alt="Open in colab" src="https://colab.research.google.com/assets/colab-badge.svg" />
  </a>
</p>

<!-- marker-after-badges -->

<!-- marker-before-header -->

Pythonic class collection to structure and access CMS metadata.

TODO: introduction

<!-- marker-after-header -->

<!-- marker-before-body -->

<!-- marker-before-getting-started -->

# Getting started

TODO: Add intro notebook.

You can find the full [API documentation on readthedocs](http://python-order.readthedocs.io).

<!-- marker-after-getting-started -->

<!-- marker-before-installation -->

# Installation

Install *order* via [pip](https://pypi.python.org/pypi/order):

```shell
pip install order
```

<!-- marker-after-installation -->

<!-- marker-before-contributing -->

# Contributing

If you like to contribute, feel free to open a pull request 🎉.

## venv

It is recommended to create a Python virtual environment (using `venv`) and install the development requirements.

```shell
python -m venv .env/order
source .env/order/bin/activate
pip install -U pip setuptools
pip install .[dev]
```

Setup the environment:
```shell
export ORDER_CLEAR_CACHE=True
export ORDER_DATA_LOCATION='/path/to/order-data'
export X509_USER_PROXY=your-cert-file
```

## Testing

TBD. After making changes, make sure to run test cases and linting checks.
Note. At this time these test are failing. Will fix them later.

```shell
./tests/test.sh
./tests/lint.sh
```

<!-- marker-after-contributing -->

<!-- marker-before-development -->

# Development

- Original source hosted at [GitHub](https://github.com/cms-cat/order)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/cms-cat/order/issues)


<!-- marker-after-development -->

<!-- marker-after-body -->
