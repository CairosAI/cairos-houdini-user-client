Make sure to have a system Python that is compatible with the Houdini Python. For Houdini 20.5 this is Python 3.11. This can also be achieved with uv or anaconda. E.g. for uv:
``` shell
uv venv --python 3.11
```

Clone the repo, then get the dependencies
``` shell
git submodule update --init
```

There are two primary ways of installing plugins in Houdini - user-specific, and "global" usually employed by studios. The global installation requires administrative privileges, and might require more effort.

Houdini provides command line tools to set the correct environment, so use these in both manual and automated setup.

# With the provided installation scripts
These scripts should cover most regular use cases.

Before running them, enter the Houdini environment. On Windows, this is done by starting Command Line Tools from the start menu.
On Linux, perform `source /opt/hfs20.0.547/houdini_setup` to load the environment.

Then, run the scripts from the directory where you cloned the plugin.

Linux studio:
```
./install.sh
```

Linux user:
```
./install_user.sh
```

Windows studio:
```
cd path-to-plugin-repo
powershell ./install.ps1
```

Windows user:
```
cd path-to-plugin-repo
powershell ./install_user.ps1
```

The script will prompt you for some locations that you can adjust to your preference and system specifics.

# Manually
The installation scripts may not cover your setup, or they may fail. In this case running things manually step by step might be clearer.

## User
A user installation does not require elevated privileges to perform.
By default Houdini reads plugins from `$HOUDINI_USER_PREF_DIR`, which is usually in `$HOME/houdiniX.XX`.

### Windows
On Windows the user prefs directory is e.g. `c:\Users\username\Documents\houdini20.5` (adjusted for Houdini version, not including build number).

You could place everything under your home directory, where you have unlimited access:
``` powershell
$plugin_dest = "c:\Users\yourusername\Documents\cairos\cairos-houdini-user-client"
$venv_path = "c:\Users\yourusername\Documents\cairos\venvs\cairos"
$package_dest = "c:\Users\yourusername\Documents\houdini20.5\packages\cairos_user.json"
```

#### Clone the plugin directly into `$plugin_dest` or copy it there
Let's say we clone it directly in the destination:
``` powershell
mkdir "c:\Users\yourusername\Documents\cairos"
cd "c:\Users\yourusername\Documents\cairos"
git clone git@github.com:CairosAI/cairos-houdini-user-client.git
cd cairos-houdini-user-client
git submodule update --init
```

#### Copy the json package file to Houdini's user preferences directory
``` powershell
cp $plugin_dest\cairos_inst_windows.json $package_dest
```
Open up the newly copied file in a text editor, and replace the curly brace placeholders with the correct paths - `{{ plugin_dest }}`, `{{venv_path }}`.

#### Create a Python virtual environment and install the dependencies
You could use the `venv_path` above, or adjust to your liking.

``` powershell
cd $plugin_dest
python -m venv $venv_path
$venv_path\Scripts\activate.ps1
python -m pip install ./requirements.txt
```

### Linux
On Linux the user prefs directory is `$HOME/houdini20.5`.

Let's assume the following locations:
``` sh
$plugin_dest = "$HOME/cairos/cairos-houdini-user-client"
$venv_path = "$HOME/cairos/venvs/cairos"
$package_dest = "$HOME/houdini20.5/packages/cairos_user.json"
```

#### Clone the plugin directly into `$plugin_dest` or copy it there
Let's say we clone it directly in the destination:
``` sh
mkdir "$HOME/cairos"
cd $HOME/cairos
git clone git@github.com:CairosAI/cairos-houdini-user-client.git
cd cairos-houdini-user-client
git submodule update --init
```

#### Copy the json package file to Houdini's user preferences directory
``` sh
cp $plugin_dest/cairos_inst.json $package_dest
```
Open up the newly copied file in a text editor, and replace the curly brace placeholders with the correct paths - `{{ plugin_dest }}`, `{{venv_path }}`.

#### Create a Python virtual environment and install the dependencies
You could use the `venv_path` above, or adjust to your liking.

``` sh
cd $plugin_dest
python -m venv $venv_path
source $venv_path/bin/activate
python -m pip install ./requirements.txt
```

### MacOS
TODO

## Studios
Studio setups require easier centralized configuration.

### Windows
Open up powershell. If you are going to write in Program Files, select "Run as Administrator".

