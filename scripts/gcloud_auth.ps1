# Run this ONCE in a normal PowerShell window. It opens your browser to sign in
# to Google, then points gcloud at the project. After it finishes, tell Claude
# "authed" and it will deploy.
$env:CLOUDSDK_PYTHON = "C:\Users\Dell\AppData\Local\Programs\Python\Python313\python.exe"
$g = "$env:LOCALAPPDATA\gcloud\google-cloud-sdk\bin\gcloud.cmd"
& $g auth login
& $g config set project rock-module-502819-i9
Write-Host "`nDone. If you saw your account listed and 'Updated property [core/project]', tell Claude 'authed'."
