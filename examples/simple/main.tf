resource "aws_sns_topic" "slack_events" {
  name = "slack-events-topic"
}

module "iam_sleuth_with_sns_topic" {
  source = "../.."

  sns_topic_arn      = aws_sns_topic.slack_events.arn
  expiration_age     = 120
  warning_age        = 10
  enable_auto_expire = false
  sns_message        = "This will show whose keys need to be rotated."
}
