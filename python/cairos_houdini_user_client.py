import os
import sys
import asyncio
from collections import deque
from pathlib import Path
import shutil
import json
from typing import Any, Dict, List, Tuple, Type, TypeVar, cast, AsyncGenerator
from datetime import datetime
import shutil

from cairos_python_lowlevel.cairos_python_lowlevel.models.avatar_public import AvatarPublic
from cairos_python_lowlevel.cairos_python_lowlevel.models.avatar_rebuilt import AvatarRebuilt
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
from cairos_python_lowlevel.cairos_python_lowlevel.models.ai_message import AIMessage
from cairos_python_lowlevel.cairos_python_lowlevel.models.stored_message import StoredMessage
from cairos_python_lowlevel.cairos_python_lowlevel.models.stored_message_type import StoredMessageType

from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_output import ChatOutput
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_thread_in_list import ChatThreadInList
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_thread_public import ChatThreadPublic
from cairos_python_lowlevel.cairos_python_lowlevel.models.human_message import HumanMessage
from cairos_python_lowlevel.cairos_python_lowlevel.models.orm_animation import OrmAnimation
from cairos_python_lowlevel.cairos_python_lowlevel.models.export import Export
from cairos_python_lowlevel.cairos_python_lowlevel.models.body_login_outseta_login_post import BodyLoginOutsetaLoginPost

from cairos_python_lowlevel.cairos_python_lowlevel.client import Client, AuthenticatedClient
from cairos_python_lowlevel.cairos_python_lowlevel.api.default import (
    process_message_thread_thread_id_post,
    export_anim_anim_thread_id_trigger_msg_id_export_post,
    post_avatar_avatar_uuid_upload_post,
    get_avatars_avatar_get,
    new_thread_thread_post,
    get_avatar_avatar_uuid_get,
    get_avatars_rebuilt_avatar_rebuilt_get,
    get_avatar_rebuilt_by_id_avatar_rebuilt_uuid_get,
    get_anim_anim_thread_id_trigger_msg_id_get,
    get_session_id_session_id_get,
    trigger_autorig_avatar_uuid_autorig_post,
    update_avatar_mapping_llm_avatar_uuid_llm_mapping_patch,
    create_blank_avatar_avatar_new_label_post,
    login_outseta_login_post,
    check_credit_balance_credit_balance_get,
    retarget_anim_anim_thread_id_trigger_msg_id_retarget_avatar_id_post,
    create_blank_avatar_avatar_new_label_post,
    delete_avatar_route_avatar_uuid_delete,
    trigger_export_avatar_uuid_export_post)

from cairos_python_lowlevel.cairos_python_lowlevel.errors import UnexpectedStatus

from uuid import uuid4, UUID
import httpx_sse

from attrs import define as _attrs_define

import traceback

