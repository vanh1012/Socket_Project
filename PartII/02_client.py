import socket
import os
import time
import threading
import tkinter as tk
from tkinter import scrolledtext

PORT = 22222
BUFSIZE = 1024

priority_map = {
    'NORMAL': 1,
    'HIGH': 4,
    'CRITICAL': 10
}

class FileState:
    def __init__(self, file_name, file_size, received_size, downloaded, priority):
        self.file_name = file_name
        self.file_size = file_size
        self.received_size = received_size
        self.downloaded = downloaded
        self.priority = priority

state = []
total_size = 0
total_received = 0

def display_progress():
    def update_display():
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

    # Schedule the update_display function to run on the main thread
    root.after(0, update_display)


def get_priority_value(priority):
    return priority_map.get(priority.strip(), 1)

def handle(client_socket, file_list):
    input_path = os.path.join(os.getcwd(), 'input.txt')

    while True:
        new_files_added = False
        with open(input_path, "r") as file_list:
            for line in file_list:
                line = line.strip()
                if not line or not len(line):
                    break
                
                new_file, _, priority = line.partition(' ')
                new_file = new_file.strip()
                
                if new_file not in [file.file_name for file in state]:
                    prepare(client_socket, priority.strip(), new_file)
                    new_files_added = True
            
        if new_files_added:
            send_state(client_socket)
            multi_download(client_socket, file_list)
        
        time.sleep(2)

def send_state(client_socket):
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, "Preparing to send state...\n")
    chat_display.config(state=tk.DISABLED)
    client_socket.sendall(b"START SENDING STATES")
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, "Sending states...\n")
    chat_display.config(state=tk.DISABLED)

    for file_state in state:
        if not file_state.downloaded:
            client_socket.send(file_state.file_name.encode('utf8'))
            response = client_socket.recv(BUFSIZE).decode('utf8')
            if response.startswith("ERROR"):
                chat_display.config(state=tk.NORMAL)
                chat_display.insert(tk.END, f"\n[CLIENT] Server response for {file_state.file_name}: {response}\n")
                chat_display.config(state=tk.DISABLED)
                continue  # skip trying to send the file priority
            
            client_socket.send(str(file_state.priority).encode('utf8'))
            response = client_socket.recv(BUFSIZE).decode('utf8')
            if response.startswith("ERROR"):
                chat_display.config(state=tk.NORMAL)
                chat_display.insert(tk.END, f"\n[CLIENT] Server response for {file_state.file_name}: {response}\n")
                chat_display.config(state=tk.DISABLED)
        
    client_socket.sendall(b"FINISHED SENDING STATES")

def prepare(client_socket, priority, new_file):
    client_socket.send(new_file.encode('utf8'))
    response = client_socket.recv(BUFSIZE).decode('utf8')
    if response.startswith("ERROR"):
        chat_display.config(state=tk.NORMAL)
        chat_display.insert(tk.END, f"\n[CLIENT] Server response for {new_file}: {response}\n")
        chat_display.config(state=tk.DISABLED)
    else:
        try:
            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, f"{new_file} {response}\n")
            chat_display.config(state=tk.DISABLED)
            file_size = int(response)
            state.append(FileState(new_file, file_size, 0, False, get_priority_value(priority)))
        except ValueError:
            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, f"\n[CLIENT] Invalid file size response for {new_file}: {response}\n")
            chat_display.config(state=tk.DISABLED)
            state[:] = [file for file in state if file.file_name != new_file]

def read_exactly(client_socket, n):
    data = bytearray()
    while len(data) < n:
        packet = client_socket.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def read_header(client_socket):
    header_data = bytearray()
    while True:
        char = client_socket.recv(1)
        if char == b'\n':
            break
        header_data += char
    return header_data.decode('utf8')

def multi_download(client_socket, files_list):
    output = os.path.join(os.getcwd(), 'output')
    os.makedirs(output, exist_ok=True)
    
    while any(not file_state.downloaded for file_state in state):
        header = read_header(client_socket).split()
        if not header:
            break
        
        if header[0] == "START":
            file_name = header[1]
            file_size = int(header[2])
            for file_state in state:
                if file_state.file_name == file_name:
                    file_state.file_size = file_size
                    file_state.received_size = 0
                    file_path = os.path.join(output, file_name)
                    file_state.output_file = open(file_path, 'wb')
                    break
        elif header[0] == "CHUNK":
            file_name = header[1]
            chunk_size = int(header[2])
            data = read_exactly(client_socket, chunk_size)
            if data is not None:
                for file_state in state:
                    if file_state.file_name == file_name:
                        file_state.output_file.write(data)
                        file_state.received_size += len(data)
                        display_progress()
                        break
        elif header[0] == "END":
            file_name = header[1]
            for file_state in state:
                if file_state.file_name == file_name:
                    file_state.downloaded = True
                    file_state.output_file.close()
                    del file_state.output_file
                    break
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, "[CLIENT] Downloaded all files")
    chat_display.config(state=tk.DISABLED)

    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, f"[CLIENT] Available files from the server:\n{files_list}")
    chat_display.config(state=tk.DISABLED)

def connect_to_server():
    global chat_display, host_entry, root

    host = host_entry.get()
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, PORT))
        update_chat_display(f"[CLIENT] Connected to {host}\n")

        files_list = client_socket.recv(BUFSIZE).decode('utf8')
        update_chat_display(f"[CLIENT] Available files from the server:\n{files_list}")

        # Handle connection in a separate thread
        handle_thread = threading.Thread(target=handle, args=(client_socket, files_list), daemon=True)
        handle_thread.start()
    except Exception as e:
        update_chat_display(f"[CLIENT] Unable to connect to {host}: {e}\n")
    finally:
        client_socket.close()

def update_chat_display(message):
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, message)
    chat_display.config(state=tk.DISABLED)
    chat_display.yview(tk.END)

def main():
    global chat_display, host_entry, root

    root = tk.Tk()
    root.title("File Transfer Client")

    host_entry = tk.Entry(root)
    host_entry.pack(fill=tk.X, padx=10, pady=5)
    host_entry.insert(0, "Enter Host IP")

    connect_button = tk.Button(root, text="Connect", command=lambda: threading.Thread(target=connect_to_server, daemon=True).start())
    connect_button.pack(pady=5)

    chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
    chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    root.mainloop()

if __name__ == "__main__":
    main()
