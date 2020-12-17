<!-- markdownlint-disable MD013 MD033 MD024  -->
# Changelog

All notable changes to this project will be documented in this file.

## [1.1.1] - 2020-12-11

### Added

- Simple example of IAM Sleuth deployment
- Terratest to verify terraform setup

### Fixed

- Few erranoues python tests fixed

## [1.1.0] - 2020-11-12

### Added

- DEBUG envar for additional debugging

### Changed

- Slack and SNS now have Title and Additional Text (previously only Slack had this)
- Moved notification text to the beginning of the message

### Removed

- Requirement of Slack or SNS setting to run, Lambda can run without any notifications

## [1.0.10] - 2020-11-12

### Added

- Serveral git precommits (markdown, terraform, terraformd-docs etc)

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
