import datetime
from crontab import CronTab

def format_command(directory:str):
    return f"cd ~/pCloudDrive/repos/saucenao ; python main.py add-to-danbooru {directory} -r -s"

def update_crontab_job(directory:str):
    """Set the crontab job to a new time to help with running the next job."""
    time = datetime.datetime.now()
    sauce_cron = CronTab(user='afrodown')
    jobs = sauce_cron.find_comment('saucenao task')
    for job in jobs:
        if not directory in job.command:
            job.command = format_command(directory)
        job.setall(time.minute, time.hour)
        sauce_cron.write()

    print(f"Crontab job updated. Next job runs at: {time.hour}:{time.minute}")
