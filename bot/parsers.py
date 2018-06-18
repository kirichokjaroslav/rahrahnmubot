import re
import signal

from bs4 import BeautifulSoup
from croniter import croniter
from pendulum import now
from requests.exceptions import ConnectTimeout, HTTPError, ReadTimeout
from requests.sessions import Session

from settings import constants, logger

try:
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver import PhantomJS
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.remote.webdriver import WebElement
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as error:
    raise ImportError(f'Please install selenium: pip install selenium\n{error.msg}')


class ACSParser(object):
    """ Custom and simple parser for ACS.
    """
    def __call__(self, parser_type):
        return self.parse(parser_type)

    def _create_phantom_entity(self):
        desired_capabilities = dict(DesiredCapabilities.PHANTOMJS)
        desired_capabilities['phantomjs.page.settings.loadImages'] = False
        try:
            phantom = PhantomJS(
                executable_path=constants.PHANTOMJS_EXEC,
                desired_capabilities=desired_capabilities,
                service_args=['--ignore-ssl-errors=true'])
            phantom.implicitly_wait(constants.PHANTOMJS_IMPLICITLY_WAIT)
            return phantom
        except WebDriverException as error:
            raise WebDriverException(
                f'Please install phantomjs: http://phantomjs.org/\n{error.msg}')
        return

    def _sign_in(self, **kwargs):
        phantom = self._create_phantom_entity()
        phantom.get(f'{constants.ACS_BASE_URL}/site/login')
        
        tag_input_login = phantom.find_element_by_xpath(f"//input[contains(@id, 'username')]")   
        tag_input_login.clear()
        tag_input_login.send_keys(kwargs.get('username'))

        tag_input_password = phantom.find_element_by_xpath(f"//input[contains(@id, 'password')]")
        tag_input_password.clear()
        tag_input_password.send_keys(kwargs.get('password'))

        phantom.find_element_by_id('login-button').submit()

        return phantom

    def parse(self, parser_type):
        """ Get parser, validate and parse received html.
        """
        parser = getattr(self, f'_parse_{parser_type}', None)
        if parser is None:
            raise AttributeError(
                f'* Parser method _parse_{parser_type} not implemented.')
        return parser()

    def parse_schedule(self, **kwargs):
        from calendar import day_name      
        result_schedule = dict({item: [] for item in tuple(day_name)})
        
        def lessons_enumerate_scrape(day, td_element):
            lesson_div_array  = td_element.find_all('div', {'class': re.compile('(mh)')})
            lessons_enumerate = []
            for div in lesson_div_array:
                lessons_enumerate.append((
                    f"{div.find('span', {'class': re.compile('(lesson)')}).text}\u002C"
                    f"%(time_first)s"
                    f"{div.find('span', {'class': re.compile('(start)')}).text }"
                    f"%(time_second)s"
                    f"{div.find('span', {'class': re.compile('(finish)')}).text}"))

            return lessons_enumerate 

        def lessons_entity_scrape(day, td_element, lessons_enumerate):
            lesson_date = td_element.find('div').text
            lesson_div_array = td_element.find_all('div', {'class': re.compile('(cell)')})          
            for index_d, div in enumerate(lesson_div_array):           
                try:
                    lesson_text = div.find('div').text
                    lesson_text_list = [
                        item.strip() for item in lesson_text.split('\n') if item
                    ]
                    for index_t, _ in enumerate(lesson_text_list):
                        lesson_text_list[index_t] = lesson_text_list[index_t]\
                            .replace('(!)\u0020', str())\
                            .replace('...', str())
                
                    lesson_subject = div.attrs.get('data-content')
                    lesson_subject_list = [
                        item.strip() for item in lesson_subject.split('<br>') if item
                    ]
                    lesson_text_list.insert(0, lesson_subject_list[1])             
                except AttributeError as error:
                    pass 
                else:
                    lesson_iter = iter(lesson_text_list)
                    result_schedule.get(day).append({
                        "lesson_date": f"%(lesson_date)s{lesson_date}\n",
                        "lesson_enumerate": f"%(lesson_enumerate)s{lessons_enumerate[index_d]}\n",
                        "lesson_subject": f"%(lesson_subject)s{next(lesson_iter, '...')}\n",
                        "lesson_title": f"%(lesson_title)s{next(lesson_iter, '...')}\n",
                        "lesson_text": (
                            f"%(lesson_class)s{next(lesson_iter, '...')}\n"
                            f"%(lesson_teach)s{next(lesson_iter, '...')}\n\n")
                    }) 
            return

        try:
            phantom = self._sign_in(**kwargs)

            tag_a_self = phantom.find_element_by_id('sidebar')\
                                .find_element_by_xpath("//a[contains(@href, 'self/time')]")
            phantom.get(f"{tag_a_self.get_attribute('href')}")
            tag_table_time = phantom.find_element_by_xpath("//table[contains(@id, 'time')]")     
            
            soup = BeautifulSoup(tag_table_time.get_attribute('innerHTML'), 'html.parser')
            tr_element_array = soup.find_all('tr')
            for day, tr_element in zip(tuple(day_name), tr_element_array):
                td_element_array = iter(tr_element.find_all('td'))
                lessons_enumerate = lessons_enumerate_scrape(day, next(td_element_array))                
                for td_element in td_element_array:
                    lessons_entity_scrape(day, td_element, lessons_enumerate)
        except Exception as error:
            logger.exception(f'* Loading took too much time - {error}')
        else:
            from handlers.models.profiles import UserScheduleModel
            from application import server
            
            server.app_context().push()

            user_schedule = UserScheduleModel.get_schedule_for_user(kwargs.get('id'))
            if not user_schedule:
                user_schedule = UserScheduleModel(**{
                    'user_id': kwargs.get('id'), 'schedule': result_schedule
                })
            user_schedule.last_update_datetime = now().to_datetime_string()
            
            user_schedule.save()
        finally:
            phantom.service.process.send_signal(signal.SIGTERM)
            phantom.quit()

    _tabs = {'rating': 1, 'module': 3}

    def parse_rating(self, **kwargs):
        from handlers.models.profiles import UserRatingModel
        from application import server
        
        def lessons_scrape(index, div_element):          
            lesson_caption = div_element.find(
                'div', {'class': re.compile('(accordion-heading)')}).text

            thead_tr_element = div_element.find('thead').find('tr').find_all(
                {'td' : True, 'th' : True}
            )
            tbody_tr_element = div_element.find('tbody').find('tr').find_all({'td' : True})
            lesson_enumerate = []
            for title_element, rating_element in \
                            zip(thead_tr_element, tbody_tr_element):
                try:
                    lesson_title = title_element.find(
                        'span', {'class': re.compile('(green)')}
                    ).text
                    lesson_presence = rating_element.find(
                        'label', {'class': re.compile('(label-warning)')}
                    ).text
                    
                    lesson_rating_success = rating_element.find(
                        'label', {'class': re.compile('(label-success)')}
                    ).text
                    lesson_rating_inverse = rating_element.find(
                        'label', {'class': re.compile('(label-inverse)')}
                    ).text
                    lesson_rating = lesson_rating_success \
                    if lesson_rating_success and int(float(lesson_rating_success)) else \
                                    lesson_rating_inverse
                except AttributeError as error:
                    pass
                else:
                    lesson_enumerate.append({
                        'lesson_title':    lesson_title,
                        'lesson_presence': lesson_presence,
                        'lesson_rating':   lesson_rating
                    })

            return dict({
                str(index): {
                    'lesson_caption':   lesson_caption,
                    'lesson_enumerate': lesson_enumerate,
                }
            })           
            
        server.app_context().push()

        user_rating = UserRatingModel.get_results_for_user(kwargs.get('id'))
        if not user_rating: return

        try:
            phantom = self._sign_in(**kwargs)

            tag_a_self = phantom.find_element_by_id('sidebar')\
                .find_element_by_xpath("//a[contains(@href, 'self/student')]")
            phantom.get(
                (
                    f"{tag_a_self.get_attribute('href')}?"
                    f"year={user_rating.choosed_year }&sem={user_rating.choosed_semester}"))
            tag_tab_acc_journal = phantom.find_element_by_xpath(f"//div[contains(@id, 'tab_{self._tabs.get('rating')}')]")     

            soup = BeautifulSoup(tag_tab_acc_journal.get_attribute('innerHTML'), 'html.parser')
            div_element_array = soup.find_all('div', {'class': re.compile('(accordion-group)')})
            result_rating = []
            for  div_element in div_element_array:
                if div_element.find('table'): result_rating.append(lessons_scrape(
                    len(result_rating) + 1, div_element)
                )          
        except Exception as error:
            logger.exception(f'* Loading took too much time - {error}')
        else:
            user_rating.rating = result_rating
            user_rating.last_update_datetime = now().to_datetime_string()
            
            user_rating.save()
        finally:
            phantom.service.process.send_signal(signal.SIGTERM)
            phantom.quit()

    def parse_module(self, **kwargs):
        from handlers.models.profiles import UserRatingModel
        from application import server
        
        server.app_context().push()

        user_module = UserRatingModel.get_results_for_user(kwargs.get('id'))
        if not user_module: return

        try:
            phantom = self._sign_in(**kwargs)

            tag_a_self = phantom.find_element_by_id('sidebar')\
                .find_element_by_xpath("//a[contains(@href, 'self/student')]")
            phantom.get((
                f"{tag_a_self.get_attribute('href')}?"
                f"year={user_module.choosed_year }&sem={user_module.choosed_semester}")
            )
            tag_tab_table = phantom.find_element_by_xpath(f"//div[contains(@id, 'tab_{self._tabs.get('module')}')]")     

            soup = BeautifulSoup(tag_tab_table.get_attribute('innerHTML'), 'html.parser')
            tr_element_array = soup.find('tbody').find_all('tr')
            result_module = []
            for tr_element in tr_element_array:
                td_element_array = iter(tr_element.find_all('td'))
                result_module.append({
                    'lesson_title':  next(td_element_array, str()).text,
                    'module_first':  next(td_element_array, str()).text,
                    'module_second': next(td_element_array, str()).text
                })
        except Exception as error:
            logger.exception(f'* Loading took too much time - {error}')
        else:
            user_module.module = result_module
            user_module.last_update_datetime = now().to_datetime_string()

            user_module.save()
        finally:
            phantom.service.process.send_signal(signal.SIGTERM)
            phantom.quit()


acs_parser = ACSParser()
