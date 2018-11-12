import sys

from socket import *
# allow to input server port
serverPort = int(sys.argv[1])

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('', serverPort))
serverSocket.listen(1)
print "The server is ready to receive"
while 1:	
    connectionSocket, addr = serverSocket.accept()
    sentence = connectionSocket.recv(1024)

    try:
        # Because sentence = "GET /..... HTTP/...."
        # We need to split
        parts = sentence.split("/")
        file_name = parts[1].split(" ")
        # open file and read the content of the file
        f = open(file_name[0])
        data = f.read()
        # Header lines
        connectionSocket.send("HTTP/1.1 200 OK\n\n")
        connectionSocket.send(data)
        
        connectionSocket.close()

    except IOError:
        connectionSocket.send("HTTP/1.1 404 NOT FOUND\n\n")
        r = "<html><body> 404 NOT FOUND </body></html>"
        connectionSocket.send(r)
        
        connectionSocket.close()
        
