import time
import random
import sys
from sys import argv
import socket
from packet import *


STATE_NONE = 0
STATE_ESTA = 1
STATE_TERM = 2


class Sender:

    num_data = 0
    num_retransmit = 0
    timeout_retransmit = 0
    tot_seg = 0
    tot_seg_PLD = 0
    tot_drop = 0

    tot_dup_seg = 0
    tot_dup_ack = 0
    tot_corr = 0
    tot_order = 0
    tot_dely = 0
    order_window = []
    order_count = 0
    delay_window = []

    seq = 0
    ack = 0
    isn_send = 0
    term_seq = 0
    term_ack = 0
    retransmit_flag = False
    sample_timer = False
    is_sampleTimer = False
    send_state = ""


    def __init__(self):
        self.receive_host_ip = str(argv[1])
        self.receiver_port = int(argv[2])
        self.file_name = str(argv[3])
        self.MWS = int(argv[4])
        self.MSS = int(argv[5])
        self.gamma = int(argv[6])  # used for timeout

        # The following 8 arguments are used exclusively by the PLD module
        self.pDrop = float(argv[7])  # Probability : 0 <= x <= 1
        self.pDuplicate = float(argv[8])  # Probability : 0 <= x <= 1
        self.pCorrupt = float(argv[9])  # Probability : 0 <= x <= 1
        self.pOrder = float(argv[10])  # Probability : 0 <= x <= 1
        self.maxOrder = float(argv[11])  # 1 <= x <= 6
        self.pDelay = float(argv[12])  # Probability : 0 <= x <= 1
        self.maxDelay = int(argv[13])  # maximum delay (in milliseconds)
        self.seed = int(argv[14])

        self.start_time = time.time() * 1000
        # Create Socket
        s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_socket.settimeout(1)

        random.seed(self.seed)

        try:
            file_to_read = open(self.file_name, "r")
            self.buffer = file_to_read.read()
            file_to_read.close()
        except:
            sys.exit("fail to read the file")

        self.handshake(s_socket)
        self.send_file(s_socket)
        self.trans_termination(s_socket)

    def handshake(self, sender_socket):
        global state
        global seq, isn_send, ack, tot_seg
        global snd_header, rcv_header
        snd_header = "snd"
        rcv_header = "rcv"
        if state != STATE_NONE:
            print("Connection has been established")
            sys.exit()

        rand_seq = 0
        npkt1 = new_packet(rand_seq, 0, True, False, False, "")
        sender_socket.sendto(str(npkt1), (self.receive_host_ip, self.receiver_port))
        tot_seg += 1
        current = current_time(self.start_time)

        write_log(snd_header, current, "S", npkt1)

        try:
            response, addr = sender_socket.recvfrom(1024)
            str_npkt1 = eval(response)

            if is_syn(str_npkt1) and is_ack(str_npkt1) and (int(get_ack(str_npkt1)) == (rand_seq + 1)):
                current = current_time(self.start_time)
                write_log(rcv_header, current, "SA", str_npkt1)

                npkt2 = new_packet(int(get_ack(str_npkt1)), int(get_seq(str_npkt1)) + 1, False, True, False, "")
                state = STATE_ESTA
                sender_socket.sendto(str(npkt2), (self.receive_host_ip, self.receiver_port))
                tot_seg += 1
                current = current_time(self.start_time)

                write_log(snd_header, current, "A", npkt2)

                seq = get_ack(npkt2)
                isn_send = get_ack(npkt2)
                ack = get_seq(npkt2) + len(get_data(npkt2))
                return
            else:
                print("Error occurred in handshake")

        except socket.timeout:
            print("HandShake TimeOut")
            sys.exit()

    def send_file(self, sender_socket):

        global num_retransmit, timeout_retransmit, tot_dup_ack
        global retransmit_flag, term_seq, term_ack, num_data
        global is_sampleTimer
        window = []
        seq_num = seq
        ack_num = ack
        time_start = time.time() * 1000
        first_packet = True
        pre_ack = -1
        dup_ack = 0

        EstimatedRTT = 500
        DevRTT = 250
        TimeoutInterval = EstimatedRTT + self.gamma * DevRTT
        sampleRTT_seq = -1
        next_sampleRTT_seq = -1

        while True:
            window_size = self.MWS / self.MSS

            cur_time = current_time(time_start)

            if cur_time >= TimeoutInterval and len(window) > 0:

                time_start = time.time()*1000
                retransmit_flag = True
                timeout_retransmit += 1
                first_seq = int(get_seq(window[0]))
                if (first_seq + self.MSS - isn_send) < len(self.buffer):
                    component = self.buffer[first_seq - isn_send:first_seq + self.MSS - isn_send]
                else:
                    component = self.buffer[first_seq - isn_send:]

                npkt1 = new_packet(first_seq, ack_num, False, False, False, component)
                self.PLD(npkt1, sender_socket)

            while not window or len(window) < window_size and (seq_num - isn_send) <= len(self.buffer):

                if first_packet or seq_num == next_sampleRTT_seq:
                    sampleRTT_seq = seq_num
                    sample_timer = True  # the seq which is the first packet of one window is qualified
                    next_sampleRTT_seq = seq_num + self.MWS # next sample RTT sequence number
                    first_packet = False

                if pre_ack >= seq_num:
                    seq_num = pre_ack

                if (seq_num + self.MSS - isn_send) >= len(self.buffer):
                    component = self.buffer[seq_num - isn_send:]
                else:
                    component = self.buffer[seq_num - isn_send:seq_num + self.MSS - isn_send]
                retransmit_flag = False
                npkt1 = new_packet(seq_num, ack_num, False, False, False, component)
                self.PLD(npkt1, sender_socket)
                sample_timer = False
                window.append(npkt1)
                if is_sampleTimer:
                    # set timer for the packet
                    npkt1[TIMER] = time.time() * 1000

                seq_num = seq_num + self.MSS

            try:
                response, addr = sender_socket.recvfrom(1024)
                str_npkt2 = eval(response)

                if is_ack(str_npkt2):
                    dupack_flag = False
                    cum_ack = int(get_ack(str_npkt2))
                    if (cum_ack - isn_send) >= len(self.buffer):

                        state = STATE_TERM
                        term_seq = int(get_ack(str_npkt2))
                        term_ack = int(get_seq(str_npkt2)) + len(get_data(str_npkt2))
                        num_data = int(get_ack(str_npkt2)) - isn_send
                        break
                    if pre_ack == cum_ack:
                        dupack_flag = True
                        dup_ack += 1
                        tot_dup_ack += 1
                        cur_time = current_time(self.start_time)

                        DA_header = rcv_header + "/DA"
                        write_log(DA_header, cur_time, "A", str_npkt2)
                    else:
                        cur_time = current_time(self.start_time)
                        write_log(rcv_header, cur_time, "A", str_npkt2)
                    if dup_ack > 2:
                        dup_ack = 0
                        retransmit_flag = True
                        cumu_seq = int(get_ack(str_npkt2))

                        if (cumu_seq + self.MSS - isn_send) < len(self.buffer):
                            component = self.buffer[cumu_seq - isn_send: cumu_seq + self.MSS - isn_send]
                        else:
                            component = self.buffer[cumu_seq - isn_send:]
                        npkt3 = new_packet(cumu_seq, ack_num, False, False, False, component)
                        num_retransmit += 1
                        self.PLD(npkt3, sender_socket)

                pre_ack = int(get_ack(str_npkt2))

                sampleRTT = 0
                for packet in window:
                    if int(int(get_seq(packet)) + int(len(get_data(packet)))) > int(get_ack(str_npkt2)):
                        time_start = time.time() * 1000
                    if int(get_seq(packet)) == sampleRTT_seq:
                        pkt_timer = packet[TIMER]
                        if pkt_timer != -1 and sampleRTT_seq + self.MSS == pre_ack:
                            sampleRTT = time.time()*1000 - pkt_timer

                if sampleRTT != 0:
                    EstimatedRTT = (1 - 0.125) * EstimatedRTT + 0.125 * sampleRTT
                    DevRTT = (1 - 0.25) * DevRTT + 0.25 * abs(sampleRTT - EstimatedRTT)
                    TimeoutInterval = EstimatedRTT + self.gamma * DevRTT

                window[:] = [packet for packet in window if int(int(get_seq(packet)) + int(len(get_data(packet)))) > pre_ack]

            except socket.timeout:
                '''

                '''
    def trans_termination(self, sender_socket):

        global num_data, num_retransmit, timeout_retransmit
        global tot_seg, tot_seg_PLD
        global tot_dup_ack, tot_drop, tot_corr, tot_order, tot_dely
        global rcv_header, snd_header

        npkt1 = new_packet(term_seq, term_ack, False, False, True, "")
        sender_socket.sendto(str(npkt1), (self.receive_host_ip, self.receiver_port))
        tot_seg += 1
        cur_time = current_time(self.start_time)
        write_log(snd_header, cur_time, "F", npkt1)

        while True:
            try:
                response, addr = sender_socket.recvfrom(1024)
                str_npkt2 = eval(response)
                if is_fin(str_npkt2):

                    cur_time = current_time(self.start_time)
                    write_log(rcv_header, cur_time, "A", str_npkt2)

                    cur_time = current_time(self.start_time)
                    write_log(rcv_header, cur_time, "F", str_npkt2)

                    # seq, ack_num, syn, ack_bit, fin, data
                    npkt3 = new_packet(int(get_ack(str_npkt2)), int(get_seq(str_npkt2)) + 1, False, True, True, "")
                    sender_socket.sendto(str(npkt3), addr)
                    tot_seg += 1

                    cur_time = current_time(self.start_time)
                    write_log(snd_header, cur_time, "A", npkt3)

                    t0 = "==========================================================" + "\n"
                    log_file.write(t0)
                    t1 = "Size of the file (in Bytes)"

                    args = [t1, num_data]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    t2 = "Segments transmitted (including drop & RXT)"
                    args = [t2, tot_seg]
                    msg = "{0:<44}{1:>14}\n".format(*args)
                    log_file.write(msg)

                    t3 = "Number of Segments handled by PLD"
                    args = [t3, tot_seg_PLD]
                    msg = "{0:<35}{1:>23}\n".format(*args)
                    log_file.write(msg)

                    t4 = "Number of Segments dropped"
                    args = [t4, tot_drop]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    t5 = "Number of Segments Corrupted"
                    args = [t5, tot_corr]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    t6 = "Number of Segments Re-ordered "
                    args = [t6, tot_order]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    t7 = "Number of Segments Duplicated"
                    args = [t7, tot_dup_seg]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    t8 = "Number of Segments Delayed"
                    args = [t8, tot_dely]
                    msg = "{0:<29}{1:>29}\n".format(*args)
                    log_file.write(msg)

                    t9 = "Number of Retransmissions due to TIMEOUT"
                    args = [t9, timeout_retransmit]
                    msg = "{0:<42}{1:>16}\n".format(*args)
                    log_file.write(msg)

                    t10 = "Number of FAST RETRANSMISSION"
                    args = [t10, num_retransmit]
                    msg = "{0:<31}{1:>27}\n".format(*args)
                    log_file.write(msg)

                    t11 = "Number of DUP ACKs received"
                    args = [t11, tot_dup_ack]
                    msg = "{0:<30}{1:>28}\n".format(*args)
                    log_file.write(msg)

                    log_file.write("==========================================================")
                    log_file.close()
                    sys.exit()
                else:
                    cur_time = time.time() * 1000 - self.start_time
                    write_log(rcv_header, cur_time, "A", str_npkt2)

            except socket.timeout:
                print ("timed out in terminate")
                sys.exit()

    def PLD(self, packet, sender_socket):
        global num_data
        global tot_seg, tot_seg_PLD
        global tot_dup_seg
        global tot_drop, tot_corr, tot_order, tot_dely
        global order_window, order_count, delay_window
        global send_state
        global retransmit_flag
        global sample_timer, is_sampleTimer
        global rcv_header, snd_header

        is_sampleTimer = False
        ran_num = random.random()
        tot_seg += 1
        tot_seg_PLD += 1

        ini_state = "snd"
        if retransmit_flag:
            send_state = "snd/RXT"
            retransmit_flag = False
        else:
            send_state = "snd"

        if order_window and order_count == self.maxOrder:
            sender_socket.sendto(str(order_window[0]), (self.receive_host_ip, self.receiver_port))

            send_state = send_state + "/rord"

            cur_time = current_time(self.start_time)
            write_log(send_state, cur_time, "D", order_window[0])
            send_state = ini_state

            if len(order_window) == 1:
                order_count = 0
                del order_window[0]

        elif order_window and order_count != self.maxOrder:
            order_count += 1

        compare_time = current_time(self.start_time)

        count = 0
        for element in delay_window:
            if compare_time >= element[1]:
                sender_socket.sendto(str(element[0]), (self.receive_host_ip, self.receiver_port))
                send_state = send_state + "dely"
                write_log(send_state, compare_time, "D", packet)
                send_state = ini_state
                del delay_window[count]
            count += 1

        if ran_num >= self.pDrop:
            ran_num = random.random()
            if ran_num >= self.pDuplicate:
                ran_num = random.random()
                if ran_num >= self.pCorrupt:
                    ran_num = random.random()
                    if ran_num >= self.pOrder:
                        ran_num = random.random()
                        if ran_num >= self.pDelay:

                            if sample_timer:
                                # if the packet is not corrupted or dropped, the variable which controls
                                # sampleRTT_timer will be true
                                is_sampleTimer = True

                            sender_socket.sendto(str(packet), (self.receive_host_ip, self.receiver_port))

                            cur_time = current_time(self.start_time)

                            write_log(send_state, cur_time, "D", packet)
                        else:
                            tot_dely += 1
                            delay = random.uniform(0, self.maxDelay)

                            cur_time = current_time(self.start_time)
                            send_time = delay + cur_time
                            delay_ele = []
                            delay_ele.append(packet)
                            delay_ele.append(send_time)
                            delay_window.append(delay_ele)

                    else:
                        if not order_window and self.maxOrder != 0:
                            tot_order += 1
                            order_window.append(packet)
                            order_count = 0
                else:
                    tot_corr += 1
                    npkt = set_data_with_error(packet)
                    sender_socket.sendto(str(npkt), (self.receive_host_ip, self.receiver_port))
                    cur_time = current_time(self.start_time)
                    send_state = send_state + "/corr"

                    write_log(send_state, cur_time, "D", npkt)
                    send_state = ini_state
            else:
                tot_dup_seg += 1
                tot_seg += 1
                tot_seg_PLD += 1

                sender_socket.sendto(str(packet), (self.receive_host_ip, self.receiver_port))
                cur_time = current_time(self.start_time)
                write_log(send_state, cur_time, "D", packet)

                sender_socket.sendto(str(packet), (self.receive_host_ip, self.receiver_port))
                cur_time = current_time(self.start_time)

                write_log("snd/dup", cur_time, "D", packet)
        else:
            tot_drop += 1
            cur_time = current_time(self.start_time)
            drop_header = "drop"
            write_log(drop_header, cur_time, "D", packet)


