class ServiceBase(object):

    def __init__(self, registry):
        self.registry = registry

    def get_service(self, service_class):
        return service_class(self.registry)
