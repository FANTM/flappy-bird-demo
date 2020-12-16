import struct

BYTE_FMT = '!hhhhhhhhhhH'

class AlphaPacket(dict):
    def __init__(self, data_tuple):
        self["accelX"] = data_tuple[0]
        self["accelY"] = data_tuple[1]
        self["accelZ"] = data_tuple[2]
        self["gyroX"] = data_tuple[3]
        self["gyroY"] = data_tuple[4]
        self["gyroZ"] = data_tuple[5]
        self["magX"] = data_tuple[6]
        self["magY"] = data_tuple[7]
        self["magZ"] = data_tuple[8]
        self["temp"] = data_tuple[9]
        self["myo"] = data_tuple[10]

def unpack_packet(byte_array):
    return AlphaPacket(struct.unpack(BYTE_FMT, byte_array))
