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

variable "enable_auto_expire" {
  type        = bool
  description = "Enable expiring AWS Access Keys older than the defined expiration_age. This will remove AWS API access for expired IAM users"
  default     = true
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

variable "sns_message" {
  type        = string
  description = "The message that will be sent through the SNS topic"
  default     = "How to doc for '<https://github.com/transcom/ppp-infra/tree/master/transcom-ppp#rotating-aws-access-keys|key rotation>. TLDR: \n```cd transcom-ppp\ngit pull && rotate-aws-access-key```\n\nOnce key is expired will require team Infra involvement to reset key and MFA"
}

variable "slack_message_title" {
  type        = string
  description = "The title of the Slack message"
  default     = "Access Key Rotation Instructions"
}

variable "slack_message_text" {
  type        = string
  description = "The content of the Slack message"
  default     = "https://github.com/transcom/ppp-infra/tree/master/transcom-ppp#rotating-aws-access-keys"
}
