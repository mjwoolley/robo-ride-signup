#!/bin/bash
# Setup Cloud Scheduler to trigger Cloud Run Job

# Configuration
PROJECT_ID="gen-lang-client-0610397472"
REGION="us-central1"
JOB_NAME="wccc-ride-signup"
SCHEDULE="0 */4 * * *"  # Every 4 hours - adjust as needed
TIMEZONE="America/Los_Angeles"  # Adjust to your timezone

echo "Setting up Cloud Scheduler for $JOB_NAME..."

# Create or update scheduler job
gcloud scheduler jobs create http ${JOB_NAME}-trigger \
  --location=$REGION \
  --schedule="$SCHEDULE" \
  --time-zone="$TIMEZONE" \
  --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
  --http-method=POST \
  --oauth-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
  --project=$PROJECT_ID

echo "✅ Cloud Scheduler created!"
echo "Schedule: $SCHEDULE ($TIMEZONE)"
echo "Next run will trigger the job according to the schedule"
echo ""
echo "To manually run the scheduler now:"
echo "gcloud scheduler jobs run ${JOB_NAME}-trigger --location=$REGION"
