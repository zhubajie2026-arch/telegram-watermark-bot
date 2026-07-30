import os
import asyncio
import threading
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler

import cv2
import numpy as np

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


album_cache = {}
album_tasks = {}


# Render 保活
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



async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🤖 去水印机器人已启动\n\n"
        "发送图片即可自动去水印\n"
        "支持相册批量处理"
    )



# 自动检测+修复水印
async def remove_watermark(
    input_file,
    output_file
):

    try:

        img = cv2.imread(
            input_file
        )


        if img is None:

            shutil.copy(
                input_file,
                output_file
            )

            return



        gray = cv2.cvtColor(
            img,
            cv2.COLOR_BGR2GRAY
        )


        # 检测亮色水印
        mask = cv2.threshold(
            gray,
            210,
            255,
            cv2.THRESH_BINARY
        )[1]


        # 边缘文字检测
        edge = cv2.Canny(
            gray,
            80,
            160
        )


        mask = cv2.bitwise_or(
            mask,
            edge
        )


        kernel = np.ones(
            (3,3),
            np.uint8
        )


        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel
        )


        result = cv2.inpaint(
            img,
            mask,
            3,
            cv2.INPAINT_TELEA
        )


        cv2.imwrite(
            output_file,
            result,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                98
            ]
        )


    except Exception as e:

        print(
            "处理错误:",
            e
        )

        shutil.copy(
            input_file,
            output_file
        )




async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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


    album_cache[group_id].append(
        msg
    )


    if group_id in album_tasks:

        album_tasks[group_id].cancel()



    album_tasks[group_id] = asyncio.create_task(
        wait_album(
            group_id,
            update
        )
    )




async def wait_album(
    group_id,
    update
):

    try:

        await asyncio.sleep(2)


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





async def process_images(
    messages,
    update
):

    await update.message.reply_text(
        "🖼 正在去水印，请稍候..."
    )


    async def one_image(
        index,
        msg
    ):

        file = await msg.photo[-1].get_file()


        input_file = (
            f"input_{index}.jpg"
        )

        output_file = (
            f"output_{index}.jpg"
        )


        await file.download_to_drive(
            input_file
        )


        await remove_watermark(
            input_file,
            output_file
        )


        return InputMediaPhoto(
            open(
                output_file,
                "rb"
            )
        )



    media = await asyncio.gather(
        *[
            one_image(i, msg)
            for i, msg in enumerate(messages)
        ]
    )


    await update.message.reply_media_group(
        media=media
    )




def main():

    if not BOT_TOKEN:

        print(
            "缺少 BOT_TOKEN"
        )

        return



    app = Application.builder().token(
        BOT_TOKEN
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
