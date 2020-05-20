variable "schedule" {
  default     = "cron(0 18 ? * MON-FRI *)"
  type        = string
  description = "Schedule to run the audit. Default daily between M-F at 18:00 UTC"
}

variable "enable_sns_topic" {
  type        = bool
  description = "Enable use of sns topic to send messages through"
  default     = false
}

variable "sns_topic_arn" {
  type        = string
  description = "SNS topic to send messages to, to be routed to slack-notify"
  default     = ""
}

variable "enable_auto_expire" {
  type        = bool
  description = "Enable expiring AWS Access Keys older than the defined expiration_age. This will remove AWS API access for expired IAM users"
  default     = true
}

variable "slack_url" {
  type        = string
  description = "The Slack webhook url to directly message Slack"
  default     = ""
}

variable "expiration_age" {
  type        = number
  description = "The age (in days) at which the keys will be considered expired and will expire if auto disable is turned on."
  default     = 90
}

variable "warning_age" {
  type        = number
  description = "The age (in days) at which the keys will be considered old and the associated user will start to receive warnings"
  default     = 80
}

variable "sns_message" {
  type        = string
  description = "The message that will be sent through the SNS topic"
  default     = ""
}

variable "slack_message_title" {
  type        = string
  description = "The title of the message sent to Slack directly"
  default     = ""
}

variable "slack_message_text" {
  type        = string
  description = "The content of the message sent to Slack directly"
  default     = ""
}

variable "deployment_bucket" {
  type        = string
  description = "The bucket that hold the lambda deployment asset"
  default     = "TODO"
}

variable "deployment_s3_key" {
  type        = string
  description = "S3 Key to the deployment assset"
  default     = "TODO"
}
