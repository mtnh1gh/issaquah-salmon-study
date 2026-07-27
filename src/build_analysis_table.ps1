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

function Mean-OrNull {
    param([object[]]$Values)
    $valid = @($Values | Where-Object { $null -ne $_ -and "$_" -ne "" })
    if ($valid.Count -eq 0) { return $null }
    return [math]::Round([double](($valid | Measure-Object -Average).Average), 3)
}

$master = foreach ($response in $returns) {
    $year = [int]$response.return_year
    $env = $environmentByYear[$year]
    if (-not $env) { throw "No environmental row for return year $year." }
    $cohortLag = if ($response.species -eq "Coho") { 2 } else { 4 }
    $cohortYear = $year - $cohortLag
    $cohortEnv = $environmentByYear[$cohortYear]
    if (-not $cohortEnv) {
        throw "No environmental row for $($response.species) cohort year $cohortYear."
    }
    $marineStartYear = $cohortYear + 1
    $marineYears = @($marineStartYear..($year - 1))
    $marinePdo = @($marineYears | ForEach-Object {
        $marineEnv = $environmentByYear[$_]
        if ($marineEnv) { $marineEnv.pdo_annual_mean }
    })

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
        cohort_lag_years = $cohortLag
        cohort_environment_year = $cohortYear
        cohort_flow_water_year_mean_cfs = $cohortEnv.flow_water_year_mean_cfs
        cohort_flow_jul_sep_mean_cfs = $cohortEnv.flow_jul_sep_mean_cfs
        cohort_swe_apr01_inches = $cohortEnv.swe_apr01_inches
        cohort_temp_jun_sep_mean_c = $cohortEnv.temp_jun_sep_mean_c
        marine_pdo_mean = Mean-OrNull $marinePdo
        marine_pdo_start_year = $marineStartYear
        marine_pdo_end_year = $year - 1
        impervious_pct = $null
        hatchery_releases = $null
        response_value_status = "derived_from_observed_events"
        environmental_value_status = "derived_from_observed_measurements"
        impervious_value_status = "not_available"
        releases_value_status = "not_available"
        response_source = "WDFW Hatchery Adult Salmon Returns; Trap Estimate events"
        environmental_sources = "USGS-12121600-DV-00060; NRCS-SNOTEL-788-WTEQ; NOAA-PDO-ERSSTV5; KINGCOUNTY-ISSAQUAH-TEMP"
        lag_definition = if ($response.species -eq "Coho") {
            "primary cohort proxy: return_year - 2"
        } else {
            "primary cohort proxy: return_year - 4; sensitivity lags 3 and 5 required"
        }
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
