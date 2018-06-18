import os

import psycopg2
from flask import current_app
from flask_script import Command, Option

import settings
from helpers import with_progress
from settings import logger


class LoadDataCommand(Command):
    """ Command to run the load data from
        fixture through the manager from the command line

        Usage: 
            Example 1:
            # Attempt to load data from the preloads 
            # directory. For a successful download, the table
            # name in the database must match the file 
            # name and field names in the database with the field names in csv 
            
            > python manage.py loaddata

            Exmaple 2:
            # Attempt to load data from the specified file. For successful
            # loading field names in the database with field 
            # names in csv must match
            
            > python manage.py loaddata --schema=user_sls_name --file=some_file.csv --delimiter=;
    """
    def __init__(self, file=None, schema=None, delimiter='|'):
        self.default_delimiter = delimiter

    def get_options(self):
        return [
            Option('--file',     '-f', dest='file'),
            Option('--schema',   '-s', dest='schema'),
            Option('--delimiter','-d', dest='delimiter', default=self.default_delimiter),
        ]
    
    @with_progress()
    def run(self, file, schema, delimiter):
        connect = psycopg2.connect(f'''\
            host={current_app.config.get('SQLALCHEMY_DATABASE_HOST')}\
            dbname={current_app.config.get('SQLALCHEMY_DATABASE_BASE')}\
            user={current_app.config.get('SQLALCHEMY_DATABASE_USER')}\
            password={current_app.config.get('SQLALCHEMY_DATABASE_PASSWORD')}
        ''')
        cursor = connect.cursor()
        
        def process_insert_csv(open_file, schema):
            csv_header = f'{open_file.readline()}'.strip().\
                replace(delimiter, f',\u0020')
            for current_row in open_file:
                csv_prepare_row = tuple(column for column in f'{current_row}'.\
                    strip().replace(f'\'', str()).split(delimiter))
                sql_statement = f'''
                    INSERT INTO {schema} ({csv_header})
                    VALUES {csv_prepare_row} ON CONFLICT DO NOTHING;
                '''
                cursor.execute(sql_statement)
        
        try:
            if file and schema:
                with open(file, 'r') as open_file:
                    try:
                        process_insert_csv(open_file, schema)
                    except psycopg2.IntegrityError as error:
                        logger.exception(msg=f'{error}') 
            else:
                from os.path import join, splitext
                for path, dirs, files in os.walk(settings.constants.PRELOADES):
                    for file in files:
                        file_name_csv = os.path.join(path, file)
                        with open(file_name_csv, 'r') as open_file:
                            file_as_schema, _ = splitext(file)
                            try:
                                process_insert_csv(open_file, file_as_schema)
                            except psycopg2.IntegrityError as error:
                                logger.exception(msg=f'{error}') 
        except Exception as error:
            logger.exception(msg=f'{error}')
        else:
            logger.info(msg=f'\u002A\u0020Loading of data from csv file was successful.')
            connect.commit()
        finally:
            cursor.close()
        
        connect.close()