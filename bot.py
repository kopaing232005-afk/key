import logging
import json
import base64
import re
from datetime import datetime, timedelta
import aiohttp
import aiohttp.web
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

BOT_TOKEN = "8977269583:AAELV4xBTgQDftA3I8z5hCXELOwHHIh0I-I"
GITHUB_TOKEN = "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"
REPO_OWNER = "kopaing232005-afk"
REPO_NAME = "key"
FILE_PATH = "key.json"

ADMIN_IDS = [7070690379]
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

RENDER_APP_URL = os.getenv("RENDER_EXTERNAL_URL", "https://key-rkwt.onrender.com")

async def handle_ping(request):
    return aiohttp.web.Response(text="Bot is Alive!")

async def self_ping():
    await asyncio.sleep(5)
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(RENDER_APP_URL) as response:
                    if response.status == 200:
                        logging.info("🔄 Self-Ping Successful: Bot kept alive.")
                    else:
                        logging.warning(f"⚠️ Self-Ping Warning: Status code {response.status}")
            except Exception as e:
                logging.error(f"❌ Self-Ping Failed: {e}")
            await asyncio.sleep(300)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return

    await update.message.reply_text(
        "👋 **AIDEN ID License Manager Bot**\n\n"
        "📝 **Usage Format:**\n"
        "👉 Add ID: `/add <Device_ID> <Time><Unit>`\n"
        "👉 Delete ID: `/del <Device_ID>`\n"
        "👉 List IDs: `/list`\n\n"
        "💡 **Units:**\n"
        "👉 `min` = Minutes -> Ex: `/add A1B2C3D4 10min`\n"
        "👉 `h` = Hours -> Ex: `/add A1B2C3D4 5h`\n"
        "👉 `D` = Days -> Ex: `/add A1B2C3D4 7D`\n"
        "👉 `m` = Months -> Ex: `/add A1B2C3D4 1m`\n\n"
        "ℹ️ *Default: 30 Minutes (If time is empty)*",
        parse_mode="Markdown"
    )

