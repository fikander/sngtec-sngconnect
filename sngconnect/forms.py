from pyramid.i18n import get_localizer, TranslationString
from pyramid.threadlocal import get_current_request
from wtforms.ext.csrf.form import SecureForm as BaseSecureForm

from sngconnect.translation import _

class FormTranslations(object):

    def __init__(self, request):
        self._localizer = get_localizer(get_current_request())

    def gettext(self, string):
        if not isinstance(string, TranslationString):
            string = _(string)
        return self._localizer.translate(string)

    def ngettext(self, singular, plural, n):
        return self._localizer.pluralize(
            singular,
            plural,
            n,
            domain='sngconnect'
        )

class SecureForm(BaseSecureForm):

    def _get_translations(self):
        return FormTranslations(get_current_request())

    def generate_csrf_token(self, csrf_context):
        return csrf_context.session.get_csrf_token()
