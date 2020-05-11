resource "aws_sns_topic" "slack_events" {
  name = "slack-events-topic"
}

module iam_sleuth {
  source             = "../.."
  sns_topic_arn      = aws_sns_topic.slack_events.arn
  enable_auto_expire = false
}
