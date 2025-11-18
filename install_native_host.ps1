(Get-Content -Raw .\\_install_native_host.ps1) -replace "`r`n", "`n" -replace "`n", "`r`n" | Set-Content .\\_install_native_host.ps1; & .\\_install_native_host.ps1 @args
