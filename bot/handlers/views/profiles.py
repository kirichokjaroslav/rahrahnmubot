from calendar import day_name
from re import findall, finditer, search

import telebot
from numpy import array_split

from application import phantom_thread_pool, server, telegram
from languages.language import languages_challenge
from menus import menus_challenge
from settings import constants, logger


# handle command '/start'
@telegram.message_handler(commands=['start'])
def handle_command_start(message):
    lang_storage = languages_challenge(message.from_user.language_code)      
    
    show_message = lang_storage['messages'].get('message_greeting') % \
        {'name': message.from_user.first_name}

    cb_functions   = ('handle_button_self_add', 'handle_button_self_no')
    inline_buttons = menus_challenge(telegram).create_yes_no_menu(
        lang_storage, cb_data=cb_functions
    )
    telegram.send_message(
                    chat_id=message.from_user.id,
                    text=f"{show_message}",
                    reply_markup=inline_buttons,
                    parse_mode='html')


# handle selectable 'Yes'
@telegram.callback_query_handler(
    func=lambda cb_function: 'button_self_add' in cb_function.data)
def handle_button_self_add(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    server.app_context().push()
    
    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{cb_function.from_user.id}')
    if user_profile:
        show_message   = lang_storage['messages'].get('message_user_exists') 
        inline_buttons = menus_challenge(telegram).create_backward_menu(
            lang_storage, cb_data=str('handle_button_main_menu')
        )       
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html',
                        reply_markup=inline_buttons)
        return
    else:
        show_message = lang_storage['messages'].get('message_login') 
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html')

    user_create = UserProfileModel(**{
        'from_user_id': f'{cb_function.from_user.id}',
        'first_name':   f'{cb_function.from_user.first_name or str()}',
        'last_name':    f'{cb_function.from_user.last_name  or str()}'}
    )
    user_create.save()

    telegram.register_next_step_handler(cb_function.message, sign_up_login)


# handle selectable 'No'
@telegram.callback_query_handler(
    func=lambda cb_function: 'button_self_no' in cb_function.data)
