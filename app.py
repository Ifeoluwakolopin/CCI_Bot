import sys
from bot.main import main

if __name__ == "__main__":
    deploy = "--deploy" in sys.argv or "-d" in sys.argv
    main(deploy=deploy)
    # jobs.sched.start()
