# TT-TOOLS-COMMON

This is a space for common utilities shared across Tenstorrent tools.
This is a helper library and not a standalone tool.

## Official Repository

[https://github.com/tenstorrent/tt-tools-common/](https://github.com/tenstorrent/tt-tools-common/)



# Getting started
Build and editing instruction are as follows -
### For tools developers

Generate and source a python3 environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
```

For users who would like to edit the code without re-building, install it in editable mode.
```
pip install --editable .
```
Recommended: install the pre-commit hooks so there is auto formatting for all files on committing.
```
pre-commit install
```

# Usage

This repo contains both frontend and backend functions that would be common to most Tenstorrent tooling.
## Frontend
It includes common themes, widgets and other styling elements to build Tenstorrent textual tools.
Under the tests directory is an example textual widget that can be used as a starting place for developers to build a new tool.

## Backend
It includes utility functions like fetching host info, math conversions, input sanitization, parsing functions etc that are used repeatedly.

## License

Apache 2.0 - https://www.apache.org/licenses/LICENSE-2.0.txt
