variable "github_project" {
    default = ""
    type = string
    description = "The unique Github project to pull from. Eg. 'trussworks/aws-iam-sleuth'"
}

variable "github_release" {
    default = ""
    type = string
    description = "The release tag to download."
}

variable "github_filename" {
    default = "deployment.zip"
    type = string
    description = "Name of the file to get when building url to pull."
}

variable "validation_sha" {
    default = ""
    type = string
    description = "SHA to validate the file."
}

###########
variable "role_arn" {
  description = "ARN of IAM role to be attached to Lambda Function."
}

variable "description" {
  description = "Description of what your Lambda Function does."
}

variable "function_name" {
  description = "A unique name for your Lambda Function"
}

variable "handler_name" {
  description = "The function entrypoint in your code."
}

variable "memory_size" {
  description = "Amount of memory in MB your Lambda Function can use at runtime."
  default     = "128"
}

variable "runtime" {
  description = "runtime"
  default     = "python3.7"
}

variable "timeout" {
  description = "The amount of time your Lambda Function has to run in seconds. Defaults to 5 minutes"
  default     = "300"
}

variable "environment" {
  description = "Environment configuration for the Lambda function"
  type        = map
  default     = {}
}

variable "dlc_target_arn" {
  description = "Lambda function dead_letter_config target_arn"
  type = string
  default = null
}
