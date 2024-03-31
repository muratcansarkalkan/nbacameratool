import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import struct
import os
import shutil

free_throw_frame = None
press_box_frame = None

floats_data = {}

cameras = ["Free Throw", "Press Box"]

# Read JSON data
with open('angles.json') as f:
    angles_data = json.load(f)

def create_menu(root):
    menubar = tk.Menu(root)
    
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Open", command=lambda: open_file(root))
    file_menu.add_command(label="Save", command=lambda: save_file(root, current_file_path, current_file_path))
    file_menu.add_command(label="Save As", command=lambda: save_as_file(root, current_file_path))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    
    menubar.add_cascade(label="File", menu=file_menu)
    
    root.config(menu=menubar)
    create_tabs(root, floats_data)

def update_float_value(camera, event, position):
    widget = event.widget
    category = widget.master.master.tab('current')  # Get the currently selected tab (category)
    
    # Get the text (angle name) of the selected tab
    angle = category['text']
    
    # Update the corresponding value in floats_data
    if camera and angle:  # Ensure category and angle are not None
        floats_data[camera][angle][position] = float(widget.get())
        print("Updated related float.")

def display_info():
    info_text = "This is some information you want to display."
    messagebox.showinfo("Information", info_text)

def update_all_float_values(root):
    # Iterate through all widgets and trigger the FocusOut event for Entry widgets
    for widget in root.winfo_children():
        if isinstance(widget, tk.Entry):
            widget.event_generate('<FocusOut>')

def create_tabs(root, floats_data):
    global free_throw_frame, press_box_frame
    
    if floats_data:  # Check if floats_data is not empty
        notebook = ttk.Notebook(root)
        notebook.pack(fill='both', expand=True)
        
        free_throw_frame = tk.Frame(notebook)
        press_box_frame = tk.Frame(notebook)
        
        notebook.add(free_throw_frame, text="Free Throw")
        notebook.add(press_box_frame, text="Press Box")
        
        # Read JSON data
        with open('angles.json') as f:
            angles_data = json.load(f)
        
        # Create notebook for angles under Free Throw
        angle_notebookft = ttk.Notebook(free_throw_frame)
        angle_notebookft.pack(fill='both', expand=True)
        
        # Populate frames with content based on JSON data
        for angle, positions in angles_data["Free Throw"].items():
            angle_frame = tk.Frame(angle_notebookft)
            angle_notebookft.add(angle_frame, text=angle)

            max_rows = 7  # Maximum number of rows before switching to a new column
            current_row = 0
            current_col = 0

            for i, (position, address) in enumerate(positions.items()):
                # Calculate current row and column
                current_row = i % max_rows
                current_col = i // max_rows
                label = tk.Label(angle_frame, text=f"{position}")
                label.grid(row=current_row, column=current_col * 2, padx=10, pady=5, sticky="w")

                # If floats_data is provided, display the loaded floats
                if floats_data:
                    float_value = floats_data["Free Throw"].get(angle, {}).get(position, "")

                    float_entry = tk.Entry(angle_frame, width=10)
                    float_entry.insert(0, str(float_value))
                    float_entry.grid(row=current_row, column=current_col * 2 + 1, padx=10, pady=5)
                    
                    # Bind function to capture changes
                    float_entry.bind('<FocusOut>', lambda event, pos=position: update_float_value("Free Throw", event, pos))

        # Create notebook for angles under Press Box
        angle_notebookpb = ttk.Notebook(press_box_frame)
        angle_notebookpb.pack(fill='both', expand=True)
        
        # Populate frames with content based on JSON data
        for angle, positions in angles_data["Press Box"].items():
            angle_frame = tk.Frame(angle_notebookpb)
            angle_notebookpb.add(angle_frame, text=angle)
            
            max_rows = 7  # Maximum number of rows before switching to a new column
            current_row = 0
            current_col = 0

            for i, (position, address) in enumerate(positions.items()):
                current_row = i % max_rows
                current_col = i // max_rows
                label = tk.Label(angle_frame, text=f"{position}")
                label.grid(row=current_row, column=current_col * 2, padx=10, pady=5, sticky="w")
                
                # If floats_data is provided, display the loaded floats
                if floats_data:
                    float_value = floats_data["Press Box"].get(angle, {}).get(position, "")
                    float_entry = tk.Entry(angle_frame, width=10)
                    float_entry.insert(0, str(float_value))
                    float_entry.grid(row=current_row, column=current_col * 2 + 1, padx=10, pady=5)
                    
                    # Bind function to capture changes
                    float_entry.bind('<FocusOut>', lambda event, pos=position: update_float_value("Press Box", event, pos))

# Define the size of a float in bytes
FLOAT_SIZE_BYTES = 4

def open_file(root):
    global current_file_path
    file_path = filedialog.askopenfilename(filetypes=[("NBA LIVE 2005/06 Camera Configuration File", "*.mgd")])
    if file_path:
        current_file_path = file_path
        
        # Destroy all widgets except the menu bar
        for widget in root.winfo_children():
            if isinstance(widget, tk.Menu):
                continue
            widget.destroy()

        # Load the floats from the file
        with open(current_file_path, 'rb') as file:
            for camera in cameras:
                floats_data[camera] = {}
                for angle, positions in angles_data[camera].items():
                    floats_data[camera][angle] = {}
                    for position, address in positions.items():
                        file.seek(int(address, 16))
                        floats_data[camera][angle][position] = struct.unpack('<f', file.read(FLOAT_SIZE_BYTES))[0]
                    
        create_tabs(root, floats_data)

def save_file(root, current_file_path, new_file_path):
    update_all_float_values(root)
    if current_file_path:
        try:
            # If the file already exists, create a backup copy with a different name
            if not os.path.exists(current_file_path):
                messagebox.showerror("Error", "The specified file does not exist.")
                return
            if new_file_path:
                if current_file_path != new_file_path:
                    # Copy the contents of the current file to the new file
                    shutil.copyfile(current_file_path, new_file_path)

                    # Update the file path to the new file path
                    current_file_path = new_file_path

            # Perform the changes in the new file
            with open(current_file_path, 'r+b') as file:
                for camera, angles in angles_data.items():
                    for angle, positions in angles.items():
                        for position, address in positions.items():
                            # Retrieve the updated float value from the input box
                            new_float_value = float(floats_data[camera][angle][position])
                            # Seek to the memory address
                            file.seek(int(address, 16))
                            # Pack and write the new float value
                            packed_float = struct.pack('<f', new_float_value)
                            file.write(packed_float)
            messagebox.showinfo("Save", "File saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while saving the file: {e}")
    else:
        messagebox.showerror("Error", "No file path specified.")

def save_as_file(root, current_file_path):
    try:
        # Get the new file path from the save dialog
        file_path = filedialog.asksaveasfilename(defaultextension=".mgd", filetypes=[("NBA LIVE 2005/06 Camera Configuration File", "*.mgd")])
        if file_path:
            save_file(root, current_file_path, file_path)
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while saving the file: {e}")
