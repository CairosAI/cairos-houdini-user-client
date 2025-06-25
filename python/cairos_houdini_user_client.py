import os
import sys
import asyncio
from pathlib import Path
import shutil
import json

from cairos_python_lowlevel.cairos_python_lowlevel.models.avatar_public import AvatarPublic
from cairos_python_lowlevel.cairos_python_lowlevel.models.body_post_avatar_avatar_uuid_upload_post import BodyPostAvatarAvatarUuidUploadPost
from cairos_python_lowlevel.cairos_python_lowlevel.models.http_validation_error import HTTPValidationError
from cairos_python_lowlevel.cairos_python_lowlevel.types import File
from httpx import HTTPError, HTTPStatusError

import hou
import haio
import tempfile

import cairos_python_client

from cairos_python_lowlevel.cairos_python_lowlevel.models.avatar_public import AvatarPublic
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_input import ChatInput
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_thread_in_list import ChatThreadInList
from cairos_python_lowlevel.cairos_python_lowlevel.models.human_message import HumanMessage
from cairos_python_lowlevel.cairos_python_lowlevel.models.orm_animation import OrmAnimation
from cairos_python_lowlevel.cairos_python_lowlevel.models.export import Export
from cairos_python_lowlevel.cairos_python_lowlevel.models.body_login_outseta_login_post import BodyLoginOutsetaLoginPost

from cairos_python_lowlevel.cairos_python_lowlevel.types import UNSET

from cairos_python_lowlevel.cairos_python_lowlevel.client import Client, AuthenticatedClient
from cairos_python_lowlevel.cairos_python_lowlevel.api.default import (
    process_message_thread_thread_id_post,
    export_anim_anim_thread_id_trigger_msg_id_export_post,
    post_avatar_avatar_uuid_upload_post,
    get_avatars_avatar_get,
    trigger_autorig_avatar_uuid_autorig_post,
    create_blank_avatar_avatar_new_label_post,
    login_outseta_login_post,
    check_credit_balance_credit_balance_get,
    retarget_anim_anim_thread_id_trigger_msg_id_retarget_avatar_id_post)

from cairos_python_lowlevel.cairos_python_lowlevel.errors import UnexpectedStatus

from uuid import uuid4, UUID
import httpx_sse

import traceback

async def async_cancel_all_tasks(loop: asyncio.AbstractEventLoop):
    tasks = [
        t for t in asyncio.all_tasks(loop=loop)
        if t is not asyncio.current_task(loop=loop)]

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

async def async_shutdown_tasks(loop: asyncio.AbstractEventLoop):
    await async_cancel_all_tasks(loop)

async def sse_handler(client: AuthenticatedClient, node: hou.Node):
    print(f"Connecting to {client._base_url}/event_log")
    async with httpx_sse.aconnect_sse(
            client=client.get_async_httpx_client(),
            method="GET",
            url=f"{client._base_url}/event_log") as event_source:
        async for evt in event_source.aiter_sse():
            # print(evt)
            if evt.event == "animation_success":
                update_status(node, "Animation success.")
                await on_sequencer_success(
                    client,
                    OrmAnimation.from_dict(evt.json()),
                    node)
            elif evt.event == "animation_error":
                print(f"Animation error {evt}")
                update_status(node, "Animation error!")
            elif evt.event == "export_success":
                try:
                    update_status(node, "Export success")
                    await on_export_success(
                        client,
                        Export.from_dict(evt.json()),
                        node)
                except:
                    traceback.print_exc()
            elif evt.event == "export_error":
                print(f"Export error {evt}")
                update_status(node, "Export error")

            elif evt.event == "avatar_upload_success":
                try:
                    await on_avatar_upload_success(
                        client,
                        AvatarPublic.from_dict(evt.json()),
                        node)
                except:
                    traceback.print_exc()
            elif evt.event == "avatar_upload_err":
                update_status(node, f"Avatar upload error: {evt.data}")
            elif evt.event == "avatar_autorig_success":
                await on_avatar_autorig_success(
                    client,
                    AvatarPublic.from_dict(evt.json()),
                    node)
            elif evt.event == "avatar_autorig_err":
                update_status(node, f"Autorig error: {evt.data}")
            elif evt.event == "animation_retarget_success":
                await on_animation_retarget_success(
                    client,
                    OrmAnimation.from_dict(evt.json()),
                    node)
            elif evt.event == "animation_retarget_err":
                update_status(node, f"Retarget error: {evt.data}")
            else:
                print(evt)

    print("Exiting sse loop")

