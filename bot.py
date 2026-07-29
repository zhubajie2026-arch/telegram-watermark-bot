import os
import cv2
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 图片去水印机器人已启动\n\n请转发图片给我处理。"
    )


async def remove_watermark(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("🖼 正在处理图片，请稍等...")

    photo = update.message.photo[-1]

    file = await photo.get_file()

    input_file = "input.jpg"
    output_file = "output.jpg"

    await file.download_to_drive(input_file)

    img = cv2.imread(input_file)

    # 简单去除浅色水印
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = cv2.threshold(
        gray,
        240,
        255,
        cv2.THRESH_BINARY
    )[1]

    result = cv2.inpaint(
        img,
        mask,
        3,
        cv2.INPAINT_TELEA
    )

    cv2.imwrite(output_file, result)

    await update.message.reply_photo(
        photo=open(output_file, "rb"),
        caption="✅ 处理完成"
    )


def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            remove_watermark
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()
