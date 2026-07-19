# Deploy Karigar to Cloud Run. Run AFTER gcloud_auth.ps1. Claude runs this.
$ErrorActionPreference = "Stop"
$env:CLOUDSDK_PYTHON = "C:\Users\Dell\AppData\Local\Programs\Python\Python313\python.exe"
$g = "$env:LOCALAPPDATA\gcloud\google-cloud-sdk\bin\gcloud.cmd"
$proj = "rock-module-502819-i9"
Set-Location "c:\Users\Dell\Desktop\Projects\KARIGAR"

& $g config set project $proj
Write-Host "Enabling required APIs (first time can take a minute)..."
& $g services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project $proj

Write-Host "Building + deploying (Cloud Build, ~5-10 min)..."
& $g run deploy karigar `
    --source . `
    --project $proj `
    --region asia-south1 `
    --allow-unauthenticated `
    --min-instances 1 `
    --max-instances 1 `
    --no-cpu-throttling `
    --memory 4Gi `
    --cpu 2 `
    --timeout 600 `
    --env-vars-file env.yaml `
    --quiet
