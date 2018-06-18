import importlib
import os

from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

from commands import *
from settings import constants
from application import (server, db)

migrate = Migrate(server, db, directory=f'{constants.BASE_DIR}/handlers/models/migrations/')

manager = Manager(server)
manager.add_command('db', MigrateCommand)
manager.add_command('loaddata', LoadDataCommand)

from handlers.models import (profiles, )

# Start command
if __name__ == '__main__':
    manager.run()
