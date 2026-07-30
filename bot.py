import asyncio
import os
import cv2
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

# 保存相册图片
album_cache = {}
album_tasks = {}

# Render端口
def run_server():
    server = HTTPServer(("0.0.0.0", 10000), SimpleHTTPRequestHandler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 去水印机器人已启动\n\n"
        "请转发频道图片给我。\n"
        "一次最多支持5张图片。"
    )


def remove_watermark(input_file, output_file):

    img = cv2.imread(input_file)

    if img is None:
        return False

    # 简单AI修复水印区域
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = cv2.threshold(
        gray,
        220,
        255,
        cv2.THRESH_BINARY
    )[1]

    result = cv2.inpaint(
        img,
        mask,
        5,
        cv2.INPAINT_TELEA
    )

    cv2.imwrite(output_file, result)

    return True

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    group_id = msg.media_group_id

    # 单张图片
    if not group_id:
        await process_images([msg], update)
        return

    # 第一次收到这个相册
    if group_id not in album_cache:
        album_cache[group_id] = []

    album_cache[group_id].append(msg)

    # 如果已经有等待任务，取消旧任务
    if group_id in album_tasks:
        album_tasks[group_id].cancel()

    # 创建新的等待任务
    album_tasks[group_id] = asyncio.create_task(
        wait_album(group_id, update)
    )


async def wait_album(group_id, update):

    try:
        # 等待相册全部图片发送完成
        await asyncio.sleep(2)

        photos = album_cache.pop(group_id, [])

        album_tasks.pop(group_id, None)

        if photos:
            await process_images(
                photos[:5],
                update
            )

    except asyncio.CancelledError:
        pass


async def process_images(messages, update):

    await update.message.reply_text(
        "🖼 正在批量处理，请稍等..."
    )

    results = []

    for i, msg in enumerate(messages):

        file = await msg.photo[-1].get_file()

        input_file = f"in_{i}.jpg"
        output_file = f"out_{i}.jpg"

        await file.download_to_drive(input_file)

        remove_watermark(
            input_file,
            output_file
        )

        results.append(
            InputMediaPhoto(
                open(output_file, "rb")
            )
        )


    await update.message.reply_media_group(
        results
    )


def main():

    app = Application.builder().token(TOKEN).build()


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )


    app.run_polling()


if __name__ == "__main__":
    main()
