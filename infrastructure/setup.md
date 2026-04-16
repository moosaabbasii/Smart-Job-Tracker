# Smart Job Tracker — Infrastructure Setup

## DynamoDB Table
- Table name: `JobApplications`
- Partition key: `application_id` (String)
- Billing mode: PAY_PER_REQUEST (on-demand) — stays in free tier

## Lambda Functions
- `add_application` — POST /applications
- `get_applications` — GET /applications
- `update_status` — PUT /applications/{id}
- `check_followups` — triggered by EventBridge daily at 9AM UTC

## API Gateway
- REST API, regional
- Routes connected to Lambda via Lambda Proxy integration

## EventBridge
- Rule: cron(0 9 * * ? *) → triggers check_followups Lambda

## SNS
- Topic: `job-followup-alerts`
- Subscription: your email address

## IAM
- Lambda execution role needs:
  - dynamodb:PutItem, GetItem, Scan, UpdateItem
  - sns:Publish
  - logs:CreateLogGroup, CreateLogDeliveryStream, PutLogEvents