T = TypeVar("T", bound="AvatarExport")
@_attrs_define
class AvatarExport:
    """ Placeholder model. This model is not exposed by OpenAPI def,
    because it is only returned in SSE, which is currently not covered by it.
    """
    user_id: str
    avatar_id: UUID
    avatar_user_id: str
    filepath: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "avatar_id": str(self.avatar_id),
            "avatar_user_id": self.avatar_user_id,
            "filepath": self.filepath
        }

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        return cls(
            user_id=d.pop("user_id"),
            avatar_id=UUID(d.pop("avatar_id")),
            avatar_user_id=d.pop("avatar_user_id"),
            filepath=d.pop("filepath"))

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
    update_status(node, f"Connecting to {client._base_url}/event_log")
    try:
        async with httpx_sse.aconnect_sse(
                client=client.get_async_httpx_client(),
                method="GET",
                url=f"{client._base_url}/event_log") as event_source:

            sse_iter = event_source.aiter_sse()
            node.setCachedUserData("cairos_sse_iter", sse_iter)
            async for evt in sse_iter:
                if client.get_async_httpx_client().is_closed:
                    break

                if evt.event == "animation_success":
                    update_status(node, "Animation success.")
                    await on_sequencer_success(
                        client,
                        OrmAnimation.from_dict(evt.json()),
                        node)
                elif evt.event == "animation_error":
                    update_status(node, "Animation error!")
                elif evt.event == "export_success":
                    try:
                        update_status(node, "Export success")
                        await on_export_success(
                            client,
                            Export.from_dict(evt.json()),
                            node)
                    except:
                        update_status(node, traceback.format_exc())
                elif evt.event == "export_error":
                    update_status(node, "Export error")

                elif evt.event == "avatar_upload_success":
                    try:
                        await on_avatar_upload_success(
                            client,
                            AvatarPublic.from_dict(evt.json()),
                            node)
                    except:
                        update_status(node, traceback.format_exc())
                elif evt.event == "avatar_upload_err":
                    update_status(node, f"Avatar upload error: {evt.data}")
                elif evt.event == "avatar_autorig_success":
                    await on_avatar_autorig_success(
                        client,
                        AvatarPublic.from_dict(evt.json()),
                        node)
                elif evt.event == "avatar_autorig_err":
                    update_status(node, f"Autorig error: {evt.data}")
                elif evt.event == "avatar_mapping_success":
                    await on_avatar_mapping_success(
                        client,
                        AvatarPublic.from_dict(evt.json()),
                        node)
                elif evt.event == "avatar_mapping_err":
                    update_status(node, f"Mapping error: {evt.data}")
                elif evt.event == "avatar_export_success":
                    await on_avatar_export_success(
                        client,
                        AvatarExport.from_dict(evt.json()),
                        node)
                elif evt.event == "avatar_export_error":
                    update_status(node, f"Export error: {evt.data}")
                elif evt.event == "animation_retarget_success":
                    await on_animation_retarget_success(
                        client,
                        OrmAnimation.from_dict(evt.json()),
                        node)
                elif evt.event == "animation_retarget_err":
                    update_status(node, f"Retarget error: {evt.data}")
                elif evt.event == "usage_report":
                    update_status(node, evt.data)
                    await display_credits(evt.data, node)
                else:
                    if node.parm("debug_log").eval() and evt.event == "debug":
                        update_status(node, str(evt))
                    else:
                        # print irrelevant messages only in the console
                        print(evt)
    except:
        print(traceback.format_exc())
    finally:
        update_status(node, "Exiting sse loop")

def sysopen(file: str):
    if sys.platform == "win32":
        os.system(f"start \"\" {file}")
    elif sys.platform == "darwin":
        os.system(f"open \"\" {file}")
    else:
        os.system(f"xdg-open {file}")

def get_avatar_from_cache(node: hou.Node, avatar_name: str) -> AvatarPublic | None:
    return next((avatar for avatar in node.cachedUserData("avatars") if avatar.label == avatar_name),
                None)

def get_avatar_rebuilt_from_cache(node: hou.Node, avatar_name: str) -> AvatarRebuilt | None:
    return next((avatar
                 for avatar in node.cachedUserData("avatars_rebuilt")
                 if avatar.label == avatar_name),
                None)

async def send_chat(client: AuthenticatedClient, chat_thread: ChatThreadInList, prompt, node: hou.Node):
    """ Final result is received by sse, animation_success or animation_error.
    """
    update_animation_status(node, "")

    update_status(node, "Sending chat")
    history = node.cachedUserData("cairos_history")
    if history is None:
        history = []

    try:
        prompt_message = HumanMessage(
            id=uuid4().hex,
            content=prompt)

        response = await process_message_thread_thread_id_post.asyncio(
            thread_id=chat_thread.id,
            client=client,
            body=ChatInput(
                prompt=prompt_message,
                history=[m.data for m in history],
                btl_objs=[]),
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))

        if isinstance(response, ChatOutput):
            messages = list(map(lambda m: StoredMessage.from_dict(m),
                                response.messages))
            if response.animation:
                update_status(node, f"Chat response received. Waiting for animation sequence.")
                update_animation_status(
                    node,
                    f"{response.animation.description}\n" +
                    f"\n".join(map(
                        lambda motion: f"{motion.sg_id:>10} | {motion.description}",
                        response.animation.sequence)))
            else:
                update_status(node, f"Chat response received.")

            messages.insert(
                0,
                StoredMessage(
                    type_=StoredMessageType.HUMAN,
                    data=prompt_message))

            update_chat_display_messages(
                node,
                [m.data
                 for m in messages
                 if ((isinstance(m.data, AIMessage) or isinstance(m.data, HumanMessage))
                     and m.data.content)])

            update_chat_history(node, messages)
            print(f"Messages are: {response.messages}")

    except UnexpectedStatus as e:
        update_status(node, f"Request error: {e.status_code}")
        if e.status_code == 426:
            content = json.loads(e.content)
            button_res = hou.ui.displayMessage(
                content["detail"],
                title="Cairos error",
                buttons=("Open webiste", "Ok"),
                default_choice=1,
                close_choice=1)

            if button_res == 0:
                update_status(node, "Opening website")
                sysopen("https://cairos.outseta.com/profile?tab=planChange")

            update_status(node, content["detail"])

    except Exception as e:
        update_status(node, f"Request error: {traceback.format_exc()}")

