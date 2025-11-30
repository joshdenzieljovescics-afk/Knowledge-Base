# PowerShell deployment script for Knowledge Base Lambda function
# This script automates the build and deployment process

param(
    [Parameter(Mandatory=$false)]
    [string]$Action = "deploy",

    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild,

    [Parameter(Mandatory=$false)]
    [switch]$Guided,

    [Parameter(Mandatory=$false)]
    [switch]$Local
)

# Color output functions
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Check prerequisites
function Check-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "AWS CLI not found. Install from: https://aws.amazon.com/cli/"
        exit 1
    }
    Write-Success "AWS CLI found"

    # Check SAM CLI
    if (-not (Get-Command sam -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "SAM CLI not found. Install from: https://docs.aws.amazon.com/serverless-application-model/"
        exit 1
    }
    Write-Success "SAM CLI found"

    # Check AWS credentials
    try {
        aws sts get-caller-identity | Out-Null
        Write-Success "AWS credentials configured"
    } catch {
        Write-Error-Custom "AWS credentials not configured. Run: aws configure"
        exit 1
    }
}

# Build the application
function Build-Application {
    Write-Info "Building application..."

    try {
        sam build
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Build completed successfully"
            return $true
        } else {
            Write-Error-Custom "Build failed"
            return $false
        }
    } catch {
        Write-Error-Custom "Build error: $_"
        return $false
    }
}

# Deploy the application
function Deploy-Application {
    param([bool]$Guided)

    Write-Info "Deploying to AWS Lambda..."

    try {
        if ($Guided) {
            sam deploy --guided
        } else {
            sam deploy
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Deployment completed successfully"

            # Get API endpoint
            Write-Info "Retrieving API endpoint..."
            $endpoint = aws cloudformation describe-stacks `
                --stack-name knowledge-base-api `
                --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' `
                --output text

            if ($endpoint) {
                Write-Success "API Endpoint: $endpoint"
                Write-Info "Update your frontend to use this endpoint"
            }

            return $true
        } else {
            Write-Error-Custom "Deployment failed"
            return $false
        }
    } catch {
        Write-Error-Custom "Deployment error: $_"
        return $false
    }
}

# Start local API
function Start-LocalApi {
    Write-Info "Starting local API server..."
    Write-Warning-Custom "Press Ctrl+C to stop the server"
    Write-Info "API will be available at: http://localhost:3000"

    sam local start-api
}

# View logs
function View-Logs {
    Write-Info "Streaming logs from Lambda function..."
    Write-Warning-Custom "Press Ctrl+C to stop"

    sam logs --stack-name knowledge-base-api --tail
}

# Delete stack
function Remove-Stack {
    Write-Warning-Custom "This will delete the entire stack including all resources!"
    $confirm = Read-Host "Are you sure? (yes/no)"

    if ($confirm -eq "yes") {
        Write-Info "Deleting stack..."
        aws cloudformation delete-stack --stack-name knowledge-base-api

        Write-Info "Waiting for deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name knowledge-base-api

        Write-Success "Stack deleted successfully"
    } else {
        Write-Info "Deletion cancelled"
    }
}

# Get stack info
function Get-StackInfo {
    Write-Info "Retrieving stack information..."

    # Get outputs
    $outputs = aws cloudformation describe-stacks `
        --stack-name knowledge-base-api `
        --query 'Stacks[0].Outputs' `
        --output json | ConvertFrom-Json

    Write-Host "`nStack Outputs:" -ForegroundColor Yellow
    foreach ($output in $outputs) {
        Write-Host "  $($output.OutputKey): $($output.OutputValue)" -ForegroundColor White
    }

    # Get stack status
    $status = aws cloudformation describe-stacks `
        --stack-name knowledge-base-api `
        --query 'Stacks[0].StackStatus' `
        --output text

    Write-Host "`nStack Status: $status" -ForegroundColor Yellow
}

# Test the API
function Test-Api {
    Write-Info "Testing deployed API..."

    # Get endpoint
    $endpoint = aws cloudformation describe-stacks `
        --stack-name knowledge-base-api `
        --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' `
        --output text

    if (-not $endpoint) {
        Write-Error-Custom "Could not retrieve API endpoint"
        return
    }

    Write-Info "Testing endpoint: $endpoint/health"

    try {
        $response = Invoke-WebRequest -Uri "$endpoint/health" -UseBasicParsing

        if ($response.StatusCode -eq 200) {
            Write-Success "API is responding correctly"
            Write-Host "Response: $($response.Content)" -ForegroundColor White
        } else {
            Write-Warning-Custom "API returned status code: $($response.StatusCode)"
        }
    } catch {
        Write-Error-Custom "API test failed: $_"
    }
}

# Main script logic
Write-Host @"
╔════════════════════════════════════════════════════════╗
║   Knowledge Base Lambda Deployment Script             ║
║   AWS SAM Application Builder & Deployer              ║
╚════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Check prerequisites first
Check-Prerequisites

# Execute action
switch ($Action.ToLower()) {
    "build" {
        Build-Application
    }

    "deploy" {
        if (-not $SkipBuild) {
            $buildSuccess = Build-Application
            if (-not $buildSuccess) {
                Write-Error-Custom "Build failed, aborting deployment"
                exit 1
            }
        }

        Deploy-Application -Guided $Guided
    }

    "local" {
        if (-not $SkipBuild) {
            $buildSuccess = Build-Application
            if (-not $buildSuccess) {
                Write-Error-Custom "Build failed"
                exit 1
            }
        }

        Start-LocalApi
    }

    "logs" {
        View-Logs
    }

    "delete" {
        Remove-Stack
    }

    "info" {
        Get-StackInfo
    }

    "test" {
        Test-Api
    }

    default {
        Write-Host @"

Usage: .\deploy.ps1 [Action] [Options]

Actions:
  deploy      Build and deploy to AWS Lambda (default)
  build       Build the application only
  local       Start local API server for testing
  logs        Stream logs from deployed Lambda
  delete      Delete the CloudFormation stack
  info        Show stack information and outputs
  test        Test the deployed API

Options:
  -SkipBuild  Skip the build step (deploy only)
  -Guided     Use guided deployment (for first deployment)

Examples:
  .\deploy.ps1                    # Build and deploy
  .\deploy.ps1 -Guided            # First time deployment
  .\deploy.ps1 deploy -SkipBuild  # Deploy without building
  .\deploy.ps1 local              # Test locally
  .\deploy.ps1 logs               # View logs
  .\deploy.ps1 info               # Show stack info
  .\deploy.ps1 test               # Test API
  .\deploy.ps1 delete             # Delete stack

"@ -ForegroundColor White
    }
}

Write-Host ""
