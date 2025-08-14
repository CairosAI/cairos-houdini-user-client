$plugin_dest_default = "c:\Program Files\Common Files\Houdini\cairos-houdini-user-client"
$houdini_path_default = "c:\Program Files\Houdini20.5.510"
$venv_path_default = Join-Path -Path $env:LocalAppData -ChildPath "\cairos\venvs\cairos"

$plugin_dest = Read-Host "Plugin install location [${plugin_dest_default}] "
if (-not $plugin_dest) { $plugin_dest = $plugin_dest_default }

$houdini_path = Read-Host "Houdini location [${houdini_path_default}] "
if (-not $houdini_path) { $houdini_path = $houdini_path_default }

$venv_path = Read-Host "Venv location [${venv_path_default}] "
if (-not $venv_path) { $venv_path = $venv_path_default }

$package_dest = Join-Path -Path $houdini_path -ChildPath "\packages\cairos_user.json"

Get-Content ./cairos_inst_windows.json | ForEach-Object {$_ -replace "{{ plugin_dest }}", $plugin_dest}| ForEach-Object {$_ -replace "{{ venv_path }}", $venv_path} | ForEach-Object {$_ -replace "\\", "/"} | Set-Content $package_dest
# cp ./cairos_inst.json $package_dest
if (-Not (Test-Path $plugin_dest)) { md -Path $plugin_dest }
cp -Path ".\*" -Destination $plugin_dest -Recurse

python -m venv $venv_path
& "$venv_path\Scripts\activate.ps1"

pip install -r ./requirements.txt