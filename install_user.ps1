$plugin_dest_default = Join-Path -Path $HOME -ChildPath "cairos\cairos-houdini-user-client"
$venv_path_default = Join-Path -Path $HOME -ChildPath "cairos\venvs\cairos"
$package_dest_default = Join-Path -Path $HOME -ChildPath "houdini20.5\packages\cairos_user.json"

$plugin_dest = Read-Host "Plugin install location [${plugin_dest_default}] "
if (-not $plugin_dest) { $plugin_dest = $plugin_dest_default }

$venv_path = Read-Host "Venv location [${venv_path_default}] "
if (-not $venv_path) { $venv_path = $venv_path_default }

$package_dest = Read-Host "Package file location [${package_dest_default}] "
if (-not $package_dest) { $package_dest = $package_dest_default }

$package_dir = Split-Path -parent $package_dest
if (-Not (Test-Path $package_dir)) { md -Path $package_dir }

if (-Not (Test-Path $venv_path)) { md -Path $venv_path }

Get-Content ./cairos_inst_windows.json | ForEach-Object {$_ -replace "{{ plugin_dest }}", $plugin_dest}| ForEach-Object {$_ -replace "{{ venv_path }}", $venv_path} | ForEach-Object {$_ -replace "\\", "/"} | Set-Content $package_dest
# cp ./cairos_inst.json $package_dest
if (-Not (Test-Path $plugin_dest)) { md -Path $plugin_dest }
cp -Path ".\*" -Destination $plugin_dest -Recurse

python -m venv $venv_path
& "$venv_path\Scripts\activate.ps1"

pip install -r ./requirements.txt
