# cp ./cairos_inst.json /opt/hfs20.5.510/packages/cairos_user.json
python -m venv /usr/local/share/cairos/venvs/cairos
source /usr/local/share/cairos/venvs/cairos/bin/activate

pip install ./deps/cairos-types
pip install ./deps/cairos-python-client
