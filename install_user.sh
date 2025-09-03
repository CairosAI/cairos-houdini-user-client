# NOTE: Run `source /opt/hfs20.0.547/houdini_setup` first to get the correct environment.
if [[ -z "$HIH" ]]; then
    printf "⚠️ Houdini environment variables not found. For easier setup, run this script from the Houdini Command Line Tools.\n\n"
    read -p "Enter base directory under which to install package: " base_dir
else
    base_dir="${HIH}"
fi

plugin_dest_default="${HOME}/cairos/cairos-houdini-user-client"
read -p "Enter plugin install location [${plugin_dest_default}]: " plugin_dest
plugin_dest="${plugin_dest:-${plugin_dest_default}}"
package_dest="${base_dir}/packages/cairos_user.json"
venv_path="${plugin_dest}/.venv"

if [ ! -d ${plugin_dest} ]; then
    mkdir -p ${plugin_dest}
fi

if [ ! -d ${venv_path} ]; then
    mkdir -p ${venv_path}
fi

if [ ! -d $(dirname ${package_dest}) ]; then
    mkdir -p $(dirname ${package_dest})
fi

# cp ./cairos_inst.json ${package_dest}
sed -e "s>{{ plugin_dest }}>${plugin_dest}>g" -e "s>{{ venv_path }}>${venv_path}>g" ./cairos_inst.json | tee ${package_dest}

cp -u -r . ${plugin_dest}

# Ideally this is a python compatible with Houdini's python, so that dependencies are correct versions. However hython may not have venv
python3.11 -m venv ${venv_path}
source ${venv_path}/bin/activate

pip install -r ./requirements.txt
