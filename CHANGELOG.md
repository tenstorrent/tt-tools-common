# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.4.17 - 02/07/2025

### Changed
- Loosened requirements on pyproject.toml to make it more compatible in different venvs

## 1.4.15 - 05/05/2025

### Changed
- parse\_reset\_json now returns a ResetInput with stricter typing

## 1.4.14 - 04/02/2025

### Added
- New flags in reset config file generation to disable sw\_version reporting

## 1.4.13 - 23/1/2025

- Removed nr\_hugepages count from compatibility, as hugepages allocation is tricky
  and deserves its own widget elsewhere.

## 1.4.12 - 16/1/2025

- Added TTHostCompatibilityMenu to replace Host Info and Compatibility boxes
- Added a count of nr\_hugepages to the TTHostCompatibilityMenu

## 1.4.11 - 30/12/2025

- Updated Luwen version to fix Maturin issue

## 1.4.10 - 16/12/2024

### Changed
- detect\_chips\_with\_callback now takes a print\_status arg

## 1.4.9 - 11/12/2024

### Changed
- A failed reset now results in a fail exit code on BH

## 1.4.8 - 11/10/2024

### Changed
- Updated reset completion logic to handle the case where the bmfw needs to upgrade itself

## 1.4.7 - 11/10/2024

### Added
- Implemented m3 reset option for Blackhole

### Fixed
- Fixed crash during driver version dection when the "extraversion" field is used
    - i.e. 1.28-bh

## 1.4.6 - 17/07/2024

### Added
- Reset support of Blackhole

## 1.4.5 - 11/07/2024

### Added
- Bump pyluwen library version (v0.3.8 -> v0.3.11)
- Moved pyluwen v0.3.11 to optional dependencies in pyproject.toml

## 1.4.4 - 21/06/2024

### Added
- Version bump of python dependencies in pyproject.toml (dependabot)
    - requests (2.31.0 -> 2.32.0)
    - tqdm (4.66.1 -> 4.66.3)
- Pydantic library version bump (1.* -> >=1.2) to resolve: [TT-SMI issue #27](https://github.com/tenstorrent/tt-smi/issues/27)

## 1.4.3 - 14/05/2024

### Added
- Arm platform check and warning for WH device resets in compatibility menu
- Added check for WH device init after reset and prompt user to reboot host if chips are still non recoverable
- Bumped textual (0.59.0) and luwen (0.3.8) lib versions

## 1.4.2 - 04/04/2024

### Added
- Added "silent" flag to WH and GS resets to make them more versatile for use in other tools

## 1.4.1 - 22/03/2024

### Fixed
- removed pyluwen version to avoid dependency issues in other repos

## 1.4.0 - 19/03/2024

### Added
- detect_device_fallible that will provide feedback about chip state during init

### Fixed
- Update min driver version to 1.26 to perform lds reset
- Reset config file uses dev/tenstorrent id
- Catch JSON errors in reset config parsing
- Make nested dirs when initializing reset config path

## 1.3.0 - 06/03/2024

### Added
- Migrated GS Tensix reset to tools_common
- Migrated all related GS data files
- Functions to fetch arc and eth fw versions from telemetry
- Unit tests for all device resets

### Fixed
- Driver check before WH reset
- Perform NB host reset between module powercycle for galaxy reset

## 1.2.0 - 28/02/2024

### Added
- Moved Galaxy reset from tt-smi to tools common
- Moved the generation and parsing of reset config json file

## 1.1.0 - 21/02/2024

### Added
- Functions to read and process arc refclk
- Added refclk check to wh link reset. Refclk value is expected to be smaller after reset
- Added CHANGELOG.md

### Fixed
- Updated fail message to warning if OS is less than Ubuntu 20.04


## 1.0.0 - 20/10/2023

First release of opensource tt-smi

### Added
- GS support and Tensix reset support
