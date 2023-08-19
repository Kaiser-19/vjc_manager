from collections import deque
import sched
import threading
import time
import traceback
from external.webserver import WebServer
from router_device import Router
from code_manager import CodeManager
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from rows_ui import Rows
import signal
import sys

import tkinter
import tkinter.messagebox
import customtkinter

customtkinter.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

NUM_WORKERS = 2  # number of workers to use for the thread pool
task_queue = Queue()
update_queue = Queue()
UNBLOCK_SCHEDULE = 75 # 1 hour and 15 minutes
TICK_INTERVAL = 60  # 1 minute
APP_WIDTH = 900
APP_HEIGHT = 580
APP_SCALING = "110%"
APP_NAME = "Wifi Manager"

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.ui_lock = threading.RLock()
        self.manager_lock = threading.RLock()
        self.router_lock = threading.RLock()
        self.running = True

        self.unblock_button_disabled = False
        self.resetdb_button_disabled = False

        self.minute_counter = 0
        # configure window
        self.title(APP_NAME)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.change_scaling_event(APP_SCALING)
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # create sidebar frame with widgets
        self.left_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.left_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.left_frame.grid_rowconfigure(4, weight=1)

        # create app name label
        self.logo_label = customtkinter.CTkLabel(self.left_frame, text=APP_NAME, font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=1, column=0, padx=20, pady=(20, 10))

        # create generate new code Button
        self.sidebar_button_1 = customtkinter.CTkButton(self.left_frame, command=self.generate_code_event)
        self.sidebar_button_1.grid(row=2, column=0, padx=20, pady=(25,5))
        self.sidebar_button_1.configure(text="Generate New Code")

        # create textbox for newly generated code
        self.newcode = customtkinter.CTkButton(self.left_frame, corner_radius=3, height=70, fg_color=("#afafaf", "#202020"), text_color_disabled=("#fafafa", "#80ccff"), font=customtkinter.CTkFont(size=15, weight="bold"))
        self.newcode.grid(row=3, column=0, padx=20, pady=5)
        self.newcode.configure(text="", state="disabled")

        # create unblock devices Button
        self.unblock_button = customtkinter.CTkButton(self.left_frame, command=self.temporary_unblock_event)
        self.unblock_button.grid(row=5, column=0, padx=20, pady=20)
        self.unblock_button.configure(text="Unblock Devices")

        # create database reset Button
        self.reset_database_button = customtkinter.CTkButton(self.left_frame, command=self.reset_db_button_event)
        self.reset_database_button.grid(row=6, column=0, padx=20, pady=20)
        self.reset_database_button.configure(text="Reset Database")

   
        # create a frame that imitates a tree view
        self.scrollable_frame = customtkinter.CTkScrollableFrame(self, label_text="Current Connections")
        self.scrollable_frame.grid(row=0, column=1, rowspan= 3, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # create a frame inside the scrollable frame
        self.inner_frame = customtkinter.CTkFrame(self.scrollable_frame)
        self.inner_frame.grid(row=0, column=0, sticky="nsew")
        self.label_width = 100  # set the width of each label

        self.label = customtkinter.CTkLabel(self.inner_frame, text="Code", width=self.label_width, font=customtkinter.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.label = customtkinter.CTkLabel(self.inner_frame, text="Status", width=self.label_width, font=customtkinter.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.label = customtkinter.CTkLabel(self.inner_frame, text="Users", width=self.label_width, font=customtkinter.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        self.label = customtkinter.CTkLabel(self.inner_frame, text="Time Remaining", width=self.label_width, font=customtkinter.CTkFont(size=14, weight="bold"))
        self.label.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        
        
        ### Main Objects Setup ###
        self.manager = CodeManager(self.on_code_expired)
        self.router = Router()
        self.router.login()
    
        self.webserver = WebServer(on_success_callback=task_queue.put)
        self.webserver_thread = threading.Thread(target=self.webserver.run)
        self.webserver_thread.start()
        self.rows = Rows(self.inner_frame, self.label_width, self.delete_row_buton_event)

        time.sleep(5)
        self.setup_environment()
        print("Setup done")

        self.update_thread = threading.Thread(target=self.update_queue)
        self.update_thread.start()

        self.tick_thread = threading.Thread(target=self.tick_loop)
        self.tick_thread.start()
        self.user_binding_thread = threading.Thread(target=self.user_binding_queue)
        self.user_binding_thread.start()
        
        try:
            self.mainloop()
        except KeyboardInterrupt:
            print("Exiting...")
        finally:
            self.running = False
            task_queue.put((None, None, None))
            update_queue.put(None)
            self.webserver_thread.join()
            self.tick_thread.join()
            self.user_binding_thread.join()
            task_queue.join()
            update_queue.join()
            self.destroy()
        ##########################
        

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)


    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def calculate_box_center(self, box):
        try:
            # Get the width and height of the screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # Get the width and height of the box
            box_width = box.winfo_width()
            box_height = box.winfo_height()

            # Calculate the x and y positions of the box to center it on the screen
            x = (screen_width - box_width) // 2
            y = (screen_height - box_height) // 2

            return (x, y)
        except:
            return (None, None)

    def generate_code_event(self):
        dialog = customtkinter.CTkInputDialog(text="Enter code duration:\n(min= 5, max= 60)", title="Generate New Code")
        x, y = self.calculate_box_center(dialog)
        if x is not None and y is not None:
            dialog.geometry("+{}+{}".format(x, y))
        duration = dialog.get_input()
        try:
            if duration is None or duration == "":
                return False
            elif duration is not None and duration != "":
                duration = max(5.0, min(60.0, float(duration)))
                duration = int(duration)
            else:
                duration = 60
        except:
            duration = 60
        with self.manager_lock:
            code = self.manager.generate_code_string()
            success = self.webserver.add_code(code, duration)
            if success:
                self.newcode.configure(text=code)
                self.update_code_list()

    def temporary_unblock_event(self):
        dialog = customtkinter.CTkInputDialog(text='Are you sure you want to temporarily unblock the currently blocked devices?\nIf yes, type in "unblock" without the quotation marks.', title="Unblock Devices")
        x, y = self.calculate_box_center(dialog)
        if x is not None and y is not None:
            dialog.geometry("+{}+{}".format(x, y))
        answer = dialog.get_input()
        try:
            if answer == "unblock":
                with self.router_lock:
                    self.router.unblock_all_devices()
            else:
                return False
        except Exception as e:
            print(f"Error in temporary_unblock_event: {e}")
            traceback.print_exc()
            return False
        
    def delete_row_buton_event(self, code):
        with self.manager_lock:
            self.manager.delete_code(code)
            self.webserver.delete_code(code)
            self.update_code_list()
        
    def reset_db_button_event(self):
        dialog = customtkinter.CTkInputDialog(text='Are you sure you want to reset the database?\nIf yes, type in "reset" without the quotation marks.', title="Reset Database")
        x, y = self.calculate_box_center(dialog)
        if x is not None and y is not None:
            dialog.geometry("+{}+{}".format(x, y))
        answer = dialog.get_input()
        try:
            if answer == "reset":
                self.webserver.reset_database()
                self.update_code_list()
            else:
                return False
        except Exception as e:
            print(f"Error in reset_db_button_event: {e}")
            traceback.print_exc()
            return False
        
    def update_code_list(self):
        try:
            codes = self.webserver.get_all_codes()
            update_queue.put(codes)
        except Exception as e:
            print(f"Error in update_code_list: {e}")
            traceback.print_exc()

    def update_frame(self, codes):
        with self.ui_lock: 
            children = self.inner_frame.winfo_children()[4:]
            rows = self.rows.group_children_to_rows(children)

            total_rows = len(rows)

            for c, code in enumerate(codes):
                key, status, init_duration = code
                users, time_remaining = self.manager.get_code_info(key)
                if time_remaining is None:
                    time_remaining = init_duration
                else:
                    self.webserver.update_code(key, time_remaining) # update time remaining in database
                if c < total_rows:
                    self.rows.update_row(rows[c], key, status, users, time_remaining)
                else:
                    self.rows.create_row(c + 1, key, status, users, time_remaining)

            self.rows.delete_extra_rows(rows, len(codes))


    def setup_environment(self):
        with self.manager_lock:
            with self.router_lock:
                try:
                    print("Setting up environment...")
                    new_router_password = self.manager.generate_code_string()
                    newday = self.webserver.is_new_day()
                    old_router_password = self.webserver.get_router_password()
                    if newday:
                        password_change_success = self.router.change_router_password(new_router_password)
                        if password_change_success:
                            self.router.unblock_all_devices()
                            self.webserver.reset_database()
                            self.webserver.change_router_password(new_router_password)
                            self.scrollable_frame.configure(label_text=f"Today's Password: {new_router_password}")
                        else:
                            print(f"Password change failed. Using old password {old_router_password}.")
                            self.scrollable_frame.configure(label_text=f"Today's Password: {old_router_password}")
                        print("New day!")
                    else:
                        print(f"Same day! Using old password {old_router_password}.")
                        self.scrollable_frame.configure(label_text=f"Today's Password: {old_router_password}")
                        # load existing codes in case app didn't shut down properly
                        codes = self.webserver.get_all_codes()
                        # create a dictionary with used codes using code as key and time remaining as value
                        used_codes = {c[0]: c[2] for c in codes if c[1] == "Used"}
                        registrants = self.webserver.get_all_registration()
                        for r in registrants:
                            mac, code = r
                            if code in used_codes:
                                self.manager.bind_user_to_code(code, mac, used_codes[code])
                    self.update_code_list()
                except Exception as e:
                    print(f"Error in setup_environment: {e}")
                    traceback.print_exc()


    def on_submit_success(self, ip, code, duration):
        with self.router_lock:
            mac = self.router.get_one_connected_device(ip)
            print(f"Form submitted successfully! IP: {ip}, MAC: {mac} Code: {code}")
            if mac:
                with self.manager_lock:
                    self.manager.bind_user_to_code(code, mac, duration)
                    self.webserver.update_registration(ip, mac) # update registration in database


    def on_code_expired(self,codes):
        if codes:
            self.webserver.delete_expired_codes(codes)


    def tick_loop(self):
        def scheduled_tick():
            with self.manager_lock:
                with self.router_lock:
                    try:
                        print(f"############################Tick: {self.minute_counter}")
                        foreign_users = self.router.get_all_connected_devices()
                        to_block = self.manager.tick(foreign_users)
                        if to_block is not None:
                            for mac in to_block:
                                self.router.block_device(mac)
                        self.minute_counter += 1
                        self.update_code_list()
                        if self.minute_counter == UNBLOCK_SCHEDULE:
                            self.minute_counter = 0
                            self.router.unblock_all_devices()
                    except Exception as e:
                        print(f"Error in scheduled_tick: {e}")
                        traceback.print_exc()

            if self.running:
                scheduler = sched.scheduler(time.time, time.sleep)
                scheduler.enter(TICK_INTERVAL, 1, scheduled_tick, ())  # Schedule the first tick
                scheduler.run()

        scheduled_tick()  # kick off scheduler



    def user_binding_queue(self):
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            while True:
                try:
                    ip, code, duration = task_queue.get()
                    print("-----------------------------------------------Got task from queue")
                    if ip is None:
                        print("Got None task, exiting")
                        break
                    executor.submit(self.on_submit_success, ip, code, duration)
                    task_queue.task_done()  # Mark the task as done
                except Exception as e:
                    print(f"Error in user_binding_queue: {e}")
                    traceback.print_exc()

    def update_queue(self):
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            while True:
                try:
                    codes = update_queue.get()
                    if codes is None:
                        print("Got None update task, exiting")
                        break
                    executor.submit(self.update_frame, codes)
                    update_queue.task_done()
                except Exception as e:
                    print(f"Error in update_queue: {e}")
                    traceback.print_exc()    


def handle_sigint(sig, frame):
    print("Ignoring KeyboardInterrupt")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_sigint)
    app = App()



    
    