# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.4.3 - 14/05/2024

### Added
- ARM platform check and warning for WH device resets in compatibility menu
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
- Migrated GS tensix reset to tools_common
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
- GS support and tensix reset support
