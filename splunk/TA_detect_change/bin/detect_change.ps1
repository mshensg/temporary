$SPLUNK_HOME = if ($env:SPLUNK_HOME -eq $null){"C:\Program Files\SplunkUniversalForwarder"} else {$env:SPLUNK_HOME}
$omit="splunkforwarder"
$splunk_configuration_folder = Join-path $SPLUNK_HOME "etc/apps"
$manifest = (Get-ChildItem -Path $SPLUNK_HOME -Filter *manifest -File).FullName | Sort-Object -Descending | Select-Object -First 1
$manifestData = Get-Content $manifest
$manifestList = @{}

foreach($i in $manifestData)
{
    $fields = $i.split(" ")
    if($fields.length -eq 6 -and $fields[5] -ne "-")
    {
        $checkfile=$fields[4]
        $checkfile=$checkfile.TrimStart($omit)
        $checkfile=Join-Path $SPLUNK_HOME $checkfile
        $manifestList[$checkfile]=$fields[5].trim()
    }
}

$filestocheck = (Get-ChildItem -Path $splunk_configuration_folder -Filter *.conf -File -Recurse).FullName
#$t=Get-Date -UFormat %s
#$t=(Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "T" + (Get-Date -Format "zzz") -replace ":",""
$t=Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff zzz"

foreach($file in $filestocheck)
{
    $hashsha256 = (Get-FileHash -Path $file -Algorithm SHA256).Hash
    $hashmd5 = (Get-FileHash -Path $file -Algorithm MD5).Hash
    if(-not $manifestList.ContainsKey($file))
    {
        $type="added"
    }elseif($manifestList[$file] -eq $hashsha256){
        $type="intact"
    }else{
        $type="modified"
    }
    $outObj = "" | Select-Object checktime, filename, sha256hash, md5hash, type
    $outObj.checktime = $t
    $outObj.filename = $file
    $outObj.sha256hash = $hashsha256
    $outObj.md5hash = $hashmd5
    $outObj.type = $type
    $outObj | Where-Object type -ne "intact" | ConvertTo-Json -Compress| Write-Output 
}
