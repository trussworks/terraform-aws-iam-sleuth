variable "schedule" {
  default     = "cron(0 18 ? * MON-FRI *)"
  type        = string
  description = "Schedule to run the audit. Default daily between M-F at 18:00 UTC"
}

variable "sns_topic_arn" {
  type        = string
  description = "SNS topic to send messages to, to be routed to slack-notify"
  default     = ""
}
