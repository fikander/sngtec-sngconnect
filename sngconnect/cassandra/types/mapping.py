try:
    import cPickle as pickle
except ImportError:
    import pickle

from pycassa import types, marshal

class MappingType(types.BytesType):

    def __init__(self, *args, **kwargs):
        super(MappingType, self).__init__(*args, **kwargs)
        self.pack_bytes = marshal.packer_for('BytesType')
        self.unpack_bytes = marshal.unpacker_for('BytesType')

    def pack(self, mapping_value, *args, **kwargs):
        mapping = pickle.dumps(
            mapping_value,
            protocol=pickle.HIGHEST_PROTOCOL
        )
        return self.pack_bytes(mapping, *args, **kwargs)

    def unpack(self, mapping_value, *args, **kwargs):
        mapping = self.unpack_bytes(mapping_value, *args, **kwargs)
        return pickle.loads(mapping)
