Write-Host "Inizializzazione del workspace Lidarino su Windows (Isaac Sim + Pixi)..." -ForegroundColor Green

# Verifica che l'ambiente Pixi sia attivo
if (-not (Get-Command ros2 -ErrorAction SilentlyContinue)) {
    Write-Host "ERRORE: ros2 non trovato. Esegui questo script dentro 'pixi shell'." -ForegroundColor Red
    exit 1
}

# Verifica che Nav2 sia disponibile
$nav2Check = ros2 pkg list 2>$null | Select-String "nav2_bringup"
if (-not $nav2Check) {
    Write-Host "ATTENZIONE: nav2_bringup non trovato nell'ambiente Pixi." -ForegroundColor Yellow
    Write-Host "Verifica la configurazione di pixi.toml." -ForegroundColor Yellow
}

Write-Host "Build del workspace..." -ForegroundColor Cyan
colcon build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Setup completato con successo!" -ForegroundColor Green
    Write-Host "Ora puoi avviare la simulazione con: ros2 launch lidarino_bringup isaac.launch.py" -ForegroundColor Yellow
} else {
    Write-Host "ERRORE: il build ha fallito. Controlla i log sopra." -ForegroundColor Red
}