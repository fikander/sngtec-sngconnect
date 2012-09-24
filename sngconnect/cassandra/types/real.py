from pycassa import types, marshal

class RealType(types.IntegerType):

    def __init__(self, *args, **kwargs):
        super(RealType, self).__init__(*args, **kwargs)
        self.pack_ascii = marshal.packer_for('AsciiType')
        self.unpack_ascii = marshal.unpacker_for('AsciiType')

    def pack(self, real_value, *args, **kwargs):
        return self.pack_ascii(str(real_value), *args, **kwargs)

    def unpack(self, real_value, *args, **kwargs):
        return self.unpack_ascii(real_value, *args, **kwargs)
