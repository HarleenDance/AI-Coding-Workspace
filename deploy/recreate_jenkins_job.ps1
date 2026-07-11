$JenkinsUrl = "http://localhost:8080"
$Auth = "chenzemian:112d6dd20984e37c247625bf097fe6223f"
$CookieJar = "$env:TEMP\jenkins-cookies.txt"

Write-Host "=== 1. Delete old FreeStyle job ==="
# 获取 crumb（带 cookie jar）
$crumbJson = & curl.exe -s -c $CookieJar -u $Auth "$JenkinsUrl/crumbIssuer/api/json"
$crumb = ($crumbJson | ConvertFrom-Json)
$crumbField = $crumb.crumbRequestField
$crumbValue = $crumb.crumb
Write-Host "Crumb: $crumbValue"

$delResult = & curl.exe -s -w "%{http_code}" -b $CookieJar -c $CookieJar -u $Auth -X POST -H "${crumbField}: ${crumbValue}" "$JenkinsUrl/job/AI-Coding-Workspace/doDelete"
Write-Host "Delete result: $delResult"

Write-Host "`n=== 2. Create new Pipeline job ==="
# 重新获取 crumb
$crumbJson2 = & curl.exe -s -b $CookieJar -c $CookieJar -u $Auth "$JenkinsUrl/crumbIssuer/api/json"
$crumb2 = ($crumbJson2 | ConvertFrom-Json)
$crumbValue2 = $crumb2.crumb
Write-Host "New crumb: $crumbValue2"

$createResult = & curl.exe -s -w "`nHTTP: %{http_code}" -b $CookieJar -c $CookieJar -u $Auth -X POST `
    -H "Content-Type: application/xml" `
    -H "$($crumb2.crumbRequestField): $crumbValue2" `
    --data-binary "@deploy/pipeline-config.xml" `
    "$JenkinsUrl/createItem?name=AI-Coding-Workspace"
Write-Host $createResult

Write-Host "`n=== 3. Verify ==="
Start-Sleep 2
$jobInfo = & curl.exe -s -u $Auth "$JenkinsUrl/job/AI-Coding-Workspace/api/json?tree=_class,buildable"
Write-Host $jobInfo
