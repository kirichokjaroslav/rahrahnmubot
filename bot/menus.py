import numpy
import telebot
from telebot.types import InlineKeyboardButton

from settings import logger


class MenusChallenge(object):

    def __call__(self, telegram):
        try:
            if not hasattr(self, 'telegram'):
                setattr(self, 'telegram', telegram)
        except (AttributeError, AssertionError) as error:
            return None, error

        return self

    def create_backward_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
             
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data=cb_data)
        )

        return inline_buttons

    def create_days_of_week_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      

        days_of_week = lang_storage['buttons'].get('button_days_of_week').split(';')
        sequencing_buttons = [InlineKeyboardButton(f"{day}") for day in days_of_week]
        for button, day in zip(sequencing_buttons, cb_data):
            button.callback_data = f"{day}"
        
        inline_buttons.row(*sequencing_buttons)
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        ) 
        
        return inline_buttons

    def create_learning_year_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        sequencing_buttons = [
            InlineKeyboardButton(f"{str(item)}/{str(item + 1)}",
                                 callback_data=str(item)) for item in cb_data
        ]
        sorted_seq_buttons = numpy.array_split(sequencing_buttons, 2)
        for row_buttons in sorted_seq_buttons: inline_buttons.row(*row_buttons)
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        ) 
        
        return inline_buttons  

    def create_lets_go_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_letsgo')}",
                                 callback_data=cb_data)
        )
        
        return inline_buttons

    def create_main_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()       
        lang_buttons = lang_storage.get('buttons')
        
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_buttons.get('button_self_student_schedule')}",
                                 callback_data='handle_button_student_schedule')
        )
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_buttons.get('button_self_student_rating')}",
                                 callback_data='handle_button_student_rating')
        )
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_buttons.get('button_updates')}",
                                 callback_data=f'handle_button_updates'),
            
            InlineKeyboardButton(f"{lang_buttons.get('button_feedback')}",
                                 callback_data=f'handle_button_feedback'),
            
            InlineKeyboardButton(f"{lang_buttons.get('button_settings')}",
                                 callback_data=f'handle_button_settings')
        )
        
        return inline_buttons

    def create_pagination_module(self, lang_storage, current_page, max_page, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()

        sequencing_buttons = []
        if current_page > 1:
            sequencing_buttons.append(InlineKeyboardButton(
                '« 1',
                callback_data=cb_data.format(page=str('1')))
            )
        if current_page > 2:
            sequencing_buttons.append(InlineKeyboardButton(
                '< {}'.format(current_page - 1),
                callback_data=cb_data.format(page=str(current_page - 1)))
            )
        sequencing_buttons.append(InlineKeyboardButton(
            '· {} ·'.format(current_page),
            callback_data=cb_data.format(page=str(current_page)))
        )
        if current_page < max_page - 1:
            sequencing_buttons.append(InlineKeyboardButton(
                '{} >'.format(current_page + 1),
                callback_data=cb_data.format(page=str(current_page + 1)))
            )
        if current_page < max_page:
            sequencing_buttons.append(InlineKeyboardButton(
                '{} »'.format(max_page),
                callback_data=cb_data.format(page=str(max_page)))
            )
        inline_buttons.row(*sequencing_buttons)
 
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        )

        return inline_buttons

    def create_rating_module_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        rating_module_buttons = iter(cb_data)
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_rating')}",
                                 callback_data=str(next(rating_module_buttons, '...'))
            ),
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_module')}",
                                 callback_data=str(next(rating_module_buttons, '...'))
            )
        )         
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        ) 
        
        return inline_buttons 

    def create_pagination_rating(self, lang_storage, current_page, max_page,
                                 start_lesson, finish_lesson, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        page_leaf, page_lesson, *_ = cb_data

        sequencing_buttons = []
        if current_page > 1:
            sequencing_buttons.append(InlineKeyboardButton(
                '\u00AB',
                callback_data=page_leaf.format(page=current_page - 1))
            )
        sequencing_buttons.extend([InlineKeyboardButton(
            f"{item}",
            callback_data=page_lesson.format(page=current_page, lesson=item)) \
            for item in range(int(start_lesson), int(finish_lesson) + 1)]
        )
        if current_page < max_page:
            sequencing_buttons.append(InlineKeyboardButton(
                '\u00BB',
                callback_data=page_leaf.format(page=current_page + 1))
            )
        inline_buttons.row(*sequencing_buttons)
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        )
   
        return inline_buttons

    def create_semester_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        semester_buttons = iter(cb_data)
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_autumn_semester')}",
                                 callback_data=str(next(semester_buttons, '...'))
            ),
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_spring_semester')}",
                                 callback_data=str(next(semester_buttons, '...'))
            )
        )         
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data='handle_button_main_menu')
        ) 
        
        return inline_buttons 

    def create_settings_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()      
        
        settings_buttons = iter(cb_data)

        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_add_self_data')}",
                                 callback_data=next(settings_buttons, '...')
            ),
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_delete_self_data')}",
                                 callback_data=next(settings_buttons, '...')
            )
        )         
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_backward')}",
                                 callback_data=next(settings_buttons, '...')
            )
        ) 
        
        return inline_buttons

    def create_yes_no_menu(self, lang_storage, cb_data=str()):
        inline_buttons = telebot.types.InlineKeyboardMarkup()       
       
        cb_data_itr = iter(cb_data)       
        inline_buttons.row(
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_yes')}",
                                 callback_data=next(cb_data_itr, '...')
            ),
            InlineKeyboardButton(f"{lang_storage['buttons'].get('button_no')}",
                                 callback_data=next(cb_data_itr, '...')
            )
        ) 
        
        return inline_buttons


menus_challenge = MenusChallenge() 
