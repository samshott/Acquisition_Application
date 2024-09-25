import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import json
import platform
import hashlib
import threading
import time
import logging
import utils.band_splitter as band_splitter


class MultiDriveCopyUtility:
    def __init__(self, master):
        self.master = master
        self.master.title("Multi-Drive Copy Utility")
        self.master.geometry("600x500")  # Increased height for additional info

        self.config_file = "app_config.json"
        self.config = self.load_config()

        self.cancel_flag = False
        self.create_widgets()
        
        # Add this at the beginning of your script, after the imports
        logging.basicConfig(filename='copy_log.txt', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.split_bands_var = tk.BooleanVar(value=True)  # Default to checked
        self.split_bands_checkbox = None  # We'll create this later
        
    def create_widgets(self):
        # Drive selection
        tk.Label(self.master, text="Select Drives:").grid(row=0, column=0, padx=10, pady=10, sticky="w")

        self.lidar_var = tk.StringVar()
        self.altum_var = tk.StringVar()
        self.sony_var = tk.StringVar()

        tk.Label(self.master, text="LiDAR:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.lidar_dropdown = ttk.Combobox(self.master, textvariable=self.lidar_var)
        self.lidar_dropdown.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(self.master, text="Altum:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.altum_dropdown = ttk.Combobox(self.master, textvariable=self.altum_var)
        self.altum_dropdown.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(self.master, text="Sony:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.sony_dropdown = ttk.Combobox(self.master, textvariable=self.sony_var)
        self.sony_dropdown.grid(row=3, column=1, padx=10, pady=5)

        # Destination folder selection
        tk.Label(self.master, text="Destination Folder:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        self.dest_folder_var = tk.StringVar()
        self.dest_folder_dropdown = ttk.Combobox(self.master, textvariable=self.dest_folder_var, width=40)
        self.dest_folder_dropdown.grid(row=4, column=1, padx=10, pady=10)
        self.dest_folder_dropdown['values'] = self.config.get('folder_history', [])
        self.dest_folder_dropdown.set("Select or enter destination folder")
        tk.Button(self.master, text="Browse", command=self.browse_destination).grid(row=4, column=2, padx=10, pady=10)

        # Copy button
        tk.Button(self.master, text="Copy Files", command=self.start_copy_process).grid(row=5, column=1, pady=20)

        # Progress information
        self.progress_frame = ttk.LabelFrame(self.master, text="Progress")
        self.progress_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.current_operation_var = tk.StringVar()
        self.current_operation_label = tk.Label(self.progress_frame, textvariable=self.current_operation_var, anchor="w")
        self.current_operation_label.grid(row=1, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.current_file_var = tk.StringVar()
        self.current_file_label = tk.Label(self.progress_frame, textvariable=self.current_file_var, anchor="w")
        self.current_file_label.grid(row=2, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.file_count_var = tk.StringVar()
        self.file_count_label = tk.Label(self.progress_frame, textvariable=self.file_count_var, anchor="w")
        self.file_count_label.grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.speed_var = tk.StringVar()
        self.speed_label = tk.Label(self.progress_frame, textvariable=self.speed_var, anchor="w")
        self.speed_label.grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.eta_var = tk.StringVar()
        self.eta_label = tk.Label(self.progress_frame, textvariable=self.eta_var, anchor="w")
        self.eta_label.grid(row=5, column=0, columnspan=2, padx=10, pady=2, sticky="w")

        self.cancel_button = tk.Button(self.progress_frame, text="Cancel", command=self.cancel_copy, state=tk.DISABLED)
        self.cancel_button.grid(row=6, column=0, columnspan=2, pady=10)

        self.master.grid_rowconfigure(6, weight=1)
        self.master.grid_columnconfigure(1, weight=1)

        self.update_drive_list()
        
        self.altum_var.trace("w", self.toggle_split_bands_checkbox)
    
    def toggle_split_bands_checkbox(self, *args):
        if self.altum_var.get():
            if not self.split_bands_checkbox:
                self.split_bands_checkbox = tk.Checkbutton(
                    self.master, 
                    text="Copy Band 1 into separate folder for processing?", 
                    variable=self.split_bands_var
                )
                self.split_bands_checkbox.grid(row=2, column=2, padx=10, pady=5, sticky="w")
        else:
            if self.split_bands_checkbox:
                self.split_bands_checkbox.grid_remove()
                
    
    def update_drive_list(self):
        drives = self.get_removable_drives()
        for dropdown in [self.lidar_dropdown, self.altum_dropdown, self.sony_dropdown]:
            dropdown['values'] = drives

    def get_removable_drives(self):
        if platform.system() == 'Darwin':  # macOS
            return self.get_mac_removable_drives()
        elif platform.system() == 'Windows':
            return self.get_windows_removable_drives()
        else:
            return []  # For other operating systems

    def get_mac_removable_drives(self):
        drives = []
        volumes_path = '/Volumes'
        for volume in os.listdir(volumes_path):
            if volume != 'Macintosh HD':  # Exclude the main drive
                drives.append(os.path.join(volumes_path, volume))
        return drives

    def get_windows_removable_drives(self):
        import win32file
        drives = []
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive_name = f'{drive}:'
            drive_type = win32file.GetDriveType(drive_name)
            if drive_type == win32file.DRIVE_REMOVABLE:
                drives.append(drive_name)
        return drives

    def browse_destination(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.dest_folder_var.set(folder_selected)
            self.add_to_folder_history(folder_selected)

    def add_to_folder_history(self, folder):
        folder_history = self.config.get('folder_history', [])
        if folder not in folder_history:
            folder_history.insert(0, folder)
            self.config['folder_history'] = folder_history[:5]  # Keep only the last 5
            self.dest_folder_dropdown['values'] = self.config['folder_history']
            self.save_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def start_copy_process(self):
        source_drives = {
            "LiDAR": self.lidar_var.get(),
            "Altum": self.altum_var.get(),
            "Sony": self.sony_var.get()
        }
        destination = self.dest_folder_var.get()

        if not destination or destination == "Select or enter destination folder":
            messagebox.showerror("Error", "Please select a destination folder.")
            return

        unselected_drives = [name for name, path in source_drives.items() if not path]
        if unselected_drives:
            warning = f"The following drives are not selected: {', '.join(unselected_drives)}. Do you want to proceed?"
            if not messagebox.askyesno("Warning", warning):
                return

        # Disable UI elements
        self.disable_ui()

        # Reset cancel flag
        self.cancel_flag = False

        # Start copying process in a separate thread
        self.copy_thread = threading.Thread(target=self.copy_files, args=(source_drives, destination), daemon=True)
        self.copy_thread.start()

        # Start a thread to check if copying is done
        threading.Thread(target=self.check_copy_complete, daemon=True).start()

    def disable_ui(self):
        for widget in [self.lidar_dropdown, self.altum_dropdown, self.sony_dropdown, 
                    self.dest_folder_dropdown, self.master.nametowidget("!button")]:
            self.set_widget_state(widget, 'disabled')
        self.cancel_button.configure(state='normal')

    def enable_ui(self):
        for widget in [self.lidar_dropdown, self.altum_dropdown, self.sony_dropdown, 
                    self.dest_folder_dropdown, self.master.nametowidget("!button")]:
            self.set_widget_state(widget, 'normal')
        self.cancel_button.configure(state='disabled')

    def set_widget_state(self, widget, state):
        try:
            # Handle ttk widgets
            if isinstance(widget, ttk.Widget):
                if state == 'normal':
                    widget.state(['!disabled'])
                elif state == 'disabled':
                    widget.state(['disabled'])
            # Handle standard tk widgets
            elif isinstance(widget, (tk.Button, tk.Entry)):
                widget.configure(state=state)
            # Recursively handle child widgets
            for child in widget.winfo_children():
                self.set_widget_state(child, state)
        except tk.TclError:
            # If we encounter an error, just skip this widget
            pass

    def cancel_copy(self):
        self.cancel_flag = True
        self.update_status("Cancelling copy process...")

    def check_copy_complete(self):
        self.copy_thread.join()
        self.master.after(0, self.enable_ui)
        if self.cancel_flag:
            self.update_status("Copy process cancelled.")
        else:
            self.update_status("Copy process completed.")

    def copy_files(self, source_drives, destination):
        total_size = 0
        for drive in source_drives.values():
            if drive:
                drive_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, _, filenames in os.walk(drive)
                                for filename in filenames)
                total_size += drive_size
                logging.info(f"Drive {drive} size: {self.format_size(drive_size)}")
        
        logging.info(f"Total size to copy: {self.format_size(total_size)}")
        copied_size = 0
        start_time = time.time()
        statistics = {}

        for drive_name, drive_path in source_drives.items():
            if not drive_path or self.cancel_flag:
                continue

            dest_subfolder = os.path.join(destination, drive_name)
            os.makedirs(dest_subfolder, exist_ok=True)
            
            try:
                self.update_progress(0, f"Preparing to copy files from {drive_name}")
                drive_stats = {'total_files': 0, 'copied_files': 0, 'total_size': 0, 'copied_size': 0}
                
                for root, _, files in os.walk(drive_path):
                    for file in files:
                        if self.cancel_flag:
                            return

                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, drive_path)
                        dst_file = os.path.join(dest_subfolder, rel_path)
                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                        
                        file_size = os.path.getsize(src_file)
                        drive_stats['total_files'] += 1
                        drive_stats['total_size'] += file_size

                        try:
                            # Copy file and verify checksum
                            if self.copy_and_verify(src_file, dst_file):
                                drive_stats['copied_files'] += 1
                                drive_stats['copied_size'] += file_size
                                copied_size += file_size
                            else:
                                logging.error(f"Failed to copy or verify: {src_file}")
                        except Exception as e:
                            logging.error(f"Error copying file {src_file}: {str(e)}")

                        progress = (copied_size / total_size) * 100 if total_size > 0 else 100
                        elapsed_time = time.time() - start_time
                        speed = copied_size / elapsed_time if elapsed_time > 0 else 0
                        eta = (total_size - copied_size) / speed if speed > 0 else 0

                        self.update_progress(progress, 
                                            f"Copying {drive_name}",
                                            f"Current file: {rel_path}",
                                            f"Progress: {self.format_size(copied_size)} / {self.format_size(total_size)}",
                                            f"Speed: {self.format_size(speed)}/s",
                                            f"ETA: {self.format_time(eta)}")

                statistics[drive_name] = drive_stats
                logging.info(f"Completed copying {drive_name}. Stats: {drive_stats}")
                self.update_status(f"Files from {drive_name} copied successfully.")
            except Exception as e:
                logging.error(f"Error copying files from {drive_name}: {str(e)}")
                self.update_status(f"Error copying files from {drive_name}: {str(e)}")

        if not self.cancel_flag:
            self.add_to_folder_history(destination)
            self.update_status("Copy process completed.")
            self.update_progress(100, "Copy process completed", "", f"Total copied: {self.format_size(copied_size)}")
            logging.info(f"Copy process completed. Total copied: {self.format_size(copied_size)}")
            
            # Run band_splitter if checkbox is checked and Altum drive was copied
            if self.split_bands_var.get() and source_drives.get("Altum"):
                altum_dest = os.path.join(destination, "Altum")
                if os.path.exists(altum_dest):
                    self.update_status("Running band splitter...")
                    try:
                        band_splitter.main(altum_dest)
                        self.update_status("Band splitting completed.")
                    except Exception as e:
                        self.update_status(f"Error during band splitting: {str(e)}")
                        logging.error(f"Error during band splitting: {str(e)}")
            
            # Show statistics and ask about emptying drives
            self.master.after(0, lambda: self.show_statistics_and_empty_drives(statistics, source_drives))
    def copy_and_verify(self, src, dst):
        self.update_status(f"Copying: {os.path.basename(src)}")
        shutil.copy2(src, dst)
        self.update_status(f"Verifying: {os.path.basename(src)}")
        if self.calculate_checksum(src) != self.calculate_checksum(dst):
            messagebox.showwarning("Checksum Mismatch", f"Checksum mismatch for file: {src}")
            return False
        return True

    def calculate_checksum(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def update_progress(self, value, operation, current_file="", file_count="", speed="", eta=""):
        self.progress_var.set(value)
        self.current_operation_var.set(operation)
        self.current_file_var.set(current_file)
        self.file_count_var.set(file_count)
        self.speed_var.set(speed)
        self.eta_var.set(eta)
        self.master.update_idletasks()

    def update_status(self, message):
        self.current_operation_var.set(message)
        self.master.update_idletasks()

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0

    def format_time(self, seconds):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def show_statistics_and_empty_drives(self, statistics, source_drives):
        stats_window = tk.Toplevel(self.master)
        stats_window.title("Copy Statistics")
        stats_window.geometry("400x300")

        # Display statistics
        tk.Label(stats_window, text="Copy Statistics:", font=('Arial', 12, 'bold')).pack(pady=10)
        for drive, stats in statistics.items():
            tk.Label(stats_window, text=f"{drive}:").pack(anchor='w', padx=10)
            tk.Label(stats_window, text=f"  Files: {stats['copied_files']}/{stats['total_files']}").pack(anchor='w', padx=20)
            tk.Label(stats_window, text=f"  Size: {self.format_size(stats['copied_size'])}/{self.format_size(stats['total_size'])}").pack(anchor='w', padx=20)

        # Ask about emptying drives
        tk.Label(stats_window, text="Select drives to empty:", font=('Arial', 12, 'bold')).pack(pady=10)
        drive_vars = {}
        for drive in source_drives:
            if source_drives[drive]:  # Only show checkboxes for selected drives
                var = tk.BooleanVar()
                tk.Checkbutton(stats_window, text=drive, variable=var).pack(anchor='w', padx=20)
                drive_vars[drive] = var

        def empty_selected_drives():
            selected_drives = [drive for drive, var in drive_vars.items() if var.get()]
            if selected_drives:
                if messagebox.askyesno("Confirm", f"Are you sure you want to empty the following drives: {', '.join(selected_drives)}?"):
                    for drive in selected_drives:
                        self.empty_drive(source_drives[drive])
                    messagebox.showinfo("Complete", "Selected drives have been emptied.")
            stats_window.destroy()

        tk.Button(stats_window, text="Empty Selected Drives", command=empty_selected_drives).pack(pady=20)

    def empty_drive(self, drive_path):
        for root, dirs, files in os.walk(drive_path, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))

    def run(self):
        self.master.mainloop()
# if __name__ == "__main__":
#     root = tk.Tk()
#     app = MultiDriveCopyUtility(root)
#     root.mainloop()