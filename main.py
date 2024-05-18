#!/usr/bin/env python -u

import sys
import codecs
import click
import src.checkresults as checkresults
import src.saucenaoscan as saucenaoscan
import src.saucenaoconfig as saucenaoconfig

config = saucenaoconfig.config

sys.stdout = codecs.getwriter('utf8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf8')(sys.stderr.detach())

# Allow an argument to subsititute for another. Good to have for reference, but no longer needed.
#########EXPAND CLICK FUNCTIONALITY##########
#class Mutex(click.Option):
#    def __init__(self, *args, **kwargs):
#        self.not_required_if:list = kwargs.pop("not_required_if")
#
#        assert self.not_required_if, "'not_required_if' parameter required"
#        kwargs["help"] = (kwargs.get("help", "") + " Option can be interchanged with \"--" + "".join(self.not_required_if) + "\".").strip()
#        super(Mutex, self).__init__(*args, **kwargs)
#
#    def handle_parse_result(self, ctx, opts, args):
#        current_opt:bool = self.name in opts
#        for mutex_opt in self.not_required_if:
#            if mutex_opt in opts:
#                if current_opt:
#                    raise click.UsageError("Illegal usage: '" + str(self.name) + "' is mutually exclusive with " + str(mutex_opt) + ".")
#                else:
#                    self.prompt = None
#        return super(Mutex, self).handle_parse_result(ctx, opts, args)
#
#####################END#####################

@click.group()
def commands():
    pass


@click.command()
@click.option("-t", "--threshold", type=click.FLOAT, default=config.settings["LOW_THRESHOLD"], show_default=True, 
              help="Compare files above minimum similarity threshold.")
def check_results(threshold:float):
    """
    Check images that didn't get automatically added to Danbooru. Will open your browser to display the image on your machine
    to compare with the image found on Danbooru. File will be favorited to Danbooru and removed locally if match is confirmed.
    """
    checkresults.check_low_threshold_results(threshold)


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("-r", "--recursive", 
              is_flag=True, show_default=True, default=False, 
              help="Pull images from all sub-directories within specified directory.")
@click.option("-h", "--high_threshold", type=int, default=config.settings["HIGH_THRESHOLD"], show_default=True, 
              help="Files that meet the high threshold will be automatically favorited to Danbooru. Default can be changed in config.json.")
@click.option("-l", "--low_threshold", type=int, default=config.settings["LOW_THRESHOLD"], show_default=True, 
              help="""Files above low threshold will be recorded and can be checked via 'check-results'.
              Results underthreshold are discarded. Default can be changed in config.json.""")
@click.option("-s", "--schedule", is_flag=True, default=False, show_default=True, 
              help="Schedules a crontab task to run.")
@click.option("-m", "--md5_only", is_flag=True, default=False, show_default=True, 
              help="Only scan files via MD5. This only searches Danbooru and will not be limited to daily searches by Saucenao.")
def scan(directory:str, recursive:bool, high_threshold:int, low_threshold:int, schedule:bool, md5_only:bool):
    """
    Connects to the Saucenao web API to look at specified file(s) and determine if they match. If they match, will favorite the image
    on Danbooru then remove the file from the local machine.
    """
    if md5_only:
        saucenaoscan.md5_scan(directory, recursive)
    else:
        saucenaoscan.full_scan(directory, recursive, high_threshold, low_threshold, schedule)


commands.add_command(check_results)
commands.add_command(scan)


if __name__ == "__main__":
    commands()
