param(
    [string]$InputPath = "data/bronze/wdfw/2026-07-19/wdfw_issaquah_hatchery_chinook_coho_adult_return_events.csv",
    [string]$OutputPath = "data/silver/wdfw_issaquah_annual_returns.csv"
)

$ErrorActionPreference = "Stop"

function Sum-Field {
    param([object[]]$Rows, [string]$Field)
    if (-not $Rows -or $Rows.Count -eq 0) {
        return 0
    }
    return [int](($Rows | Measure-Object -Property $Field -Sum).Sum)
}

$rows = Import-Csv -LiteralPath $InputPath
$trapRows = @($rows | Where-Object { $_.event -eq "Trap Estimate" })

if ($trapRows.Count -eq 0) {
    throw "No Trap Estimate rows found in $InputPath"
}
if (@($trapRows | Where-Object { $_.species -notin @("Chinook", "Coho") }).Count -gt 0) {
    throw "Unexpected species found in Trap Estimate records."
}
if (@($trapRows | Where-Object { $_.origin -notin @("HATCHERY", "WILD") }).Count -gt 0) {
    throw "Unexpected origin found in Trap Estimate records."
}

$annual = $trapRows |
    Group-Object { ([datetime]$_.date).Year }, species |
    ForEach-Object {
        $group = @($_.Group)
        $hatchery = @($group | Where-Object { $_.origin -eq "HATCHERY" })
        $wild = @($group | Where-Object { $_.origin -eq "WILD" })
        $hatcheryAdults = Sum-Field $hatchery "adult_count"
        $wildAdults = Sum-Field $wild "adult_count"
        $hatcheryJacks = Sum-Field $hatchery "jack_count"
        $wildJacks = Sum-Field $wild "jack_count"
        $ordered = @($group | Sort-Object { [datetime]$_.date })

        [pscustomobject][ordered]@{
            return_year = ([datetime]$group[0].date).Year
            species = $group[0].species
            hatchery_adults = $hatcheryAdults
            wild_adults = $wildAdults
            total_adults = $hatcheryAdults + $wildAdults
            hatchery_jacks = $hatcheryJacks
            wild_jacks = $wildJacks
            total_jacks = $hatcheryJacks + $wildJacks
            adult_plus_jacks = $hatcheryAdults + $wildAdults + $hatcheryJacks + $wildJacks
            trap_event_rows = $group.Count
            first_trap_event = ([datetime]$ordered[0].date).ToString("yyyy-MM-dd")
            last_trap_event = ([datetime]$ordered[-1].date).ToString("yyyy-MM-dd")
            response_definition = "sum Trap Estimate adult_count across HATCHERY and WILD origins; jacks retained separately"
        }
    } |
    Sort-Object return_year, species

# Published WDFW figures used as executable reconciliation checks.
$checks = @(
    @{ Year = 2016; Species = "Chinook"; HatcheryAdults = 2442; WildAdults = 154 },
    @{ Year = 2025; Species = "Chinook"; HatcheryAdults = 4562; WildAdults = 154 },
    @{ Year = 2025; Species = "Coho"; HatcheryAdults = 3647; WildAdults = 212 }
)
foreach ($check in $checks) {
    $row = $annual | Where-Object {
        $_.return_year -eq $check.Year -and $_.species -eq $check.Species
    }
    if (
        -not $row -or
        $row.hatchery_adults -ne $check.HatcheryAdults -or
        $row.wild_adults -ne $check.WildAdults
    ) {
        throw "WDFW reconciliation failed for $($check.Year) $($check.Species)."
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
$annual | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Encoding utf8

Write-Host "Wrote $($annual.Count) annual species records to $OutputPath"
Write-Host "Coverage: $($annual[0].return_year)-$($annual[-1].return_year); 1995-1996 have no Trap Estimate records."
