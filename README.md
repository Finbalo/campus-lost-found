# Campus Lost & Found

Serverless lost-and-found board on AWS, all provisioned with Terraform and deployed by GitHub Actions.

**Stack:** S3 + CloudFront (site and photos) - API Gateway HTTP API - Lambda (Python) - DynamoDB - SNS (match alerts)

## Run it

1. **Push this folder to a new GitHub repo** (`main` branch).
2. **Bootstrap once** (needs AWS CLI configured + Terraform >= 1.10):
   ```bash
   cd bootstrap
   terraform init
   terraform apply -var="github_repo=YOUR_USER/YOUR_REPO"
   ```
   It prints `TF_STATE_BUCKET` and `AWS_ROLE_ARN`.
3. **Add GitHub repo secrets** (Settings > Secrets and variables > Actions):
   - `AWS_ROLE_ARN`
   - `TF_STATE_BUCKET`
   - `NOTIFY_EMAIL` (optional, gets match alerts; confirm the AWS email once)
4. **Push to `main`.** The pipeline tests, applies Terraform, uploads the site, and invalidates CloudFront. The live URL shows in the run summary.

PRs run lint, tests, `terraform validate` and `terraform plan` without applying.

## Tear down
`cd terraform && terraform destroy` (with the same backend flags), then `terraform destroy` in `bootstrap`. Empty the photo bucket first if it has files.

## Next upgrades
Cognito login, a tighter IAM role for the pipeline, a custom domain with ACM + Route 53, WAF rate limiting.
