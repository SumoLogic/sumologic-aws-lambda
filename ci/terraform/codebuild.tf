resource "aws_iam_role" "codebuild" {
  name = "sumologic-aws-lambda-codebuild"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

}

resource "aws_cloudwatch_log_group" "codebuild" {
  name              = "/aws/codebuild/sumologic-aws-lambda"
  retention_in_days = "180"
}

data "aws_iam_policy_document" "codebuild" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      aws_cloudwatch_log_group.codebuild.arn,
      "${aws_cloudwatch_log_group.codebuild.arn}:*",
    ]
  }


  statement {
    actions = ["s3:PutObject"]

    resources = [
      "arn:aws:s3:::replicon-release-artifact/sumologic-aws-lambda/*",
      "arn:aws:s3:::replicon-build-artifacts/sumologic-aws-lambda/*",
    ]
  }

  statement {
    actions = ["s3:GetObject"]

    resources = [
      "arn:aws:s3:::codepipeline-*",
      "arn:aws:s3:::codepipeline-*/*",
    ]
  }
}

resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.name

  policy = data.aws_iam_policy_document.codebuild.json
}

resource "aws_codebuild_project" "sumologic-aws-lambda" {
  name          = "sumologic-aws-lambda"
  description   = "sumologic-aws-lambda codebuild"
  service_role  = aws_iam_role.codebuild.arn
  badge_enabled = true
  build_timeout = "15"

  artifacts {
    type = "NO_ARTIFACTS"
  }


  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:7.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = false
  }

  source {
    type                = "GITHUB"
    location            = "https://github.com/replicon/sumologic-aws-lambda.git"
    git_clone_depth     = 1
    buildspec           = "buildspec.yml"
    report_build_status = true
  }

  tags = {
    "Name" = "sumologic-aws-lambda"
  }
}

# Webhook commented out until repository permissions are resolved
# resource "aws_codebuild_webhook" "sumologic-aws-lambda" {
#   project_name = aws_codebuild_project.sumologic-aws-lambda.name
#
#   filter_group {
#     filter {
#       type    = "EVENT"
#       pattern = "PUSH"
#     }
#
#     filter {
#       type    = "HEAD_REF"
#       pattern = "refs/heads/main"
#     }
#
#     filter {
#       type    = "FILE_PATH"
#       pattern = "cloudwatchlogs-with-dlq/*"
#     }
#   }
# }