def handle_button_self_no(cb_function):
    handle_button_main_menu(cb_function)


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_main_menu' in cb_function.data)
def handle_button_main_menu(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    

    show_message   = (
        f"{lang_storage['messages'].get('message_welcome')}"    
        f"\n"
        f"{lang_storage['messages'].get('message_select_menu')}"
    )
    inline_buttons = menus_challenge(telegram).create_main_menu(lang_storage)   
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_updates' in cb_function.data)
def handle_button_updates(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)     
    
    show_message   = lang_storage['messages'].get('message_updates')    
    inline_buttons = menus_challenge(telegram).create_backward_menu(
        lang_storage, cb_data=str('handle_button_main_menu')
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)  


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_feedback' in cb_function.data)
def handle_button_feedback(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)

    show_message   = lang_storage['messages'].get('message_feedback')    
    inline_buttons = menus_challenge(telegram).create_backward_menu(
        lang_storage, cb_data=str('handle_button_main_menu')
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)    


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_settings' in cb_function.data)
def handle_button_settings(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    show_message = lang_storage['messages'].get('message_settings')    
    cb_functions = (
        'handle_button_self_add',
        'handle_button_self_delete', 
        'handle_button_main_menu'
    )
    inline_buttons = menus_challenge(telegram).create_settings_menu(
        lang_storage, cb_data=cb_functions)
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)  


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_self_delete' in cb_function.data)
def handle_button_self_delete(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    server.app_context().push()

    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{cb_function.from_user.id}')
    if user_profile: user_profile.delete()
    
    show_message = lang_storage['messages'].get('message_completed') 
    telegram.answer_callback_query(
                    cb_function.id,
                    show_alert=True,
                    text=f'{show_message}')


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_student_schedule' in cb_function.data)
def handle_button_student_schedule(cb_function):  
    lang_storage = languages_challenge(cb_function.from_user.language_code)

    server.app_context().push()

    show_message = lang_storage['messages'].get('message_day_of_week')
    inline_buttons = menus_challenge(telegram).create_days_of_week_menu(
        lang_storage, cb_data=tuple(day_name)
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: cb_function.data in tuple(day_name))
def handle_button_days_of_week(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    inline_buttons = menus_challenge(telegram).create_backward_menu(
        lang_storage, cb_data=str('handle_button_student_schedule')
    )   
    
    try:
        schedule_days = extract_schedule(cb_function)
        assert schedule_days
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return 

    def lesson_specifically(lesson) -> list:
        tab = '\t'; return [
            f"<b>{4*tab}{lesson.get('lesson_date')}</b>" % {
                'lesson_date': lang_storage['messages'].get('message_lesson_date')},
            f"{lesson.get('lesson_title')}" % {
                'lesson_title': lang_storage['messages'].get('message_lesson_title')},            
            f"{lesson.get('lesson_subject')}" % {
                'lesson_subject': lang_storage['messages'].get('message_lesson_subject')}, 
            f"{4*tab}{lesson.get('lesson_enumerate')}" % {
                'lesson_enumerate': lang_storage['messages'].get('message_lesson_enumerate'),
                'time_first':       lang_storage['messages'].get('message_lesson_from'),
                'time_second':      lang_storage['messages'].get('message_lesson_to')},
            f"{lesson.get('lesson_text')}" % {
                'lesson_class': f"{8*tab}{lang_storage['messages'].get('message_lesson_class')}",
                'lesson_teach': f"{8*tab}{lang_storage['messages'].get('message_lesson_teach')}"}        
        ]

    schedule_day = schedule_days.get(cb_function.data)
    if not schedule_day:
        show_message = lang_storage['messages'].get('message_oops')    
    else:
        show_message = f"{lang_storage['messages'].get('message_lesson_caption')}"
        for lesson in schedule_day: show_message += ''.join(lesson_specifically(lesson))

    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: 'button_student_rating' in cb_function.data)
def handle_button_student_rating(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    
    
    server.app_context().push()

    from pendulum import now
    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{cb_function.from_user.id}')
    try:
        assert user_profile
        assert user_profile.learning_start_date.isdigit()
        assert\
            (int(now().year) - int(user_profile.learning_start_date))\
            <= constants.PERIOD_OF_STUDY
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return 

    show_message = lang_storage['messages'].get('message_learning_year')
    start_date = int(user_profile.learning_start_date)
    inline_buttons = menus_challenge(telegram).create_learning_year_menu(
        lang_storage, cb_data=(item for item in range(start_date, now().year + 1))
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: cb_function.data in
    available_year(cb_function)
)
def handle_button_year(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    

    server.app_context().push()

    cb_functions = (item for item in constants.SEMESTERS.keys())
    inline_buttons = menus_challenge(telegram).create_semester_menu(
        lang_storage, cb_data=cb_functions
    )

    try:
        from ..models.profiles import UserProfileModel
        user_profile = UserProfileModel.get_user(
            from_user_id=f'{cb_function.from_user.id}')
        assert user_profile
        
        from ..models.profiles import UserRatingModel
        user_rating = UserRatingModel.get_results_for_user(
            user_profile.id) or \
            UserRatingModel(**{
                'user_id':      user_profile.id,
                'choosed_year': int(cb_function.data)}
            )
        assert user_rating
        user_rating.choosed_year = int(cb_function.data)

        from pendulum import now
        user_rating.last_update_datetime = now().to_datetime_string()
        
        user_rating.save()
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return 

    show_message = lang_storage['messages'].get('message_semester')
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: cb_function.data in 
    (item for item in constants.SEMESTERS.keys())
)
def handle_button_semester(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
 
    server.app_context().push()

    cb_functions = (
        'handle_button_academic_rating',
        'handle_button_academic_module'
    )
    inline_buttons = menus_challenge(telegram).create_rating_module_menu(
        lang_storage, cb_data=cb_functions)

    try:
        from ..models.profiles import UserProfileModel
        user_profile = UserProfileModel.get_user(
            from_user_id=f'{cb_function.from_user.id}')
        assert user_profile
        
        from ..models.profiles import UserRatingModel
        user_rating = UserRatingModel.get_results_for_user(user_profile.id) or \
                        UserRatingModel(**{
                            'user_id': user_profile.id,
                            'choosed_semester': constants.SEMESTERS.get(cb_function.data)}
                        )
        assert user_rating
        user_rating.choosed_semester = constants.SEMESTERS.get(cb_function.data)

        from pendulum import now
        user_rating.last_update_datetime = now().to_datetime_string()
        
        user_rating.save()
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return 

    show_message = lang_storage['messages'].get('message_rating_or_module')
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=\
    lambda cb_function: 'button_academic_rating' in cb_function.data)
def handle_button_academic_rating(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    try:
        rating = extract_rating(cb_function)
        assert rating

        # if rating information is extract, then
        # split lessons to the pages
        pages_count = round(len(rating) / constants.PAGES_COUNT) or 1
        pages_imaginary = array_split(rating, pages_count)
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return 

    show_message = f"{lang_storage['messages'].get('message_rating_caption')}"
    pages_enumerate = []; start_page, *_ = pages_imaginary
    for lesson in pages_imaginary[pages_imaginary.index(start_page)]: 
        pages_enumerate.append(int(*lesson))
        *_, last_lesson = pages_enumerate        
        
        lesson_caption = lesson.get(f"{last_lesson}").get('lesson_caption').strip()      
        show_message  += ''.join(f"<b>{last_lesson}\u002e</b>\u0020{lesson_caption}\n\n")

    start_lesson, finish_lesson = min(pages_enumerate), max(pages_enumerate)
    
    cb_functions   = (str('page_rating:{page}'), str('lesson_rating:{page}:{lesson}'))
    inline_buttons = menus_challenge(telegram).create_pagination_rating(
                                                    lang_storage, 1, pages_count, start_lesson,
                                                    finish_lesson, cb_data=cb_functions
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: 'page_rating' in cb_function.data)
def handle_button_page_rating(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)

    server.app_context().push()

    try:
        from ..models.profiles import UserProfileModel
        user_profile = UserProfileModel.get_user(from_user_id=f'{cb_function.from_user.id}')
        assert user_profile
        
        from ..models.profiles import UserRatingModel
        user_rating = UserRatingModel.get_results_for_user(user_id=f'{user_profile.id}')
        assert user_rating

        # if rating information is extract, then
        # split lessons to the pages
        pages_count = round(len(user_rating.rating) / constants.PAGES_COUNT) or 1
        pages_imaginary = array_split(user_rating.rating, pages_count)
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return  

    page = findall(r'\d+', cb_function.data).pop()

    show_message = f"{lang_storage['messages'].get('message_rating_caption')}"
    pages_enumerate = []
    for lesson in pages_imaginary[int(page) - 1]: 
        pages_enumerate.append(int(*lesson))
        *_, last_lesson = pages_enumerate        
        
        lesson_caption = lesson.get(f"{last_lesson}").get('lesson_caption').strip()      
        show_message  += ''.join(f"<b>{last_lesson}\u002e</b>\u0020{lesson_caption}\n\n")
    
    start_lesson, finish_lesson = min(pages_enumerate), max(pages_enumerate)

    cb_functions   = (str('page_rating:{page}'), str('lesson_rating:{page}:{lesson}'))
    inline_buttons = menus_challenge(telegram).create_pagination_rating(
                                                    lang_storage, int(page), pages_count,
                                                    start_lesson, finish_lesson, cb_data=cb_functions
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: 'lesson_rating' in cb_function.data)
def handle_button_lesson_rating(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)

    server.app_context().push()

    try:
        from ..models.profiles import UserProfileModel
        user_profile = UserProfileModel.get_user(from_user_id=f'{cb_function.from_user.id}')
        assert user_profile
        
        from ..models.profiles import UserRatingModel
        user_rating = UserRatingModel.get_results_for_user(user_id=f'{user_profile.id}')
        assert user_rating
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return  

    def lesson_specifically(lesson) -> list:
        empty_data = lang_storage['messages'].get('message_empty_data')
        tab = '\t'; lesson_sequence = str()
        if lesson.get('lesson_enumerate'):
            for item in lesson.get('lesson_enumerate'):
                lesson_title    = item.get('lesson_title')    or empty_data
                lesson_presence = item.get('lesson_presence') or empty_data
                lesson_rating   = item.get('lesson_rating')   or empty_data

                lesson_sequence += (
                    f"{4*tab}<b>%(lesson_title)s</b>{lesson_title}\n"
                    f"{8*tab}<b>%(lesson_presence_rating)s{lesson_presence}</b>\u002C\u0020{lesson_rating}\n\n" 
                ) % {
                    'lesson_title': lang_storage['messages'].get('message_rating_title'),              
                    'lesson_presence_rating': lang_storage['messages'].get('message_rating_presence_rating')
                }    
        else:
            lesson_sequence += f"{4*tab}<b>{empty_data}</b>"

        return ''.join([f"<b>{lesson.get('lesson_caption').strip()}</b>", '\n\n', lesson_sequence])

    page, lesson_number, *_ = findall(r'\d+', cb_function.data)
    
    for lesson in user_rating.rating: 
        if str(lesson_number) in lesson:
            show_message = lesson_specifically(lesson.get(str(lesson_number))); break

    inline_buttons = menus_challenge(telegram).create_backward_menu(
        lang_storage, cb_data=str('page_rating:{page}').format(page=page) 
    )
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=\
    lambda cb_function: 'button_academic_module' in cb_function.data)
def handle_button_academic_module(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)
    
    try:
        module = extract_module(cb_function)
        assert module

        # if module information is extract, then
        # split lessons to the pages
        pages_count = round(len(module) / constants.PAGES_COUNT) or 1
        pages_imaginary = array_split(module, pages_count)
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return   

    def lesson_specifically(lesson) -> list:
        empty_data = lang_storage['messages'].get('message_empty_data')
        tab = '\t'; return [
            f"<b>\u00b7\u0020{lesson.get('lesson_title')}</b>\n",
            f"{4*tab}%(module_first)s - <b>{lesson.get('module_first')   or empty_data}</b>\n"   % {
                'module_first': lang_storage['messages'].get('message_module_first')},
            f"{4*tab}%(module_second)s - <b>{lesson.get('module_second') or empty_data}</b>\n\n" % {
                'module_second': lang_storage['messages'].get('message_module_second')},      
        ]

    show_message = f"{lang_storage['messages'].get('message_module_caption')}"
    inline_buttons = menus_challenge(telegram).create_pagination_module(
        lang_storage, 1, pages_count, cb_data=str('page_module:{page}')
    )
    start_page, *_ = pages_imaginary
    for lesson in pages_imaginary[pages_imaginary.index(start_page)]: 
        show_message += ''.join(lesson_specifically(lesson))

    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


@telegram.callback_query_handler(
    func=lambda cb_function: 'page_module' in cb_function.data)
def handle_button_page_module(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)

    server.app_context().push()

    try:
        from ..models.profiles import UserProfileModel
        user_profile = UserProfileModel.get_user(from_user_id=f'{cb_function.from_user.id}')
        assert user_profile
        
        from ..models.profiles import UserRatingModel
        user_module = UserRatingModel.get_results_for_user(user_id=f'{user_profile.id}')
        assert user_module

        # if module information is extract, then
        # split lessons to the pages
        pages_count = round(len(user_module.module) / constants.PAGES_COUNT) or 1
        pages_imaginary = array_split(user_module.module, pages_count)
    except (AssertionError, Exception) as error:
        exception_message_error(cb_function, lang_storage, error); return    

    def lesson_specifically(lesson) -> list:
        empty_data = lang_storage['messages'].get('message_empty_data')
        tab = '\t'; return [
            f"<b>\u00b7\u0020{lesson.get('lesson_title')}</b>\n",
            f"{4*tab}%(module_first)s - <b>{lesson.get('module_first')   or empty_data}</b>\n"   % {
                'module_first': lang_storage['messages'].get('message_module_first')},
            f"{4*tab}%(module_second)s - <b>{lesson.get('module_second') or empty_data}</b>\n\n" % {
                'module_second': lang_storage['messages'].get('message_module_second')},      
        ]

    page = findall(r'\d+', cb_function.data).pop()

    show_message = f"{lang_storage['messages'].get('message_module_caption')}"
    inline_buttons = menus_challenge(telegram).create_pagination_module(
        lang_storage, int(page), pages_count, cb_data=str('page_module:{page}')
    )
    for lesson in pages_imaginary[int(page) - 1]:
        show_message += ''.join(lesson_specifically(lesson))
    try:
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html',
                        reply_markup=inline_buttons)
    except telebot.apihelper.ApiException as error:
        logger.error(f'{error}')


@telegram.message_handler(
    func=lambda message: True, content_types=['text']) 
def sign_up_login(message):  
    lang_storage = languages_challenge(message.from_user.language_code) 
    
    server.app_context().push()

    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{message.from_user.id}')
    if user_profile:
        user_profile.update_profile(**{'username': f'{message.text.strip()}'})
        user_profile.save()

    show_message = lang_storage['messages'].get('message_password') 
    telegram.send_message(
                    chat_id=message.chat.id,
                    text=f'{show_message}',
                    parse_mode='html')
    
    telegram.register_next_step_handler(message, sign_up_password)


@telegram.message_handler(
    func=lambda message: True, content_types=['text'])
def sign_up_password(message):
    lang_storage = languages_challenge(message.from_user.language_code) 
    
    server.app_context().push()

    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{message.from_user.id}')
    if user_profile:
        user_profile.set_password(
            password=f'{message.text}', salt=f'{message.from_user.id}')
        user_profile.save()

    show_message = lang_storage['messages'].get('message_learning') 
    telegram.send_message(
                    chat_id=message.chat.id,
                    text=f'{show_message}',
                    parse_mode='html')
    
    telegram.register_next_step_handler(message, sign_up_learning)


@telegram.message_handler(
    func=lambda message: True, content_types=['text'])
def sign_up_learning(message):
    lang_storage = languages_challenge(message.from_user.language_code) 
    
    server.app_context().push()

    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{message.from_user.id}')
    if user_profile:
        user_profile.update_profile(**{'learning_start_date': f'{message.text.strip()}'})
        user_profile.save()

    show_message = lang_storage['messages'].get('message_auth_complete') 
    inline_buttons = menus_challenge(telegram).create_lets_go_menu(
        lang_storage, cb_data=str('handle_button_main_menu')
    )
    telegram.send_message(
                    chat_id=message.chat.id,
                    text=f'{show_message}' % {'name': message.from_user.first_name},
                    parse_mode='html',
                    reply_markup=inline_buttons)


def available_year(cb_function):
    from ..models.profiles import UserProfileModel
    user_profile = UserProfileModel.get_user(
        from_user_id=f'{cb_function.from_user.id}')
    if not user_profile: return []
    from pendulum import now 
    date_start = int(user_profile.learning_start_date)
    return [
        str(item) for item in range(date_start, now().year + 1)]


def extractor(user_profile, parser_engine) -> bool:          
    try:
        kwargs = user_profile.to_dict()
        kwargs.update({
            'password': user_profile.get_password(user_profile.from_user_id)}
        )
        phantom_thread_pool.add_goal(parser_engine, **kwargs)
        phantom_thread_pool.wait_completion()
    except:
        return False    
    return True


def extract_schedule(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    

    user_profile = user_profile_suitable(cb_function.from_user.id)
    if not user_profile: return

    def extract_schedule_engine(user_profile) -> bool:
        from parsers import acs_parser
        
        show_message = lang_storage['messages'].get('message_wait_schedule')
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html')

        return extractor(user_profile, acs_parser.parse_schedule)
    
    from ..models.profiles import UserScheduleModel
    user_schedule = UserScheduleModel.get_schedule_for_user(user_profile.id)
    if user_schedule:
        # check the relevance
        from pendulum import parse, now
        dt_last_update = user_schedule.last_update_datetime.isoformat()
        
        dt_schedule = parse(dt_last_update, exact=True)
        schedule_days_diff = dt_schedule.diff(now()).in_days()
        if schedule_days_diff > constants.SCHEDULE_ACTUAL_DAYS:
            # make a request to the asc, parse and save
            # and return/show result
            if extract_schedule_engine(user_profile):
                user_schedule = UserScheduleModel.get_schedule_for_user(user_profile.id)
                return user_schedule.schedule if user_schedule else str()
            return str()
        else:
            return user_schedule.schedule or str()           
    else:    
        # make a request to the asc, parse and save into parser
        # and return/show result
        if extract_schedule_engine(user_profile):
            user_schedule = UserScheduleModel.get_schedule_for_user(user_profile.id)
            return user_schedule.schedule if user_schedule else str()
        return str()
       
    return str()


def extract_rating(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    

    user_profile = user_profile_suitable(cb_function.from_user.id)
    if not user_profile: return

    def extract_rating_engine(user_profile) -> bool:
        from parsers import acs_parser
        
        show_message = lang_storage['messages'].get('message_wait_rating')
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html')
        
        return extractor(user_profile, acs_parser.parse_rating)

    if extract_rating_engine(user_profile):
        from ..models.profiles import UserRatingModel

        user_rating = UserRatingModel.get_results_for_user(user_profile.id)
        return user_rating.rating if user_rating else str()

    return str()


def extract_module(cb_function):
    lang_storage = languages_challenge(cb_function.from_user.language_code)    

    user_profile = user_profile_suitable(cb_function.from_user.id)
    if not user_profile: return

    def extract_module_engine(user_profile) -> bool:
        from parsers import acs_parser
        
        show_message = lang_storage['messages'].get('message_wait_module')
        telegram.edit_message_text(
                        text=f'{show_message}',
                        chat_id=cb_function.from_user.id,
                        message_id=cb_function.message.message_id,
                        parse_mode='html')
        
        return extractor(user_profile, acs_parser.parse_module)
    
    if extract_module_engine(user_profile):
        from ..models.profiles import UserRatingModel

        user_module = UserRatingModel.get_results_for_user(user_profile.id)
        return user_module.module if user_module else str()

    return str()


def exception_message_error(cb_function, lang_storage, error=str()):
    logger.exception(f"{error}")

    show_message = lang_storage['messages'].get('message_oops')
    inline_buttons = menus_challenge(telegram).create_backward_menu(
        lang_storage, cb_data=str('handle_button_main_menu')
    )        
    telegram.edit_message_text(
                    text=f'{show_message}',
                    chat_id=cb_function.from_user.id,
                    message_id=cb_function.message.message_id,
                    parse_mode='html',
                    reply_markup=inline_buttons)


def user_profile_suitable(user_id):
    server.app_context().push()

    from ..models.profiles import UserProfileModel 
    user_profile = UserProfileModel.get_user(f'{user_id}')
    return user_profile \
        if user_profile and user_profile.username and user_profile.password else None
