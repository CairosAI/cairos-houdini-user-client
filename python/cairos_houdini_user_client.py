import hou
import json
import asyncio
from pathlib import Path

import cairos_python_client

from cairos_python_lowlevel.cairos_python_lowlevel.models.avatar_metadata import AvatarMetadata
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_input import ChatInput
from cairos_python_lowlevel.cairos_python_lowlevel.models.chat_thread_in_list import ChatThreadInList
from cairos_python_lowlevel.cairos_python_lowlevel.models.human_message import HumanMessage
from cairos_python_lowlevel.cairos_python_lowlevel.models.orm_animation import OrmAnimation
from cairos_python_lowlevel.cairos_python_lowlevel.models.export import Export

from cairos_python_lowlevel.cairos_python_lowlevel.client import Client, AuthenticatedClient
from cairos_python_lowlevel.cairos_python_lowlevel.api.default import process_message_thread_thread_id_post, export_anim_anim_thread_id_trigger_msg_id_export_post

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
            if client.get_async_httpx_client().is_closed:
                print("Client is closed. Stopping SSE")
                return

            # print(evt)
            if evt.event == "animation_success":
                update_status(node, "Animation success")
                await on_sequencer_success(
                    client,
                    OrmAnimation.from_dict(evt.json()))
            elif evt.event == "animation_error":
                print(f"Animation error {evt}")
                update_status(node, "Animation error")
            elif evt.event == "export_success":
                try:
                    update_status(node, "Export success")
                    await on_export_success(
                        client,
                        Export.from_dict(evt.json()))
                except:
                    traceback.print_exc()
            elif evt.event == "export_error":
                print(f"Export error {evt}")
                update_status(node, "Export error")
            else:
                print(evt)

    print("Exiting sse loop")

async def send_chat(client: AuthenticatedClient, avatar: AvatarMetadata, chat_thread: ChatThreadInList, prompt, node: hou.Node):
    print(f"Sending chat {prompt}")
    update_status(node, "Sending chat")
    await process_message_thread_thread_id_post.asyncio(
        thread_id=chat_thread.id,
        client=client,
        body=ChatInput(
            prompt=HumanMessage(
                id=uuid4().hex,
                content=prompt),
            history=[],
            avatar=avatar,
            btl_objs=[]),
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print("Chat response received")
    update_status(node, "Chat response received")

async def send_export(client: AuthenticatedClient, thread_id: str, trigger_msg: UUID):
    res = await export_anim_anim_thread_id_trigger_msg_id_export_post.asyncio(
        thread_id=thread_id,
        trigger_msg_id=trigger_msg.hex,
        client=client,
        outseta_nocode_access_token=client._cookies.get(cairos_python_client.token_cookie_name, ""))

    print("Export response received")
    print(res)

async def on_sequencer_success(client: AuthenticatedClient, animation: OrmAnimation):
    # trigger export
    # how to get context
    print("Received sequencer success. Triggering export")
    try:
        await send_export(client, animation.job_thread, animation.job_trigger)
    except:
        traceback.print_exc()

async def download_export(client: AuthenticatedClient, export: Export):
    filename = Path(hou.getenv("HOUDINI_TEMP_DIR")).with_suffix(
        Path(export.filepath).suffix)
    result = await client.get_async_httpx_client().get(
        url=f"{client._base_url}/anim/{export.job_thread}/{export.job_trigger.hex}/download")

    with open(filename, "wb") as f:
        f.write(result.content)
        print(f"Wrote {filename}")

    print("Download complete")
    print(result)

async def on_export_success(client: AuthenticatedClient, export: Export):
    # download archive
    # unpack it
    # use contents
    print("Export successful")
    print(export)
    res = await download_export(client, export)
    print("Downloaded export")
    print(res)

def start_sse_listener(client: AuthenticatedClient, node: hou.Node):
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    asyncio.run_coroutine_threadsafe(sse_handler(client, node), loop)
    print(f"Started sse handler with {client}")

def update_status(node: hou.Node, status: str):
    return node.parm("status").set(status)

def on_exit(loop: asyncio.AbstractEventLoop):
    future = asyncio.run_coroutine_threadsafe(async_shutdown_tasks(loop), loop)
    future.result()

    print("Stopping event loop")
    loop.call_soon_threadsafe(loop.stop)
    loop.call_soon_threadsafe(loop.close)


async def close_client(client: AuthenticatedClient):
    print("Closing http client")
    await client.get_async_httpx_client().aclose()
