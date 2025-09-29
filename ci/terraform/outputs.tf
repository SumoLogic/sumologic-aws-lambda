output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = aws_codebuild_project.sumologic-aws-lambda.name
}

output "codebuild_project_arn" {
  description = "ARN of the CodeBuild project"
  value       = aws_codebuild_project.sumologic-aws-lambda.arn
}

# output "codebuild_webhook_url" {
#   description = "CodeBuild webhook URL"
#   value       = aws_codebuild_webhook.sumologic-aws-lambda.url
# }


output "cloudwatch_log_group" {
  description = "CloudWatch log group for CodeBuild"
  value       = aws_cloudwatch_log_group.codebuild.name
}