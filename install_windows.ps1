$plugin_dest_default = "c:\Program Files\Common Files\houdini_plugins\cairos-houdini-user-client"
$houdini_path_default = "c:\Program Files\Houdini20.5.510"
$venv_path_default = Join-Path -Path $LocalAppData -ChildPath "\cairos\venvs\cairos"

$plugin_dest = Read-Host ("Plugin install location [${0}] " -f $plugin_dest_default)
if (-not $plugin_dest) { $plugin_dest = $plugin_dest_default }

$houdini_path = Read-Host ("Houdini location [${0}] " -f $houdini_path_default)
if (-not $houdini_path) { $houdini_path = $houdini_path_default }

$venv_path = Read-Host ("Venv location [${0}] " -f $venv_path_default)
if (-not $venv_path) { $venv_path = $venv_path_default }

$package_dest = Join-Path -Path $houdini_path -ChildPath "\packages\cairos_user.json"

cp ./cairos_inst.json $package_dest
cp . $plugin_dest

python 3.11 -m venv $venv_path
$venv_path\Scripts\activate.ps1

pip install -r ./requirements.txt