from socket import socket, AF_INET, SOCK_STREAM, timeout
from threading import Thread, Lock
import sys
from argparse import ArgumentParser

#TODO: Implement a client that connects to your server to chat with other clients here

# Use sys.stdout.flush() after print statemtents

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument('-join', action="store_true")
	parser.add_argument('-host', required=True)
	parser.add_argument('-port', required=True)
	parser.add_argument('-username')
	parser.add_argument('-passcode')
	args = parser.parse_args()

	SERVER_HOST = args.host
	SERVER_PORT = int(args.port)
	state = "WAIT_ON_PASSCODE"
	print_client_status = False # if true, print additional stuff for debugging
	# if print_client_status: print(vars(args))
	
	with socket(family=AF_INET, type=SOCK_STREAM) as cs:
		cs.connect((SERVER_HOST, SERVER_PORT)) # does the three-way handshake

		request_username = True
		request_passcode = True
		if args.passcode != None:
			passcode = args.passcode
			request_passcode = False
		if args.username != None: 
			display_name = args.username
			request_username = False

		stop_listening = False
		recv_lock = Lock()
		def listening_to_other_clients():
			while True:
				try:
					cs.settimeout(0.01)
					# if print_client_status: print("should receive")
					with recv_lock:
						# if print_client_status: print(f"is the lock taken? {recv_lock.locked()}")
						print(cs.recv(1024).decode()); sys.stdout.flush()
					# if print_client_status: print("Received something")
					if stop_listening: break
				except timeout:
					if print_client_status: print(f"is the lock taken? {recv_lock.locked()}")
					pass
				except Exception as e:
					# if print_client_status: print(f"listening to other clients failed: {type(e)}")
					if recv_lock.locked(): recv_lock.release()
					break
		listening_thread = Thread(target=listening_to_other_clients)
		listening_thread.start()

		while True:
			if state == "WAIT_ON_PASSCODE":
				try:
					if request_passcode: passcode = input("PLEASE ENTER THE PASSCODE: ")
					with recv_lock:
						# cs.settimeout(0.01)
						cs.send(passcode.encode())
						server_response = cs.recv(1024).decode()
					if server_response == "WAIT_ON_PASSCODE":
						print("Incorrect passcode"); sys.stdout.flush()
						request_passcode = True
					else:
						print(f"Connected to {SERVER_HOST} on port {SERVER_PORT}"); sys.stdout.flush()
					state = server_response
				except:
					stop_listening = True
					if recv_lock.locked(): recv_lock.release()
					break
			elif state == "CHOOSE_DISPLAY_NAME":
				try:
					if request_username: display_name = input("PLEASE ENTER YOUR DISPLAY NAME: ")
					with recv_lock:
						# cs.settimeout(0.01)
						cs.send(display_name.encode())
						server_response = cs.recv(1024).decode()
					if server_response != "INVALID NAME": # proceed
						state = "IN_CHATROOM"
						# print(server_response)
						# sys.stdout.flush()
					else:
						request_username = True
				except:
					stop_listening = True
					if recv_lock.locked(): recv_lock.release()
					break
			elif state == "IN_CHATROOM":
				try:
					msg = input("")
					with recv_lock:
						# cs.settimeout(0.01)
						cs.send(msg.encode())
						server_response = cs.recv(1024).decode()
					if server_response != "EXIT ACK":
						# print(server_response); sys.stdout.flush()
						pass
					else:
						stop_listening = True
						break
				except:
					stop_listening = True
					if recv_lock.locked(): recv_lock.release()
					break
		listening_thread.join()
	sys.exit()
