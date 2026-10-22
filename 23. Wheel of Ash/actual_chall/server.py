import socket
import challenge

HOST = "127.0.0.1"
PORT = 5000
MAX_QUERIES =4000
query_count=0

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen()

print(f"Server is listening on {HOST}:{PORT}...")


conn, addr = server_socket.accept()
print(f"Got a connection from {addr}")

banner = (
    "================================\n"
    "        THE WHEEL OF ASH\n"
    "================================\n"
    "\n"
    "The wheel remembers.\n"
    "\n"
    f"n = {challenge.n}\n"
    f"e = {challenge.e}\n"
    f"R = {challenge.R}\n"
    f"Echo = {challenge.Echo}\n"
    "\n"
    "Commands: help, compare <value>, quit\n"
)

conn.sendall(banner.encode())

while True:
    data = conn.recv(1024)

    if not data:
        print("Client disconnected.")
        break

    line = data.decode().strip()
    if not line:
        conn.sendall(b"Empty input. get help.\n")
        continue

    parts = line.split(maxsplit=1)
    command = parts[0].upper()
    argument = parts[1] if len(parts) > 1 else None

    if command == "HELP":
        conn.sendall(b"Commands: help, compare <value>, QUIT\n")

    
    elif command == "COMPARE":
        if argument is None:
            conn.sendall(b"Usage: compare <value>\n")
        elif query_count >= MAX_QUERIES:
            conn.sendall(b"Query limit reached. Connection will close.\n")
            break
        else:
            try:
                Cx = int(argument)
            except ValueError:
                conn.sendall(b"Ciphertext must be an integer.\n")
            else:
                if Cx < 0 or Cx >= challenge.n:
                    conn.sendall(b"Ciphertext out of range.\n")
                else:
                    query_count += 1
                    try:
                        result = challenge.oracle(Cx)
                    except Exception as ex:
                        print(f"Unexpected error in oracle: {ex}")
                        conn.sendall(b"Internal error processing query.\n")
                    else:
                        conn.sendall(
                            b"TRUE\n" if result else b"FALSE\n"
                        )
    elif command == "QUIT":
        conn.sendall(b"Bye!\n")
        break

    else:
        conn.sendall(b"Unknown command. Type help.\n")
conn.close()
server_socket.close()
print("Server shut down.")
