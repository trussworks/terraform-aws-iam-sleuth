<!-- markdownlint-disable MD013 MD033 MD024  -->
# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2021-03-04

### Added

- Warning message for keys expiring due to inactivity, INACTIVITY_WARNING_AGE
- Test for new variable

### Changed

- Change name of inactivity age variable to INACTIVITY_AGE

## [1.2.0] - 2021-02-08

### Added

- Auto-expire access keys if they have not been used in X number of days
- Tests for new variable

## [1.1.2] - 2021-01-07

### Changed

- Updating CircleCI image
- Precommit plugins
- Upgrade TF providers
- Allow for TF 0.14
- Cleanup circleci yaml

## [1.1.1] - 2020-12-11

### Added

- Simple example of IAM Sleuth deployment
- Terratest to verify related terraform code

### Changed

- make file test target to include running of terratest

### Fixed

- Few erroneous python tests fixed

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
