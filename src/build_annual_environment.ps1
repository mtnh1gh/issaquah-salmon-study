param(
    [string]$ReturnsPath = "data/silver/wdfw_issaquah_annual_returns.csv",
    [string]$UsgsPath = "data/bronze/usgs/2026-07-19/usgs_12121600_daily_discharge_1986-10-01_2025-09-30.json",
    [string]$SnotelPath = "data/bronze/nrcs/2026-07-19/nrcs_snotel_788_stampede_pass_daily_swe_1980-04-01_2025-04-01.csv",
    [string]$PdoPath = "data/bronze/noaa/2026-07-19/noaa_pdo_ersstv5.csv",
    [string]$TemperaturePath = "data/bronze/king_county/2026-07-19/king_county_issaquah_creek_temperature_grab_samples.csv",
    [string]$OutputPath = "data/silver/issaquah_annual_environment.csv"
)

$ErrorActionPreference = "Stop"

function Mean-OrNull {
    param([object[]]$Values)
    $valid = @($Values | Where-Object { $null -ne $_ -and "$_" -ne "" })
    if ($valid.Count -eq 0) { return $null }
    return [math]::Round([double](($valid | Measure-Object -Average).Average), 3)
}

function Min-OrNull {
    param([object[]]$Values)
    $valid = @($Values | Where-Object { $null -ne $_ -and "$_" -ne "" })
    if ($valid.Count -eq 0) { return $null }
    return [math]::Round([double](($valid | Measure-Object -Minimum).Minimum), 3)
}

$responseYears = @(Import-Csv -LiteralPath $ReturnsPath |
    ForEach-Object { [int]$_.return_year } |
    Sort-Object -Unique)
# Extend five years before the response series so pre-specified Chinook cohort
# lags do not lose otherwise usable adult-return years.
$years = (($responseYears[0] - 5)..$responseYears[-1])

# USGS daily discharge. Water year Y runs from October Y-1 through September Y.
$usgsJson = Get-Content -Raw -LiteralPath $UsgsPath | ConvertFrom-Json
$flow = @($usgsJson.value.timeSeries[0].values[0].value | ForEach-Object {
    $date = [datetime]$_.dateTime
    [pscustomobject]@{
        date = $date
        water_year = if ($date.Month -ge 10) { $date.Year + 1 } else { $date.Year }
        value = [double]$_.value
        qualifier = ($_.qualifiers -join ";")
    }
})

# NRCS file has metadata comments before the CSV header.
$snotelLines = Get-Content -LiteralPath $SnotelPath
$headerIndex = 0
while ($headerIndex -lt $snotelLines.Count -and -not $snotelLines[$headerIndex].StartsWith("Date,")) {
    $headerIndex++
}
if ($headerIndex -ge $snotelLines.Count) { throw "NRCS CSV header not found." }
$swe = @(($snotelLines[$headerIndex..($snotelLines.Count - 1)] -join [Environment]::NewLine) |
    ConvertFrom-Csv |
    ForEach-Object {
        $valueText = $_.'Snow Water Equivalent (in) Start of Day Values'
        [pscustomobject]@{
            date = [datetime]$_.Date
            value = if ([string]::IsNullOrWhiteSpace($valueText)) { $null } else { [double]$valueText }
        }
    })

$pdoRows = @(Import-Csv -LiteralPath $PdoPath)
$pdoValueColumn = @($pdoRows[0].PSObject.Properties.Name | Where-Object { $_ -ne "Date" })[0]
$pdo = @($pdoRows | ForEach-Object {
    $value = [double]($_.$pdoValueColumn)
    [pscustomobject]@{
        date = [datetime]$_.Date
        value = if ($value -eq -9999) { $null } else { $value }
    }
})

# SE 56th St is selected because it has uninterrupted June-September sampling
# throughout the 1997-2025 response period; the upstream site has a 2009-2012 gap.
$temperature = @(Import-Csv -LiteralPath $TemperaturePath |
    Where-Object { $_.site -eq "Issaquah Creek at SE 56th St" } |
    ForEach-Object {
        [pscustomobject]@{
            date = [datetime]$_.collect_datetime
            value = [double]$_.value
        }
    })

$output = foreach ($year in $years) {
    $waterYearFlow = @($flow | Where-Object { $_.water_year -eq $year })
    $summerFlow = @($flow | Where-Object {
        $_.date.Year -eq $year -and $_.date.Month -in @(7, 8, 9)
    })
    $aprilSwe = @($swe | Where-Object {
        $_.date.Year -eq $year -and $_.date.Month -eq 4 -and $_.date.Day -eq 1
    })
    $annualPdo = @($pdo | Where-Object { $_.date.Year -eq $year })
    $summerTemperature = @($temperature | Where-Object {
        $_.date.Year -eq $year -and $_.date.Month -in @(6, 7, 8, 9)
    })

    [pscustomobject][ordered]@{
        return_year = $year
        flow_water_year_mean_cfs = Mean-OrNull @($waterYearFlow.value)
        flow_water_year_days = $waterYearFlow.Count
        flow_jul_sep_mean_cfs = Mean-OrNull @($summerFlow.value)
        flow_jul_sep_min_cfs = Min-OrNull @($summerFlow.value)
        flow_jul_sep_days = $summerFlow.Count
        swe_apr01_inches = if ($aprilSwe.Count -eq 1) { $aprilSwe[0].value } else { $null }
        pdo_annual_mean = Mean-OrNull @($annualPdo.value)
        pdo_months = @($annualPdo | Where-Object { $null -ne $_.value }).Count
        temp_jun_sep_mean_c = Mean-OrNull @($summerTemperature.value)
        temp_jun_sep_samples = $summerTemperature.Count
        temp_station = "King County 0631; Issaquah Creek at SE 56th St; grab samples"
    }
}

$badFlow = @($output | Where-Object {
    $_.return_year -lt 2025 -and ($_.flow_water_year_days -lt 365 -or $_.flow_jul_sep_days -lt 92)
})
if ($badFlow.Count -gt 0) { throw "Unexpected incomplete USGS years: $($badFlow.return_year -join ', ')" }
$badTemperature = @($output | Where-Object {
    $_.return_year -in $responseYears -and $_.temp_jun_sep_samples -lt 4
})
if ($badTemperature.Count -gt 0) {
    throw "Temperature coverage rule failed for: $($badTemperature.return_year -join ', ')"
}

$outputDirectory = Split-Path -Parent $OutputPath
if ($outputDirectory) {
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
}
$output | Export-Csv -LiteralPath $OutputPath -NoTypeInformation -Encoding utf8
Write-Host "Wrote $($output.Count) annual environmental records to $OutputPath"
