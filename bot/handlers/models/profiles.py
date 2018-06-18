from pendulum import now
from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        SmallInteger, String, JSON, and_, event, exists, or_)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from application import db
from helpers import BaseModel, crypto_password


class UserBaseModel(BaseModel):
    def save(self):
        super(UserBaseModel, self).save(db_instance=db)

    def delete(self):
        super(UserBaseModel, self).delete(db_instance=db)


class UserProfileModel(db.Model, UserBaseModel):
    """ The User profile model
    """
    __tablename__ = 'user_profile'
    __repr_attrs__ = ['firstname', 'lastname']

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(String(64), unique=True, nullable=False)
    
    username = Column(String(128), nullable=True)
    password = Column(String(255), nullable=True)
    
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)
    learning_start_date = Column(String(64), nullable=True)

    schedules = relationship(
        'UserScheduleModel', 
        backref=backref('schedule_owner'),  passive_deletes='all', lazy='dynamic')
    rating = relationship(
        'UserRatingModel', 
        backref=backref('rating_owner'),  passive_deletes='all', lazy='dynamic')

    last_update_datetime = Column(DateTime(), nullable=False)

    def __init__(self, **kwargs):
        """ Creates a new candidate.
        """
        # Mandatory Fields
        self.from_user_id = kwargs.get('from_user_id')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')

        # Optional Fields
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')

        # Automatic Fields
        self.last_update_datetime = now().to_datetime_string()

    @classmethod
    def get_user(cls, from_user_id: str):
        """ Get user by telegram from_user {id: *}
        """
        try:
            return cls.query.filter(
                cls.from_user_id == from_user_id 
            ).one_or_none()
        except (MultipleResultsFound, NoResultFound):
            return
    
    def set_password(self, password, salt):
        self.password = crypto_password(password, salt, encode=True) \
        if password else str()

    @classmethod
    def get_password(cls, from_user_id):
        try:
            loaded_user = cls.query.filter(
                cls.from_user_id == from_user_id 
            ).one_or_none()
            return crypto_password(
                loaded_user.password, loaded_user.from_user_id, decode=True)
        except (MultipleResultsFound, NoResultFound):
            return
    
    def update_profile(self, **kwargs):
        for name, value in kwargs.items():
            if name in self.__dict__: setattr(self, name, type(name)(value))


class UserScheduleModel(db.Model, UserBaseModel):
    """ The User schedule model
    """
    __tablename__ = 'user_schedule'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id  = Column(Integer, ForeignKey('user_profile.id', ondelete='CASCADE'), unique=True)
    schedule = Column(JSON, nullable=True)
    
    last_update_datetime = Column(DateTime(), nullable=False)

    def __init__(self, **kwargs):
        """ Creates a new schedule record.
        """
        # Mandatory Fields
        self.user_id  = kwargs.get('user_id')
        self.schedule = kwargs.get('schedule')

        # Automatic Fields
        self.last_update_datetime = now().to_datetime_string()

    @classmethod
    def get_schedule_for_user(cls, user_id: int):
        """ Get schedule for telegram user
        """
        try:
            return cls.query.filter(
                cls.user_id == user_id 
            ).one_or_none()
        except (MultipleResultsFound, NoResultFound):
            return


class UserRatingModel(db.Model, UserBaseModel):
    """ The User rating model
    """
    __tablename__ = 'user_rating'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id  = Column(Integer, ForeignKey('user_profile.id', ondelete='CASCADE'), unique=True)
    
    choosed_year = Column(Integer, nullable=True)
    choosed_semester = Column(Integer, nullable=True)
    rating = Column(JSON, nullable=True)
    module = Column(JSON, nullable=True)

    last_update_datetime = Column(DateTime(), nullable=False)

    def __init__(self, **kwargs):
        """ Creates a new rating record.
        """
        # Mandatory Fields
        self.user_id = kwargs.get('user_id')
        
        self.choosed_year = kwargs.get('choosed_year')
        self.choosed_semester = kwargs.get('choosed_semester')
        self.rating = kwargs.get('rating')
        self.module = kwargs.get('module')

        # Automatic Fields
        self.last_update_datetime = now().to_datetime_string()

    @classmethod
    def get_results_for_user(cls, user_id: int):
        """ Get academic results for telegram user
        """
        try:
            return cls.query.filter(
                cls.user_id == user_id 
            ).one_or_none()
        except (MultipleResultsFound, NoResultFound):
            return


class UserPaymentModel(db.Model, UserBaseModel):
    """ The User pay service model
    """
    __tablename__ = 'user_payment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_user_id = Column(String(64), unique=True, nullable=False)
    is_paid = Column(Boolean, unique=False, default=False)

    last_update_datetime = Column(DateTime(), nullable=False)

    def __init__(self, **kwargs):
        """ Creates a new rating record.
        """
        # Mandatory Fields
        self.user_from_id = kwargs.get('user_from_id')
        self.is_paid = bool(kwargs.get('is_paid'))
 
        # Automatic Fields
        self.last_update_datetime = now().to_datetime_string()

    @classmethod
    def get_paid_for_user(cls, user_from_id: str):
        """ Get paid status for telegram user
        """
        try:
            return cls.query.filter(
                cls.user_from_id == user_from_id 
            ).one_or_none()
        except (MultipleResultsFound, NoResultFound):
            return