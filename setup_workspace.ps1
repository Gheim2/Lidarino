Write-Host "Inizializzazione del workspace Lidarino su Windows (Pixi)..." -ForegroundColor Green

# 1. Scarica le dipendenze esterne
Write-Host "Scaricamento delle repository esterne..." -ForegroundColor Cyan
vcs import src --input lidarino.repos

# 2. Inserisce il blocco per il pacchetto non desiderato
Write-Host "Esclusione di multirobot_map_merge..." -ForegroundColor Cyan
$ignorePath = "src\m-explore-ros2\map_merge\COLCON_IGNORE"
if (!(Test-Path $ignorePath)) {
    New-Item -ItemType File -Path $ignorePath -Force | Out-Null
}

Write-Host "Setup completato! Le dipendenze di sistema sono gestite da Pixi." -ForegroundColor Green
Write-Host "Ora puoi eseguire 'pixi run build'" -ForegroundColor Yellow