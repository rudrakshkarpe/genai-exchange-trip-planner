#!/bin/bash

# This script sets various Google Cloud related environment variables.
# It must be SOURCED to make the variables available in your current shell.
# Example: source ./set_gcp_env.sh

# --- Configuration ---
GOOGLE_CLOUD_LOCATION="europe-west1"
REPO_NAME="cloud-run-source-deploy"
# ---------------------

echo "--- Setting Google Cloud Environment Variables ---"

# --- --- --- --- --- ---


# 3. Export PROJECT_ID (Get from config to confirm it was set correctly)
export PROJECT_ID="kisan-project-gcp"
echo "Exported PROJECT_ID=$PROJECT_ID"

# 4. Export PROJECT_NUMBER
# Using --format to extract just the projectNumber value
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
echo "Exported PROJECT_NUMBER=$PROJECT_NUMBER"

# 5. Export SERVICE_ACCOUNT_NAME (Default Compute Service Account)
export SERVICE_ACCOUNT_NAME=$(gcloud compute project-info describe --format="value(defaultServiceAccount)")
echo "Exported SERVICE_ACCOUNT_NAME=$SERVICE_ACCOUNT_NAME"

# 8. Export GOOGLE_CLOUD_PROJECT (Often used by client libraries)
# This is usually the same as PROJECT_ID
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
echo "Exported GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"

# 9. Export GOOGLE_GENAI_USE_VERTEXAI
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
echo "Exported GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI"

# 10. Export GOOGLE_CLOUD_LOCATION
export GOOGLE_CLOUD_LOCATION="$GOOGLE_CLOUD_LOCATION"
echo "Exported GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"

# 11. Export REPO_NAME
export REPO_NAME="$REPO_NAME"
echo "Exported REPO_NAME=$REPO_NAME"

# 12. Export REGION
export REGION="$GOOGLE_CLOUD_LOCATION"
echo "Exported REGION=$GOOGLE_CLOUD_LOCATION"

echo "--- Environment setup complete ---"

export IMAGE_TAG="latest"
export AGENT_NAME="planning"
export IMAGE_NAME="planning-agent"
export IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"
export SERVICE_NAME="planning-agent"
export PUBLIC_URL="https://planning-agent-${PROJECT_NUMBER}.${REGION}.run.app"

echo "Building ${AGENT_NAME} agent..."
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --substitutions=_AGENT_NAME=${AGENT_NAME},_IMAGE_PATH=${IMAGE_PATH}

echo "Image built and pushed to: ${IMAGE_PATH}"

gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE_PATH} \
  --platform=managed \
  --region=${REGION} \
  --set-env-vars="A2A_HOST=0.0.0.0" \
  --set-env-vars="A2A_PORT=8002" \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE" \
  --set-env-vars="GOOGLE_CLOUD_LOCATION=${REGION}" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars="PUBLIC_URL=${PUBLIC_URL}" \
  --allow-unauthenticated \
  --project=${PROJECT_ID} \
  --min-instances=1

export PLANNER_AGENT_URL=$(gcloud run services list --platform=managed --region=europe-west1 --format='value(URL)' | grep planning-agent)

echo "Image deployed: ${PLANNER_AGENT_URL}"