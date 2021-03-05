import json
import logging
import logging.config

from pythonjsonlogger import jsonlogger


# setup module wide logger
LOGGER = logging.getLogger('sleuth')
LOGGER.setLevel(logging.INFO)

logHandler = logging.StreamHandler()
supported_keys = [
            'asctime',
            'created',
            'filename',
            'funcName',
            'levelname',
            'levelno',
            'lineno',
            'module',
            'msecs',
            'message',
            'name',
            'process',
            'processName',
            'relativeCreated',
        ]

log_format = lambda x: ['%({0:s})'.format(i) for i in x]
custom_format = ' '.join(log_format(supported_keys))

formatter = jsonlogger.JsonFormatter(custom_format)
logHandler.setFormatter(formatter)
LOGGER.addHandler(logHandler)

from sleuth.auditor import audit

VERSION = '1.2.1'

def handler(event, context):
    """
    Incoming lambda handler
    """

    LOGGER.info('Running aws-iam-sleuth {}'.format(VERSION))

    audit()

    body = {}
    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response


if __name__ == '__main__':
  handler(None, None)
