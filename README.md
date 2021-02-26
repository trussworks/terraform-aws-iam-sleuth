# AWS Key Sleuth

[Changelog](./CHANGELOG.md)

<!-- markdownlint-disable MD013 MD033  -->

## What is this for

An auditing tool for AWS keys that audits, alerts, and disable keys if not within compliance settings. This reduces AWS administrator involvement since majority of users will cycle key before being disabled.

## How does this work

Sleuth runs periodically, normally once a day in the middle of business hours. Sleuth does the following:

- Inspect each Access Key based on:
  - set creation age threshold (default 90 days)
  - set last accessed age threshold (optional, set to creation age threshold as default)
- If Access Key is approaching threshold will ping user with a reminder to cycle key
- If key age is at or over threshold will disable Access Key along with a final notice
- If user has special KeyAutoExpire tag set to False, the key will not be auto-expired

Notifications can be sent directly to Slack using a V1 token or through SNS Topic.

### Configure Environment

Sleuth relies on IAM Tags to know the Slack account/group ID to mention when assembling the notification. Specifically `Name` and `Slack` tags. A sample of a TF IAM user is below

```hcl
resource "aws_iam_user" "tfunke" {
  name = "tfunke"

  tags = {
    Name       = "Tobias Funke"
    Slack      = "UPML12345"
  }
}
```

#### Slack

For a Slack user the standard SlackID is sufficient. For a group the `Slack` tag must have a value of the form `subteam-SP12345` (no `^` is allowed). More info on Slack group identifiers [here](https://api.slack.com/reference/surfaces/formatting#mentioning-groups).

For listing Slack account IDs in bulk look at the [user_hash_dump.py](./scripts/user_hash_dump.py) script.

If the information isn't specified an error will be thrown in the logs and the plain text username will be in the notification.

Required environment variable to enabled Slack integration is `SLACK_URL`.


#### SNS

For SNS ensure the IAM role the lambda is running has permission to publish to the SNS topic.

Required environment variable to enable SNS integration is `SNS_TOPIC`.


## Suggested Deployment Method

Using the Terraform module [terraform-aws-lambda](https://github.com/trussworks/terraform-aws-lambda) you can deploy the code released to this Github repository.

```hcl
module "iam_sleuth" {
  source                 = "trussworks/lambda/aws"
  version                = "2.2.0"
  name                   = "iam_sleuth"
  handler                = "handler.handler"
  job_identifier         = "iam_sleuth"
  runtime                = "python3.8"
  timeout                = "500"
  role_policy_arns_count = 2
  role_policy_arns = ["${aws_iam_policy.sleuth_policy.arn}",
  "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"]

  github_project  = "trussworks/aws-iam-sleuth"
  github_filename = "deployment.zip"
  github_release  = "v1.0.10"

  validation_sha = "7a501951f8c91758acfcd3e17a06ea7e1fe4021f3b08e54064091d73a95dd6bb"

  source_types = ["events"]
  source_arns  = ["${aws_cloudwatch_event_rule.sleuth_lambda_rule_trigger.arn}"]

  env_vars = {
    ENABLE_AUTO_EXPIRE  = "false"
    EXPIRATION_AGE      = 90
    WARNING_AGE         = 50
    LAST_USED_AGE       = 30
    SLACK_URL           = data.aws_ssm_parameter.slack_url.value
    SNS_TOPIC           = ""
    MSG_TITLE           = "Key Rotation Instructions"
    MSG_TEXT            = "Please run.\n ```aws-vault rotate AWS-PROFILE```"
  }

  tags = {
    "Service" = "iam_sleuth"
  }

}
```

### Envars

The behavior can be configured by environment variables.

| Name | Description |
|------|------------ |
| ENABLE_AUTO_EXPIRE | Must be set to `true` for key disable action |
| EXPIRATION_AGE | Age of key creation (in days) to disable a AWS key |
| WARNING_AGE | Age of key creation (in days) to send notifications, must be lower than EXPIRATION_AGE |
| LAST_USED_AGE | OPTIONAL, defaults to EXPIRATION_AGE, Age of last key usage (in days) to send notifications, must be lower than or equal to EXPIRATION_AGE |
| MSG_TITLE | Title of the notification message |
| MSG_TEXT | Instructions on key rotation |
| SLACK_URL | Incoming webhook to send notifications to |
| SNS_TOPIC | Topic to send a SNS formatted message to |
| DEBUG | If present will log additional things |


## Screenshots

A user is pinged directly with an AWS key 8 days before of the 90 day limit.

<img src="docs/media/readme/mention.png" style="zoom:41%;" />

For IAM accounts that are used by bots such as Jenkins or CircleCI Sleuth can ping a group such as Infra or Engineers to ensure the account does not get disabled by accident.

<img src="docs/media/readme/group.png" style="zoom:38%;" />

A user failed to cycle their AWS key. Sleuth disabled the out of compliant key and posts a single notification to the user. This is the last notification the user will receive.

<img src="docs/media/readme/disable.png" style="zoom:59%;" />

## Developer Setup

Install dependencies:

```sh
brew install circleci pre-commit python direnv ghr
pre-commit install --install-hooks
```

Now for downloading the python dependencies:

```sh
# skip if you already have virtualenv on your machine
python3 -m pip install --user virtualenv
virtualenv venv
source venv/bin/activate
pip install -r ./sleuth/requirements.txt
```

### Testing

To test the Python app:

```sh
pytest
```
