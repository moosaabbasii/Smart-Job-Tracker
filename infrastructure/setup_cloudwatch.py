"""
Phase 5 — CloudWatch monitoring setup
- Log groups for all 4 Lambda functions (with 14-day retention)
- Dashboard: invocation counts + errors for each function
- Billing alarm at $1/month threshold (us-east-1 only, requires billing alerts enabled)

Usage:
    py infrastructure/setup_cloudwatch.py
"""

import boto3
import json

REGION = "us-east-1"
LAMBDA_FUNCTIONS = [
    "add_application",
    "get_applications",
    "update_status",
    "check_followups",
]
DASHBOARD_NAME = "SmartJobTracker"
ALARM_EMAIL = ""          # leave blank — billing alarms go to the root account
RETENTION_DAYS = 14


def create_log_groups(logs_client):
    for fn in LAMBDA_FUNCTIONS:
        log_group = f"/aws/lambda/{fn}"
        try:
            logs_client.create_log_group(logGroupName=log_group)
            print(f"  Created log group: {log_group}")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            print(f"  Log group already exists: {log_group}")

        # Set retention policy
        logs_client.put_retention_policy(
            logGroupName=log_group,
            retentionInDays=RETENTION_DAYS,
        )
        print(f"    Retention set to {RETENTION_DAYS} days")


def create_dashboard(cw_client):
    # Build one row of widgets per Lambda (Invocations + Errors side by side)
    widgets = []
    y = 0
    for fn in LAMBDA_FUNCTIONS:
        # Invocations widget
        widgets.append({
            "type": "metric",
            "x": 0, "y": y, "width": 12, "height": 6,
            "properties": {
                "title": f"{fn} — Invocations",
                "metrics": [[
                    "AWS/Lambda", "Invocations",
                    "FunctionName", fn,
                    {"stat": "Sum", "period": 86400}
                ]],
                "view": "timeSeries",
                "region": REGION,
            }
        })
        # Errors widget
        widgets.append({
            "type": "metric",
            "x": 12, "y": y, "width": 12, "height": 6,
            "properties": {
                "title": f"{fn} — Errors",
                "metrics": [[
                    "AWS/Lambda", "Errors",
                    "FunctionName", fn,
                    {"stat": "Sum", "period": 86400, "color": "#d62728"}
                ]],
                "view": "timeSeries",
                "region": REGION,
            }
        })
        y += 6

    dashboard_body = json.dumps({"widgets": widgets})
    cw_client.put_dashboard(
        DashboardName=DASHBOARD_NAME,
        DashboardBody=dashboard_body,
    )
    print(f"  Dashboard '{DASHBOARD_NAME}' created/updated")
    print(f"  URL: https://{REGION}.console.aws.amazon.com/cloudwatch/home"
          f"?region={REGION}#dashboards:name={DASHBOARD_NAME}")


def create_billing_alarm(cw_client):
    """
    Billing metrics live only in us-east-1 regardless of the resource region.
    Requires 'Receive Billing Alerts' to be enabled in the Billing console:
    https://console.aws.amazon.com/billing/home#/preferences
    """
    # We'll send the alarm to the default CloudWatch alarm action (visible in
    # the console).  To also get an email, pass an SNS ARN as actions_enabled.
    cw_client_billing = boto3.client("cloudwatch", region_name="us-east-1")
    cw_client_billing.put_metric_alarm(
        AlarmName="SmartJobTracker-BillingAlarm-1USD",
        AlarmDescription="Alert when estimated AWS charges exceed $1",
        Namespace="AWS/Billing",
        MetricName="EstimatedCharges",
        Dimensions=[{"Name": "Currency", "Value": "USD"}],
        Statistic="Maximum",
        Period=86400,           # daily
        EvaluationPeriods=1,
        Threshold=1.0,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="notBreaching",
    )
    print("  Billing alarm 'SmartJobTracker-BillingAlarm-1USD' created")
    print("  NOTE: Billing alerts must be enabled in the AWS Billing console")
    print("  https://console.aws.amazon.com/billing/home#/preferences")


def main():
    logs_client = boto3.client("logs", region_name=REGION)
    cw_client = boto3.client("cloudwatch", region_name=REGION)

    print("\n=== Phase 5: CloudWatch Monitoring ===\n")

    print("[1/3] Creating CloudWatch log groups...")
    create_log_groups(logs_client)

    print("\n[2/3] Creating CloudWatch dashboard...")
    create_dashboard(cw_client)

    print("\n[3/3] Creating billing alarm...")
    create_billing_alarm(cw_client)

    print("\nDone! Phase 5 complete.")


if __name__ == "__main__":
    main()
