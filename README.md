# Smart Job Tracker

A serverless job application tracking platform built on AWS. Log applications, track statuses, set follow-up reminders, and get daily email alerts — all through a real-time dashboard.

Built this because spreadsheets don't cut it when you're applying to 50+ places at once and need to actually stay on top of follow-ups.

---

## What It Does

- **Auto-logs applications** — a Chrome extension detects when you submit a job on LinkedIn, Indeed, Greenhouse, Lever, or Workday and logs it instantly — no manual input
- **Track applications** — log every job you apply to with company, role, status, date, and notes
- **Status pipeline** — move applications through Applied → Phone Screen → Interview → Offer / Rejected
- **Follow-up reminders** — set a follow-up date on any application and get an automated email at 9 AM that day
- **Live dashboard** — real-time metrics, a pipeline bar showing your funnel, and searchable/filterable application cards
- **Zero manual infrastructure** — entirely serverless, scales automatically, costs nothing at this usage level

---

## Architecture

```
Streamlit Dashboard (local)
        │
        ▼
API Gateway (REST)
        ├── POST /applications   →  add_application  (Lambda)  →  DynamoDB
        ├── GET  /applications   →  get_applications (Lambda)  →  DynamoDB
        └── PUT  /applications/{id} → update_status (Lambda)  →  DynamoDB

EventBridge (cron: 9 AM UTC daily)
        └──  check_followups (Lambda)  →  SNS  →  Email alert

CloudWatch
        ├── Log groups for all 4 Lambda functions (14-day retention)
        ├── Dashboard: invocation counts + error rates per function
        └── Billing alarm at $1/month threshold
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Python, Streamlit |
| API | AWS API Gateway (REST) |
| Compute | AWS Lambda (Python 3.12) |
| Database | AWS DynamoDB (on-demand) |
| Scheduling | AWS EventBridge |
| Notifications | AWS SNS |
| Monitoring | AWS CloudWatch |
| Auth/Permissions | AWS IAM |

---

## Project Structure

```
smart-job-tracker/
├── backend/
│   ├── add_application.py     # POST /applications
│   ├── get_applications.py    # GET  /applications
│   ├── update_status.py       # PUT  /applications/{id}
│   └── check_followups.py     # EventBridge → SNS daily reminders
├── extension/
│   ├── manifest.json          # Chrome Extension Manifest V3
│   ├── background.js          # Service worker — API calls, notifications, dedup
│   ├── content/
│   │   ├── linkedin.js        # LinkedIn Easy Apply detector
│   │   ├── indeed.js          # Indeed detector
│   │   ├── greenhouse.js      # Greenhouse detector
│   │   ├── lever.js           # Lever detector
│   │   └── workday.js         # Workday detector
│   ├── popup/
│   │   ├── popup.html         # Extension popup UI
│   │   ├── popup.css          # Popup styles
│   │   └── popup.js           # Popup logic
│   ├── icons/                 # Extension icons (16/48/128px)
│   └── generate_icons.py      # Script to regenerate icons
├── frontend/
│   └── app.py                 # Streamlit dashboard
├── infrastructure/
│   ├── setup.md               # AWS setup reference
│   └── setup_cloudwatch.py    # CloudWatch log groups, dashboard, billing alarm
├── requirements.txt
└── README.md
```

---

## Chrome Extension

The extension auto-logs applications the moment you submit them — no copy-pasting, no manual entry.

**Supported platforms:** LinkedIn Easy Apply, Indeed, Greenhouse, Lever, Workday

**How it works:**
1. You submit a job application on any supported platform
2. The content script detects the confirmation page/modal
3. Role and company are extracted from the page (LinkedIn uses document title parsing for reliability)
4. A POST request fires to the API Gateway → DynamoDB stores it
5. A Chrome notification confirms the log
6. The Streamlit dashboard updates on next refresh

**Load in Chrome (developer mode):**
1. Go to `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. The extension icon appears in your toolbar

---

## Running Locally

**Prerequisites**
- Python 3.10+
- AWS account with credentials configured (`~/.aws/credentials`)
- All AWS resources deployed (see `infrastructure/setup.md`)

**Install dependencies**
```bash
pip install -r requirements.txt
```

**Start the dashboard**
```bash
py -m streamlit run frontend/app.py
```
Opens at `http://localhost:8501`

**Deploy CloudWatch monitoring**
```bash
py infrastructure/setup_cloudwatch.py
```

---

## Cost

Strictly $0. Every service used falls within the AWS Free Tier at this scale:

- DynamoDB: 25 GB storage + 200M requests/month free
- Lambda: 1M invocations/month free
- API Gateway: 1M calls/month free
- EventBridge: 14M events/month free
- SNS: 1M email deliveries/month free
- CloudWatch: Logs + basic metrics free

A $1 billing alarm is configured as a safety net.

---

## Roadmap

These are features actively planned for future versions:

**Chrome Extension — Auto-logging** ✅ Built
Detects job application submissions on LinkedIn Easy Apply, Indeed, Greenhouse, Lever, and Workday — logs them automatically with zero manual input.

**Gmail Integration — Email parsing**
Connect via Gmail API to scan for job-related confirmation emails ("Thanks for applying", "Application received") and auto-populate the tracker. Works retroactively on your existing inbox.

**Analytics Dashboard**
Response rate by company size, industry, and application source. Track which platforms give the best return. Visualize your pipeline conversion at each stage.

**Multi-user Support**
Add Cognito authentication so multiple users can have isolated dashboards. Each user gets their own DynamoDB partition.

**Mobile-friendly UI**
Responsive layout overhaul so the dashboard works properly on phone — useful for logging applications on the go.

---

## Background

Built as a personal AWS project to get hands-on with serverless architecture beyond just reading docs. Every component is wired together manually — no SAM, no CDK, no shortcuts. The goal was to understand exactly how API Gateway talks to Lambda, how EventBridge triggers work, how IAM roles scope permissions, and how to monitor all of it through CloudWatch.

The Chrome extension and Gmail parser are next — combining browser engineering with the existing AWS backend.
