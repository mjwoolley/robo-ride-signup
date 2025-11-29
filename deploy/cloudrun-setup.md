# Google Cloud Run Deployment Setup

Complete guide to deploy WCCC Ride Signup Agent to Google Cloud Run with hourly scheduling and failure alerts.

## Prerequisites

- Google Cloud account with billing enabled
- GitHub repository with this code

## Step 1: Install gcloud CLI

```bash
# macOS
brew install google-cloud-sdk

# Initialize and login
gcloud init
gcloud auth login
```

## Step 2: Set Project Variables

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export JOB_NAME="wccc-ride-signup"

gcloud config set project $PROJECT_ID
```

## Step 3: Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  monitoring.googleapis.com
```

## Step 4: Create Artifact Registry Repository

```bash
gcloud artifacts repositories create wccc-ride-signup \
  --repository-format=docker \
  --location=$REGION \
  --description="WCCC Ride Signup Agent images"
```

## Step 5: Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com

echo "Save the contents of github-actions-key.json as GitHub secret GCP_SA_KEY"
```

## Step 6: Build and Push Initial Image

```bash
# Configure Docker
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/wccc-ride-signup/$JOB_NAME:latest .
docker push $REGION-docker.pkg.dev/$PROJECT_ID/wccc-ride-signup/$JOB_NAME:latest
```

## Step 7: Create Cloud Run Job

```bash
gcloud run jobs create $JOB_NAME \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/wccc-ride-signup/$JOB_NAME:latest \
  --region $REGION \
  --memory 2Gi \
  --cpu 1 \
  --task-timeout 10m \
  --max-retries 1 \
  --set-env-vars "GOOGLE_API_KEY=your-key" \
  --set-env-vars "LANGSMITH_API_KEY=your-key" \
  --set-env-vars "LANGSMITH_PROJECT=wccc-ride-signup" \
  --set-env-vars "LANGCHAIN_TRACING_V2=true" \
  --set-env-vars "WCCC_USERNAME=your-username" \
  --set-env-vars "WCCC_PASSWORD=your-password" \
  --set-env-vars "RIDE_SEARCH_TERM=B/B- Ride, Jenn" \
  --set-env-vars "PAGE_TIMEOUT_SECONDS=30"
```

## Step 8: Create Cloud Scheduler (Hourly Trigger)

```bash
# Create service account for scheduler
gcloud iam service-accounts create scheduler-invoker \
  --display-name="Cloud Scheduler Invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Create hourly schedule
gcloud scheduler jobs create http wccc-hourly-trigger \
  --location=$REGION \
  --schedule="0 * * * *" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
  --http-method=POST \
  --oauth-service-account-email=scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com
```

## Step 9: Set Up Failure Alerts

### Create Email Notification Channel

```bash
# First, create a notification channel via Console or:
gcloud beta monitoring channels create \
  --display-name="WCCC Agent Alerts" \
  --type=email \
  --channel-labels=email_address=your-email@example.com

# Get the channel ID
gcloud beta monitoring channels list --format="value(name)"
```

### Create Alert Policy

```bash
# Replace CHANNEL_ID with your notification channel ID
export CHANNEL_ID="projects/$PROJECT_ID/notificationChannels/YOUR_CHANNEL_ID"

gcloud alpha monitoring policies create \
  --display-name="WCCC Ride Signup Job Failures" \
  --condition-display-name="Job execution failed" \
  --condition-filter='resource.type="cloud_run_job" AND resource.labels.job_name="wccc-ride-signup" AND metric.type="run.googleapis.com/job/completed_execution_count" AND metric.labels.result="failed"' \
  --condition-threshold-value=1 \
  --condition-threshold-comparison=COMPARISON_GE \
  --condition-threshold-duration=0s \
  --condition-threshold-aggregation-aligner=ALIGN_COUNT \
  --condition-threshold-aggregation-period=300s \
  --notification-channels=$CHANNEL_ID \
  --documentation="WCCC Ride Signup Agent job failed. Check Cloud Run logs for details."
```

### Alternative: Create Alert via Console

1. Go to [Cloud Monitoring > Alerting](https://console.cloud.google.com/monitoring/alerting)
2. Click **Create Policy**
3. Add condition:
   - Resource type: **Cloud Run Job**
   - Metric: **Completed execution count**
   - Filter: `job_name = "wccc-ride-signup"` and `result = "failed"`
   - Threshold: >= 1
4. Add notification channel (email)
5. Name: "WCCC Ride Signup Job Failures"

## Step 10: Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add:

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_REGION` | `us-central1` (or your region) |
| `GCP_SA_KEY` | Contents of `github-actions-key.json` |
| `GOOGLE_API_KEY` | Your Gemini API key |
| `LANGSMITH_API_KEY` | Your LangSmith API key |
| `WCCC_USERNAME` | WCCC login username |
| `WCCC_PASSWORD` | WCCC login password |
| `RIDE_SEARCH_TERM` | `B/B- Ride, Jenn` |

## Step 11: Test Deployment

```bash
# Trigger a manual run
gcloud run jobs execute $JOB_NAME --region $REGION

# View logs
gcloud run jobs executions list --job $JOB_NAME --region $REGION
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB_NAME" --limit 50
```

## Ongoing Deployment

Push to `main` branch triggers automatic deployment via GitHub Actions.

## Monitoring

- **Logs**: [Cloud Run Jobs](https://console.cloud.google.com/run/jobs)
- **Executions**: `gcloud run jobs executions list --job $JOB_NAME --region $REGION`
- **Alerts**: [Cloud Monitoring](https://console.cloud.google.com/monitoring/alerting)
- **LangSmith**: [smith.langchain.com](https://smith.langchain.com/)

## Cost Estimate

- Cloud Run: ~$0.50-1/month (2GB memory, ~2min/hour)
- Artifact Registry: ~$0.10/month
- Cloud Scheduler: Free tier (3 jobs free)
- **Total: ~$1-3/month**

## Troubleshooting

### Job times out
Increase `--task-timeout` in the job configuration (max 60m for jobs).

### Browser issues
Check that Playwright dependencies are installed. View logs:
```bash
gcloud logging read "resource.type=cloud_run_job" --limit 100
```

### Authentication errors
Verify environment variables are set correctly in Cloud Run job.
