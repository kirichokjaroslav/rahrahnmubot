import json
import inspect

support_languages = {"en": "en", "ua": "ua", "ru": "ru",} 

class LanguagesChallenge(object):

    def __init__(self, languages_file, *args, **kwargs):
        self.__languages_file = languages_file

    def __call__(self, language_code, *args, **kwargs):
        return self.get_language_data(language_code)

    def get_language_data(self, language_code): 
        lcode = self._get_language_code(language_code)
        with open(self.__languages_file, encoding='utf-8') as language_file:  
            language_data = json.load(language_file)
        return language_data.get(lcode, support_languages.get("en"))

    def _get_language_code(self, language_code):
        if not language_code:
            return support_languages.get("en")
        
        if "-" in language_code:
            language_code = language_code.split("-")[0]
        
        return support_languages.get(language_code, support_languages.get("en"))


from settings import constants
languages_challenge = LanguagesChallenge(languages_file=constants.LANGUAGES_FILE)
