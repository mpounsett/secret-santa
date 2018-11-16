# -*- coding: utf-8 -*-

import configparser
import inspect
import logging


def gen_config():
    return inspect.cleandoc(
        """
        # A sample configuration file.  Process configuration is in the
        # [general] section.  All other section names are santas.

        [general]
        send_email = False
        max_tries = 5
        # pidfile = /var/run/secret_santa.pid
        mail_server = smtp.google.com
        mail_tls = True
        # user and password are optional
        # mail_user = smtpUserName
        # mail_password = smtpPassword
        mail_from = santa@example.com
        mail_subject = Family secret santa!
        mail_body = Hi {{ name }}!
                    Your secret santa pick has been done.  The name you've
                    received is:

                                    {{ pair }}

                    Merry Christmas!
                    Regards,
                        - The Family Robot

        [Joe]
        email = joe_blow@example.com
        exclude = Holly

        [Holly]
        email = holly_hobby@example.com
        exclude = Joe, Jane

        [Jane]
        email = jane_doe@example.com
        exclude = Peter

        [Peter]
        email = peter_piper@example.com
        exclude = Jane
        """
    )


def load_config(args, config_paths):
    config = configparser.SafeConfigParser()
    logger = logging.getLogger('load_config')
    logger.debug('finding configuration files')
    cfgs = config.read(config_paths)
    if not cfgs:
        raise RuntimeError(
            "No configuration loaded from {!r}".format(config_paths)
        )
    else:
        logger.info("Loaded configuration from {!r}".format(cfgs))

    return config
