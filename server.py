from socket import *
from threading import Thread, Lock
from argparse import ArgumentParser
import sys
from datetime import datetime, timedelta

#TODO: Implement all code for your server here

# Use sys.stdout.flush() after print statemtents

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument('-start', action='store_true')
	parser.add_argument('-port', required=True)
	parser.add_argument('-passcode', required=True)
	args = parser.parse_args()
	
	SERVER_HOST = '127.0.0.1'
	SERVER_PORT = int(args.port)
	PASSCODE = args.passcode
	print_server_status = False # if true, print additional stuff for debugging

	if len(PASSCODE) > 5 or not PASSCODE.isalpha():
		raise ValueError("passcode much contain a maximum of 5 alphanumeric characters")

	with socket(family=AF_INET, type=SOCK_STREAM) as ss:
		ss.bind((SERVER_HOST, SERVER_PORT))
		ss.listen(1)
		
		print(f"Server started on port {SERVER_PORT}. Accepting connections"); sys.stdout.flush()

		# initialize global variables
		INITIAL_STATE = "WAIT_ON_PASSCODE"
		client_sockets = []
		client_display_names = []
		client_state = []
		client_threads = []
		closing_threads = []
		connection_closure_lock = Lock()

		def receive(conn_socket):
			def clean_close():
				with connection_closure_lock:
					rm_idx = client_sockets.index(conn_socket)
					client_sockets.remove(conn_socket)

					removed_client = client_display_names.pop(rm_idx)
					del client_state[rm_idx]

					closing_thread = client_threads[rm_idx]
					client_threads.remove(closing_thread)
					closing_threads.append(closing_thread)

					for socket in client_sockets:
						socket.send(f"{removed_client} left the chatroom".encode())

				conn_socket.close()
				print(f"{removed_client} left the chatroom"); sys.stdout.flush()
					
					# if print_server_status: 
					# 	print(f"total connected clients: {len(client_sockets)}")
					# 	print(f"usernames: {client_display_names}")
					# 	print(f"states: {client_state}")

			def app_response(client_input, curr_state):
				# do stuff with data
				next_state = curr_state # repeat state unless specified otherwise
				if curr_state == "WAIT_ON_PASSCODE":
					if client_input == PASSCODE:
						server_reponse = "CHOOSE_DISPLAY_NAME"
						with connection_closure_lock:
							edit_idx = client_sockets.index(conn_socket)
							client_state[edit_idx] = "CHOOSE_DISPLAY_NAME"
						next_state = "CHOOSE_DISPLAY_NAME"
					else:
						server_reponse = curr_state
				elif curr_state == "CHOOSE_DISPLAY_NAME":
					if len(client_input) <= 8 and len(client_input.split()) == 1:
						server_reponse = f"{client_input} joined the chatroom"
						with connection_closure_lock: # register client name
							edit_idx = client_sockets.index(conn_socket)
							client_display_names[edit_idx] = client_input
							client_state[edit_idx] = "IN_CHATROOM"
							print(server_reponse); sys.stdout.flush()
							for idx, socket in enumerate(client_sockets):
								if client_state[idx] == "IN_CHATROOM" and socket != conn_socket:
									# if print_server_status: print("SEND EVERYONE join notification")
									socket.send(server_reponse.encode())
						next_state = "IN_CHATROOM"
					else:
						server_reponse = "INVALID NAME"
				elif curr_state == "IN_CHATROOM":
					processed_msg = client_input
					
					# Check 1: ":mytime" or ":+1hr"
					if processed_msg == ":mytime":
						processed_msg = datetime.now().strftime('%a %b %d %X %Y')
					elif f"{processed_msg[:2]}{processed_msg[-2:]}" == ":+hr" and processed_msg[2].isdigit():
						final_time = datetime.now() + timedelta(hours=int(processed_msg[2]))
						processed_msg = final_time.strftime('%a %b %d %X %Y')
					
					processed_msg = processed_msg.replace(":)", "[feeling happy]").replace(":(", "[feeling sad]")

					if processed_msg == ":Exit":
						next_state = "EXIT"
						server_reponse = "EXIT ACK"
					else:
						splitted_input = processed_msg.split()
						with connection_closure_lock:
							src_idx = client_sockets.index(conn_socket)
							if splitted_input[0] == ":dm" and splitted_input[1] in client_display_names:
								processed_msg = " ".join(splitted_input[2:])
								server_reponse = f"{client_display_names[src_idx]}: {processed_msg}"
								print(f"{client_display_names[src_idx]} to {splitted_input[1]}: {processed_msg}"); sys.stdout.flush()
								dest_idx = client_display_names.index(splitted_input[1])
								dest_socket = client_sockets[dest_idx]
								dest_socket.send(server_reponse.encode())
							else:
								server_reponse = f"{client_display_names[src_idx]}: {processed_msg}"
								print(server_reponse); sys.stdout.flush()
								for idx, socket in enumerate(client_sockets):
									if client_state[idx] == "IN_CHATROOM" and socket != conn_socket:
										socket.send(server_reponse.encode())
					
				return server_reponse, next_state

			curr_state = INITIAL_STATE
			
			while True:
				try:
					conn_socket.settimeout(20)
					client_input = conn_socket.recv(1024).decode() # doesn't proceed until it receives message
					server_reponse, curr_state = app_response(client_input, curr_state)
					conn_socket.send(server_reponse.encode())
					if curr_state == "EXIT":
						raise Exception("Client exited")
				except Exception:					
					clean_close()
					break

		while True:
			# deal with TCP connection request
			conn, addr = ss.accept() # doesn't proceed until it receives request
			# if print_server_status: print(f"Accepted connection from {addr}") 

			client_thread = Thread(target=receive, args=(conn,))
			client_thread.start()

			with connection_closure_lock:
				client_sockets.append(conn)
				client_display_names.append("(PLACEHOLDER)")
				client_state.append(INITIAL_STATE)
				client_threads.append(client_thread)
				while len(closing_threads) > 0:
					closing_threads.pop(0).join()
					# if print_server_status: print("finished thread joined main")

			# if print_server_status:
			# 	print(f"total connected clients: {len(client_sockets)}")
			# 	print(f"usernames: {client_display_names}")
			# 	print(f"states: {client_state}")
