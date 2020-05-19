<!-- markdownlint-disable MD013 MD033 MD024  -->
# Changelog

All notable changes to this project will be documented in this file.

## [1.0.5] - 2020-05-19

### Added

- Serveral git precommits (markdown, terraform, terraformd-docs etc)


### Changed

- Deployment now uses pre-built zip file for lambda


### Removed

- Dropped custom packaging setup (very fragile)

## [0.9.0] - 2020-03-28

### Added

- TF managed code to assist in deployment

### Changed

- Deployment from Serverless to fully managed TF module
- Moved sleuth to lower level module and update handler, tests etc

### Removed

- Deployment via Serverless framework

## [0.8.0] - 2019-06-20

### Added

- Added this changelog document
- Version which is added to the print out doc

### Changed

- For team/group mention will display the IAM account username and the team/group mention in `()`
- If the responsible slack ID is not know for an IAM account will return `UNKNOWN` to indicate that it needs to be looked into.
