import base64
import inspect
import json
import os
import threading
from functools import wraps
from queue import Empty, Queue
from threading import Thread
from weakref import WeakValueDictionary

import pendulum
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask_sqlalchemy import Model
from sqlalchemy import DateTime
from sqlalchemy.orm import aliased

from settings import constants, logger


class Singleton(type):
    """ Singleton metaclass
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

""" Define an Abstract Base Model for models
"""
class MetaBaseModel(Model.__class__):
    """ A metaclass for the BaseModel.
        Implement '__getitem__ for managing aliases.
    """
    def __init__(cls, *args):
        super().__init__(*args)
        cls.aliases = WeakValueDictionary()

    def __getitem__(cls, key):
        try:
            alias = cls.aliases[key]
        except KeyError:
            alias = aliased(cls)
            cls.aliases[key] = alias

        return alias

try:
    from flask_sqlalchemy import inspect
    from sqlalchemy.orm.state import InstanceState
except ImportError as error:
    def __nomodule(*args, **kwargs): raise error
    inspect = __nomodule
    InstanceState = __nomodule


class BaseModel(object):
    """ General class with universal functions.
    """
    def _get_entity_propnames(self, entity):
        """ Get entity property names
            :param entity: Entity
            :type entity: sqlalchemy.ext.declarative.api.DeclarativeMeta
            :returns: Set of entity property names
            :rtype: set
        """
        inspect_object = entity if isinstance(entity, InstanceState) else inspect(entity)
        return set(
            inspect_object.mapper.column_attrs.keys() + # Columns
            inspect_object.mapper.relationships.keys()  # Relationships
        )

    def _get_entity_loaded_propnames(self, entity):
        """ Get entity property names that are loaded (e.g. won't produce new queries)
            :param entity: Entity
            :type entity: sqlalchemy.ext.declarative.api.DeclarativeMeta
            :returns: Set of entity property names
            :rtype: set
        """
        inspect_object = inspect(entity)
        keynames = self._get_entity_propnames(inspect_object)
        # If the entity is not transient -- exclude unloaded keys
        # Transient entities won't load these anyway, so it's safe to include all columns and get defaults
        if not inspect_object.transient:
            keynames -= inspect_object.unloaded
        # If the entity is expired -- reload expired attributes as well
        # Expired attributes are usually unloaded as well!
        if inspect_object.expired:
            keynames |= inspect_object.expired_attributes

        return keynames

    def _prepare(self, name):
        """ JSON serializer for objects not 
            serializable by default json code
        """
        from datetime import datetime, date
        if isinstance(name, (datetime, date)):
            return pendulum.instance(name).to_datetime_string()
        return name

    def delete(self, db_instance=object):
        """ Deletes the object from the database.
            Example:
                up = UserProfile(**kwargs)
                up.delete()
        """
        db_instance.session.delete(self)
        db_instance.session.commit()

    def save(self, db_instance=object):
        """ Saves the object to the database.
            Example:
                up = UserProfile(**kwargs)
                up.save()
        """
        db_instance.session.add(self)
        db_instance.session.commit()

    def to_dict(self, exluded_keys=set()):
        return {
            name: self._prepare(getattr(self, name))
            for name in self._get_entity_loaded_propnames(self) - exluded_keys
        }


class PhantomJSExecutor(Thread):
    """ Thread executing tasks/goal from a given tasks/goal queue.
        Thread is signalable, to exit
    """
    def __init__(self, goals, threads_n):
        Thread.__init__(self)
        
        self.goals = goals
        self.daemon = True
        self.threads_number = threads_n
        self.done = threading.Event()
        
        self.start()

    def run(self):       
        while not self.done.is_set():
            try:
                func, args, kwargs = self.goals.get(
                    block=True, timeout=constants.PHANTOMJS_QUEUE_TIMEOUT)
                try:
                    func(*args, **kwargs)
                except Exception as error:
                    logger.exception(f'{error}')
                finally:
                    self.goals.task_done()
            except Empty: pass
        return

    def signal_exit(self):
        """ Signal to thread to exit
        """
        self.done.set()


class PhantomJSThreadPool(object):
    """ Pool of threads consuming tasks from a queue 
    """
    def __init__(self, threads_n, goals=[]):
        self.goals = Queue(threads_n)
        self.executors = []
        self.done = False
        
        self._init_executors(threads_n)
        
        for goal in goals: self.goals.put(goal)

    def __del__(self):
        self._close_all_threads()

    def _close_all_threads(self):
        """ Signal all threads to exit and lose the
            references to them
        """
        for executor in self.executors:
            executor.signal_exit()
        self.executors = []

    def _init_executors(self, threads_n):
        for item in range(threads_n): self.executors.append(
            PhantomJSExecutor(self.goals, item))

    def add_goal(self, func, *args, **kwargs):
        """ Add a task to the queue
        """
        self.goals.put((func, args, kwargs))

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue
        """
        self.goals.join()


def json_decode(target_data):
    try:
        request_data = json.loads(target_data.decode("utf-8"))
    except ValueError as error:
        logger.exception(msg=f'{error}')
    else:
        return request_data

def valid_mandatory_fields(target_data, fields=set()):
    """ Checks for missing/empty fields.
    """
    if not fields.issubset(set(target_data.keys())):
        return False

    present_fields = fields.intersection(set(target_data.keys()))
    values_fields = {target_data[field] for field in present_fields}

    if len({'', None}.intersection(values_fields)) > 0:
        return False

    return True

def with_progress(text='Loading... Pease wait'):
    """Send information message if the execution time could be long

    Arguments:
        text (str): information message text
    """
    if not isinstance(text, str):
        raise TypeError("The 'text' argument must be str type")

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # To Do Code
            func(*args, **kwargs)
        return wrapper
    return decorator

def crypto_password(password, salt=str(), encode=False, decode=False):
    algo = PBKDF2HMAC(
        algorithm=hashes.SHA256(), 
        length=32, 
        salt=bytes(salt.encode()), iterations=100000,
        backend=default_backend())
    b64 = base64.urlsafe_b64encode(
        algo.derive(bytes(salt.encode())))
    fernet = Fernet(b64)
    if\
        encode:
        return fernet.encrypt(bytes(password.encode())).decode('utf-8')
    elif\
        decode:
        return fernet.decrypt(bytes(password.encode())).decode('utf-8')
    else:
        return
