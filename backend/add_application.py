import json
import logging
import uuid
import boto3
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("JobApplications")

VALID_STATUSES = {"Applied", "Phone Screen", "Interview", "Offer", "Rejected"}


def get_user_id(event):
    try:
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    except (KeyError, TypeError):
        return None


def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
        if not user_id:
            return {
                "statusCode": 401,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Unauthorized"}),
            }

        body = json.loads(event.get("body", "{}"))

        required = ["company", "role", "status"]
        for field in required:
            if not body.get(field):
                return {
                    "statusCode": 400,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": f"Missing required field: {field}"}),
                }

        if body["status"] not in VALID_STATUSES:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}),
            }

        item = {
            "application_id": str(uuid.uuid4()),
            "user_id": user_id,
            "company": body["company"].strip(),
            "role": body["role"].strip(),
            "status": body["status"],
            "date_applied": body.get("date_applied", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "notes": body.get("notes", "").strip(),
            "follow_up_date": body.get("follow_up_date", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        table.put_item(Item=item)

        logger.info(f"User {user_id}: added application {item['application_id']} — {item['role']} at {item['company']}")
        return {
            "statusCode": 201,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(item),
        }
    except Exception as e:
        logger.error(f"Failed to add application: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to add application"}),
        }
