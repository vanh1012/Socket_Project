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

        # Create the list of files with their sizes
        files_list = []
        for file in files:
            file_size = os.path.getsize(os.path.join('shared_files', file))
            # Convert file size to a readable format (KB, MB, etc.)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if file_size < 1024.0:
                    size_str = f"{file_size:.1f}{unit}"
                    break
                file_size /= 1024.0
            files_list.append(f"{file} {size_str}")
        
        # Send the list of files to the client
        files_list_str = "\n".join(files_list)
        conn.sendall(files_list_str.encode('utf8'))
        
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
    sock.bind(("127.0.0.1", 22222))
    sock.listen(5)
    print(f"Server listening on 127.0.0.1:22222")

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
