# This should be run from within Houdini Command Tools, so that the environment is set up
if (-Not (Test-Path env:HOUDINI_USER_PREF_DIR)) {
    Write-Output "⚠️ Houdini environment variables not found. For easier setup, run this script from the Houdini Command Line Tools.\n"
    $base_dir = Read-Host "Enter base directory under which to install package: "
} else {
    $base_dir = $env:HOUDINI_USER_PREF_DIR
}

$plugin_dest_default = Join-Path -Path $HOME -ChildPath "cairos\cairos-houdini-user-client"
$plugin_dest = Read-Host "Enter plugin install location [${plugin_dest_default}]: "
if (-not $plugin_dest) { $plugin_dest = $plugin_dest_default }

$venv_path = Join-Path -Path $plugin_dest -ChildPath ".venv"
$package_dest = Join-Path -Path $base_dir -ChildPath "packages\cairos_user.json"
$package_dir = Split-Path -parent $package_dest
if (-Not (Test-Path $package_dir)) { md -Path $package_dir }
if (-Not (Test-Path $venv_path)) { md -Path $venv_path }

Get-Content ./cairos_inst_windows.json | ForEach-Object {$_ -replace "{{ plugin_dest }}", $plugin_dest}| ForEach-Object {$_ -replace "{{ venv_path }}", $venv_path} | ForEach-Object {$_ -replace "\\", "/"} | Set-Content $package_dest
# cp ./cairos_inst.json $package_dest
if (-Not (Test-Path $plugin_dest)) { md -Path $plugin_dest }
cp -Path ".\*" -Force -Destination $plugin_dest -Recurse

python -m venv $venv_path
& "$venv_path\Scripts\activate.ps1"

pip install -r ./requirements.txt
