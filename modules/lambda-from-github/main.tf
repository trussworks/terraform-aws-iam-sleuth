locals {
    github_dl_url = "https://github.com/${var.github_project}/releases/download/${var.github_release}"
}

resource "null_resource" "get_github_release_artifact" {
    triggers = {
      version_string = "${var.github_release}"
      file_hash = "${var.validation_sha}"
    }
    provisioner "local-exec" {
        command = "bash ${path.module}/scripts/dl-release.sh ${local.github_dl_url} ${var.github_filename} ${var.validation_sha}"
    }
}


# have to defined a lambda with and without dead_letter_config. _sigh_
resource "aws_lambda_function" "lambda" {
  count = var.dlc_target_arn != null ? 1 : 0
  filename         = var.github_filename
  description      = var.description
  source_code_hash = var.validation_sha
  role             = var.role_arn
  function_name    = var.function_name
  handler          = var.handler_name
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size

  environment {
    variables = var.environment
  }

  dead_letter_config {
    target_arn = var.dlc_target_arn
  }
}

resource "aws_lambda_function" "lambda_nodlc" {
  count = var.dlc_target_arn == null ? 1 : 0
  filename         = var.github_filename
  description      = var.description
  source_code_hash = var.validation_sha
  role             = var.role_arn
  function_name    = var.function_name
  handler          = var.handler_name
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size

  environment {
    variables = var.environment
  }

}
