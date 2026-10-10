# Complete Beginner's AWS Deployment Guide: Rubber Duck

Welcome! This guide is written specifically for developers new to AWS. It walks you through deploying **Rubber Duck** from scratch, with numbered, click-by-click instructions, exact AWS Console menu names, screenshots guidance, verification steps, and troubleshooting notes under every step.

---

## Table of Contents
1. [Step A: Create or Verify AWS Account, Select Region, and Enable Billing Alerts](#step-a-create-or-verify-aws-account-select-region-and-enable-billing-alerts)
2. [Step B: Set Up a $5 AWS Budget Alert (Zero Surprise Charges)](#step-b-set-up-a-5-aws-budget-alert-zero-surprise-charges)
3. [Step C: Create IAM User with Deployment Permissions, Install CLIs, & Run `aws configure`](#step-c-create-iam-user-with-deployment-permissions-install-clis--run-aws-configure)
4. [Step D: Obtain a Free Google Gemini API Key & Store in AWS SSM](#step-d-obtain-a-free-google-gemini-api-key--store-in-aws-ssm)
5. [Step E: Build and Deploy the Serverless Backend with AWS SAM](#step-e-build-and-deploy-the-serverless-backend-with-aws-sam)
6. [Step F: Connect Frontend to Backend (Function URL) & Build](#step-f-connect-frontend-to-backend-function-url--build)
7. [Step G: Host Frontend on AWS (Amazon S3 + CloudFront or AWS Amplify)](#step-g-host-frontend-on-aws-amazon-s3--cloudfront-or-aws-amplify)
8. [Step H: End-to-End Verification (curl & Browser Testing)](#step-h-end-to-end-verification-curl--browser-testing)
9. [Step I: View Real-Time CloudWatch Logs & Custom EMF Metrics](#step-i-view-real-time-cloudwatch-logs--custom-emf-metrics)
10. [Step J: Push to Public GitHub Repository (Protecting Secrets)](#step-j-push-to-public-github-repository-protecting-secrets)
11. [Step K: Teardown & Cleanup After Hackathon Judging](#step-k-teardown--cleanup-after-hackathon-judging)

---

## Step A: Create or Verify AWS Account, Select Region, and Enable Billing Alerts

### Actions:
1. Open [https://aws.amazon.com](https://aws.amazon.com) and click **Sign In to the Console** (or **Create an AWS Account** if you don't have one).
2. Once signed in, look at the top navigation bar on the top-right corner next to your account name. Click the region selector dropdown and select **US East (N. Virginia) `us-east-1`**.
   > *Why `us-east-1`?* It provides full Free Tier access for all serverless features and is the primary region for AWS CloudFront and SAM.
3. In the top search bar, type `Billing and Cost Management` and select it.
4. In the left navigation menu, click **Billing Preferences** (under *Preferences and settings*).
5. Check the box **Receive CloudWatch Billing Alerts** (and **Receive Free Tier usage alerts**).
6. Enter your personal email address and click **Save preferences**.

### What you should see:
- A green banner stating *"Preferences saved successfully"*.
- The top-right region selector permanently shows **N. Virginia (us-east-1)**.

### If it fails:
- **"Access Denied on Billing"**: If you are logged in as an IAM user instead of the Root account, log in as Root once, go to **Account Settings**, scroll to **IAM User and Role Access to Billing Information**, click **Edit**, and check **Activate IAM Access**.

---

## Step B: Set Up a $5 AWS Budget Alert (Zero Surprise Charges)

### Actions:
1. In the AWS Console search bar, type `Budgets` and select **AWS Budgets**.
2. Click the orange **Create budget** button.
3. Under *Budget setup*, choose **Use a template (simplified)**.
4. Select the template **Zero spend budget** OR choose **Monthly cost budget**:
   - Set **Budget amount**: `$5.00`.
   - Set **Email recipients**: your email address.
5. Click **Create budget**.

### What you should see:
- Your budget list displays a `$5.00 monthly cost budget` with status *"OK"* (0% spent).
- AWS will automatically email you if your usage exceeds 85% ($4.25).

### If it fails:
- If you see a notification to activate Cost Explorer first, click **Enable Cost Explorer** and allow 2–4 hours for initial cost allocation to refresh. The simplified budget will still function.

---

## Step C: Create IAM User with Deployment Permissions, Install CLIs, & Run `aws configure`

### Part 1: Create IAM User in AWS Console
1. In the AWS search bar, type `IAM` and click **IAM**.
2. In the left sidebar, click **Users**, then click the orange **Create user** button.
3. **Step 1**: Enter `User name`: `rubber-duck-deployer`. Leave *"Provide user access to the AWS Management Console"* unchecked (this user is for CLI deployment only). Click **Next**.
4. **Step 2**: Select **Attach policies directly**.
5. In the permissions search box, check:
   - `AdministratorAccess` (or for strict least privilege: `AWSCloudFormationFullAccess`, `AWSLambda_FullAccess`, `AmazonDynamoDBFullAccess`, `IAMFullAccess`, `AmazonSSMReadOnlyAccess`).
   > *Note for hackathons*: `AdministratorAccess` on a personal development account simplifies CloudFormation role delegation.
6. Click **Next**, review, and click **Create user**.
7. Click on your newly created user (`rubber-duck-deployer`).
8. Click the **Security credentials** tab.
9. Scroll down to **Access keys** and click **Create access key**.
10. Select **Command Line Interface (CLI)**, check the confirmation checkbox, and click **Next**.
11. Click **Create access key**.
12. **CRITICAL**: Copy the **Access key ID** and **Secret access key** (or download the `.csv` file). You will never see the secret key again.

### Part 2: Install AWS CLI & SAM CLI on Your Machine

#### On Linux (Ubuntu / Debian / Arch):
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version

# Install AWS SAM CLI
wget https://github.com/aws/aws-sam-cli/releases/latest/download/aws-sam-cli-linux-x86_64.zip
unzip aws-sam-cli-linux-x86_64.zip -d sam-installation
sudo ./sam-installation/install
sam --version
```

#### On macOS:
```bash
brew install awscli
brew install aws-sam-cli
```

#### On Windows (PowerShell as Admin):
```powershell
winget install Amazon.AWSCLI
winget install Amazon.SAM-CLI
```

### Part 3: Run `aws configure`
In your terminal, execute:
```bash
aws configure
```
Enter your values:
- `AWS Access Key ID`: *(paste your Access Key ID)*
- `AWS Secret Access Key`: *(paste your Secret Access Key)*
- `Default region name`: `us-east-1`
- `Default output format`: `json`

### Verification:
Run:
```bash
aws sts get-caller-identity
```

### What you should see:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/rubber-duck-deployer"
}
```

### If it fails:
- **"InvalidClientTokenId"**: You mistyped or added a whitespace in the Access Key ID. Re-run `aws configure` and paste carefully.

---

## Step D: Obtain a Free Google Gemini API Key & Store in AWS SSM

### Actions:
1. Open Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account.
3. Click the blue **Create API key** button.
4. Select or create a Google Cloud project and click **Create API key in existing project**.
5. Copy your generated key (format begins with `AIzaSy...`).

### Store in AWS Systems Manager Parameter Store (Encrypted):
In your terminal, run this command to store it securely in AWS:
```bash
aws ssm put-parameter \
  --name "/rubber-duck/gemini-api-key" \
  --type "SecureString" \
  --value "YOUR_GEMINI_API_KEY_HERE" \
  --overwrite \
  --region us-east-1
```

### What you should see:
```json
{
    "Version": 1,
    "Tier": "Standard"
}
```

### If it fails:
- If you encounter permission issues with SSM, you can also pass it directly during SAM deployment in Step E.

---

## Step E: Build and Deploy the Serverless Backend with AWS SAM

### Actions:
From the root of the project directory:

```bash
cd backend
sam build
sam deploy --guided
```

### SAM Prompts to answer:
- **Stack Name [sam-app]**: `rubber-duck-backend`
- **AWS Region [us-east-1]**: `us-east-1`
- **Parameter GeminiApiKey []**: Press Enter (leave blank if stored in SSM; or paste your Gemini key if you didn't use SSM)
- **Parameter GeminiModel [gemini-2.5-flash]**: Press Enter
- **Parameter EnvironmentName [Production]**: Press Enter
- **Confirm changes before deploy [y/N]**: `N`
- **Allow SAM CLI IAM role creation [Y/n]**: `Y`
- **Disable rollback for failures [y/N]**: `N`
- **RubberDuckFunction Function URL has no authentication. Is this okay? [y/N]**: `y`
- **Save arguments to configuration file [Y/n]**: `Y`
- **SAM configuration file [samconfig.toml]**: Press Enter
- **SAM configuration environment [default]**: Press Enter

SAM will now deploy CloudFormation resources:
1. `SessionsTable` (Amazon DynamoDB)
2. `StatsTable` (Amazon DynamoDB)
3. `RubberDuckFunctionRole` (IAM Role)
4. `RubberDuckFunction` (AWS Lambda arm64 Function)
5. `RubberDuckFunctionUrl` (Public HTTPS Function URL)

### What you should see:
```
CloudFormation outputs from deployed stack
------------------------------------------------------------------------------------------------------------------------------------------------------
Outputs
------------------------------------------------------------------------------------------------------------------------------------------------------
Key                 RubberDuckFunctionUrl
Description         Public HTTPS URL for the Rubber Duck Backend Lambda Function URL
Value               https://abcdef1234567890.lambda-url.us-east-1.on.aws/

Key                 RubberDuckFunctionName
Description         Lambda Function Name (for CloudWatch logs inspection)
Value               rubber-duck-api-Production
------------------------------------------------------------------------------------------------------------------------------------------------------
Successfully created/updated stack - rubber-duck-backend in us-east-1
```

👉 **SAVE YOUR `RubberDuckFunctionUrl` VALUE!** You will use it in Step F.

### If it fails:
- **"No changes to deploy"**: Your stack is already up to date.
- **"Function URL requires AuthType"**: Ensure you answered `y` to allow unauthenticated public Function URL for the web client.

---

## Step F: Connect Frontend to Backend (Function URL) & Build

### Actions:
1. Return to the root directory and navigate to `frontend`:
```bash
cd ../frontend
```
2. Create your `.env.production` file using your Function URL from Step E:
```bash
echo "VITE_API_URL=https://abcdef1234567890.lambda-url.us-east-1.on.aws" > .env.production
```
*(Replace `https://abcdef1234567890.lambda-url.us-east-1.on.aws` with your exact URL, including the trailing slash or without).*

3. Run the production build:
```bash
npm run build
```

### What you should see:
```
✓ 2267 modules transformed.
dist/index.html                     1.21 kB
dist/assets/index-BiKzYvdc.js      101.87 kB
dist/assets/framer-C1Ae3gnn.js     122.69 kB
dist/assets/vendor-CRnlBLF1.js     133.93 kB
dist/assets/markdown-BeU0cigU.js   158.30 kB
✓ built in 7.96s
```
Your compiled website is now in `frontend/dist/`.

---

## Step G: Host Frontend on AWS (Amazon S3 + CloudFront or AWS Amplify)

You can choose either Option 1 (CloudFront + S3, classic AWS architecture) or Option 2 (AWS Amplify Hosting, zero-config CDN). Both qualify for the AWS Builder Center hackathon and are within the Free Tier.

### Option 1: S3 + CloudFront (Recommended)

#### 1. Create S3 Bucket:
```bash
# Choose a globally unique bucket name (e.g., rubber-duck-web-<yourname>)
BUCKET_NAME="rubber-duck-web-$(whoami)-$(date +%s)"
echo "Bucket name: $BUCKET_NAME"

aws s3 mb s3://$BUCKET_NAME --region us-east-1
```

#### 2. Configure S3 for Static Website Hosting:
```bash
aws s3 website s3://$BUCKET_NAME --index-document index.html --error-document index.html

# Enable public read policy
cat <<EOF > s3_policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF

# Disable block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Apply policy
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://s3_policy.json
rm s3_policy.json
```

#### 3. Upload the Built Frontend:
```bash
aws s3 sync dist/ s3://$BUCKET_NAME/ --delete
```

#### 4. Create CloudFront Distribution:
In the AWS Console:
1. Search for `CloudFront` and click **Create distribution**.
2. **Origin domain**: Select your S3 bucket endpoint (`$BUCKET_NAME.s3-website-us-east-1.amazonaws.com`).
3. Under **Default cache behavior**:
   - Viewer protocol policy: **Redirect HTTP to HTTPS**.
   - Allowed HTTP methods: **GET, HEAD**.
4. Under **Web Application Firewall (WAF)**: Select *Do not enable security protections* (to avoid WAF charges).
5. Click **Create distribution**.
6. CloudFront will deploy in 2–3 minutes and provide a domain like `https://d12345678abcdef.cloudfront.net`.

### Option 2: AWS Amplify Hosting (Fast Alternative)
1. In the AWS Console, search for `AWS Amplify`.
2. Click **Deploy an app** -> **Deploy without Git provider**.
3. App name: `rubber-duck`.
4. Environment name: `production`.
5. Method: Drag and drop the `frontend/dist` folder (or zip it with `zip -r dist.zip dist/` and upload).
6. Click **Save and deploy**.
7. Amplify will provide an instant HTTPS URL (e.g. `https://production.d123456789.amplifyapp.com`).

---

## Step H: End-to-End Verification (curl & Browser Testing)

Let's verify that your Lambda backend and frontend are communicating properly.

### 1. Test the `/health` Endpoint:
```bash
curl -i https://YOUR_FUNCTION_URL/health
```
**Expected response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Access-Control-Allow-Origin: *

{"status": "ok", "service": "Rubber Duck API", "version": "1.0.0"}
```

### 2. Test the `/stats` Endpoint:
```bash
curl -i https://YOUR_FUNCTION_URL/stats
```
**Expected response**:
```json
{
  "total_sessions": 0,
  "bugs_solved": 0,
  "solved_without_show_me": 0,
  "solved_without_show_me_pct": 100.0,
  "avg_questions": 0.0,
  "total_ratings": 0,
  "positive_ratings": 0,
  "thumbs_up_pct": 100.0
}
```

### 3. Test a Debugging Message with `/chat`:
```bash
curl -i -X POST https://YOUR_FUNCTION_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-cli-1", "message": "TypeError: Cannot read properties of undefined (reading user)"}'
```
**Expected response**:
```json
{
  "session_id": "test-cli-1",
  "reply": "What is the value of the object immediately before accessing .user on that line?",
  "state": "asking",
  "streak": 0,
  "hints_used": 0,
  "question_count": 1,
  "recap": null
}
```

### 4. Test in Browser:
1. Open your CloudFront or Amplify URL in your browser.
2. Verify:
   - Mascot is floating/blinking peacefully with greeting *"Quack. What's broken?"*.
   - Click one of the 3 clickable example bugs.
   - Duck transitions to "thinking" state (head tilt + bobbing dots).
   - Duck replies with exactly ONE question under 60 words with word-by-word reveal.
   - Click the **Hint** chip -> Duck provides a gentle nudge.
   - Type *"I found it!"* -> Duck hops, confetti erupts, and "What You Learned" recap card appears with 👍/👎 rating buttons!
   - Click the stats icon in the top header -> Verify the live stats modal displays real DynamoDB numbers.

---

## Step I: View Real-Time CloudWatch Logs & Custom EMF Metrics

This step provides the proof you can screenshot for your hackathon submission and article!

### 1. View CloudWatch Logs:
1. In the AWS Console search bar, type `CloudWatch`.
2. In the left navigation, click **Logs** -> **Log groups**.
3. Click `/aws/lambda/rubber-duck-api-Production`.
4. Click the top Log stream to view live execution logs.
5. You will see the structured EMF payloads printed in real time:
```json
{
  "_aws": {
    "Timestamp": 1728540000000,
    "CloudWatchMetrics": [
      {
        "Namespace": "RubberDuck",
        "Dimensions": [["Environment"]],
        "Metrics": [
          {"Name": "SessionsStarted", "Unit": "Count"},
          {"Name": "BugsSolved", "Unit": "Count"}
        ]
      }
    ]
  },
  "Environment": "Production",
  "SessionsStarted": 1
}
```

### 2. View Custom Metrics in CloudWatch:
1. In CloudWatch left sidebar, click **Metrics** -> **All metrics**.
2. Under *Custom Namespaces*, click **RubberDuck**.
3. Select **Environment**.
4. Check the boxes for:
   - `SessionsStarted`
   - `BugsSolved`
   - `HintsUsed`
   - `ShowMeUsed`
   - `RatingsSubmitted`
5. Click the **Graphed metrics** tab above the graph and set period to **1 Minute** -> **Number** or **Line Chart**.
6. Take a screenshot for your article!

---

## Step J: Push to Public GitHub Repository (Protecting Secrets)

### 1. Verify Ignored Files:
Ensure no secrets or keys are committed:
```bash
git status
```
Check that:
- `.env` and `.env.production` are NOT tracked.
- `.venv/` and `node_modules/` are NOT tracked.
- Only `.env.example` templates and source code are staged.

### 2. Initialize and Commit:
```bash
git init
git add .
git commit -m "feat: complete Rubber Duck AI debugging companion for AWS Builder Center hackathon"
```

### 3. Push to GitHub:
1. Create a new public repository on [https://github.com/new](https://github.com/new) named `rubber-duck`.
2. Link and push:
```bash
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/rubber-duck.git
git push -u origin main
```

---

## Step K: Teardown & Cleanup After Hackathon Judging

When judging has concluded and you want to decommission the project so zero resources remain:

### 1. Delete the SAM Backend Stack:
```bash
cd backend
sam delete --stack-name rubber-duck-backend --no-prompts
```
This cleanly deletes:
- Lambda function
- Function URL
- Both DynamoDB tables
- IAM execution roles
- CloudWatch log groups

### 2. Delete S3 Bucket and CloudFront Distribution:
```bash
# Empty S3 bucket
aws s3 rm s3://$BUCKET_NAME --recursive

# Delete bucket
aws s3 rb s3://$BUCKET_NAME
```
In the AWS Console under CloudFront:
1. Select the distribution -> click **Disable**.
2. Once disabled (after ~2 minutes) -> click **Delete**.

### 3. Verify Budget:
Your AWS Budget remains at \$0 spent throughout the lifecycle!