async def add_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return

    if not context.args:
        await update.message.reply_text("❌ Please provide a Device ID.\nUsage: `/add <Device_ID>`", parse_mode="Markdown")
        return

    device_id = context.args[0].upper()
    current_time = datetime.utcnow() + timedelta(hours=6, minutes=30)
    
    expire_datetime = None
    display_text = "30 Minutes"

    if len(context.args) > 1:
        time_input = context.args[1].strip()
        match = re.match(r"^(\d+)(min|h|D|m)$", time_input)
        
        if not match:
            await update.message.reply_text("❌ Invalid format! Use: `10min`, `5h`, `7D`, or `1m`")
            return
        
        value = int(match.group(1))
        unit = match.group(2)

        if unit == "min":
            expire_datetime = (current_time + timedelta(minutes=value)).strftime("%Y-%m-%d %H:%M")
            display_text = f"{value} Minutes"
        elif unit == "h":
            expire_datetime = (current_time + timedelta(hours=value)).strftime("%Y-%m-%d %H:%M")
            display_text = f"{value} Hours"
        elif unit == "D":
            expire_datetime = (current_time + timedelta(days=value)).strftime("%Y-%m-%d %H:%M")
            display_text = f"{value} Days"
        elif unit == "m":
            expire_datetime = (current_time + timedelta(days=value * 30)).strftime("%Y-%m-%d %H:%M")
            display_text = f"{value} Months"
    else:
        expire_datetime = (current_time + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    status_msg = await update.message.reply_text("⏳ Connecting to GitHub database...")

    async with aiohttp.ClientSession() as session:
        async with session.get(GITHUB_API_URL, headers=headers) as resp:
            if resp.status != 200:
                await status_msg.edit_text(f"❌ Failed to fetch data from GitHub. (Error Code: {resp.status})")
                return
            
            repo_data = await resp.json()
            sha = repo_data["sha"]
            file_content = base64.b64decode(repo_data["content"]).decode("utf-8")
            
            try:
                json_data = json.loads(file_content)
            except json.JSONDecodeError:
                json_data = {"devices": []}

        devices_list = json_data.get("devices", [])
        found = False
        for item in devices_list:
            if item["id"] == device_id:
                item["status"] = "active"
                item["expire"] = expire_datetime
                found = True
                break
        
        if not found:
            devices_list.append({"id": device_id, "status": "active", "expire": expire_datetime})
        
        json_data["devices"] = devices_list
        updated_content = json.dumps(json_data, indent=4)
        encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")
        
        commit_data = {"message": f"Telegram Bot: Added/Updated Device ID {device_id}", "content": encoded_content, "sha": sha}
        async with session.put(GITHUB_API_URL, headers=headers, json=commit_data) as put_resp:
            if put_resp.status in [200, 201]:
                await status_msg.edit_text(
                    f"✅ **Success!**\n\n"
                    f"📱 **Device ID:** `{device_id}`\n"
                    f"⏳ **Expire:** `{expire_datetime}` ({display_text})\n"
                    f"🟢 **Status:** `active`",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(f"❌ GitHub update failed. (Error Code: {put_resp.status})")

async def delete_device_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return

    if not context.args:
        await update.message.reply_text("❌ Please provide a Device ID.\nUsage: `/del <Device_ID>`", parse_mode="Markdown")
        return

    device_id = context.args[0].upper()
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    status_msg = await update.message.reply_text("⏳ Connecting to GitHub database...")

    async with aiohttp.ClientSession() as session:
        async with session.get(GITHUB_API_URL, headers=headers) as resp:
            if resp.status != 200:
                await status_msg.edit_text(f"❌ Failed to fetch data from GitHub. (Error Code: {resp.status})")
                return
            
            repo_data = await resp.json()
            sha = repo_data["sha"]
            file_content = base64.b64decode(repo_data["content"]).decode("utf-8")
            
            try:
                json_data = json.loads(file_content)
            except json.JSONDecodeError:
                json_data = {"devices": []}

        devices_list = json_data.get("devices", [])
        
        original_count = len(devices_list)
        devices_list = [item for item in devices_list if item["id"] != device_id]
        
        if len(devices_list) == original_count:
            await status_msg.edit_text(f"❌ Device ID `{device_id}` not found in database.", parse_mode="Markdown")
            return

        json_data["devices"] = devices_list
        updated_content = json.dumps(json_data, indent=4)
        encoded_content = base64.b64encode(updated_content.encode("utf-8")).decode("utf-8")
        
        commit_data = {"message": f"Telegram Bot: Deleted Device ID {device_id}", "content": encoded_content, "sha": sha}
        async with session.put(GITHUB_API_URL, headers=headers, json=commit_data) as put_resp:
            if put_resp.status in [200, 201]:
                await status_msg.edit_text(
                    f"🗑️ **Deleted Successfully!**\n\n"
                    f"📱 **Device ID:** `{device_id}` has been removed.",
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(f"❌ GitHub update failed. (Error Code: {put_resp.status})")

async def list_devices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    status_msg = await update.message.reply_text("⏳ Fetching device list from GitHub...")

    async with aiohttp.ClientSession() as session:
        async with session.get(GITHUB_API_URL, headers=headers) as resp:
            if resp.status != 200:
                await status_msg.edit_text(f"❌ Failed to fetch data. (Error Code: {resp.status})")
                return
            
            repo_data = await resp.json()
            file_content = base64.b64decode(repo_data["content"]).decode("utf-8")
            
            try:
                json_data = json.loads(file_content)
            except json.JSONDecodeError:
                json_data = {"devices": []}

    devices_list = json_data.get("devices", [])
    
    if not devices_list:
        await status_msg.edit_text("📱 **No registered devices found in the database.**", parse_mode="Markdown")
        return

    groups = {}
    for device in devices_list:
        dev_id = device.get("id", "UNKNOWN")
        id_len = len(dev_id)
        if id_len not in groups:
            groups[id_len] = []
        groups[id_len].append(device)

    sorted_lengths = sorted(groups.keys(), reverse=True)

    response_text = f"📋 **Registered Devices List ({len(devices_list)})**\n"
    response_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

    for length in sorted_lengths:
        devs_in_group = groups[length]
        response_text += f"\n📊 **{length}-Digit IDs (Total: {len(devs_in_group)})**\n"
        response_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        
        for index, device in enumerate(devs_in_group, start=1):
            dev_id = device.get("id", "UNKNOWN")
            expire = device.get("expire", "No Expire Set")
            status = device.get("status", "unknown")
            status_emoji = "🟢" if status == "active" else "🔴"
            
            response_text += (
                f"{index}. 📱 **ID:** `{dev_id}`\n"
                f"     ⏳ **Expire:** `{expire}`\n"
                f"     {status_emoji} **Status:** `{status}`\n"
            )
        response_text += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"

    await status_msg.edit_text(response_text, parse_mode="Markdown")

def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    token = os.getenv("BOT_TOKEN", BOT_TOKEN)
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_device_id))
    application.add_handler(CommandHandler("del", delete_device_id))
    application.add_handler(CommandHandler("list", list_devices))
    
    port = int(os.getenv("PORT", 8080))
    web_app = aiohttp.web.Application()
    web_app.add_routes([aiohttp.web.get('/', handle_ping)])
    
    runner = aiohttp.web.AppRunner(web_app)
    loop.run_until_complete(runner.setup())
    site = aiohttp.web.TCPSite(runner, '0.0.0.0', port)
    loop.run_until_complete(site.start())
    
    logging.info(f"🟢 Web Server started on port {port}.")
    
    loop.create_task(self_ping())
    
    application.run_polling(close_loop=False)

if __name__ == '__main__':
    main()
