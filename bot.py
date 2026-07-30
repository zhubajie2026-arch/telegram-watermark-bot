import os
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import shutil

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
        "🤖 图片处理机器人已启动\n\n"
        "支持频道相册5张批量处理"
    )



# 快速处理（保持原图）
async def fast_process(input_file, output_file):

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


    # 单张图片
    if not group_id:

        await process_images(
            [msg],
            update
        )
        return



    # 相册缓存
    if group_id not in album_cache:

        album_cache[group_id] = []


    album_cache[group_id].append(msg)



    # 取消旧任务
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
        "⚡ 正在快速处理..."
    )


    async def one_image(index, msg):

        file = await msg.photo[-1].get_file()


        input_file = f"input_{index}.jpg"

        output_file = f"output_{index}.jpg"


        await file.download_to_drive(
            input_file
        )


        await fast_process(
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
