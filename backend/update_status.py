import json
import logging
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

        path_params = event.get("pathParameters") or {}
        application_id = path_params.get("id")

        if not application_id:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing application_id in path"}),
            }

        # Verify ownership before updating
        existing = table.get_item(Key={"application_id": application_id}).get("Item")
        if not existing:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Application not found"}),
            }
        if existing.get("user_id") != user_id:
            return {
                "statusCode": 403,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Forbidden"}),
            }

        body = json.loads(event.get("body", "{}"))
        new_status = body.get("status")

        if not new_status:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing required field: status"}),
            }

        if new_status not in VALID_STATUSES:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}),
            }

        update_expr = "SET #s = :s, updated_at = :u"
        expr_names = {"#s": "status"}
        expr_values = {
            ":s": new_status,
            ":u": datetime.now(timezone.utc).isoformat(),
        }

        if "notes" in body:
            update_expr += ", notes = :n"
            expr_values[":n"] = body["notes"].strip() if isinstance(body["notes"], str) else body["notes"]

        if "follow_up_date" in body:
            update_expr += ", follow_up_date = :f"
            expr_values[":f"] = body["follow_up_date"]

        table.update_item(
            Key={"application_id": application_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )

        result = table.get_item(Key={"application_id": application_id})
        updated_item = result.get("Item", {})

        logger.info(f"User {user_id}: updated application {application_id} → status: {new_status}")
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(updated_item),
        }
    except Exception as e:
        logger.error(f"Failed to update application: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to update application"}),
        }
