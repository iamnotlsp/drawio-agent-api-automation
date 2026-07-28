param(
    [string]$BaseUrl = "http://127.0.0.1:8091",
    [string]$GroupBuyBaseUrl = "http://127.0.0.1:8092"
)

$ErrorActionPreference = "Stop"

python -m pytest `
    --base-url $BaseUrl `
    --group-buy-base-url $GroupBuyBaseUrl `
    --alluredir "allure-results" `
    --clean-alluredir `
    -v

if ($LASTEXITCODE -ne 0) {
    throw "pytest failed with exit code: $LASTEXITCODE"
}

allure generate "allure-results" `
    --clean `
    --output "docs"

if ($LASTEXITCODE -ne 0) {
    throw "Allure generation failed with exit code: $LASTEXITCODE"
}

$escapedUserProfile = $env:USERPROFILE.Replace("\", "\\")

Get-ChildItem -LiteralPath "docs" `
    -Recurse `
    -Filter "*.json" | ForEach-Object {
        $content = [System.IO.File]::ReadAllText(
            $_.FullName
        )
        $sanitized = $content.Replace(
            $escapedUserProfile,
            "%USERPROFILE%"
        ).Replace(
            $env:USERPROFILE,
            "%USERPROFILE%"
        )

        if ($sanitized -ne $content) {
            [System.IO.File]::WriteAllText(
                $_.FullName,
                $sanitized,
                [System.Text.UTF8Encoding]::new($false)
            )
        }
    }

Write-Host "Allure report generated: docs/index.html"
