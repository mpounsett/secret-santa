# -*- coding: utf-8 -*-

import argparse
import fcntl
import inspect
import logging
import os
import pprint
import random
import smtplib
import sys

from email.mime.text import MIMEText
from jinja2 import Template

import secret_santa.version
import secret_santa.config
import secret_santa.file


class PIDFile(object):
    """
    Context manager that locks with a pid file.
    """
    def __init__(self, path):
        self.path = path
        self.pidfile = None

    def __enter__(self):
        self.pidfile = open(self.path, "a+")
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            logger = logging.getLogger('PIDHandler')
            logger.info(
                "Already running according to {}".format(self.path)
            )
            sys.exit()
        self.pidfile.seek(0)
        self.pidfile.truncate()
        self.pidfile.write(str(os.getpid()))
        self.pidfile.flush()
        self.pidfile.seek(0)
        return self.pidfile

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        try:
            self.pidfile.close()
        except IOError as err:
            if err.errno != 9:
                raise
        os.remove(self.path)


class App(object):
    app_name = 'secret-santa'
    app_description = '''
    'Twas brillig, and the slithy toves
    Did gyre and gimble in the wabe.
    All mimsy were the borogoves,
    And the mame raths outgrabe.
    '''
    config_files = [
        "secret-santa.cfg",
        os.path.expanduser("~/.secretsantarc"),
        "/etc/secret-santa.cfg",
        "/usr/local/etc/secret-santa.cfg",
    ]

    def __init__(self):
        self.args = self.parse_args()
        self.config = None

        if self.args.genconfig:
            print(secret_santa.config.gen_config())
            sys.exit()

        self.setup_logging()
        self.config = secret_santa.config.load_config(
            self.args, self.get_config_paths(os.environ)
        )
        self.setup_logging()

        self.pid_file = "/var/run/{file}.pid".format(
            file=self.app_name.lower()
        )
        if self.config.has_option(self.app_name.lower(), 'pidfile'):
            self.pid_file = self.config.get(self.app_name.lower(), 'pidfile')
        if self.args.pid_file:
            self.pid_file = self.args.pid_file

    def run(self):
        with PIDFile(self.pid_file):
            return self.main_loop()

    def parse_args(self):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=inspect.cleandoc(self.app_description))
        parser.add_argument(
            '-c', '--config',
            help="Configuration file path",
            type=str,
            dest='config_file',
        )
        parser.add_argument(
            '-p', '--pid',
            help="The PID file to write when running",
            dest='pid_file',
        )
        parser.add_argument(
            '--genconfig',
            help="Print a sample config file to stdout",
            action='store_true',
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            '-v', '--verbose',
            help="Run in verbose mode",
            action='store_true',
        )
        group.add_argument(
            '-q', '--quiet',
            help="Print only errors on the console",
            action='store_true'
        )
        parser.add_argument(
            '-V', '--version',
            help="Prints version information and exits.",
            action='version',
            version="%(prog)s {}".format(secret_santa.version.__VERSION__),
        )
        parser.add_argument(
            '-C', '--no-circles',
            help="Prevent two-person circles in pairings.",
            action='store_true',
        )
        parser.add_argument(
            '-w', '--write-pairings',
            help="Write out pairings to a file",
            type=str,
            dest='pairings_file',
        )
        return parser.parse_args()

    def get_config_paths(self, env):
        app_env = '{}_CONFIG'.format(self.app_name.upper())

        if env.get(app_env, False):
            self.config_files = [env.get(app_env)]
        if self.args.config_file:
            self.config_files = [self.args.config_file]

        if not self.config_files:
            raise RuntimeError("Empty list of potential config files.")
        return self.config_files

    def setup_logging(self):
        console_format = '%(asctime)s %(levelname)s %(message)s'
        console_time = '%T'

        console = logging.StreamHandler()

        if self.config:
            if self.config.has_option(
                    self.app_name.lower(), 'console_format'):
                console_format = self.config.get(
                    self.app_name.lower(), 'console_format')
            if self.config.has_option(
                    self.app_name.lower(), 'timestring'):
                console_time = self.config.get(
                    self.app_name.lower(), 'timestring')

        console.setFormatter(logging.Formatter(console_format, console_time))

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

        root_logger.addHandler(console)

        if self.args.verbose:
            root_logger.setLevel(logging.INFO)
        elif self.args.quiet or not sys.stdout.isatty():
            root_logger.setLevel(logging.ERROR)
        else:
            root_logger.setLevel(logging.WARNING)

        self.logger = logging.getLogger(self.app_name.lower())

    def pick_pairings(self):
        pairings = {}
        people = self.config.sections()
        people.remove(self.app_name.lower())

        for person in self.config.sections():
            if person == self.app_name.lower():
                continue

            self.logger.info("======")
            self.logger.info("Selecting pairing for {!r}".format(person))

            exclude = self.config.get(person, 'exclude').split()

            options = people.copy()
            self.logger.info("Beginning options: {!r}".format(options))

            if person in options:
                self.logger.info("Excluding {!r} (self)".format(person))
                options.remove(person)
            for x in exclude:
                if x in options:
                    self.logger.info("Excluding {!r} (excluded)".format(x))
                    options.remove(x)
            if self.args.no_circles:
                for pair in pairings:
                    if pairings[pair] == person and pair in options:
                        self.logger.info("Excluding {!r} (circular)".format(
                            pair))
                        options.remove(pair)

            self.logger.info("Remaining options: {!r}".format(options))

            if not options:
                self.logger.error(
                    "No remaining options for {!r}".format(person)
                )
                raise IndexError

            pairings[person] = random.choice(options)
            people.remove(pairings[person])

            self.logger.info("Selected {!r}".format(pairings[person]))

        return pairings

    def send_message(self, to, name, pair):

        self.logger.info("Sending email to {!r} ({!r})".format(name, to))

        app = self.app_name.lower()

        if (self.config.has_option(app, 'mail_user') and
                self.config.has_option(app, 'mail_password')):
            user = self.config.get(app, 'mail_user')
            password = self.config.get(app, 'mail_password')
        else:
            user = password = None

        msg = MIMEText(Template(
            self.config.get(app, 'mail_body')
        ).render(name=name, pair=pair))

        msg['Subject'] = Template(
            self.config.get(app, 'mail_subject')
        ).render(name=name, pair=pair)
        msg['From'] = self.config.get(app, 'mail_from')
        msg['To'] = to

        server = self.config.get(self.app_name.lower(), 'mail_server')
        if ":" in server:
            (host, port) = server.split(":")
        else:
            (host, port) = (server, 587)

        try:
            s = smtplib.SMTP(host, port)
            if self.config.getboolean(app, 'mail_tls'):
                s.starttls()
            if user and password:
                s.login(user, password)
        except Exception as e:
            self.logger.error("Failed to setup SMTP session: {!r}".format(e))
        else:
            try:
                s.send_message(msg)
                s.quit()
            except:
                self.logger.error("Failed to send message: {!r}".format(e))

    def main_loop(self):
        max_tries = self.config.getint(self.app_name.lower(), 'max_tries')
        tries = 0
        picked = False
        while tries < max_tries and not picked:
            tries += 1
            try:
                pairings = self.pick_pairings()
            except IndexError:
                self.logger.error("Retrying pairings.")
                pairings = None
            else:
                picked = True

        if pairings is None:
            self.logger.error("Failed to find all pairings.")
            sys.exit(1)

        if self.args.pairings_file:
            with secret_santa.file.safe_write(self.args.pairings_file) as f:
                f.write(pprint.pformat(pairings))

        for k, v in pairings.items():
            email = self.config.get(k, 'email')
            self.send_message(email, k, v)


def setup_app():
    app = App()
    app.run()
