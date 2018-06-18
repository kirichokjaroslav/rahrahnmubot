import sched
import time

import pendulum
import telebot
from flask import Flask, abort, request, current_app
from flask_api import status
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy

from helpers import PhantomJSThreadPool
from settings import ConfiguratorFactory, Phase, constants, logger

""" Main module of the telegram bot
    to integrate with the ACS service
"""
telegram = telebot.TeleBot(token=constants.API_TOKEN)
server = Flask(__name__)

db = SQLAlchemy()
debugger = DebugToolbarExtension()
phantom_thread_pool = PhantomJSThreadPool(
    constants.PHANTOMJS_THREADS_COUNT)

choosed_configurator = ConfiguratorFactory.create_configurator(
        Phase.DEVELOPMENT.value)
choosed_configurator(server)

def set_webhook(telegram):
    if server.config['DEBUG']:
        telegram.set_webhook(
            url=f'{constants.WEBHOOK_URL_BASE}{constants.WEBHOOK_URL_PATH}')
    else:
        with open(constants.WEBHOOK_SSL_CERT, 'rb') as certificate_file:
            telegram.set_webhook(
                url=f'{constants.WEBHOOK_URL_BASE}{constants.WEBHOOK_URL_PATH}',
                certificate=certificate_file)

""" Empty webserver index, return nothing, just http 200
"""
@server.route('/', methods=['GET', 'HEAD'])
def index():
    return (u"* Connected!", status.HTTP_200_OK)

@server.route(constants.WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
 
        telegram.process_new_updates([update])
        return (u"* Webhook!", status.HTTP_200_OK)
    else:
        abort(status.HTTP_403_FORBIDDEN)

try:
    """ Connect your SQLAlchemy object to your application
    """
    db.init_app(server)
    """ Connect to flask debugger
    """
    debugger.init_app(server)
    """ Remove and start webhook, it fails
        sometimes the set if there is a previous webhook
    """
    telegram.remove_webhook()
    """ Importtant step! Start all application modules
    """
    scheduler = sched.scheduler(time.time, time.sleep)
    scheduler.enter(
        constants.WEBHOOK_SETUP_WAIT,
        constants.WEBHOOK_SETUP_PRIORITY, set_webhook, (telegram,)
    )
    scheduler.run()
    logger.debug('* Telegram bot: The first stage of launch!')
except Exception as error:
    logger.exception(f'{error}')
    time_str = pendulum.now().to_datetime_string()
    text_str = f'* Telegram bot: Critical error! Unable to start application.'
    raise SystemExit(f'{time_str}\u0020{text_str}')

from handlers.views.profiles import *
if __name__ == '__main__':
    if server.config['DEBUG']:
        server.run(
            host=constants.WEBHOOK_LISTEN_HOST,
            port=constants.WEBHOOK_LISTEN_PORT,
            debug=server.config['DEBUG'])
    else:
        server.run(
            host=constants.WEBHOOK_LISTEN_HOST,
            port=constants.WEBHOOK_LISTEN_PORT,
            ssl_context=(
                constants.CERTIFICATES_SERVER_CRT_FILE,
                constants.CERTIFICATES_SERVER_KEY_FILE),
            debug=server.config['DEBUG'])
