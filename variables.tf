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

variable "expiration_age" {
  type        = number
  description = "The age (in days) at which the keys will be considered expired and will expire if auto disable is turned on."
  default     = 90
}

variable "warning_age" {
  type        = number
  description = "The age (in days) at which the keys will be considered old and the associated user will start to receive warnings."
  default     = 80
}
