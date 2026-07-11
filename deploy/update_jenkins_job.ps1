$JenkinsUrl = "http://localhost:8080"
$Username = "chenzemian"
$ApiToken = "112d6dd20984e37c247625bf097fe6223f"
$Auth = "${Username}:${ApiToken}"

Write-Host "=== 1. Get CSRF Crumb ==="
$crumbJson = & curl.exe -s -u $Auth "$JenkinsUrl/crumbIssuer/api/json"
Write-Host $crumbJson

$crumb = ($crumbJson | ConvertFrom-Json)
$crumbField = $crumb.crumbRequestField
$crumbValue = $crumb.crumb
Write-Host "Crumb field: $crumbField"
Write-Host "Crumb value: $crumbValue"

Write-Host "`n=== 2. Update Job Config ==="
$result = & curl.exe -s -w "`nHTTP: %{http_code}" -u $Auth -X POST `
    -H "Content-Type: application/xml" `
    -H "${crumbField}: ${crumbValue}" `
    --data-binary "@deploy/pipeline-config.xml" `
    "$JenkinsUrl/job/AI-Coding-Workspace/config.xml"
Write-Host $result

Write-Host "`n=== 3. Verify Job Type ==="
Start-Sleep 2
$jobInfo = & curl.exe -s -u $Auth "$JenkinsUrl/job/AI-Coding-Workspace/api/json"
Write-Host $jobInfo
