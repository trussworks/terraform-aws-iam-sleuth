# AWS Key Sleuth

[Changelog](./CHANGELOG.md)

<!-- markdownlint-disable MD013 MD033  -->
<!-- BEGINNING OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## Requirements

| Name      | Version |
| --------- | ------- |
| terraform | >= 0.12 |

## Providers

| Name | Version |
| ---- | ------- |
| aws  | n/a     |

## Inputs

| Name                | Description                                                                                                                  | Type     | Default                      | Required |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------- | :------: |
| enable_auto_expire  | Enable expiring AWS Access Keys older than the defined expiration_age. This will remove AWS API access for expired IAM users | `bool`   | `true`                       |    no    |
| expiration_age      | The age (in days) at which the keys will be considered expired and will expire if auto disable is turned on.                 | `number` | `90`                         |    no    |
| schedule            | Schedule to run the audit. Default daily between M-F at 18:00 UTC                                                            | `string` | `"cron(0 18 ? * MON-FRI *)"` |    no    |
| slack_message_text  | The content of the message sent to Slack directly                                                                            | `string` | n/a                          |   yes    |
| slack_message_title | The title of the message sent to Slack directly                                                                              | `string` | n/a                          |   yes    |
| sns_message         | The message that will be sent through the SNS topic                                                                          | `string` | n/a                          |   yes    |
| sns_topic_arn       | SNS topic to send messages to, to be routed to slack-notify                                                                  | `string` | `""`                         |    no    |
| warning_age         | The age (in days) at which the keys will be considered old and the associated user will start to receive warnings            | `number` | `80`                         |    no    |

## Outputs

No output.

<!-- END OF PRE-COMMIT-TERRAFORM DOCS HOOK -->

## What is this for

An auditing tool for AWS keys that audits, alerts, and disable keys if not within compliance settings. This reduces AWS administrator involvement since majority of users will cycle key before being disabled.

## How does this work

Sleuth runs periodically, normally once a day in the middle of business hours. Sleuth does the following:

- Inspect each Access Key based on set age threshold (default 90 days)
- If Access Key is approaching threshold will ping user with a reminder to cycle key
- If key age is at or over threshold will disable Access Key along with a final notice

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

For a Slack user the standard SlackID is sufficient. For a group the `Slack` tag must have a value of the form `subteam-SP12345` (no `^` is allowed). More info on Slack group identifiers [here](https://api.slack.com/reference/surfaces/formatting#mentioning-groups).

For listing Slack account IDs in bulk look at the [user_hash_dump.py](./scripts/user_hash_dump.py) script.

If the information isn't specified an error will be thrown in the logs and the plain text username will be in the notification.

#### Slack Webhook URL

`enable_slack_webhook` is turned on by default but it comes with several expectations:

- account you will be running this module within has access to the SMM Parameter Store
- the store contains a secret key called `slack_url` within the `iam-sleuth`
- the secret key points to a slack webhook url you've created through the Slack API

At Truss, we created this secret through [chamber](https://github.com/segmentio/chamber)

```sh
chamber write iam-sleuth slack_url <SLACK_WEBHOOK_URL>
```

#### Deploy

Now all the dependencies are ready and the environment is prepped for Sleuth usage we can now deploy the lambda.

```hcl
module "iam_sleuth" {
  source = "../to/module/aws-api-key-sleuth"
  sns_topic_arn = data.aws_sns_topic.slack_events.arn
}
```

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
brew install circleci pre-commit terraform python direnv
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

To test the module itself:

```sh
make test
```

or

```sh
AWS_VAULT_KEYCHAIN_NAME=<NAME> aws-vault exec <PROFILE> -- make test
```
