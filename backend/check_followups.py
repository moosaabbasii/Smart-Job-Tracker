import json
import logging
import os
import boto3
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

table = dynamodb.Table("JobApplications")
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        items = []
        response = table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        logger.info(f"Checked {len(items)} applications for follow-ups on {today}")

        due = [
            item for item in items
            if item.get("follow_up_date") == today
            and item.get("status") not in ("Offer", "Rejected")
        ]

        if not due:
            logger.info("No follow-ups due today.")
            return {"statusCode": 200, "body": json.dumps({"checked": len(items), "due": 0})}

        lines = [f"Smart Job Tracker — Follow-up Reminders for {today}\n"]
        for item in due:
            lines.append(f"- {item['role']} at {item['company']} (Status: {item['status']})")

        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"Job Follow-up Reminders — {today}",
            Message="\n".join(lines),
        )

        logger.info(f"Sent reminders for {len(due)} application(s).")
        return {"statusCode": 200, "body": json.dumps({"checked": len(items), "due": len(due)})}
    except Exception as e:
        logger.error(f"check_followups failed: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
