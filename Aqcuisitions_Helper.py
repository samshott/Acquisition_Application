import tkinter as tk
from tkinter import messagebox
from multi_drive_copy_utility import MultiDriveCopyUtility  # Import the class

class DataOrganizationApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Data Organization App")
        self.master.geometry("300x200")
        self.show_main_menu()

    def show_main_menu(self):
        self.clear_window()
        tk.Button(self.master, text="Data Organization", command=self.show_data_organization_menu, height=2, width=20).pack(pady=10)
        tk.Button(self.master, text="Exit", command=self.master.quit, height=2, width=20).pack(pady=10)

    def show_data_organization_menu(self):
        self.clear_window()
        tk.Button(self.master, text="Field Copy Sensor USB drives", command=self.field_copy, height=2, width=30).pack(pady=10)
        tk.Button(self.master, text="Office Copy Secondary Drive", command=self.office_copy, height=2, width=30).pack(pady=10)
        tk.Button(self.master, text="Back to Main Menu", command=self.show_main_menu, height=2, width=30).pack(pady=10)

    def clear_window(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    def field_copy(self):
        # Create a new top-level window
        field_copy_window = tk.Toplevel(self.master)
        field_copy_window.title("Field Copy Sensor USB drives")
        
        # Create an instance of MultiDriveCopyUtility in the new window
        MultiDriveCopyUtility(field_copy_window)
        
        # Optional: Wait for this window to be closed before allowing interaction with the main window
        field_copy_window.transient(self.master)
        field_copy_window.grab_set()
        self.master.wait_window(field_copy_window)

    def office_copy(self):
        messagebox.showinfo("Info", "Office Copy Secondary Drive functionality not implemented yet.")

if __name__ == "__main__":
    root = tk.Tk()
    app = DataOrganizationApp(root)
    root.mainloop()