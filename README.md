# AWS Key Sleuth

[Changelog](./CHANGELOG.md)

## What is this for?

A tool that will help in auditing AWS key age and help notify users via Slack or SNS topic that their AWS key may be coming out of compliance.

## How does this work?

Sleuth runs periodically, normally once a day in the middle of business hours. Sleuth does the following:

- Inspect each Access Key based on set age threshold (default 90 days)
- If Access Key is approaching threshold will ping user with a reminder to cycle key
- If key age at or over threshold will disable Access Key along with a final notice

Notifications can be sent directly to Slack via V1 token or through SNS Topic.

## Usage

### Setup

This tool depends on an external non-published TF module. As of time of writing this is a manual process for now. 

```bash
$ cd WORK_DIR
$ git clone https://github.com/ruzin/terraform_aws_lambda_python.git
$ cd terraform_aws_lambda_python
$ git remote add retentionscience git@github.com:retentionscience/terraform_aws_lambda_python.git
$ git checkout retentionscience/master

```

Now pull down the Sleuth private TF module

```bash
$ cd WORK_DIR
$ git clone https://github.com/trussworks/aws-iam-sleuth/
```



### Configure Environment

Sleuth relies on IAM Tags to know the Slack account/group ID to mention when assembling the notification. Specifically `Name` and `Slack` tags. A sample of a TF IAM user is below

```
resource "aws_iam_user" "tfunke" {
  name = "tfunke"

  tags = {
    Name       = "Tobias Funke"
    Slack      = "UPML12345"
  }
}
```

For a Slack user the standard SlackID is suffecient. For a group the `Slack` tag must have a value of the form `subteam-SP12345` (no `^` is allowed). More info on Slack groups [here](https://api.slack.com/reference/surfaces/formatting#mentioning-groups). 

For listing Slack account IDs in bulk check out the `user_hash_dump.py` script located in the `scripts` dir.

If the information isn't specified an error will be thrown in the logs and the plain text username will be in the notification.

#### Deploy

Now all the dependencies are ready and the environment is prepped for Sleuth usage we can now deploy the lambda.

```
module "iam_sleuth" {
  source = "../to/module/aws-api-key-sleuth"
  sns_topic_arn = data.aws_sns_topic.slack_events.arn
}
```



## Screenshots

A user is pinged directly with a key 8 days shy of the 90 day limit. 

<img src="docs/media/readme/mention.png" style="zoom:41%;" />

For IAM accounts that are used by bots such as Jenkins or CircleCI Sleuth can ping a group such as Infra or Engineers to ensure the account doesn't get disabled by accident.

<img src="docs/media/readme/group.png" style="zoom:38%;" />

A user failed to cycle the key the the Sleuth disabled it to remain compliant.

<img src="docs/media/readme/disable.png" style="zoom:59%;" />



