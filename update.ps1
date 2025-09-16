[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Owner,
  [Parameter(Mandatory=$true)][string]$Repo,
  [string]$ChannelTag = "latest",
  [string]$Target = (Join-Path $env:USERPROFILE "NFE_Alert"),
  [string]$ZipNamePattern = "nfe_alert*.zip",
  [string]$ShaNamePattern = "nfe_alert*.zip.sha256",
  [string]$TempRoot = $env:TEMP,
  [switch]$Cleanup = $true,
  [switch]$Force = $false
)

# Detect if standard common parameter -Verbose was supplied
$isVerbose = $PSBoundParameters.ContainsKey('Verbose')

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Headers = @{ "User-Agent" = $env:COMPUTERNAME }

# Preferir token desde el archivo .env en el directorio del script o en el cwd.
# Si no se encuentra allí, como fallback se permite leer variables de entorno del sistema.
$token = $null
try {
  $scriptDir = Split-Path -Parent $PSCommandPath
} catch {
  # En entornos interactivos $PSCommandPath puede no existir; usar el directorio actual
  $scriptDir = (Get-Location).Path
}
$envPaths = @()
if ($scriptDir) {
  $envPaths += Join-Path -Path $scriptDir -ChildPath '.env'
}
$envPaths += Join-Path -Path (Get-Location).Path -ChildPath '.env'
foreach ($p in $envPaths) {
  if (Test-Path $p) {
    if ($isVerbose) { Write-Host "Leyendo .env desde: $p" }
    foreach ($line in Get-Content -Path $p -ErrorAction SilentlyContinue) {
      if ($line -match '^[\s]*GITHUB_TOKEN\s*=\s*(.+)$') {
        $v = $Matches[1].Trim()
        # Quitar comillas si existen
        if (($v.StartsWith("'") -and $v.EndsWith("'")) -or ($v.StartsWith('"') -and $v.EndsWith('"'))) {
          $v = $v.Substring(1, $v.Length - 2)
        }
        $token = $v
        break
      }
    }
    if ($token) { break }
  }
}

# Fallback a variables de entorno del sistema SOLO si no encontramos token en .env
if (-not $token) {
  if ($env:GITHUB_TOKEN) {
    if ($isVerbose) { Write-Host "Usando GITHUB_TOKEN desde variables de entorno del sistema (fallback)." }
    $token = $env:GITHUB_TOKEN
  } elseif ($env:GITHUB_PAT_NFE_UY) {
    if ($isVerbose) { Write-Host "Usando GITHUB_PAT_NFE_UY desde variables de entorno del sistema (fallback)." }
    $token = $env:GITHUB_PAT_NFE_UY
  }
}

if ($token) {
  $Headers["Authorization"] = "Bearer $token"
  if ($isVerbose) { Write-Host "Authorization header preparado (token detectado)." }
} else {
  if ($isVerbose) { Write-Host "No se detectó token GITHUB; se intentará descarga pública." }
}

# 1) Obtener release (latest o por tag)
$apiBase = "https://api.github.com/repos/$Owner/$Repo/releases"
$relUrl = if ($ChannelTag -ieq "latest") { "$apiBase/latest" } else { "$apiBase/tags/$ChannelTag" }

# Intentar obtener release por endpoint específico; si falla (404) hacemos fallback listando releases
try {
  if ($isVerbose) { Write-Host "Obteniendo release desde: $relUrl" }
  $rel = Invoke-WebRequest -Uri $relUrl -Headers $Headers -ErrorAction Stop | ConvertFrom-Json
} catch {
  # Si pedimos latest y falló con 404, intentar listar releases y tomar el primero como fallback.
  if ($ChannelTag -ieq "latest") {
    if ($isVerbose) { Write-Host "No se pudo obtener /latest: $($_.Exception.Message). Intentando listar releases..." }
    try {
      $all = Invoke-WebRequest -Uri $apiBase -Headers $Headers -ErrorAction Stop | ConvertFrom-Json
      if ($all -and $all.Count -gt 0) {
        $rel = $all | Select-Object -First 1
        if ($isVerbose) { Write-Host "Usando release fallback: $($rel.tag_name)" }
      } else {
        throw "No hay releases disponibles en el repositorio."
      }
    } catch {
      throw "No se pudo obtener 'latest' release ni listar releases: $($_.Exception.Message)"
    }
    
  } else {
    if ($isVerbose) { Write-Host "Fallo GET por tag ($ChannelTag). Probando a listar releases y buscar tag..." }
    $all = Invoke-WebRequest -Uri $apiBase -Headers $Headers -ErrorAction Stop | ConvertFrom-Json
    $rel = $all | Where-Object { $_.tag_name -eq $ChannelTag } | Select-Object -First 1
    if (-not $rel) { throw "No se encontró un Release con tag '$ChannelTag' (ni en /releases/tags ni listando /releases)." }
  }
}

