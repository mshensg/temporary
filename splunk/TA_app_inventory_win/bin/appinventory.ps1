$SPLUNK_HOME=if ($env:SPLUNK_HOME -eq $null){if (Test-Path "C:\Program Files\SplunkUniversalForwarder"){"C:\Program Files\SplunkUniversalForwarder"} else {"C:\Program Files (x86)\SplunkUniversalForwarder"} } else {$env:SPLUNK_HOME}

$splunk_configuration_folder="etc/apps"
$splunk_system_local_folder="etc/system/local"

$app_folder=Join-path $SPLUNK_HOME $splunk_configuration_folder
$sys_folder=Join-path $SPLUNK_HOME $splunk_system_local_folder

$exclusion_apps=@("introspection_generator_addon",
"journald_input",
"learned",
"search",
"SplunkUniversalForwarder",
"splunk_httpinput",
"splunk_internal_metrics")

$splunk_applications=Get-ChildItem $app_folder -Directory | Where-Object {$_.Name -notin $exclusion_apps}
$splunk_applications += (Get-Item $sys_folder)

$t=Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"

ForEach($p in $splunk_applications)
{
    $filelist=@()
    #$filecontent=@{}
    $filecontent=@()
    $conffiles = Get-ChildItem -Name *.conf -Path $p.FullName -Recurse -File | ForEach-Object {Join-Path $p.FullName $_}
    ForEach($fl in $conffiles)
    {
        $content=((Get-Content $fl) | Out-String)
        $filelist += $fl
        #$filecontent[$fl]=$content #output dict
        $filecontent += @{$fl=$content}
    }
    $result=@{_timestamp=$t;
        application=$p.FullName;
        filelist=$filelist;
        filecontent=$filecontent
    }
    Write-Output ($result | ConvertTo-Json -Compress -Depth 20)
}
