param(
    [string]$ReturnsPath = "data/processed/wdfw_issaquah_annual_returns.csv",
    [string]$EnvironmentPath = "data/processed/issaquah_annual_environment.csv",
    [string]$OutputPath = "data/processed/issaquah_creek_master.csv"
)

$ErrorActionPreference = "Stop"

$returns = Import-Csv -LiteralPath $ReturnsPath
$environment = Import-Csv -LiteralPath $EnvironmentPath
$environmentByYear = @{}
foreach ($row in $environment) {
    $environmentByYear[[int]$row.return_year] = $row
}

$master = foreach ($response in $returns) {
    $year = [int]$response.return_year
    $env = $environmentByYear[$year]
    if (-not $env) { throw "No environmental row for return year $year." }

    [pscustomobject][ordered]@{
        return_year = $year
        species = $response.species
        hatchery_adults = [int]$response.hatchery_adults
        wild_adults = [int]$response.wild_adults
        total_adults = [int]$response.total_adults
        hatchery_jacks = [int]$response.hatchery_jacks
        wild_jacks = [int]$response.wild_jacks
        total_jacks = [int]$response.total_jacks
        adult_plus_jacks = [int]$response.adult_plus_jacks
        flow_water_year_mean_cfs = $env.flow_water_year_mean_cfs
        flow_jul_sep_mean_cfs = $env.flow_jul_sep_mean_cfs
        flow_jul_sep_min_cfs = $env.flow_jul_sep_min_cfs
        swe_apr01_inches = $env.swe_apr01_inches
        pdo_annual_mean = $env.pdo_annual_mean
        temp_jun_sep_mean_c = $env.temp_jun_sep_mean_c
        temp_jun_sep_samples = [int]$env.temp_jun_sep_samples
        impervious_pct = $null
        hatchery_releases = $null
        response_source = "WDFW Hatchery Adult Salmon Returns; Trap Estimate events"
        environmental_source_status = "complete except imperviousness"
        release_source_status = "blocked: RMIS authorization or FISH export required"
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
$master | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Encoding utf8
Write-Host "Wrote $($master.Count) species-year records to $OutputPath"
