from __future__ import generators

import logging
import os
import random
from abc import ABCMeta, abstractclassmethod
from enum import Enum


class Constants(object):

    def __setattr__(self, name, value):
        try:
            self.__dict__[name] = value
        except KeyError:
            raise AttributeError('__setattr__() in class Constants failed.')
        
    def __getattr__(self, name, value):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError('__getattr__() in class Constants failed.')
     
    def __delattr__(self, item):
        if self.__dict__[item]:
            raise AttributeError('__delattr__() it is forbidden to delete attributes.')


formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)


constants = Constants()

constants.BASE_DIR = f'{os.path.dirname(os.path.realpath(__file__))}'
constants.DEBUG = True
constants.API_TOKEN = ''
if constants.DEBUG:
    # ngrok forwarding
    constants.WEBHOOK_HOST = ''
else:
    constants.WEBHOOK_HOST = '<ip/host where the bot is running>'
constants.WEBHOOK_PORT = 443  # 443, 80, 88 or 8443 (port need to be 'open')
constants.WEBHOOK_LISTEN_HOST = 'localhost'  # In some VPS you may need to put here the IP addr
constants.WEBHOOK_LISTEN_PORT = 8080
constants.WEBHOOK_SETUP_WAIT = 5
constants.WEBHOOK_SETUP_PRIORITY = 1
constants.WEBHOOK_SSL_CERT = f'{constants.BASE_DIR}/significant/webhook_cert.pem'  # Path to the ssl certificate
constants.WEBHOOK_SSL_PRIV = f'{constants.BASE_DIR}/significant/webhook_pkey.pem'  # Path to the ssl private key
constants.CREDENTIALS_FILE = f'{constants.BASE_DIR}/significant/configurations.pty'
constants.LOGS_DIR = f'{constants.BASE_DIR}/logs'
# Quick'n'dirty SSL certificate generation:
#   openssl genrsa -out webhook_pkey.pem 2048
#   openssl req -new -x509 -days 3650 -key webhook_pkey.pem -out webhook_cert.pem
# When asked for "Common Name (e.g. server FQDN or YOUR name)" you should reply
# with the same value in you put in WEBHOOK_HOST
constants.WEBHOOK_URL_BASE = f'https://{constants.WEBHOOK_HOST}:{constants.WEBHOOK_PORT}'
constants.WEBHOOK_URL_PATH = f'/{constants.API_TOKEN}/'

constants.LANGUAGES_FILE = f'{constants.BASE_DIR}/languages/dialogs.json'

constants.PHANTOMJS_EXEC = f'{constants.BASE_DIR}/phantom/phantomjs'
constants.PHANTOMJS_QUEUE_TIMEOUT   = 10
constants.PHANTOMJS_THREADS_COUNT   = 15
constants.PHANTOMJS_IMPLICITLY_WAIT = 10

constants.ACS_BASE_URL = 'https://acadreg.nmu.ua'
constants.SCHEDULE_ACTUAL_DAYS = 3
constants.PERIOD_OF_STUDY = 6
constants.SEMESTERS = {'Autumn': 0, 'Spring': 1}
constants.PAGES_COUNT = 5


class NoValue(Enum):
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


class Phase(NoValue):
    DEVELOPMENT = 'DevelopmentApplicationConfigurator'
    TEST = 'TestingApplicationConfigurator'
    PRODUCTION = 'ProductionApplicationConfigurator'


class Configurator(object):
    """ Class configurator that reads information
        from the application settings file
    """
    def config_from_file(self) -> dict:
        """ Reading data from configuration files
            according to the specified path
        """
        with open(constants.CREDENTIALS_FILE, 'r') as credentials_file_opened:
            try:
                import configparser
            except ImportError:
                import ConfigParser as configparser
            parser = configparser.ConfigParser()
            parser.read_file(credentials_file_opened)
            parser_dict = {
                section:dict(parser.items(section=section)) for section in parser.sections()
            }
        return parser_dict


class ConfiguratorFactory(object):
    factories = {}
    @staticmethod
    def add_factory(name, factory):
        ConfiguratorFactory.factories.put[name] = factory
    
    @staticmethod
    def create_configurator(name):
        if not name in ConfiguratorFactory.factories:
            ConfiguratorFactory.factories[name] = eval(name + '.Factory()')
        return ConfiguratorFactory.factories[name].create()


class BaseApplicationConfigurator(metaclass=ABCMeta):
    """ Base configuration
    """
    def __call__(self, *args):
        server, *_ = args
        return self.config(server)

    @abstractclassmethod
    def config(self, server):
        configs = configurator.config_from_file()      
        server.config.update(
            {first.upper():second for *_, sections in configs.items() for first, second in sections.items()}
        )
        sqlalchemy_database_uri = 'postgresql://{user}:{password}@{host}/{base}'.\
        format(
            user=server.config.get('SQLALCHEMY_DATABASE_USER'),
            password=server.config.get('SQLALCHEMY_DATABASE_PASSWORD'),
            host=server.config.get('SQLALCHEMY_DATABASE_HOST'),
            base=server.config.get('SQLALCHEMY_DATABASE_BASE'),
        )
        server.config.update({
            'SQLALCHEMY_DATABASE_URI': sqlalchemy_database_uri,
            'TESTING': False,
            'DEBUG_TB_ENABLED': False,
            'DEBUG_TB_INTERCEPT_REDIRECTS': False,
            'JWT_BLACKLIST_ENABLED': True,
            'JWT_BLACKLIST_TOKEN_CHECKS': ['access', 'refresh'],
        })


class DevelopmentApplicationConfigurator(BaseApplicationConfigurator):
    """ Development configuration
    """
    def __call__(self, *args):
        server, *_ = args
        super(DevelopmentApplicationConfigurator, self).config(server)
        return self.config(server)

    def config(self, server):
        server.config.update({
            'DEBUG_TB_ENABLED': True
        })

    class Factory:
        def create(self): return DevelopmentApplicationConfigurator()


class TestingApplicationConfigurator(BaseApplicationConfigurator):
    """ Testing configuration
    """
    def __call__(self, *args):
        server, *_ = args
        super(TestingApplicationConfigurator, self).config(server)
        return self.config(server)

    def config(self, server):
        sqlalchemy_database_uri = 'postgresql://{user}:{password}@{host}/{base}'.\
        format(
            user=server.config.get('SQLALCHEMY_DATABASE_USER'),
            password=server.config.get('SQLALCHEMY_DATABASE_PASSWORD'),
            host=server.config.get('SQLALCHEMY_DATABASE_HOST'),
            base=server.config.get('SQLALCHEMY_DATABASE_BASE'),
        )
        server.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': sqlalchemy_database_uri,
        })

    class Factory:
        def create(self): return TestingApplicationConfigurator()


class ProductionApplicationConfigurator(BaseApplicationConfigurator):
    """ Production configuration
    """
    def __call__(self, *args):
        server, *_ = args
        super(ProductionApplicationConfigurator, self).config(server)
        return self.config(server)
        
    def config(self, server):
        sqlalchemy_database_uri = 'postgresql://{user}:{password}@{host}/{base}'.\
            format(
                user=server.config.get('SQLALCHEMY_DATABASE_USER'),
                password=server.config.get('SQLALCHEMY_DATABASE_PASSWORD'),
                host=server.config.get('SQLALCHEMY_DATABASE_HOST'),
                base=server.config.get('SQLALCHEMY_DATABASE_BASE'),
            )
        server.config.update({
            'SQLALCHEMY_DATABASE_URI': sqlalchemy_database_uri
        })

    class Factory:
        def create(self): return ProductionApplicationConfigurator()


configurator = Configurator()