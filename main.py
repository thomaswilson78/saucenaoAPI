#!/usr/bin/env python -u

import sys
import codecs
import click
import saucenaolog
import addtodanbooru


sys.stdout = codecs.getwriter('utf8')(sys.stdout.detach())
sys.stderr = codecs.getwriter('utf8')(sys.stderr.detach())

#########EXPAND CLICK FUNCTIONALITY##########

class Mutex(click.Option):
    def __init__(self, *args, **kwargs):
        self.not_required_if:list = kwargs.pop("not_required_if")

        assert self.not_required_if, "'not_required_if' parameter required"
        kwargs["help"] = (kwargs.get("help", "") + " Option can be interchanged with \"--" + "".join(self.not_required_if) + "\".").strip()
        super(Mutex, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx, opts, args):
        current_opt:bool = self.name in opts
        for mutex_opt in self.not_required_if:
            if mutex_opt in opts:
                if current_opt:
                    raise click.UsageError("Illegal usage: '" + str(self.name) + "' is mutually exclusive with " + str(mutex_opt) + ".")
                else:
                    self.prompt = None
        return super(Mutex, self).handle_parse_result(ctx, opts, args)

#####################END#####################

@click.group()
def commands():
    pass


@click.command()
@click.option("-t", "--threshold", type=click.FLOAT, default=80, show_default=True, 
              help="Compare files above minimum similarity threshold.")
@click.option("-f", "--force", is_flag=True, show_default=True, default=False, 
              help="Force all files to be compared, even those that have been previously checked.")
@click.option("-ln","--log_name", type=click.Path(exists=True, dir_okay=False), default="./saucenao_log.txt", show_default=True,
              help="Name of the log file to be checked.")
def check_log(threshold:float, force:bool, log_name:str):
    """
    Allow manual review of files added to the log file, determined by the minimum threshold.
    Opens a browser window with two tabs, one for Danbooru the other for the file stored locally.
    If indicated they matched, will favorite on Danbooru and remove the file & log record.
    """
    saucenaolog.check_log(threshold, force, log_name)


@click.command()
@click.argument("-d", "--directory", 
                type=click.Path(exists=True, file_okay=False), cls=Mutex, not_required_if='file', 
                help="Directory to pull images from.")
@click.argument("-f", "--file", 
                type=click.Path(exists=True, dir_okay=False), cls=Mutex, not_required_if='directory', 
                help="Image to check.")
@click.option("-r", "--recursive", 
              is_flag=True, show_default=True, default=False, 
              help="Pull images from all sub-directories within specified directory.")
@click.option("-t", "--threshold", type=int, default=0, show_default=True, 
              help="Only allow files above minimum similarity threshold.")
@click.option("-l", "--log_only", is_flag=True, default=False, show_default=True, 
              help="Do not connect to Danbooru, just add files to the log file (good for if Danbooru goes down).")
@click.option("-ln","--log_name", type=click.Path(dir_okay=False, writable=True), default="./saucenao_log.txt", show_default=True,
              help="Name of the log file to be written to.")
def add_to_danbooru(file:str, directory:str, recursive:bool, threshold:int, log_only:bool, log_name):
    """
    Connects to the Saucenao web API to look at specified file(s) and determine if they match. If they match, will favorite the image
    on Danbooru then remove the file from the local machine.
    """
    addtodanbooru.add_to_danbooru(file, directory, recursive, threshold, log_only, log_name)


commands.add_command(check_log)
commands.add_command(add_to_danbooru)


if __name__ == "__main__":
    commands()
