import os
import asyncio
import threading
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler

import replicate

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()


album_cache = {}
album_tasks = {}


# Render 保活端口
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
        "🤖 AI去水印机器人已启动\n\n"
        "发送图片即可自动去除水印\n"
        "支持相册批量处理"
    )



# Replicate AI 去水印
async def ai_process(input_file, output_file):

    try:

        output = await asyncio.to_thread(
            replicate.run,
            "cjwbw/rembg",
            {
                "image": open(
                    input_file,
                    "rb"
                )
            }
        )


        if output:

            with open(
                output_file,
                "wb"
            ) as f:

                f.write(
                    output.read()
                )

        else:

            shutil.copy(
                input_file,
                output_file
            )


    except Exception as e:

        print(
            "AI处理错误:",
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


    album_cache[group_id].append(msg)


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
        "🤖 AI正在去水印，请稍候..."
    )


    async def one_image(index, msg):

        file = await msg.photo[-1].get_file()


        input_file = f"input_{index}.jpg"

        output_file = f"output_{index}.png"



        await file.download_to_drive(
            input_file
        )


        await ai_process(
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


    if not REPLICATE_TOKEN:

        print(
            "缺少 REPLICATE_API_TOKEN"
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
