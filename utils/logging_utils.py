import logging

LOG_PATTERN = '[%(asctime)s][%(levelname)s] [%(filename)15s:%(lineno)s][%(funcName)15s()] | [%(process)d:%(thread)d] ' \
              '| %(message)s '
LOG_DATE_PATTERN = '%Y-%m-%dT%H:%M:%S.%s%z'


def configure_logs():
    logging.basicConfig(
        format=LOG_PATTERN,
        level=logging.INFO,
        datefmt=LOG_DATE_PATTERN,
    )
