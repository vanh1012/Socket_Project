import socket
import os
import threading

HOST = socket.gethostname()
PORT = 22222
BUFSIZE = 1024

class FileState:
    def __init__(self, file_name, sent_size, downloaded, priority):
        self.file_name = file_name
        self.sent_size = sent_size
        self.downloaded = downloaded
        self.priority = priority

def receive_state(conn):
    state = []
    
    print("recv state")
    while True:
        name = conn.recv(BUFSIZE).decode('utf8')
        # print("state name", name)
        
        if name == "FINISHED SENDING STATES":
            print("[SERVER] Finished receiving states of files")
            break
        
        if not name:
            conn.sendall("ERROR: Cannot receive file name".encode('utf8'))
        else:
            if not os.path.isfile(os.path.join('shared_files', name)):
                conn.sendall("ERROR: File not found".encode('utf8'))
                continue
            conn.sendall("Received file name".encode('utf8'))
            
        priority = conn.recv(BUFSIZE).decode('utf8')
        if not priority:
            conn.sendall("ERROR: Cannot receive file priority".encode('utf8'))
        else:
            conn.sendall("Received file priority".encode('utf8'))
        
        state.append(FileState(name, 0, False, int(priority)))
    
    return state

def send_header(conn, header):
    conn.sendall(f"{header}\n".encode('utf8'))

def send_file_chunk(conn, file_state, share_file):
    file_path = os.path.join(share_file, file_state.file_name)
    with open(file_path, 'rb') as file:
        file.seek(file_state.sent_size)
        chunk_size = BUFSIZE * file_state.priority
        data = file.read(chunk_size)
        
        if file_state.sent_size == 0:
            file_size = os.path.getsize(file_path)
            send_header(conn, f"START {file_state.file_name} {file_size}")
        
        send_header(conn, f"CHUNK {file_state.file_name} {len(data)}")
        conn.sendall(data)
        file_state.sent_size += len(data)
        
        if file_state.sent_size >= os.path.getsize(file_path):
            send_header(conn, f"END {file_state.file_name}")
            file_state.downloaded = True

def send_files(conn, state, share_file):
    while any(not file_state.downloaded for file_state in state):
        for file_state in state:
            if not file_state.downloaded:
                send_file_chunk(conn, file_state, share_file)
    
    print("\n[SERVER] Sent all files")

def handle_client(conn, addr):
    print(f"[SERVER] Connected by {addr}")
    state = []
    share_file = os.path.join(os.getcwd(), 'shared_files')

    try:
        while True:
            files = [f for f in os.listdir(share_file) if os.path.isfile(os.path.join(share_file, f))]
            if not files:
                conn.sendall("ERROR: No files available for download".encode('utf8'))
                return
            
            files_list = "\n".join(files)
            conn.sendall(files_list.encode('utf8'))
            
            while True:
                data = conn.recv(BUFSIZE).decode('utf8')
                if data == "START SENDING STATES":
                    state = receive_state(conn)
                    if state:
                        send_files(conn, state, share_file)
                    
                    # Check if all files are downloaded
                    if all(file.downloaded for file in state):
                        conn.sendall("ALL FILES DOWNLOADED".encode('utf8'))
                        break  # Exit the inner loop to re-send the file list

                elif not data:
                    break
                
                full_path = os.path.join(share_file, data)
                if not os.path.isfile(full_path):
                    conn.sendall("ERROR: File not found".encode('utf8'))
                else:
                    file_size = os.path.getsize(full_path)
                    conn.sendall(str(file_size).encode('utf8'))

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, PORT))
    sock.listen(5)
    print("[SERVER] Host name: ", sock.getsockname())
    print("[SERVER] Waiting for connections...")

    try:
        while True:
            conn, addr = sock.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr),daemon = True)
            client_thread.start()
    except KeyboardInterrupt:
        print("[SERVER] Server shutting down...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
    