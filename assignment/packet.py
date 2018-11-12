# packet.py

SEQ = 0
ACK_NUM = 1
FLAG = 2
DATA = 3
CHECKSUM = 4
TIMER = 5

FLAG_SYN = 0b100
FLAG_ACK = 0b010
FLAG_FIN = 0b001


def new_packet(seq, ack_num, syn, ack_bit, fin, data):
    flag = 0b000
    if syn:
        flag = flag | FLAG_SYN
    if ack_bit:
        flag = flag | FLAG_ACK
    if fin:
        flag = flag | FLAG_FIN

    checksum = calculate_checksum(data)
    timer = -1
    packet = [seq, ack_num, flag, data, checksum, timer]
    return packet


def calculate_checksum(data):
    s = 0
    if len(data) == 0:
        s = -1
    else:
        for i in range(0, len(data), 2):
            if i + 1 < len(data):
                a = ord(data[i])
                b = ord(data[i + 1])
                s = s + (a + (b << 8))
            elif i + 1 == len(data):
                s += ord(data[i])
            else:
                print "Something Wrong Here"

        s = s + (s >> 16)
        s = ~s & 0xffff

    return s


def set_data_with_error(packet):

    if len(packet[DATA]) > 0:

        original_data = get_data(packet)

        for byte in bytearray(original_data):

            error_bit = (int(byte) + 1) % 256
            print "error_bit---" + str(error_bit)

            break

        error_char = chr(error_bit)
        error_str = error_char + original_data[1:]

        # new_p = new_packet(packet[SEQ], packet[ACK_NUM], is_syn(packet), is_fin(packet), is_fin(packet), error_str)
        packet[DATA] = error_str
        set_checksum(packet[CHECKSUM], packet)

        return packet

    else:
        print "No data can be corrupted"
        # What if no data can be corrupted


def is_syn(packet):
    boo = packet[FLAG] & FLAG_SYN
    return boo == FLAG_SYN


def is_fin(packet):
    boo = packet[FLAG] & FLAG_FIN
    return boo == FLAG_FIN


def is_ack(packet):
    boo = packet[FLAG] & FLAG_ACK
    return boo == FLAG_ACK


def get_data(packet):
    return packet[DATA]


def get_ack(packet):
    return packet[ACK_NUM]


def get_seq(packet):
    return packet[SEQ]


def get_checksum(packet):
    return packet[CHECKSUM]


def set_checksum(checksum, packet):
    packet[CHECKSUM] = checksum
    return packet

