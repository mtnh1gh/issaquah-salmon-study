param(
    [string]$ReturnsPath = "data/processed/wdfw_issaquah_annual_returns.csv",
    [string]$EnvironmentPath = "data/processed/issaquah_annual_environment.csv",
    [string]$MasterPath = "data/processed/issaquah_creek_master.csv",
    [string]$FeatureRegistryPath = "docs/feature_registry.csv",
    [string]$ReportPath = "docs/data_validation_report.md"
)

$ErrorActionPreference = "Stop"
$results = [System.Collections.Generic.List[object]]::new()

function Add-Check {
    param(
        [string]$Category,
        [string]$Check,
        [string]$Severity,
        [bool]$Passed,
        [string]$Details
    )
    $script:results.Add([pscustomobject]@{
        Category = $Category
        Check = $Check
        Severity = $Severity
        Passed = $Passed
        Details = $Details
    })
}

function Has-Columns {
    param([object]$Row, [string[]]$Required)
    $actual = @($Row.PSObject.Properties.Name)
    return @($Required | Where-Object { $_ -notin $actual }).Count -eq 0
}

$returns = @(Import-Csv -LiteralPath $ReturnsPath)
$environment = @(Import-Csv -LiteralPath $EnvironmentPath)
$master = @(Import-Csv -LiteralPath $MasterPath)
$features = @(Import-Csv -LiteralPath $FeatureRegistryPath)

$requiredMaster = @(
    "return_year", "species", "hatchery_adults", "wild_adults", "total_adults",
    "total_jacks", "adult_plus_jacks", "flow_water_year_mean_cfs",
    "flow_jul_sep_mean_cfs", "flow_jul_sep_min_cfs", "swe_apr01_inches",
    "pdo_annual_mean", "temp_jun_sep_mean_c", "cohort_lag_years",
    "cohort_environment_year", "cohort_flow_water_year_mean_cfs",
    "cohort_swe_apr01_inches", "cohort_temp_jun_sep_mean_c", "marine_pdo_mean",
    "impervious_pct", "hatchery_releases", "response_value_status",
    "environmental_value_status", "impervious_value_status",
    "releases_value_status", "response_source", "environmental_sources",
    "lag_definition"
)
Add-Check "Schema" "Required master columns" "Critical" `
    (Has-Columns $master[0] $requiredMaster) `
    "Required columns: $($requiredMaster.Count)"

$duplicateMaster = @($master | Group-Object return_year, species | Where-Object Count -gt 1)
Add-Check "Keys" "Unique return_year/species" "Critical" `
    ($duplicateMaster.Count -eq 0) `
    "Duplicate groups: $($duplicateMaster.Count)"

$species = @($master.species | Sort-Object -Unique)
$years = @($master.return_year | ForEach-Object { [int]$_ } | Sort-Object -Unique)
Add-Check "Coverage" "Expected species and years" "Critical" `
    ($species.Count -eq 2 -and "Chinook" -in $species -and "Coho" -in $species -and
        $years.Count -eq 29 -and $years[0] -eq 1997 -and $years[-1] -eq 2025) `
    "Species: $($species -join ', '); years: $($years[0])-$($years[-1]) ($($years.Count))"

Add-Check "Coverage" "Expected row counts" "Critical" `
    ($returns.Count -eq 58 -and $environment.Count -eq 34 -and $master.Count -eq 58) `
    "Returns=$($returns.Count); environment=$($environment.Count); master=$($master.Count)"

$negativeCounts = @($master | Where-Object {
    [int]$_.hatchery_adults -lt 0 -or [int]$_.wild_adults -lt 0 -or
    [int]$_.total_jacks -lt 0
})
Add-Check "Range" "Non-negative fish counts" "Critical" `
    ($negativeCounts.Count -eq 0) "Invalid rows: $($negativeCounts.Count)"

$badPhysical = @($master | Where-Object {
    [double]$_.flow_jul_sep_min_cfs -lt 0 -or
    [double]$_.flow_jul_sep_mean_cfs -lt [double]$_.flow_jul_sep_min_cfs -or
    [double]$_.swe_apr01_inches -lt 0 -or
    [double]$_.temp_jun_sep_mean_c -lt 0 -or [double]$_.temp_jun_sep_mean_c -gt 30
})
Add-Check "Range" "Environmental physical bounds" "Critical" `
    ($badPhysical.Count -eq 0) "Invalid rows: $($badPhysical.Count)"

$badAdultTotals = @($master | Where-Object {
    [int]$_.total_adults -ne ([int]$_.hatchery_adults + [int]$_.wild_adults) -or
    [int]$_.adult_plus_jacks -ne ([int]$_.total_adults + [int]$_.total_jacks)
})
Add-Check "Reconciliation" "Response component equations" "Critical" `
    ($badAdultTotals.Count -eq 0) "Invalid rows: $($badAdultTotals.Count)"

$publishedChecks = @(
    @{ Year = 2016; Species = "Chinook"; H = 2442; W = 154 },
    @{ Year = 2025; Species = "Chinook"; H = 4562; W = 154 },
    @{ Year = 2025; Species = "Coho"; H = 3647; W = 212 }
)
$publishedFailures = @($publishedChecks | Where-Object {
    $check = $_
    $row = $master | Where-Object {
        [int]$_.return_year -eq $check.Year -and $_.species -eq $check.Species
    }
    -not $row -or [int]$row.hatchery_adults -ne $check.H -or [int]$row.wild_adults -ne $check.W
})
Add-Check "Reconciliation" "Published WDFW checks" "Critical" `
    ($publishedFailures.Count -eq 0) "Failures: $($publishedFailures.Count)"

