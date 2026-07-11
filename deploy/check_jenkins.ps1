$JenkinsUrl = "http://localhost:8080"
$Username = "chenzemian"
$ApiToken = "112d6dd20984e37c247625bf097fe6223f"

# 用 curl.exe 测试连接
Write-Host "=== Testing Jenkins with curl.exe ==="
& curl.exe -s -o NUL -w "HTTP status: %{http_code}`n" -u "${Username}:${ApiToken}" "$JenkinsUrl/api/json?tree=mode"
