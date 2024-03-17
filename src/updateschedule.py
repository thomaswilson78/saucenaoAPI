import datetime
import re
from crontab import CronTab


def format_command(directory:str):
    return f"cd ~/pCloudDrive/repos/saucenao ; python main.py add-to-danbooru {directory} -r -s"


def update_crontab_job(directory:str):
    """Set the crontab job to a new time to help with running the next job."""
    dirct = re.escape(directory)
    time = datetime.datetime.now()
    sauce_cron = CronTab(user='afrodown')
    jobs = sauce_cron.find_comment('saucenao task')
    for job in jobs:
        # Yes, adding that space is important. Othewise could be determined to be part of a path rather than the complete path
        # i.e. "/path/ab" would be in "/path/ab/cd", but that space would throw it off (and spaces in a path must be escaped)
        if not dirct+" " in job.command:
            job.command = format_command(dirct) 
        job.setall(time.minute, time.hour)
        sauce_cron.write()

    print(f"Crontab job updated. Next job runs at: {time.hour}:{time.minute}")
