import pickle

from pycassa import types, marshal

class PickleType(types.IntegerType):

    def __init__(self, *args, **kwargs):
        super(PickleType, self).__init__(*args, **kwargs)
        self.pack_bytes = marshal.packer_for('BytesType')
        self.unpack_bytes = marshal.unpacker_for('BytesType')

    def pack(self, data, *args, **kwargs):
        pickled_data = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
        return self.pack_bytes(pickled_data, *args, **kwargs)

    def unpack(self, pickled_data, *args, **kwargs):
        return pickle.loads(pickled_data)
