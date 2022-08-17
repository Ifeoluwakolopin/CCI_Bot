from bot import *

## Run full bot test locally using polling, before pushing to Heroku.
def main():
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("blog", blog_posts))
    dp.add_handler(CommandHandler("campuses", campuses))
    dp.add_handler(CommandHandler("feedback", feedback))
    dp.add_handler(CommandHandler("membership", membership_school))
    dp.add_handler(msg_handler)
    dp.add_handler(cb_handler)

    updater.start_polling()
    updater.idle()
    #jobs.sched.start()


if __name__ == "__main__":
    main()