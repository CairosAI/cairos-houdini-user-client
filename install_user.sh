plugin_dest_default=${HOME}/cairos-houdini-user-client
venv_path_default=${HOME}/cairos/venvs/cairos
package_dest_default=${HOME}/houdini20.5/packages/cairos_user.json

read -p "Plugin install location [${plugin_dest_default}] " plugin_dest
plugin_dest=${plugin_dest:-${plugin_dest_default}}

read -p "Houdini package location [${package_dest_default}] " package_dest
package_dest=${package_dest:-${package_dest_default}}

read -p "Venv to install python dependencies in [${venv_path_default}] " venv_path
venv_path=${venv_path:-${venv_path_default}}

if [ ! -d ${plugin_dest} ]; then
    mkdir ${plugin_dest}
fi

if [ ! -d ${venv_path} ]; then
    mkdir ${venv_path}
fi

if [ ! -d $(dirname ${package_dest}) ]; then
    mkdir $(dirname ${venv_path})
fi

# cp ./cairos_inst.json ${package_dest}
sed -e "s@{{ plugin_dest }}@${plugin_dest}@g" -e "s@{{ venv_path }}@${venv_path}@g" ./cairos_inst.json | tee ${package_dest}

cp -r . ${plugin_dest}

# Ideally this is a python compatible with Houdini's python, so that dependencies are correct versions.
python3.11 -m venv ${venv_path}
source ${venv_path}/bin/activate

pip install -r ./requirements.txt
