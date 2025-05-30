venv_path=/usr/local/share/cairos/venvs/cairos

python3.11 -m venv ${venv_path}
source ${venv_path}/bin/activate

pip install -r ./requirements.txt
