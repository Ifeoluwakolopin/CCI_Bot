import sys
from bot.main import main
import jobs

if __name__ == "__main__":
    deploy = "--deploy" in sys.argv or "-d" in sys.argv
    main(deploy=deploy)
    jobs.sched.start()