async def send_chat(client: AuthenticatedClient, chat_thread: ChatThreadInList, prompt, node: hou.Node):
    """ Final result is received by sse, animation_success or animation_error.
    """
    print(f"Sending chat {prompt}")
    update_status(node, "Sending chat")
    try:
        response = await process_message_thread_thread_id_post.asyncio(
            thread_id=chat_thread.id,
            client=client,
            body=ChatInput(
                prompt=HumanMessage(
                    id=uuid4().hex,
                    content=prompt),
                history=[],
                btl_objs=[]),
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

        print(f"Chat response received: {response}. Waiting for animation sequence.")
        update_status(node, "Chat response received. Waiting for animation sequence.")
    except UnexpectedStatus as e:
        print(f"Request error: {e.status_code}")
        if e.status_code == 426:
            content = json.loads(e.content)
            button_res = hou.ui.displayMessage(
                content["detail"],
                title="Cairos error",
                buttons=("Open webiste", "Ok"),
                default_choice=1,
                close_choice=1)

            if button_res == 0:
                print("Opening website")
                if sys.platform == "win32":
                    os.system(f"start \"\" https://cairos.outseta.com/profile?tab=planChange")
                elif sys.platform == "darwin":
                    os.system(f"open \"\" https://cairos.outseta.com/profile?tab=planChange")
                else:
                    os.system(f"xdg-open https://cairos.outseta.com/profile?tab=planChange")

            print(content)
            update_status(node, content["detail"])

    except Exception as e:
        print(f"Request error: {e}")

async def send_export(client: AuthenticatedClient, thread_id: str, trigger_msg: UUID):
    """ Final result is received by sse, export_success or export_error.
    """
    res = await export_anim_anim_thread_id_trigger_msg_id_export_post.asyncio(
        thread_id=thread_id,
        trigger_msg_id=trigger_msg.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print("Export response received. Waiting for export to complete.")
    print(res)

async def send_retarget(client: AuthenticatedClient, thread_id: str, trigger_msg: UUID, avatar_name: str):
    avatars = await get_avatars_avatar_get.asyncio(
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    assert avatars and not isinstance(avatars, HTTPValidationError), "Avatars are empty!"
    avatar: AvatarPublic | None = next((a for a in avatars if a.label == avatar_name), None)
    if avatar is None:
        hou.ui.displayMessage(f"Avatar does not exist: {avatar_name}")
        return

    res = await retarget_anim_anim_thread_id_trigger_msg_id_retarget_avatar_id_post.asyncio(
        thread_id=thread_id,
        trigger_msg_id=trigger_msg.hex,
        avatar_id=avatar.id.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print("Retarget response received. Waiting for retarget to complete.")
    print(res)

async def send_autorig(client: AuthenticatedClient, avatar: AvatarPublic):
    """ Final result is received by sse, avatar_autorig_success or avatar_autorig_err.
    """
    print(f"Sending autorig for {avatar.label}")
    res = await trigger_autorig_avatar_uuid_autorig_post.asyncio(
        uuid=avatar.id.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print("Autorig response received. Wait for process to complete.")
    print(res)

async def upload_avatar(
        client: AuthenticatedClient,
        avatar_name: str,
        avatar_geo_node: hou.SopNode,
        node: hou.Node):
    """ Final result is received by sse, avatar_upload_success or avatar_upload_err.
    """
    print(f"Uploading avatar {avatar_name}")
    avatars = await get_avatars_avatar_get.asyncio(
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    assert avatars and not isinstance(avatars, HTTPValidationError), "Avatars are empty!"
    avatar: AvatarPublic | None = next((a for a in avatars if a.label == avatar_name), None)

    if avatar is None:
        update_status(node, "Avatar was not found. Creating a new one.")
        print("Avatar was not found. Creating a new one.")
        avatar_resp = await create_blank_avatar_avatar_new_label_post.asyncio(
            label=avatar_name,
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

        update_status(node, "Created new avatar.")
        print(f"Created new avatar: {avatar_resp}")
        if avatar_resp and not isinstance(avatar_resp, HTTPValidationError):
            avatar = avatar_resp

    assert avatar, "No avatar selected"

    tmp: tuple[int, str] = tempfile.mkstemp(
        prefix=f"cairos_{avatar_name}",
        suffix=".bgeo",
        dir=node.parm("tempdir").eval())

    # TODO for now do not delete temporary file
    try:
        with open(tmp[1], "wb+") as f:
            update_status(node, "Exporting geometry for avatar...")
            avatar_geo_node.geometry().saveToFile(f.name)
            print(f"Saved geometry to {f.name}")
            update_status(node, "Geometry exported, uploading.")

            await post_avatar_avatar_uuid_upload_post.asyncio(
                uuid=avatar.id.hex,
                client=client,
                body=BodyPostAvatarAvatarUuidUploadPost(
                    file=File(
                        payload=f,
                        file_name=f.name)),
                outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

            update_status(node, "Avatar file uploaded. Wait for processing.")
    except:
        traceback.print_exc()


async def on_sequencer_success(client: AuthenticatedClient, animation: OrmAnimation, node: hou.Node):
    # trigger export
    # how to get context
    """ sse handler """
    print("Received sequencer success.")
    if node.parm("retarget_animation").eval():
        update_status(node, "Sending retarget request")
        await send_retarget(
            client,
            animation.job_thread,
            animation.job_trigger,
            node.parm("retarget_avatar").eval())
    else:
        update_status(node, "Sending export request")
        await send_export(client, animation.job_thread, animation.job_trigger)

async def on_avatar_upload_success(client: AuthenticatedClient, avatar: AvatarPublic, node: hou.Node):
    """ sse handler """
    print("Received upload processing success. Wait for autorig")
    update_status(node, "Received upload processing success. Wait for autorig")
    await send_autorig(client, avatar)

async def on_avatar_autorig_success(client: AuthenticatedClient, avatar: AvatarPublic, node: hou.Node):
    """ sse handler. Do not do anything, just notify """
    print("Autorig successful!")
    update_status(node, "Autorig successful. Avatar is now ready to use")

async def download_export(client: AuthenticatedClient, export: Export, temp_dir: Path) -> Path:
    filename = temp_dir\
        .joinpath(f"{export.job_thread}_{export.job_trigger}")\
        .with_suffix(Path(export.filepath).suffix)

    out_dir = temp_dir\
        .joinpath(f"{export.job_thread}_{export.job_trigger}/extracted")

    # Download content with explicit client get. This probably does not work in api?
    result = await client.get_async_httpx_client().get(
        url=f"{client._base_url}/anim/{export.job_thread}/{export.job_trigger.hex}/download")

    print(f"Download complete: {result}")
    with open(filename, "wb") as f:
        f.write(result.content)
        print(f"Wrote {filename}")

    shutil.unpack_archive(filename, out_dir)

    return out_dir

async def check_credits(client: AuthenticatedClient, node: hou.Node):
    print("Checking credits")
    result = await check_credit_balance_credit_balance_get.asyncio(
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print(f"Result: {result}")
    hou.ui.displayMessage(
        result,
        title="Cairos credits")

async def load_exported_files(output_directory: Path, node: hou.Node):
    retargeted = next(output_directory.glob("*retargeted*"))
    sequencer = next(output_directory.glob("*sequencer*"))

    if retargeted and sequencer:
        node.node("retarget").parm("fbxfile").set(str(retargeted))
        node.node("retarget1").parm("fbxfile").set(str(retargeted))
        node.node("sequence").parm("fbxfile").set(str(sequencer))

    update_status(node, "Loaded export assets. Done.")

async def on_animation_retarget_success(client: AuthenticatedClient, animation: OrmAnimation, node: hou.Node):
    print(f"Retarget success! {animation}")
    update_status(node, f"Retarget successful! {animation}.\nTriggering export")
    res = await send_export(client, thread_id=animation.job_thread, trigger_msg=animation.job_trigger)
    print(f"Export submitted: {res}")

async def on_export_success(client: AuthenticatedClient, export: Export, node: hou.Node):
    # download archive
    # unpack it
    # use contents
    """ sse handler """
    print("Export successful. Downloading export artifacts.")
    print(export)
    output_directory = await download_export(client, export, Path(node.parm("tempdir").eval()))
    update_status(node, "Export downloaded. Unpacking and loading.")
    # TODO set paths from export in scene.
    return await load_exported_files(output_directory, node)

async def start_sse_listener(client: AuthenticatedClient, node: hou.Node):
    await sse_handler(client, node)
    print(f"Started sse handler with {client}")

def update_status(node: hou.Node, status: str):
    return node.parm("status").set(status)

def on_exit(loop: asyncio.AbstractEventLoop):
    async def ashutdown(loop):
        tasks = [task for task in asyncio.all_tasks(loop) if task is not
             asyncio.current_task(loop)]
        list(map(lambda task: task.cancel(), tasks))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(results)
        loop.stop()
    asyncio.run_coroutine_threadsafe(ashutdown(loop), loop).result()

async def close_client(client: AuthenticatedClient):
    print("Closing http client")
    await client.get_async_httpx_client().aclose()

async def handle_login(url, username, password, node):
    # Here initialize asyncio loop
    try:
        unauth_client = Client(
            url,
            verify_ssl=False,
            raise_on_unexpected_status=True)

        response = await login_outseta_login_post.asyncio_detailed(
            client=unauth_client,
            body=BodyLoginOutsetaLoginPost(
                username=username,
                password=password))

        cookies = cairos_python_client.parse_cookies(response.headers.get("Set-Cookie"))
        client = AuthenticatedClient(
            base_url=url,
            token=cookies.get(cairos_python_client.token_cookie_name, ""),
            verify_ssl=False,
            cookies=cookies,
            raise_on_unexpected_status=True)

        if client:
            node.setCachedUserData("cairos_client", client)
            node.parm("status").set("logged in")
            node.setCachedUserData("cairos_url", url)
            node.setCachedUserData("cairos_user", username)

            avatars = await get_avatars_avatar_get.asyncio(
                client=client,
                outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))
            node.setCachedUserData("avatars", avatars)

            await start_sse_listener(client, node)
        else:
            print("login unsuccessful")
            update_status(node, "could not log in")
    except Exception:
        print("Error!!!")
        traceback.print_exc()