$badLags = @($master | Where-Object {
    $expected = if ($_.species -eq "Coho") { 2 } else { 4 }
    [int]$_.cohort_lag_years -ne $expected -or
    [int]$_.cohort_environment_year -ne ([int]$_.return_year - $expected) -or
    [int]$_.marine_pdo_start_year -ne ([int]$_.cohort_environment_year + 1) -or
    [int]$_.marine_pdo_end_year -ne ([int]$_.return_year - 1)
})
Add-Check "Temporal" "Protocol cohort and marine alignment" "Critical" `
    ($badLags.Count -eq 0) "Invalid rows: $($badLags.Count)"

$missingCore = @($master | Where-Object {
    @(
        $_.total_adults, $_.flow_water_year_mean_cfs, $_.flow_jul_sep_mean_cfs,
        $_.swe_apr01_inches, $_.pdo_annual_mean, $_.temp_jun_sep_mean_c,
        $_.cohort_flow_water_year_mean_cfs, $_.cohort_swe_apr01_inches,
        $_.cohort_temp_jun_sep_mean_c, $_.marine_pdo_mean
    ) -contains ""
})
Add-Check "Missingness" "No missing core values" "Critical" `
    ($missingCore.Count -eq 0) "Rows with missing core values: $($missingCore.Count)"

$blockedFieldsCorrect = @($master | Where-Object {
    $_.impervious_pct -ne "" -or $_.hatchery_releases -ne "" -or
    $_.impervious_value_status -ne "not_available" -or
    $_.releases_value_status -ne "not_available"
}).Count -eq 0
Add-Check "Missingness" "Blocked fields are blank and flagged" "Critical" `
    $blockedFieldsCorrect "Checked impervious_pct and hatchery_releases on $($master.Count) rows"

$badTempCoverage = @($master | Where-Object { [int]$_.temp_jun_sep_samples -lt 4 })
Add-Check "Coverage" "Temperature sample threshold" "Critical" `
    ($badTempCoverage.Count -eq 0) "Rows below four samples: $($badTempCoverage.Count)"

$badProvenance = @($master | Where-Object {
    [string]::IsNullOrWhiteSpace($_.response_source) -or
    [string]::IsNullOrWhiteSpace($_.environmental_sources) -or
    $_.response_value_status -ne "derived_from_observed_events" -or
    $_.environmental_value_status -ne "derived_from_observed_measurements"
})
Add-Check "Provenance" "Source and value-status fields" "Critical" `
    ($badProvenance.Count -eq 0) "Invalid rows: $($badProvenance.Count)"

$requiredFeatureFields = @(
    "feature_id", "name", "description", "response_or_predictor", "species",
    "source_id", "raw_fields", "spatial_unit", "temporal_aggregation",
    "life_stage", "lag_definition", "units", "transformation",
    "missing_data_rule", "value_status", "leakage_risk",
    "included_in_model", "rationale"
)
$featureIdsUnique = @($features | Group-Object feature_id | Where-Object Count -gt 1).Count -eq 0
Add-Check "Registry" "Feature registry contract" "Critical" `
    ((Has-Columns $features[0] $requiredFeatureFields) -and $featureIdsUnique -and $features.Count -ge 13) `
    "Features registered: $($features.Count); duplicate IDs: $(-not $featureIdsUnique)"

$criticalFailures = @($results | Where-Object { $_.Severity -eq "Critical" -and -not $_.Passed })
$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
$gateDecision = if ($criticalFailures.Count -eq 0) {
    "**PASS.** Phase 2 validation has no critical failures. The dataset may proceed to exploratory analysis under the locked protocol."
} else {
    "**FAIL.** $($criticalFailures.Count) critical check(s) failed. Exploratory analysis is blocked."
}
$lines = @(
    "# Data validation report",
    "",
    "Generated: $timestamp",
    "",
    "Inputs are cached local snapshots; no live API was used.",
    "",
    "| Category | Check | Severity | Result | Details |",
    "|---|---|---|---|---|"
)
foreach ($result in $results) {
    $status = if ($result.Passed) { "PASS" } else { "FAIL" }
    $details = $result.Details.Replace("|", "\|")
    $lines += "| $($result.Category) | $($result.Check) | $($result.Severity) | $status | $details |"
}
$lines += @(
    "",
    "## Gate decision",
    "",
    $gateDecision,
    "",
    "Known unavailable fields remain `impervious_pct` and `hatchery_releases`; both are blank and explicitly flagged rather than imputed."
)
Set-Content -LiteralPath $ReportPath -Value $lines -Encoding utf8

if ($criticalFailures.Count -gt 0) {
    $criticalFailures | Format-Table -AutoSize
    throw "Phase 2 validation failed with $($criticalFailures.Count) critical error(s)."
}
Write-Host "Phase 2 validation passed: $($results.Count) checks, 0 critical failures."
