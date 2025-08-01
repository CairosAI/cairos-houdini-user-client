# Cairos Houdini user client

Use [Cairos](https://cairos.ai) inside Houdini

## Installing
Make sure to have a system Python that is compatible with the Houdini Python. For Houdini 20.5 this is Python 3.11. This can also be achieved with uv or anaconda. E.g. for uv:
``` shell
uv venv --python 3.11
```

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

You will be asked for the location to copy the plugin to, the location of Houdini, the location of a virtual environment, containing some needed dependencies.

The script
- Copies the plugin.
- Copies a json package in Houdini's directory, which points Houdini to the plugin.
- Initializes a virtual environment for the dependencies and installs them.

## Using

![Cairos HDA](./screenshot-cairos-hda.png)

In Houdini, you can add a Geometry node `Cairos Houdini user client`.

Go to the Settings tab and click login. Enter the Cairos address you will be using, your username and password. The public address is https://app.cairos.ai/api

To sign up, go to https://cairos.ai .

On successful login, you can go to the Animation tab and submit chat prompts, and manage your avatars in the Avatar tab.

## Workflow

### Animating

![Workflow overview](./cairos-houdini-user-workflow.png)

You start with an animation, that you obtain by chatting with the agent and getting suggested movements.

This animation uses a default avatar, which is processed fast. This permits iterating to refine the animation with further prompts.

Once the sequence is completed, it is exported, downloaded locally, and loaded in Houdini.

### Managing avatars
You can upload, autorig, export, and delete avatars from the HDA.

You can select an existing avatar from the list, or enter the name for a new one in "Character name", then upload you selected geometry from "Character skin SOP" to it.

When uploading or autorigging a character, it is automatically exported, downloaded locally, and loaded in Houdini.
