#!/usr/bin/env python -u

import sys
import codecs
import click
import checkresults
import addtodanbooru


sys.stdout = codecs.getwriter('utf8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf8')(sys.stderr.detach())

#########EXPAND CLICK FUNCTIONALITY##########
# Allows you to have a parameter for one value or the other. Good to have for reference, but no longer needed.
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
@click.option("-t", "--threshold", type=click.FLOAT, default=80, show_default=True, 
              help="Compare files above minimum similarity threshold.")
@click.option("-f", "--force", is_flag=True, show_default=True, default=False, 
              help="Force all files to be compared, even those that have been previously checked.")
def check_results(threshold:float, force:bool):
    """
    Check images that didn't get automatically added to Danbooru. Will open your browser to display the image on your machine
    to compare with the image found on Danbooru. File will be favorited to Danbooru and removed locally if match is confirmed.
    """
    checkresults.check_low_threshold_results(threshold, force)


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("-r", "--recursive", 
              is_flag=True, show_default=True, default=False, 
              help="Pull images from all sub-directories within specified directory.")
@click.option("-t", "--threshold", type=int, default=60, show_default=True, 
              help="Only allow files above minimum similarity threshold.")
@click.option("-s", "--schedule", is_flag=True, default=False, show_default=True, 
              help="Schedules a crontab task to run.")
@click.option("-h","--hash_only", is_flag=True, default=False, show_default=True,
              help="Only check the MD5 values, do not search on Danbooru")
def add_to_danbooru(directory:str, recursive:bool, threshold:int, schedule:bool, hash_only:bool):
    """
    Connects to the Saucenao web API to look at specified file(s) and determine if they match. If they match, will favorite the image
    on Danbooru then remove the file from the local machine.
    """
    addtodanbooru.add_to_danbooru(directory, recursive, threshold, schedule, hash_only)


commands.add_command(check_results)
commands.add_command(add_to_danbooru)


if __name__ == "__main__":
    commands()