async def export_animation(client: AuthenticatedClient, thread_id: str, trigger_msg: UUID, node: hou.Node):
    """ Final result is received by sse, export_success or export_error.
    """
    await export_anim_anim_thread_id_trigger_msg_id_export_post.asyncio(
        thread_id=thread_id,
        trigger_msg_id=trigger_msg.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
        cairos_session=cairos_python_client.get_session(client._cookies))

    update_status(node, "Export response received. Waiting for export to complete.")

async def retarget_latest_animation(
        client: AuthenticatedClient,
        node: hou.Node,
        avatar_name: str):
    try:
        animation: OrmAnimation | None = node.cachedUserData("latest_animation")
        if not animation:
            hou.ui.displayMessage("No animation found in cache")
            return

        return await send_retarget(
            client,
            animation.job_thread,
            animation.job_trigger,
            avatar_name,
            node)
    except:
        hou.ui.displayMessage(traceback.format_exc())

async def send_retarget(
        client: AuthenticatedClient,
        thread_id: str,
        trigger_msg: UUID,
        avatar_name: str,
        node: hou.Node):
    avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
    if avatar is None:
        hou.ui.displayMessage(f"Avatar does not exist: {avatar_name}")
        return

    await retarget_anim_anim_thread_id_trigger_msg_id_retarget_avatar_id_post.asyncio(
        thread_id=thread_id,
        trigger_msg_id=trigger_msg.hex,
        avatar_id=avatar.id.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
        cairos_session=cairos_python_client.get_session(client._cookies))

    update_status(node, "Retarget response received. Waiting for retarget to complete.")

async def autorig_avatar(client: AuthenticatedClient, avatar_name: str, node: hou.Node):
    """ Final result is received by sse, avatar_autorig_success or avatar_autorig_err.
    """
    try:
        avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
        assert avatar, "Avatar not found"
        update_status(node, f"Sending autorig for {avatar_name}")

        await trigger_autorig_avatar_uuid_autorig_post.asyncio(
            uuid=avatar.id.hex,
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))

        update_status(node, "Autorig response received. Wait for process to complete.")
    except Exception as e:
        update_status(node, f"Error when requesting autorig: {e}")

async def llm_map_avatar(client: AuthenticatedClient, avatar_name: str, node: hou.Node):
    try:
        avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
        assert avatar, "Avatar not found"
        update_status(node, f"Sending autorig for {avatar_name}")

        await update_avatar_mapping_llm_avatar_uuid_llm_mapping_patch.asyncio(
            uuid=avatar.id.hex,
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))
    except Exception as e:
        update_status(node, f"Error when requesting automapping: {e}")

async def create_avatar(client: AuthenticatedClient, avatar_name: str, node: hou.Node):
    update_status(node, f"Creating avatar {avatar_name}")
    try:
        res = await create_blank_avatar_avatar_new_label_post.asyncio(
            avatar_name,
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))
    except Exception as e:
        update_status(node, f"Error while creating avatar: {e}")
        return

    if isinstance(res, AvatarPublic):
        update_status(node, f"Avatar created: {res}")
        await reload_avatars_cache(client, node)
    else:
        update_status(node, f"Error while creating avatar: {res}")

