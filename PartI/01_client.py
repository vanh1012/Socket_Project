import socket
import sys
import os
import time
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext
import threading

class FileState:
    def __init__(self, file_name, file_size):
        self.file_name = file_name
        self.file_size = file_size
        self.received_size = 0

def update_chat_display(message):
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, message + "\n")
    chat_display.config(state=tk.DISABLED)
    chat_display.yview(tk.END)

def display_progress():
    chat_display.config(state=tk.NORMAL)
    chat_display.delete(1.0, tk.END)  # Clear the display
    
    chat_display.insert(tk.END, "Download Progress:\n")
    chat_display.insert(tk.END, "="*50 + "\n")
    
    for file_state in state:
        percentage = (file_state.received_size / file_state.file_size) * 100 if file_state.file_size else 0
        percentage = min(100, percentage)
        bar_length = 40
        filled_length = int(bar_length * percentage // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        chat_display.insert(tk.END, f"{file_state.file_name} [{bar}] {percentage:.2f}%\n")
    
    chat_display.insert(tk.END, "="*50 + "\n")
    chat_display.config(state=tk.DISABLED)
    chat_display.yview(tk.END)

def send_request_and_download(client_socket, file_name):
    # Send file name to the server
    client_socket.send(file_name.encode())

    # Receive response from the server
    response = client_socket.recv(1024).decode()
    if response.startswith("ERROR"):
        root.after(0, update_chat_display, f"Server response for {file_name}: {response}")
        return
    
    file_size = int(response)
    file_state = FileState(file_name, file_size)
    state.append(file_state)
    output_directory = Path("output")
    output_directory.mkdir(exist_ok=True)
    local_file_path = output_directory / file_name

    with open(local_file_path, "wb") as file:
        while file_state.received_size < file_size:
            data = client_socket.recv(1024)
            if not data:
                break
            file.write(data)
            file_state.received_size += len(data)
            root.after(0, display_progress)

    root.after(0, update_chat_display, f"All File downloaded successfully")

def connect_to_server():
    global client_socket
    host = host_entry.get()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, 22222))
        root.after(0, update_chat_display, "Connected successfully")
        
        # Get the list of files from the server
        files_list = client_socket.recv(4096).decode()
        root.after(0, update_chat_display, "Available files from the server:\n" + files_list)
    except Exception as e:
        root.after(0, update_chat_display, f"Unable to connect: {e}")
        return

    downloaded_files = set()
    input_file_path = "input.txt"
    output_directory = Path("output")
    output_directory.mkdir(exist_ok=True)

    try:
        while True:
            time.sleep(2)
            
            # Read the input.txt file and compare its content
            if os.path.exists(input_file_path):
                with open(input_file_path, "r") as file_list:
                    current_files = [line.strip() for line in file_list]

                # Check if files are already downloaded
                downloaded_files_set = {f.name for f in output_directory.iterdir() if f.is_file()}
                current_files = [f for f in current_files if f not in downloaded_files_set]

                # Find new files that need to be downloaded
                for file in current_files:
                    if file not in downloaded_files:
                        root.after(0, update_chat_display, f"Requesting download for: {file}")
                        send_request_and_download(client_socket, file)
                        downloaded_files.add(file)
    except KeyboardInterrupt:
        root.after(0, update_chat_display, "Shutting down client...")
    finally:
        client_socket.close()

def start_download_thread():
    download_thread = threading.Thread(target=connect_to_server)
    download_thread.daemon = True
    download_thread.start()

def main():
    global root, chat_display, state, host_entry, client_socket
    state = []

    root = tk.Tk()
    root.title("File Download Progress")

    tk.Label(root, text="Enter Host IP:").pack(pady=5)
    host_entry = tk.Entry(root)
    host_entry.pack(pady=5)

    connect_button = tk.Button(root, text="Connect", command=start_download_thread)
    connect_button.pack(pady=5)

    chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
    chat_display.pack(expand=True, fill=tk.BOTH)

    root.mainloop()

if __name__ == "__main__":
    main()
