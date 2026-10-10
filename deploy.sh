#!/usr/bin/env bash
# ==============================================================================
# Rubber Duck - Automated Deployment Helper Script
# Deploys AWS SAM backend and syncs the built React frontend to Amazon S3
# ==============================================================================

set -e

echo "🦆 ====================================================="
echo "🦆   Deploying Rubber Duck to AWS"
echo "🦆 ====================================================="

# Check AWS CLI
if ! command -v aws &> /dev/null; then
  echo "❌ Error: AWS CLI is not installed or not in PATH."
  echo "👉 See MANUAL_STEPS.md Step 3 for quick installation."
  exit 1
fi

# Check SAM CLI
if ! command -v sam &> /dev/null; then
  echo "❌ Error: AWS SAM CLI is not installed or not in PATH."
  echo "👉 See MANUAL_STEPS.md Step 3 for quick installation."
  exit 1
fi

# 1. Build and deploy backend with SAM
echo ""
echo "🚀 Step 1: Building and deploying backend with AWS SAM..."
cd backend
sam build
sam deploy --resolve-s3 --stack-name rubber-duck-backend --capabilities CAPABILITY_IAM

# Extract Function URL
FUNCTION_URL=$(aws cloudformation describe-stacks \
  --stack-name rubber-duck-backend \
  --query "Stacks[0].Outputs[?OutputKey=='RubberDuckFunctionUrl'].OutputValue" \
  --output text)

echo "✅ Backend deployed successfully!"
echo "🔗 Function URL: $FUNCTION_URL"

cd ..

# 2. Configure frontend
echo ""
echo "⚙️ Step 2: Configuring frontend VITE_API_URL..."
echo "VITE_API_URL=$FUNCTION_URL" > frontend/.env.production

# 3. Build frontend
echo ""
echo "📦 Step 3: Building production frontend..."
cd frontend
npm run build
cd ..

echo ""
echo "🎉 Frontend build ready in frontend/dist!"
echo "👉 Follow MANUAL_STEPS.md Step 7 to upload to your S3 bucket or AWS Amplify."
echo "🦆 Quack! You are ready to debug."
