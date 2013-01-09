class ServiceBase(object):

    def __init__(self, request):
        self.request = request

    def get_service(self, service_class):
        return service_class(self.request)
