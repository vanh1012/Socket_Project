import socket
import os

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        # Get the list of files to download
        files = [f for f in os.listdir('shared_files') if os.path.isfile(os.path.join('shared_files', f))]
        if not files:
            conn.sendall(b"ERROR: No files available for download")
            return
        
        # Send the list of files to the client
        files_list = "\n".join(files)
        conn.sendall(files_list.encode('utf8'))
        
        while True:
            file_name = conn.recv(1024).decode()
            if not file_name:
                break
            
            full_path = os.path.join('shared_files', file_name)
            if not os.path.isfile(full_path):
                conn.sendall(b"ERROR: File not found")
                continue

            file_size = os.path.getsize(full_path)
            conn.sendall(str(file_size).encode('utf8'))

            with open(full_path, "rb") as file:
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    conn.sendall(chunk)
            print(f"File {file_name} sent successfully")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def main():
    # Ensure the directory for shared files exists
    os.makedirs('shared_files', exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((socket.gethostname(), 22222))
    sock.listen(5)
    print("Host Name: ", sock.getsockname())

    try:
        while True:
            conn, addr = sock.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()