import socket
import sys
import os
import time
from pathlib import Path

def display_progress(file_name, received, total):
    percentage = (received / total) * 100
    sys.stdout.write(f"\rDownloading {file_name} .... {percentage:.2f}%")
    sys.stdout.flush()

def send_request_and_download(client_socket, file_name):
    # Send file name to the server
    client_socket.send(file_name.encode())

    # Receive response from the server
    response = client_socket.recv(1024).decode()
    if response.startswith("ERROR"):
        print(f"\nServer response for {file_name}: {response}")
        return
    
    file_size = int(response)
    received_size = 0
    output_directory = Path("output")
    output_directory.mkdir(exist_ok=True)
    local_file_path = output_directory / file_name

    with open(local_file_path, "wb") as file:
        while received_size < file_size:
            data = client_socket.recv(1024)
            if not data:
                break
            file.write(data)
            received_size += len(data)
            display_progress(file_name, received_size, file_size)

    print(f"\n{file_name} downloaded successfully")

def main():
    host = input("Enter Host Name: ")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, 22222))
        print("Connected successfully")
        
        # Get the list of files from the server
        files_list = client_socket.recv(4096).decode()
        print("Available files from the server:\n" + files_list)
    except Exception as e:
        print("Unable to connect:", e)
        exit(1)

    downloaded_files = set()
    input_file_path = "input.txt"

    try:
        while True:
            time.sleep(2)
            
            # Read the input.txt file and compare its content
            if os.path.exists(input_file_path):
                with open(input_file_path, "r") as file_list:
                    current_files = {line.strip() for line in file_list}
            
                # Find new files that need to be downloaded
                new_files = current_files - downloaded_files

                for file in new_files:
                    print(f"\nRequesting download for: {file}")
                    send_request_and_download(client_socket, file)
                    downloaded_files.add(file)
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()