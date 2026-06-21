$ErrorActionPreference = "Stop"

$body = @{
  query = "CUSB hostel facility kya hai?"
  filters = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8080/api/chat" -Method POST -ContentType "application/json" -Body $body