# Si ya tenemos en destino el mismo tag, evitar reinstalar salvo que se fuerce
$localVersionFile = Join-Path $Target '.nfe_release_tag'
$remoteTag = $rel.tag_name
if (-not $Force) {
  if (Test-Path $localVersionFile) {
    try {
      $localTag = (Get-Content $localVersionFile -Raw).Trim()
    } catch { $localTag = $null }
    if ($localTag -and ($localTag -eq $remoteTag)) {
      Write-Host "Ya estas en la version mas reciente: $remoteTag. Usa -Force para forzar reinstalacion.";
      exit 0
    }
  }
}

# 2) Tomar ZIP y SHA del asset usando los patrones parametrizados
$zipAsset = $rel.assets | Where-Object { $_.name -like $ZipNamePattern } | Select-Object -First 1
$shaAsset = $rel.assets | Where-Object { $_.name -like $ShaNamePattern } | Select-Object -First 1
if (-not $zipAsset) { throw "No se encontró el ZIP en el Release (pattern: $ZipNamePattern)." }

# 3) Descargar (browser_download_url si es público; API + octet-stream si es privado)
$tmp = Join-Path $TempRoot ("app_update_" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$zipPath = Join-Path $tmp $zipAsset.name
$shaPath = if ($shaAsset) { Join-Path $tmp $shaAsset.name } else { $null }

if ($token) {
  # Si tenemos token, preferimos descargar el asset vía API (octet-stream)
  $hdr = $Headers.Clone(); $hdr["Accept"] = "application/octet-stream"
  if ($Verbose) { Write-Host "Descargando (API) $($zipAsset.name) -> $zipPath" }
  Invoke-WebRequest -Uri $zipAsset.url -Headers $hdr -OutFile $zipPath
  if ($shaAsset) {
    if ($Verbose) { Write-Host "Descargando (API) $($shaAsset.name) -> $shaPath" }
    Invoke-WebRequest -Uri $shaAsset.url -Headers $hdr -OutFile $shaPath
  }
} else {
  if ($Verbose) { Write-Host "Descargando (public) $($zipAsset.name) -> $zipPath" }
  Invoke-WebRequest -Uri $zipAsset.browser_download_url -OutFile $zipPath  
  if ($shaAsset) {
    if ($Verbose) { Write-Host "Descargando (public) $($shaAsset.name) -> $shaPath" }
    Invoke-WebRequest -Uri $shaAsset.browser_download_url -OutFile $shaPath
  }
}

# 4) Verificar SHA‑256 (si existe)
if ($shaPath -and (Test-Path $shaPath)) {
  $raw = Get-Content $shaPath -Raw
  $raw = $raw -replace "`r", ""
  $first = ($raw -split "`n")[0].Trim()
  $expected = $null
  if ($first -match "([a-fA-F0-9]{64})") { $expected = $Matches[1] } else { $expected = $first.Split(" ")[0] }
  if ($Verbose) { Write-Host "SHA esperada: $expected" }
  $actual   = (Get-FileHash $zipPath -Algorithm SHA256).Hash
  if ($Verbose) { Write-Host "SHA actual:   $actual" }
  if ($expected -ne $actual) { if ($Cleanup) { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue } ; throw "SHA256 no coincide. Aborto." }
}

# 5) Descomprimir a temp y copiar sobre $Target (mirror)
$extract = Join-Path $tmp "extract"
Expand-Archive -Path $zipPath -DestinationPath $extract -Force            # [3](https://github.com/softprops/action-gh-release/blob/master/README.md)

# Detectar si el ZIP contiene una sola carpeta raíz
$children = Get-ChildItem -Path $extract -Force
$dirs = $children | Where-Object { $_.PSIsContainer }
if ($dirs.Count -eq 1) { $src = $dirs[0].FullName } else { $src = $extract }

if (-not (Test-Path $src)) { if ($Cleanup) { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue } ; throw "Directorio de origen no existe: $src" }

New-Item -ItemType Directory -Path $Target -Force | Out-Null
if ($Verbose) { Write-Host "Copiando desde $src -> $Target (mirror)" }
Start-Process -FilePath robocopy -ArgumentList @("$src", "$Target", "/E") -Wait

# Escribir tag remoto en archivo local para futuras comprobaciones
try {
  if ($Verbose) { Write-Host "Escribiendo tag instalado en: $localVersionFile" }
  # Asegurar que la carpeta destino existe y escribir el tag
  New-Item -ItemType Directory -Path (Split-Path -Path $localVersionFile -Parent) -Force | Out-Null
  Set-Content -Path $localVersionFile -Value $remoteTag -Force -Encoding UTF8
} catch {
  if ($Verbose) { Write-Host "Advertencia: no se pudo escribir ${localVersionFile}: $($_.Exception.Message)" }
}

# Limpiar temporales si corresponde
if ($Cleanup) {
  if ($Verbose) { Write-Host "Limpiando temporales: $tmp" }
  Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
}

Write-Host "Actualizado desde $($rel.tag_name) → $Target"
