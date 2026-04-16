import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("JobApplications")


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

        # Verify ownership before deleting
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

        table.delete_item(Key={"application_id": application_id})

        logger.info(f"User {user_id}: deleted application {application_id}")
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"success": True}),
        }
    except Exception as e:
        logger.error(f"Failed to delete application: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to delete application"}),
        }
