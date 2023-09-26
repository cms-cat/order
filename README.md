<center>
  <a href="https://github.com/cms-cat/order">
    <img src="https://media.githubusercontent.com/media/cms-cat/order/master/assets/logo240.png" />
  </a>
</center>


<!-- marker-after-logo -->


[![Documentation status](https://readthedocs.org/projects/cms-order/badge/?version=latest)](http://cms-order.readthedocs.io/en/latest)
[![Lint and test](https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml/badge.svg)](https://github.com/cms-cat/order/actions/workflows/lint_and_test.yml)
[![Code coverge](https://codecov.io/gh/cms-cat/order/branch/master/graph/badge.svg?token=SNFRGYOITJ)](https://codecov.io/gh/cms-cat/order)
[![Package version](https://img.shields.io/pypi/v/order.svg?style=flat)](https://pypi.python.org/pypi/order)
[![License](https://img.shields.io/github/license/cms-cat/order.svg)](https://github.com/cms-cat/order/blob/master/LICENSE)
[![PyPI downloads](https://img.shields.io/pypi/dm/order.svg)](https://pypi.python.org/pypi/order)
[![Open in colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cms-cat/order/blob/master/examples/intro.ipynb)

Pythonic class collection to structure and access CMS metadata.

TODO: introduction


<!-- marker-after-header -->


## Getting started

TODO: Add intro notebook.

You can find the full [API documentation on readthedocs](http://python-order.readthedocs.io).


<!-- marker-after-getting-started -->


## Installation and dependencies

Install *order* via [pip](https://pypi.python.org/pypi/order):

```shell
pip install order
```


## Contributing and testing

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


## Development

- Original source hosted at [GitHub](https://github.com/cms-cat/order)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/cms-cat/order/issues)
