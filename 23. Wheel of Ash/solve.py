import socket

HOST = "127.0.0.1"
PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Connected. Reading banner...")

def recv_line():
    """Read from the socket until we hit a newline, return it decoded."""
    buffer = b""
    while not buffer.endswith(b"\n"):
        chunk = sock.recv(1)
        if not chunk:
            break
        buffer += chunk
    return buffer.decode().strip()



# read and print the whole banner until we reach the "Commands:" line
n = e = R = Echo = None
while True:
    line = recv_line()
    print("SERVER>", line)
    if line.startswith("n = "):
        n = int(line.split("=")[1].strip())
    elif line.startswith("e = "):
        e = int(line.split("=")[1].strip())
    elif line.startswith("R = "):
        R = int(line.split("=")[1].strip())
    elif line.startswith("Echo = "):
        Echo = int(line.split("=")[1].strip())
    elif line.startswith("Commands:"):
        break

print()
print(f"Parsed: n={n}, e={e}, R={R}, Echo={Echo}")

def compare(x):
    """
    Ask the server's oracle about a specific x value.
    We compute Cx = x^e mod n ourselves, send it, and interpret
    the TRUE/FALSE response.
    """
    Cx = pow(x, e, n)
    sock.sendall(f"COMPARE {Cx}\n".encode())
    response = recv_line()
    return response == "TRUE"

# --- binary search for M2 ---
lo = 0
hi = n

queries_used = 0

while lo < hi:
    mid = (lo + hi) // 2
    result = compare(mid)
    queries_used += 1

    if result:
        # mid is "ahead of" M2 -> M2 is in the lower half
        hi = mid
    else:
        # mid is "behind" M2 (or equal) -> M2 is in the upper half
        lo = mid + 1

M2 = lo

print(f"Queries used: {queries_used}")
print(f"Recovered M2 = {M2}")

M1 = (M2 - R) % n

from Crypto.Util.number import long_to_bytes
flag = long_to_bytes(M1)

print(f"M1 = {M1}")
print(f"FLAG = {flag.decode()}")

sock.close()
