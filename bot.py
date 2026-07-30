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

album_cache = {}
album_tasks = {}


# Render端口
def run_server():
    server = HTTPServer(
        ("0.0.0.0", 10000),
        SimpleHTTPRequestHandler
    )
    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 去水印机器人已启动\n\n"
        "支持频道相册5张图片批量处理"
    )



# 半透明重复水印处理
def remove_watermark(input_file, output_file):

    img = cv2.imread(input_file)

    if img is None:
        return False


    original = img.copy()


    # 转灰度
    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )


    # 检测较亮、低透明度文字区域
    mask1 = cv2.threshold(
        gray,
        180,
        255,
        cv2.THRESH_BINARY
    )[1]


    # 去除过大的区域，避免伤害图片
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (2,2)
    )

    mask = cv2.morphologyEx(
        mask1,
        cv2.MORPH_OPEN,
        kernel
    )


    # 只轻微修复
    result = cv2.inpaint(
        original,
        mask,
        2,
        cv2.INPAINT_TELEA
    )


    # 保留高清
    cv2.imwrite(
        output_file,
        result,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            95
        ]
    )

    return True




async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message

    group_id = msg.media_group_id


    if not group_id:

        await process_images(
            [msg],
            update
        )
        return



    if group_id not in album_cache:

        album_cache[group_id] = []


    album_cache[group_id].append(msg)



    if group_id in album_tasks:

        album_tasks[group_id].cancel()



    album_tasks[group_id] = asyncio.create_task(
        wait_album(
            group_id,
            update
        )
    )




async def wait_album(group_id, update):

    try:

        await asyncio.sleep(3)


        photos = album_cache.pop(
            group_id,
            []
        )


        album_tasks.pop(
            group_id,
            None
        )


        if photos:

            await process_images(
                photos[:5],
                update
            )


    except asyncio.CancelledError:

        pass




async def process_images(messages, update):

    await update.message.reply_text(
        "🖼 正在处理水印，请稍等..."
    )


    media = []


    for i, msg in enumerate(messages):

        file = await msg.photo[-1].get_file()


        input_file = f"in_{i}.jpg"
        output_file = f"out_{i}.jpg"


        await file.download_to_drive(
            input_file
        )


        remove_watermark(
            input_file,
            output_file
        )


        media.append(
            InputMediaPhoto(
                open(
                    output_file,
                    "rb"
                )
            )
        )


    await update.message.reply_media_group(
        media
    )




def main():

    app = Application.builder().token(
        TOKEN
    ).build()


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
