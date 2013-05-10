import decimal

from pyramid.i18n import get_localizer, TranslationString
from pyramid.threadlocal import get_current_request
from wtforms.ext.csrf.form import SecureForm as BaseSecureForm
from wtforms import fields
import babel.numbers

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

class LocalizedDecimalField(fields.DecimalField):

    def _value(self):
        if self.raw_data:
            return self.raw_data[0]
        elif self.data is not None:
            return babel.numbers.format_decimal(
                self.data,
                format='0.##################################################',
                locale=self.locale
            )
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist and valuelist[0]:
            try:
                self.data = decimal.Decimal(
                    str(
                        babel.numbers.parse_decimal(
                            valuelist[0],
                            locale=self.locale
                        )
                    )
                )
            except babel.numbers.NumberFormatError:
                self.data = None
                raise ValueError(self.gettext("Not a valid decimal value"))

    def set_locale(self, locale):
        self.locale = locale
