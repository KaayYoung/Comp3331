#!/usr/bin/env python3.6

# implement UDP client(User Datagram Protocol)
import time
import sys
import numpy as np
total = len(sys.argv)

seq = 0
rtt_arr = []

def get_time():
	return int(round(time.time() * 1000))

from socket import *
serverName = str(sys.argv[total - 2])
serverPort = int(sys.argv[total - 1])

clientSocket = socket(AF_INET, SOCK_DGRAM)
clientSocket.settimeout(1.0)

while seq < 10:

	clientSocket.connect((serverName, serverPort))
	start = get_time()

	try: 
		outmessage = "hello"
		clientSocket.send(outmessage.encode('utf-8')) 
		modifiedMessage = clientSocket.recv(1024)
		
		end = get_time()
		# the length of time it takes for a signal to be sent 
		# plus the time that signal is be received (round trip delay)
		rtt = end - start

		rtt_arr.append(rtt) 
		#print(modifiedMessage)

		sentence = "ping to 127.0.0.1, seq = " + str(seq) + ", rtt = " + str(rtt)
	except timeout:
		sentence = "ping to 127.0.0.1, seq = " + str(seq) + ", rtt = " + "TIMEOUT"

	print(sentence)  
	seq = seq + 1

avg_rtt = np.mean(rtt_arr)
print("rtt min/avg/max = " + str(min(rtt_arr)) + "/" + str(avg_rtt) + "/" + str(max(rtt_arr)) + " ms")