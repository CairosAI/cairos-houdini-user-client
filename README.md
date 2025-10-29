# Cairos Houdini user client

Use [Cairos](https://cairos.bottleshipvfx.com) inside Houdini

## Installing
See [INSTALL.md](INSTALL.md)

## Using the Cairos plugin

![Cairos HDA](./screenshot-cairos-hda.png)

In Houdini, you can add a Geometry node `Cairos Houdini user client`.

Go to the Settings tab and click login. Enter the Cairos address you will be using, your username and password. The public address is <https://app.cairos.bottleshipvfx.com/api>

To sign up, go to <https://cairos.bottleshipvfx.com> .

On successful login, you can go to the Animation tab and submit chat prompts, and manage your avatars in the Avatar tab.

## Workflow

### Animating

You start with an animation, that you obtain by chatting with the agent and getting suggested movements.

This animation uses a default avatar, which is processed fast. This permits iterating to refine the animation with further prompts.

Once the sequence is completed, it is exported, downloaded locally, and loaded in Houdini.

### Managing avatars
You can upload, autorig, export, and delete avatars from the HDA.

You can select an existing avatar from the list, or enter the name for a new one in "Character name", then upload you selected geometry from "Character skin SOP" to it.

When uploading or autorigging a character, it is automatically exported, downloaded locally, and loaded in Houdini.
