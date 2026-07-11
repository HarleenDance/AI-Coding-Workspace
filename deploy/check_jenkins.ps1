try {
    $r = Invoke-WebRequest -Uri 'http://localhost:8080/' -UseBasicParsing -TimeoutSec 5
    Write-Host "Jenkins HTTP status: $($r.StatusCode)"
} catch {
    Write-Host "Jenkins check failed: $($_.Exception.Message)"
}
