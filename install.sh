plugin_dest_default=/opt/houdini_plugins/cairos-houdini-user-client
houdini_path_default=/opt/hfs20.5.510
venv_path_default=/usr/local/share/cairos/venvs/cairos

read -p "Plugin install location [${plugin_dest_default}] " plugin_dest
plugin_dest=${plugin_dest:-${plugin_dest_default}}

read -p "Houdini location [${houdini_path_default}] " houdini_path
houdini_path=${houdini_path:-${houdini_path_default}}

read -p "Venv to install python dependencies in [${venv_path_default}] " venv_path
venv_path=${venv_path:-${venv_path_default}}

echo "Installing plugin. Note that you might need elevated privileges."

package_dest=${houdini_path}/packages/cairos_user.json

# cp ./cairos_inst.json ${package_dest}
sed -e "s@{{ plugin_dest }}@${plugin_dest}@g" -e "s@{{ venv_path }}@${venv_path}@g" ./cairos_inst.json | tee ${package_dest}

cp -r . ${plugin_dest}

# Ideally this is a python compatible with Houdini's python, so that dependencies are correct versions.
python3.11 -m venv ${venv_path}
source ${venv_path}/bin/activate

pip install -r ./requirements.txt
