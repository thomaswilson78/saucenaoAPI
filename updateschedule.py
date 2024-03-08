import datetime
import re
from crontab import CronTab


def format_command(directory:str):
    return f"cd ~/pCloudDrive/repos/saucenao ; python main.py add-to-danbooru -d {directory} -r -s"


def update_crontab_job(directory:str):
    """Set the crontab job to a new time to help with running the next job."""
    directory = "/home/afrodown/pCloudDrive/Images/Vidya/+Gachas/Blue Archive"
    dirct = re.escape(directory)
    time = datetime.datetime.now()
    sauce_cron = CronTab(user='afrodown')
    jobs = sauce_cron.find_comment('saucenao task')
    for job in jobs:
        if not dirct in job.command:
            job.command = format_command(dirct)
        job.setall(time.minute, time.hour)
        sauce_cron.write()

    print(f"Crontab job updated. Next job runs at: {time.hour}:{time.minute}")
