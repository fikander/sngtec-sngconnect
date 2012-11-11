from wtforms.ext.csrf.form import SecureForm as BaseSecureForm

class SecureForm(BaseSecureForm):

    def generate_csrf_token(self, csrf_context):
        return csrf_context.session.get_csrf_token()
