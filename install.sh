plugin_dest=/opt/houdini_plugins/cairos-houdini-user-client
package_dest=/opt/hfs20.5.510/packages/cairos_user.json
venv_path=/usr/local/share/cairos/venvs/cairos

cp ./cairos_inst.json ${package_dest}
cp -r . ${plugin_dest}

# Ideally this is a python compatible with Houdini's python, so that dependencies are correct versions.
python3.11 -m venv ${venv_path}
source ${venv_path}/bin/activate

pip install -r ./requirements.txt
