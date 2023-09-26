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
  <a href="https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml">
    <img alt="Lint and test" src="https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml/badge.svg" />
  </a>
  <a href="https://codecov.io/gh/cms-cat/order">
    <img alt="Code coverge" src="https://codecov.io/gh/cms-cat/order/branch/master/graph/badge.svg?token=SNFRGYOITJ" />
  </a>
  <a href="https://pypi.python.org/pypi/order">
    <img alt="Package version" src="https://img.shields.io/pypi/v/order.svg?style=flat" />
  </a>
  <a href="https://github.com/cms-cat/order/blob/master/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/cms-cat/order.svg" />
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

# Getting started

TODO: Add intro notebook.

You can find the full [API documentation on readthedocs](http://python-order.readthedocs.io).


# Installation and dependencies

Install *order* via [pip](https://pypi.python.org/pypi/order):

```shell
pip install order
```


# Contributing and testing

If you like to contribute, feel free to open a pull request 🎉.
Just make sure to add new test cases and run them via:

```shell
python -m unittest tests
```

In general, tests should be run for Python 3.7 - 3.11.
To run tests in a docker container, do

```shell
# run the tests
./tests/docker.sh python:3.9

# or interactively by adding a flag "1" to the command
./tests/docker.sh python:3.9 1
> pip install -r requirements.txt
> python -m unittest tests
```

In addition, [PEP 8](https://www.python.org/dev/peps/pep-0008) compatibility should be checked with [flake8](https://pypi.org/project/flake8):

```shell
flake8 order tests setup.py
```

TODO: maybe move to black


# Development

- Original source hosted at [GitHub](https://github.com/cms-cat/order)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/cms-cat/order/issues)

<!-- marker-after-body -->
