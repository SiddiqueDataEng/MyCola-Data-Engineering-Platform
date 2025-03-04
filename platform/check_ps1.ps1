$errors = $null
$null = [System.Management.Automation.Language.Parser]::ParseFile(
    'F:\siddi\clickstream_sales_analytics\platform\setup_clickhouse.ps1',
    [ref]$null,
    [ref]$errors
)
if ($errors.Count -eq 0) {
    Write-Host "PARSE OK"
} else {
    foreach ($e in $errors) { Write-Host $e.Message }
}
