resource "aws_sns_topic" "slack_events" {
  name = "slack-events-topic"
}

resource "aws_ssm_parameter" "slack_url" {
  name        = "/iam-sleuth/slack-url"
  description = "Slack webhook url to send messages directly through"
  type        = "SecureString"
  value       = "fake slack webhook url"
}

module "iam_sleuth_with_sns_topic_and_slack_url" {
  source = "../.."

  sns_topic_arn       = aws_sns_topic.slack_events.arn
  expiration_age      = 120
  warning_age         = 10
  enable_auto_expire  = false
  sns_message         = "This will show whose keys need to be rotated."
  slack_message_title = "IAM Key Report"
  slack_message_text  = "Who needs their keys rotated?"
  slack_url           = aws_ssm_parameter.slack_url.value
}
