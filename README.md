# Cairos Houdini user client

Use Cairos inside Houdini

## Installing
Make sure to have a system Python that is compatible with the Houdini Python. For Houdini 20.5 this is Python 3.11.

Clone the repo, then get the dependencies
``` shell
git submodule update --init
```

Then run the installation script

Linux:
```
./install.sh
```

Windows:
```
./install.ps1
```

The script
- Copies the plugin.
- Copies a json package in Houdini's directory, which points Houdini to the plugin.
- Initializes a virtual environment for the dependencies and installs them.

## Using
In Houdini, you can add a node `Cairos Houdini user client`.

Go to the Settings tab and click login. Enter the Cairos address you will be using, your username and password.

On successful login, you can go to the Animation tab and submit chat prompts, and manage your avatars in the Avatar tab.