async def upload_avatar(
        client: AuthenticatedClient,
        avatar_name: str,
        avatar_geo_node: hou.SopNode,
        node: hou.Node):
    """ Final result is received by sse, avatar_upload_success or avatar_upload_err.
    """
    clear_status(node)
    update_status(node, f"Uploading avatar {avatar_name}")
    try:
        avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)

        if avatar is None:
            update_status(node, "Avatar was not found. Creating a new one.")
            avatar_resp = await create_blank_avatar_avatar_new_label_post.asyncio(
                label=avatar_name,
                client=client,
                outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
                cairos_session=cairos_python_client.get_session(client._cookies))

            update_status(node, "Created new avatar.")
            if avatar_resp and not isinstance(avatar_resp, HTTPValidationError):
                avatar = avatar_resp
                avatars_cache = node.cachedUserData("avatars")
                avatars_cache.append(avatar)
                node.setCachedUserData("avatars", avatars_cache)

        assert avatar, "No avatar selected"

        tmp: tuple[int, str] = tempfile.mkstemp(
            prefix=f"cairos_{avatar_name}",
            suffix=".bgeo",
            dir=node.parm("tempdir").eval())

        # TODO for now do not delete temporary file
        with open(tmp[1], "wb+") as f:
            update_status(node, "Exporting geometry for avatar...")
            avatar_geo_node.geometry().saveToFile(f.name)
            update_status(node, f"Saved geometry to {f.name}")
            update_status(node, "Geometry exported, uploading.")

            await post_avatar_avatar_uuid_upload_post.asyncio(
                uuid=avatar.id.hex,
                client=client,
                body=BodyPostAvatarAvatarUuidUploadPost(
                    file=File(
                        payload=f,
                        file_name=f.name)),
                outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
                cairos_session=cairos_python_client.get_session(client._cookies))

            update_status(node, "Avatar file uploaded. Wait for processing.")
    except:
        update_status(node, traceback.format_exc())

async def export_avatar(client: AuthenticatedClient, avatar_name: str, node: hou.Node):
    """ Final result is received by sse, avatar_export_success or avatar_export_err.
    """

    try:
        avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
        assert avatar, "Avatar not found"
        update_status(node, f"Sending avatar export for {avatar.label}")
        await trigger_export_avatar_uuid_export_post.asyncio(
            uuid=avatar.id.hex,
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))

        update_status(node, "Avatar export response received. Wait for process to complete.")
    except:
        update_status(node, traceback.format_exc())


async def delete_avatar(client: AuthenticatedClient, node: hou.Node, avatar_name: str):
    try:
        avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
        assert avatar, "Avatar not found"
        update_status(node, f"Deleting avatar {avatar_name}")
        await delete_avatar_route_avatar_uuid_delete.asyncio(
            uuid=str(avatar.id),
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))
        await reload_avatars_cache(client, node)
        update_status(node, "Deleted avatar")

    except:
        update_status(node, traceback.format_exc())

async def on_sequencer_success(client: AuthenticatedClient, animation: OrmAnimation, node: hou.Node):
    # trigger export
    # how to get context
    """ sse handler """
    try:
        update_status(node, "Received sequencer success.")
        node.setCachedUserData("latest_animation", animation)
        update_status(node, "Sending export request")
        await export_animation(client, animation.job_thread, animation.job_trigger, node)
    except:
        hou.ui.displayMessage(f"Error when processing sequence: {traceback.format_exc()}")

async def on_avatar_upload_success(client: AuthenticatedClient, avatar: AvatarPublic, node: hou.Node):
    """ sse handler """
    update_status(node, "Received upload processing success. Requesting export, please wait...")
    await reload_avatars_cache(client, node)
    await export_avatar(client, avatar.label, node)
    await update_avatar_status(client, node, avatar.label)

async def on_avatar_autorig_success(client: AuthenticatedClient, avatar: AvatarPublic, node: hou.Node):
    """ sse handler. Do not do anything, just notify """
    update_status(node, "Autorig successful. Requesting export, please wait...")
    await reload_avatars_cache(client, node)
    await export_avatar(client, avatar.label, node)
    await update_avatar_status(client, node, avatar.label)

