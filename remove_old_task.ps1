$oldTasks = @('BrokerTracker_1500', 'BrokerTracker_1730')

foreach ($taskName in $oldTasks) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed $taskName"
    }
}
