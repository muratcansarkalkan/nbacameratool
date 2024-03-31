import tkinter as tk
from menus import create_menu, open_file, save_file, save_as_file

def main():
    root = tk.Tk()
    root.title("NBA Live Camera Tool")
    root.geometry('700x400')
    global current_file_path
    current_file_path = None
    
    create_menu(root)
    
    # root.bind("<Control-o>", lambda event: open_file(root))
    # root.bind("<Control-s>", lambda event: save_file(root, current_file_path, current_file_path))
    # root.bind("<Control-S>", lambda event: save_as_file(root, current_file_path))
    # root.bind("<Control-q>", lambda event: root.quit())
    
    root.mainloop()

if __name__ == "__main__":
    main()
