# AWS Key Sleuth



## What is this for?

This is a tool that will help in auditing the AWS key age and help notify users via Slack or SNS topic that their AWS key may be coming out of compliance.

## Deploy

This tool is made with [Serverless](https://serverless.com/) using the [python plugin](https://serverless.com/plugins/serverless-python-requirements/). All the Lambda related configuration should be set. All that is needed is to deploy. Since Serverless can use stages we'll use `LIVE` to keep versions seperate.

```bash
serverless deploy --stage live
```







