import time
import sys
from sys import argv
from socket import *
from packet import *

STATE_NONE = 0
STATE_SEND = 1
STATE_TERM = 2


class Receiver:

    def __init__(self):
        self.receiver_port = int(argv[1])
        self.file_name = str(argv[2])


def main():

    global state, num_data, time_diff
    state = STATE_NONE
    log_file = open('Receiver_log.txt', 'w')
    log_file.close()
    log_file = open('Receiver_log.txt', 'a')

    receiver = Receiver()

    # Create Socket
    recv_socket = socket(AF_INET, SOCK_DGRAM)
    recv_socket.bind(("", receiver.receiver_port))

    tot_segments = 0
    data_segments = 0

    base_time = time.time() * 1000
    first_packet = True
    container = []
    rec_seq = 0
    rec_ack = 0
    tot_dup_ack = 0
    tot_dup_seg = 0
    tot_corr = 0
    dup_sent = False
    pre_ack = -1
    time_diff = 0

    while True:
        data, sender = recv_socket.recvfrom(receiver.receiver_port)
        npkt = eval(data)

        sender_host = sender[0]
        sender_port = sender[1]

        if state == STATE_NONE:
            num_data = 0

            cur_time = current_time(base_time)
            ini_time = cur_time
            if ini_time > 0.01:
                time_diff = ini_time - 0.01

            write_log("rcv", 0.01, "S", npkt, log_file)
            tot_segments += 1

            state = STATE_SEND
            npkt2 = new_packet(str(rec_seq), int(get_seq(npkt)) + 1, True, True, False, "")
            recv_socket.sendto(str(npkt2), (sender_host, sender_port))

            cur_time = current_time(base_time)

            write_log("snd", cur_time, "SA", npkt2, log_file)

            seq_send = int(get_seq(npkt)) + 1
            rec_ack = seq_send
            pre_seq = seq_send
        elif is_fin(npkt):

            cur_time = current_time(base_time)

            if is_ack(npkt) and int(get_ack(npkt)) == rec_seq + 1:
                write_log("rcv", cur_time, "A", npkt, log_file)
            else:
                write_log("rcv", cur_time, "F", npkt, log_file)
            tot_segments += 1
            num_data = int(get_seq(npkt)) - (seq_send + 1)
            if is_ack(npkt) and int(get_ack(npkt)) == rec_seq + 1:
                
                state = STATE_TERM
                t0 = '==============================================' + '\n'
                log_file.write(t0)
                t1 = "Amount of data received (bytes)"
                args = [t1, num_data]
                msg = "{0:<32}{1:>14}\n".format(*args)
                log_file.write(msg)

                t2 = "Total Segments Received"
                args = [t2, tot_segments]
                msg = "{0:<24}{1:>22}\n".format(*args)
                log_file.write(msg)

                t3 = "Data segments received"
                args = [t3, data_segments]
                msg = "{0:<25}{1:>21}\n".format(*args)
                log_file.write(msg)

                t4 = "Data Segments with Bit Errors"
                args = [t4, tot_corr]
                msg = "{0:<32}{1:>14}\n".format(*args)
                log_file.write(msg)

                t5 = "Duplicate data segments received"
                args = [t5, tot_dup_seg]
                msg = "{0:<34}{1:>12}\n".format(*args)
                log_file.write(msg)

                t6 = "Duplicate ACKs sent"
                args = [t6, tot_dup_ack]
                msg = "{0:<21}{1:>25}\n".format(*args)
                log_file.write(msg)

                log_file.write('==============================================')
                log_file.close()
                sys.exit()
            else:
                ack_a = int(get_seq(npkt)) + 1
                npkt3 = new_packet(get_ack(npkt), ack_a, False, False, True, "")
                recv_socket.sendto(str(npkt3), (sender_host, sender_port))

                cur_time = current_time(base_time)

                write_log("snd", cur_time, "A", npkt3, log_file)
                rec_seq = get_ack(npkt)

                npkt3 = new_packet(get_ack(npkt), ack_a, False, True, False, "")
                recv_socket.sendto(str(npkt3), (sender_host, sender_port))

                cur_time = current_time(base_time)

                write_log("snd", cur_time, "F", npkt3, log_file)

                continue

        elif state == STATE_SEND:
            dup_sent = False
            if is_ack(npkt):
                tot_segments += 1
                cur_time = current_time(base_time)

                write_log("rcv", cur_time, "A", npkt, log_file)
            else:
                p_checksum = get_checksum(npkt)
                error_checksum = calculate_checksum(npkt[DATA])
                cur_time = current_time(base_time)
                if p_checksum != error_checksum and len(get_data(npkt)) != 0:
                    tot_corr += 1
                    write_log("rcv/corr", cur_time, "D", npkt, log_file)
                else:
                    data_segments += 1
                    tot_segments += 1

                    write_log("rcv", cur_time, "D", npkt, log_file)

                    if first_packet and int(get_seq(npkt)) == seq_send:

                        first_packet = False

                        rec_ack = int(get_seq(npkt)) + int(len(get_data(npkt)))

                        with open(receiver.file_name, "a") as written_file:
                            written_file.write(str(get_data(npkt)))

                    elif rec_ack == int(get_seq(npkt)) and not first_packet:

                        if pre_seq == int(get_seq(npkt)) and pre_seq >= int(get_seq(npkt)):
                            tot_dup_seg += 1

                            dup_sent = True
                        else:

                            rec_ack = int(get_seq(npkt)) + int(len(get_data(npkt)))
                            pre_seq = int(get_seq(npkt))

                            if container:
                                with open(receiver.file_name, "a") as written_file:
                                    written_file.write(str(get_data(npkt)))
                                for packet in container:
                                    if rec_ack == int(get_seq(packet)):

                                        with open(receiver.file_name, "a") as written_file:
                                            written_file.write(str(get_data(packet)))
                                        rec_ack = int(get_seq(packet)) + int(len(get_data(packet)))
                                container[:] = [a for a in container if int(get_seq(a)) > int(rec_ack)]
                            else:

                                with open(receiver.file_name, "a") as written_file:
                                    written_file.write(str(get_data(npkt)))

                    else:

                        if pre_seq == rec_ack and pre_seq >= int(get_seq(npkt)):
                            tot_dup_seg += 1
                            dup_sent = True
                        else:
                            pre_seq = int(get_seq(npkt))
                            container.append(npkt)

                    if not dup_sent:
                        npkt4 = new_packet(int(get_ack(npkt)), rec_ack, False, True, False, "")

                        recv_socket.sendto(str(npkt4), (sender_host, sender_port))
                        cur_time = current_time(base_time)

                        if pre_ack == int(get_ack(npkt4)):
                            tot_dup_ack += 1

                            write_log("snd/DA", cur_time, "A", npkt4, log_file)
                        else:
                            write_log("snd", cur_time, "A", npkt4, log_file)
                            pre_ack = int(get_ack(npkt4))


def current_time(ini_time):
    diff = time.time() * 1000 - ini_time - time_diff
    return diff


def write_log(header, now_time, msg_type, packet, log):
    format_time = round(now_time / 1000, 3)

    args = [header, format_time, msg_type, str(get_seq(packet)), str(len(get_data(packet))), str(get_ack(packet))]
    msg = "{0:<15}{1:>14.2f}{2:>10}{3:>18}{4:>14}{5:>18}\n".format(*args)
    log.write(msg)


main()