First define the target locations. These paths are defaults, replace them to your preference.
They will be referenced in subsequent commands.
You can create variables like here, or you could directly paste the path in place of the variable in the commands below.

``` powershell
$plugin_dest = "c:\Program Files\Common Files\Houdini\cairos-houdini-user-client"
$houdini_path = "c:\Program Files\Houdini20.5.510"
$venv_path = Join-Path -Path $env:LocalAppData -ChildPath "\cairos\venvs\cairos"
$package_dest = "c:\Program Files\Houdini20.5.510\packages\cairos_user.json"
```

#### Copy the plugin from the cloned directory to your system
``` powershell
cp -Path ".\*" -Destination $plugin_dest -Recurse
```

Note, this is optional. If you wish to use the plugin straight from the cloned location, replace `$plugin_dest` in the next section with the cloned location.

#### Copy the Houdini json package file to Houdini's directory.
This command will copy the file and automatically replace the location placeholders:
``` powershell
Get-Content ./cairos_inst_windows.json | ForEach-Object {$_ -replace "{{ plugin_dest }}", $plugin_dest}| ForEach-Object {$_ -replace "{{ venv_path }}", $venv_path} | ForEach-Object {$_ -replace "\\", "/"} | Set-Content $package_dest
```

Alternatively, you can copy the package yourself and replace the placeholders in a text editor:

* Copy `cairos_inst_windows.json` to `$package_dest`
* Open the file and
  * Replace `{{ venv_path }}` with the path to the virtual environment specified above.
  * Replace `{{ plugin_dest }}` with the location where you copied the plugin.
  * Replace backslashes (`\`) with forward slashes (`/`)

#### Create a Python virtual environment and install the dependencies
##### Using the built-in Python venv module
Create:
`python -m venv $venv_path`

Activate:
`$venv_path/Scripts/activate.ps1`

Install modules (with environment activated):
`pip install -r ./requirements.txt`

##### Using [Astral uv](https://docs.astral.sh/uv/)
Create:
`uv venv --python 3.11 $venv_path`

Activate:
`$venv_path/Scripts/activate.ps1`

Install modules:
`uv pip install -r ./requirements.txt`

##### Using [Anaconda](https://docs.conda.io/projects/conda/en/latest/index.html)
*Note:* the Anaconda environment may break some of Houdini's dependencies, and not work.

Create with the provided environment yml:
`conda env create -f cairos_conda.yml`

Activate:
`conda activate cairos`

Find out venv path, insert it in the Houdini json package:

* Execute `conda info` and look for "active env location". By default this is `c:\ProgramData\anaconda3\envs\cairos`.
* In `cairos_user.json` that you copied to the Houdini packages directory, replace `{{ venv_path }}` with the env location (will require administrator rights). Replace backslashes in the json file with forward slashes.
* This will tell Houdini where to find the Python library dependencies.

### Linux
Specify destination paths. These paths are defaults, replace them to your preference.
They will be referenced in subsequent commands.
``` sh
plugin_dest=/opt/houdini_plugins/cairos-houdini-user-client
houdini_path=/opt/hfs20.5.510
venv_path=/usr/local/share/cairos/venvs/cairos
package_dest=/opt/hfs20.5.510/packages/cairos_user.json
```
#### Copy the plugin from the cloned directory to your system

#### Copy package file
Either copy the package file using this command:
``` sh
sed -e "s@{{ plugin_dest }}@${plugin_dest}@g" -e "s@{{ venv_path }}@${venv_path}@g" ./cairos_inst.json | tee ${package_dest}
```
or straight up copying and replacing the placeholders:

* Copy `cairos_inst.json` to `$package_dest`
* Open the file and
  * Replace `{{ venv_path }}` with the path to the virtual environment specified above.
  * Replace `{{ plugin_dest }}` with the location where you copied the plugin.

#### Create a Python virtual environment and install the dependencies
##### Using the built-in Python venv module
Create:
`python -m venv $venv_path`

Activate:
`source $venv_path/bin/activate`

Install modules (with environment activated):
`pip install -r ./requirements.txt`

##### Using [Astral uv](https://docs.astral.sh/uv/)
Create:
`uv venv --python 3.11 $venv_path`

Activate:
`source $venv_path/bin/activate`

Install modules:
`uv pip install -r ./requirements.txt`
