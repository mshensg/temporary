$lastSystem=Get-EventLog -LogName System -Newest 1
$lastSecurity=Get-EventLog -LogName Security -Newest 1

$currentTime=Get-Date

$outObj = "" | Select-Object currenttimeepoch, currenttime, lastsystemevent, lastsecurityevent
$outObj.currenttimeepoch = Get-Date -Date $currentTime -UFormat "%s"
$outObj.currenttime=Get-Date -Date $currentTime -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
$outObj.lastsecurityevent=($lastSecurity | Select-Object TimeGenerated,TimeGeneratedReadable,TimeWritten,TimeWrittenReadable,MachineName,CategoryNumber,EventID,EntryType,Message,Source,ReplacementStrings)
$outObj.lastsystemevent=($lastSystem | Select-Object TimeGenerated,TimeGeneratedReadable,TimeWritten,TimeWrittenReadable,MachineName,CategoryNumber,EventID,EntryType,Message,Source,ReplacementStrings)

$outObj.lastsecurityevent.TimeGeneratedReadable=Get-Date -Date $outObj.lastsecurityevent.TimeGenerated -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
$outObj.lastsecurityevent.TimeWrittenReadable=Get-Date -Date $outObj.lastsecurityevent.TimeWritten -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
$outObj.lastsystemevent.TimeGeneratedReadable=Get-Date -Date $outObj.lastsystemevent.TimeGenerated -Format "yyyy-MM-dd HH:mm:ss.fff zzz"
$outObj.lastsystemevent.TimeWrittenReadable=Get-Date -Date $outObj.lastsystemevent.TimeWritten -Format "yyyy-MM-dd HH:mm:ss.fff zzz"

$outObj | ConvertTo-Json -Compress | Write-Output
