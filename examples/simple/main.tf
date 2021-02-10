#
# Simple IAM Sleuth deployment
#
# No Slack or SNS notifications

module "iam_sleuth" {
  source                 = "trussworks/lambda/aws"
  version                = "2.2.3"
  name                   = "iam-sleuth"
  handler                = "handler.handler"
  job_identifier         = "test"
  runtime                = "python3.8"
  timeout                = "500"
  role_policy_arns_count = 2
  role_policy_arns = [aws_iam_policy.sleuth_policy.arn,
    "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"]

  github_project  = "trussworks/aws-iam-sleuth"
  github_filename = "deployment.zip"
  github_release  = "v1.2.0"

  validation_sha = "e828dc6992c986091631de26f2fca5ea700d375b25e4482b8db7366028445852"

  source_types = ["events"]
  source_arns  = [aws_cloudwatch_event_rule.lambda_rule_trigger.arn]


  env_vars = {
    ENABLE_AUTO_EXPIRE  = false
    EXPIRATION_AGE      = 90
    WARNING_AGE         = 85
    LAST_USED_AGE       = 30
    MSG_TITLE           = "Key Rotation Instructions"
    MSG_TEXT            = "Please run key rotation tool!"
  }
}


#
# Cloudwatch Event
#
 resource "aws_cloudwatch_event_rule" "lambda_rule_trigger" {
   name        = "iam-sleuth-trigger"
   description = "Trigger to audit IAM keys"

   schedule_expression = "cron(0 18 ? * MON-FRI *)"
 }

#
# IAM
#

data "aws_iam_policy_document" "basic_task_role_policy_doc" {
  # Allow to list and disable keys
  statement {
    actions = [
      "iam:UpdateAccessKey",
      "iam:ListAccessKeys",
      "iam:ListUserTags",
    ]

    resources = ["arn:aws:iam::*:user/*"]
  }

  # Allow to list and disable keys
  statement {
    actions = [
      "iam:ListUsers",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "sleuth_policy" {
  name        = "aws-iam-sleuth-policy"
  description = "Policy for IAM sleuth lambda checker"
  policy      = data.aws_iam_policy_document.basic_task_role_policy_doc.json
}
