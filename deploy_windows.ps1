# === НАСТРОЙКИ ===
$repoUrl = "https://github.com/VSZ2020/WeatherAggregator.git"
$baseDir = "C:\deploy"
$releasesDir = "$baseDir\releases"
$currentLink = "$baseDir\current"
$logFile = "$baseDir\deploy.log"
# $telegramBotToken = "your_bot_token"
# $telegramChatId = "your_chat_id"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$newRelease = "$releasesDir\release_$timestamp"

function Log($msg) {
    $entry = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg
    $entry | Tee-Object -Append -FilePath $logFile
}

# function Send-Telegram($text) {
#     Invoke-RestMethod -Uri "https://api.telegram.org/bot$telegramBotToken/sendMessage" `
#         -Method Post -Body @{
#             chat_id = $telegramChatId
#             text    = $text
#         } | Out-Null
# }

Log "[*] Начало деплоя: $timestamp"
Send-Telegram "🚀 Деплой запущен: $timestamp"

# === Определяем свободный порт ===
$nginxConfig = Get-Content "C:\nginx\conf\fastapi.conf"
if ($nginxConfig -match "127.0.0.1:8001") {
    $newPort = 8002
    $oldPort = 8001
} else {
    $newPort = 8001
    $oldPort = 8002
}

# === Клонирование проекта ===
Log "[*] Клонируем репозиторий..."
git clone $repoUrl $newRelease

# === Виртуальное окружение ===
Log "[*] Создаём виртуальное окружение..."
python -m venv "$newRelease\venv"
& "$newRelease\venv\Scripts\Activate.ps1"
pip install --upgrade pip
pip install -r "$newRelease\requirements.txt"

# === Запуск нового экземпляра ===
Log "[*] Запуск на порту $newPort"
$mainScript = "$newRelease\main.py"
$logPath = "$newRelease\uvicorn.log"
$pidFile = "$newRelease\uvicorn.pid"

Start-Process `
    -FilePath "$newRelease\venv\Scripts\python.exe" `
    -ArgumentList "-m uvicorn main:app --host 127.0.0.1 --port $newPort" `
    -WorkingDirectory $newRelease `
    -RedirectStandardOutput $logPath `
    -RedirectStandardError $logPath `
    -PassThru | ForEach-Object { $_.Id | Out-File $pidFile -Encoding ascii }

# === Обновление nginx-конфига ===
Log "[*] Переключение nginx на порт $newPort"
(gc "C:\nginx\conf\fastapi.conf") -replace "127.0.0.1:$oldPort", "127.0.0.1:$newPort" | Set-Content "C:\nginx\conf\fastapi.conf"
Start-Process -FilePath "nginx.exe" -ArgumentList "-s reload" -WorkingDirectory "C:\nginx" -NoNewWindow -Wait

# === Обновляем симлинк (если есть junction) ===
if (Test-Path $currentLink) {
    Remove-Item $currentLink -Force
}
cmd /c mklink /J "$currentLink" "$newRelease" | Out-Null

# === Остановка старого процесса ===
$oldRelease = Get-ChildItem "$releasesDir" | Sort-Object LastWriteTime -Descending | Select-Object -Skip 1 -First 1
$oldPidFile = "$($oldRelease.FullName)\uvicorn.pid"

if (Test-Path $oldPidFile) {
    $oldPid = Get-Content $oldPidFile
    try {
        Stop-Process -Id $oldPid -Force
        Log "[*] Остановлен процесс $oldPid"
        Remove-Item $oldPidFile
    } catch {
        Log "⚠️ Не удалось остановить PID $oldPid"
    }
}

# === Очистка старых релизов (> 7 дней) ===
Log "[*] Удаляем старые релизы"
Get-ChildItem $releasesDir | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Recurse -Force

Log "[✓] Деплой завершён: порт $newPort"
# Send-Telegram "✅ Деплой завершён на порту $newPort`nПапка: $newRelease"