def write_log(header, now_time, msg_type, packet):
    format_time = round(now_time / 1000, 3)

    args = [header, format_time, msg_type, str(get_seq(packet)), str(len(get_data(packet))), str(get_ack(packet))]
    msg = "{0:<15}{1:>14.2f}{2:>10}{3:>18}{4:>14}{5:>18}\n".format(*args)
    log_file.write(msg)


def current_time(ini_time):
    diff = time.time() * 1000 - ini_time
    return diff


def main():

    global state, timeout, log_file
    global num_data, num_retransmit, timeout_retransmit
    global tot_seg, tot_seg_PLD, tot_dup_seg
    global tot_dup_ack, tot_drop, tot_corr, tot_order, tot_dely
    global order_window, order_count, delay_window
    global seq, isn_send, ack
    global term_seq, term_ack
    global retransmit_flag
    global sample_timer, is_sampleTimer
    global snd_header, rcv_header
    global send_state

    order_count = 0
    num_data = 0
    num_retransmit = 0
    timeout_retransmit = 0

    tot_seg = 0
    tot_seg_PLD = 0
    tot_drop = 0

    tot_dup_seg = 0
    tot_dup_ack = 0
    tot_corr = 0
    tot_order = 0
    tot_dely = 0

    seq = 0
    isn_send = 0
    ack = 0
    term_seq = 0
    term_ack = 0
    send_state = ""
    retransmit_flag = False
    sample_timer = False
    is_sampleTimer = False
    order_window = []
    state = STATE_NONE
    delay_window = []

    snd_header = ""
    rcv_header = ""
    timeout = 1  # need to change here
    log_file = open('Sender_log.txt', 'w')
    log_file.close()
    log_file = open('Sender_log.txt', 'a')
    Sender()


main()