async def on_avatar_mapping_success(client: AuthenticatedClient, avatar: AvatarPublic, node: hou.Node):
    """ sse handler. Do not do anything, just notify """
    update_status(node, "Mapping successful. Requesting export, please wait...")
    await reload_avatars_cache(client, node)
    await export_avatar(client, avatar.label, node)
    await update_avatar_status(client, node, avatar.label)

async def on_avatar_export_success(client: AuthenticatedClient, avatar_export: AvatarExport, node: hou.Node):
    """ sse handler """
    update_status(node, "Received export processing success.")
    output_directory = await download_exported_avatar(
        client,
        avatar_export,
        Path(node.parm("tempdir").eval()),
        node)
    update_status(node, "Export downloaded. Unpacking and loading.")
    # TODO set paths from export in scene.
    return await load_exported_avatar(output_directory, node)

async def download_export(client: AuthenticatedClient, export: Export, temp_dir: Path, node: hou.Node) -> Path:
    """ Note: on windows mkdir does not allow paths will colon in them
    """
    time_string = datetime.now().isoformat().replace(":", "_")
    animation: OrmAnimation | HTTPValidationError | None = await get_anim_anim_thread_id_trigger_msg_id_get.asyncio(
        client=client,
        thread_id=export.job_thread,
        trigger_msg_id=export.job_trigger.hex,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    # This shouldn't ever fail
    assert isinstance(animation, OrmAnimation), f"Animation for export was not found: {export}"
    time_and_name = "_".join((time_string, animation.nice_name or ""))
    base_dir = temp_dir\
        .joinpath("animations")\
        .joinpath(time_and_name)


    filename = base_dir\
        .joinpath(f"{export.job_thread}_{export.job_trigger}")\
        .with_suffix(Path(export.filepath).suffix)

    out_dir = base_dir\
        .joinpath(f"{export.job_thread}_{export.job_trigger}/extracted")
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    # Download content with explicit client get. This probably does not work in api?
    result = await client.get_async_httpx_client().get(
        url=f"{client._base_url}/anim/{export.job_thread}/{export.job_trigger.hex}/download")

    update_status(node, f"Download complete: {result}")
    with open(filename, "wb") as f:
        f.write(result.content)
        update_status(node, f"Wrote {filename}")

    if sys.platform == "win32":
        # on Windows, long paths need this prefix to work (with some operations)
        filename = "\\\\?\\" + str(filename)

    shutil.unpack_archive(filename, out_dir)

    downloads = node.cachedUserData("downloaded_animations")
    downloads.append((time_and_name, out_dir))
    node.setCachedUserData("downloaded_animations", downloads)
    node.parm("select_exported_animation").set(time_and_name)

    return out_dir

async def download_exported_avatar(
        client: AuthenticatedClient,
        avatar_export: AvatarExport,
        temp_dir: Path,
        node: hou.Node):
    time_string = datetime.now().isoformat().replace(":", "_")
    avatar: AvatarPublic | HTTPValidationError | None = await get_avatar_avatar_uuid_get.asyncio(
        uuid=avatar_export.avatar_id.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    assert isinstance(avatar, AvatarPublic), f"Avatar for export not found: {avatar_export}"
    time_and_name = "_".join((time_string, avatar.label))
    base_dir = temp_dir\
        .joinpath("avatars")\
        .joinpath(time_and_name)

    filename = base_dir\
        .joinpath(f"{avatar_export.avatar_id}")\
        .with_suffix(Path(avatar_export.filepath).suffix)

    out_dir = base_dir\
        .joinpath(f"{avatar_export.avatar_id}/extracted")

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    # Download content with explicit client get. This probably does not work in api?
    result = await client.get_async_httpx_client().get(
        url=f"{client._base_url}/avatar/{avatar_export.avatar_id}/download")

    update_status(node, f"Download complete: {result}")
    with open(filename, "wb") as f:
        f.write(result.content)
        update_status(node, f"Wrote {filename}")

    if sys.platform == "win32":
        # on Windows, long paths need this prefix to work (with some operations)
        filename = "\\\\?\\" + str(filename)

    shutil.unpack_archive(filename, out_dir)

    downloads = node.cachedUserData("downloaded_avatars")
    downloads.append((time_and_name, out_dir))
    node.setCachedUserData("downloaded_avatars", downloads)
    node.parm("select_exported_avatar").set(time_and_name)

    return out_dir

async def download_avatar_rebuilt(
        client: AuthenticatedClient,
        avatar_name: str,
        temp_dir: Path,
        node: hou.Node):
    time_string = datetime.now().isoformat().replace(":", "_")
    update_status(node, f"Starting rebuilt avatar download: {avatar_name}")
    avatar_rebuilt = get_avatar_rebuilt_from_cache(
        node,
        avatar_name)

    assert isinstance(avatar_rebuilt , AvatarRebuilt), f"Rebuilt avatar not found: {avatar_name}"
    time_and_name = "_".join((time_string, avatar_rebuilt.label))
    base_dir = temp_dir\
        .joinpath("avatars_rebuilt")\
        .joinpath(time_and_name)

    filename = base_dir\
        .joinpath(f"{avatar_rebuilt.id}")\
        .with_suffix(Path(avatar_rebuilt.filepath).suffix)

    out_dir = base_dir\
        .joinpath(f"{avatar_rebuilt.id}/extracted")

    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    # Download content with explicit client get. This probably does not work in api?
    result = await client.get_async_httpx_client().get(
        url=f"{client._base_url}/avatar_rebuilt/{avatar_rebuilt.id}/download")

    update_status(node, f"Download complete: {result}")
    with open(filename, "wb") as f:
        f.write(result.content)
        update_status(node, f"Wrote {filename}")

    if sys.platform == "win32":
        # on Windows, long paths need this prefix to work (with some operations)
        filename = "\\\\?\\" + str(filename)

    shutil.unpack_archive(filename, out_dir)

    downloads = node.cachedUserData("downloaded_avatars_rebuilt")
    downloads.append((time_and_name, out_dir))
    node.setCachedUserData("downloaded_avatars_rebuilt", downloads)
    node.parm("select_exported_avatar_rebuilt").set(time_and_name)

    return out_dir

async def check_credits(client: AuthenticatedClient, node: hou.Node):
    result = await check_credit_balance_credit_balance_get.asyncio(
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    update_status(node, f"Result: {result}")
    assert isinstance(result, str)
    await display_credits(result, node)
    hou.ui.displayMessage(
        result,
        title="Cairos credits")

async def display_credits(credits: str, node: hou.Node):
    node.parm("credits").set(credits)

async def load_exported_avatar(output_directory: Path, node: hou.Node):
    avatar_file = output_directory.joinpath("output_autorig.bgeo.sc")

    if avatar_file:
        node.node("file_character").parm("file").set(str(avatar_file))

    update_status(node, f"Loaded export assets: {avatar_file}. Done.")

async def load_exported_animation(output_directory: Path, node: hou.Node):
    retargeted = output_directory.joinpath("output_full.bgeo.sc")

    if retargeted:
        node.node("file_animation").parm("file").set(str(retargeted))
        node.node("file_animation").parm("reload").pressButton()

    update_status(node, "Loaded export assets. Done.")

async def on_animation_retarget_success(client: AuthenticatedClient, animation: OrmAnimation, node: hou.Node):
    update_status(node, f"Retarget successful! {animation.job_thread} {animation.job_trigger}.\nTriggering export")
    res = await export_animation(client, thread_id=animation.job_thread, trigger_msg=animation.job_trigger, node=node)
    update_status(node, f"Export submitted: {res}")

async def on_export_success(client: AuthenticatedClient, export: Export, node: hou.Node):
    # download archive
    # unpack it
    # use contents
    """ sse handler """
    update_status(node, "Export successful. Downloading export artifacts.")
    output_directory = await download_export(
        client,
        export,
        Path(node.parm("tempdir").eval()),
        node)
    update_status(node, "Export downloaded. Unpacking and loading.")
    # TODO set paths from export in scene.
    return await load_exported_animation(output_directory, node)

async def start_sse_listener(client: AuthenticatedClient, node: hou.Node):
    await sse_handler(client, node)

def update_status(node: hou.Node, status: str):
    q: deque | None = node.cachedUserData("status_queue")
    if q is None:
        q = deque(maxlen=5)

    q.append(f"{datetime.now().isoformat()}: {status}")
    print(status)
    return node.parm("status").set("\n".join([msg for msg in q]))

def update_animation_status(node: hou.Node, status: str):
    return node.parm("animation_status").set(status)

def update_chat_display_messages(node: hou.Node, messages: list[HumanMessage | AIMessage]):
    """ Pushes messages on a queue.
    This is meant for visualization in the hda interface, in contrast to chat history.
    It only contains human and ai messages.
    """
    chat_queue: deque | None = node.cachedUserData("chat_queue")
    username = node.userData("cairos_user")
    if chat_queue is None:
        chat_queue = deque(maxlen=10)
        node.setCachedUserData("chat_queue", chat_queue)

    chat_queue.extend([f"{datetime.now().isoformat()} [{'ai' if msg.type_ == StoredMessageType.AI else username}]: {msg.content}" for msg in messages if msg != ""])
    return node.parm("chat_display_messages").set("\n".join(msg for msg in chat_queue))

def update_chat_history(node: hou.Node, messages: list[StoredMessage]):
    """ Keeps messages in a list, which gets sent
    with chat requests. This provides the "history" functionality of chat.
    """
    history = node.cachedUserData("cairos_history")
    if history is None:
        history = []
    node.setCachedUserData("cairos_history", history + messages)

async def update_avatar_status(client: AuthenticatedClient, node: hou.Node, avatar_name: str):
    avatar: AvatarPublic | None = get_avatar_from_cache(node, avatar_name)
    if not avatar:
        print(f"Avatar not found: {avatar_name}")
        return

    if avatar.status:
        return node.parm("avatar_status").set(",".join(str(a) for a in avatar.status))

async def reload_avatars_cache(client: AuthenticatedClient, node: hou.Node):
    try:
        response = await get_avatars_avatar_get.asyncio_detailed(
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""),
            cairos_session=cairos_python_client.get_session(client._cookies))

        cookies = cairos_python_client.parse_cookies(response.headers.get("Set-Cookie"))
        if "cairos_session" in cookies and "cairos_session" not in client._cookies:
            update_status(node, f"Setting session: {cookies['cairos_session']}")
            client._cookies.update({
                "cairos_session": cookies["cairos_session"]})

        avatars = response.parsed
        update_status(node, f"Loaded avatars")

        return node.setCachedUserData("avatars", avatars)
    except:
        update_status(node, traceback.format_exc())

async def reload_avatars_rebuilt_cache(client: AuthenticatedClient, node: hou.Node):
    try:
        response = await get_avatars_rebuilt_avatar_rebuilt_get.asyncio_detailed(
            client=client,
            outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

        cookies = cairos_python_client.parse_cookies(response.headers.get("Set-Cookie"))
        if "cairos_session" in cookies and "cairos_session" not in client._cookies:
            update_status(node, f"Setting session: {cookies['cairos_session']}")
            client._cookies.update({
                "cairos_session": cookies["cairos_session"]})

        avatars = response.parsed
        update_status(node, f"Loaded rebuilt avatars")

        return node.setCachedUserData("avatars_rebuilt", avatars)
    except:
        update_status(node, traceback.format_exc())

def clear_status(node: hou.Node):
    q: deque | None = node.cachedUserData("status_queue")
    if q is not None:
        q.clear()
    return node.parm("status").set("")

def clear_chat(node: hou.Node):
    chat_queue: deque | None = node.cachedUserData("chat_queue")
    if chat_queue is not None:
        chat_queue.clear()
    return node.parm("chat_display_messages").set("")

async def clear_exported_animations(node: hou.Node):
    for d in Path(node.parm("tempdir").eval()).joinpath("animations").iterdir():
        shutil.rmtree(d)

    node.setCachedUserData("downloaded_animations", [])

async def clear_exported_avatars(node: hou.Node):
    for d in Path(node.parm("tempdir").eval()).joinpath("avatars").iterdir():
        shutil.rmtree(d)

    node.setCachedUserData("downloaded_avatars", [])

def clear(node: hou.Node):
    node.parm("prompt").set("")
    clear_status(node)
    clear_chat(node)
    update_animation_status(node, "")
    client = node.cachedUserData("cairos_client")
    thread = cairos_python_client.create_thread(client=client)
    node.setCachedUserData("current_thread", thread)
    node.setCachedUserData("cairos_history", [])

def on_exit(loop: asyncio.AbstractEventLoop):
    async def ashutdown(loop):
        tasks = [task for task in asyncio.all_tasks(loop) if task is not
             asyncio.current_task(loop)]
        list(map(lambda task: task.cancel(), tasks))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
    asyncio.run_coroutine_threadsafe(ashutdown(loop), loop).result()

async def close_client(client: AuthenticatedClient, node: hou.Node):
    q: deque | None = node.cachedUserData("status_queue")
    cq: deque | None = node.cachedUserData("chat_queue")
    if q:
        q.clear()
    if cq:
        cq.clear()

    try:
        await client.get_async_httpx_client().aclose()
    except:
        print(traceback.format_exc())
    finally:
        node.destroyCachedUserData("cairos_sse_iter")
        node.destroyCachedUserData("cairos_client")

def parse_existing_downloads(temp_dir: Path) -> list[tuple[str, str]]:
    downloads = []
    if temp_dir.exists():
        for sub in temp_dir.iterdir():
            download_file = next(sub.glob("**/output_full.bgeo.sc"), None)
            if download_file:
                downloads.append((sub.name, download_file.parent))
    else:
        temp_dir.mkdir(parents=True, exist_ok=True)

    return downloads

def parse_existing_avatar_downloads(temp_dir: Path) -> list[tuple[str, str]]:
    downloads = []
    if temp_dir.exists():
        for sub in temp_dir.iterdir():
            download_file = next(sub.glob("**/output_autorig.bgeo.sc"), None)
            if download_file:
                downloads.append((sub.name, download_file.parent))
    else:
        temp_dir.mkdir(parents=True, exist_ok=True)

    return downloads

async def handle_login(url, username, password, node):
    try:
        node.setCachedUserData("status_queue", deque(maxlen=5))
        node.setCachedUserData("chat_queue", deque(maxlen=10))
        node.setCachedUserData(
            "downloaded_animations",
            parse_existing_downloads(Path(node.parm("tempdir").eval()).joinpath("animations")))
        node.setCachedUserData(
            "downloaded_avatars",
            parse_existing_avatar_downloads(Path(node.parm("tempdir").eval()).joinpath("avatars")))

        node.parm("status").set("")
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

        node.setUserData("cairos_url", url)
        node.setUserData("cairos_user", username)

        if client:
            node.setCachedUserData("cairos_client", client)
            update_status(node, "logged in")

            sess_id = await get_session_id_session_id_get.asyncio(
                client=client,
                outseta_nocode_access_token=client._cookies.get(
                    cairos_python_client.token_cookie_name, ""))
            if isinstance(sess_id, str):
                client._cookies["cairos_session"] = sess_id
            else:
                update_status(node, f"Failed while getting session id {sess_id}")

            loop = asyncio.get_event_loop()
            loop.create_task(start_sse_listener(client, node))

            # start out with a new thread
            chat_thread: ChatThreadPublic | HTTPValidationError | None = await new_thread_thread_post.asyncio(
                client=client,
                outseta_nocode_access_token=client._cookies.get(
                    cairos_python_client.token_cookie_name, ""))

            assert isinstance(chat_thread, ChatThreadPublic)
            node.setCachedUserData("current_thread", chat_thread)
            await reload_avatars_cache(client, node)
        else:
            update_status(node, "could not log in")
    except Exception:
        update_status(node, f"Error!!! {traceback.format_exc()}")
