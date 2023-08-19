import threading
import random
import string

from code_class import Code

#  Class that manages the codes and the users associated with it
class CodeManager:

    #constant for foreign user time limit
    FOREIGN_USER_TIME_LIMIT = 5 # 5 minutes

    # Constructor
    def __init__(self, on_code_expired_callback=None):
        self._timed_codes = dict() # a list of codes currently in use
        self._timed_users = set() # a list of users using codes
        self._user_list = dict() # a dictionary of mac addresses and their associated codes
        self._foreign_users = dict() # a list of mac addresses that are not using a code
        self._lock = threading.Lock()  # Add a lock
        self._on_code_expired_callback = on_code_expired_callback

    # Generates a string of 11 characters as code and add it to the list of codes
    def generate_code_string(self):
        code_string = ''.join(random.choices(string.ascii_letters + string.digits, k=11))
        code_string = code_string.upper()
        # print (f"Code generated: {code_string}")
        return code_string

    # Creates a code object and bind a mac address to it then add them to their appropriate lists. If code object does not exist, create it
    def bind_user_to_code(self, code, mac_address, duration):
        # add a lock to the function
        with self._lock:
            if mac_address in self._user_list: # check if the user is already using a code
                old_code = self._user_list[mac_address]
                if old_code in self._timed_codes:
                    self._timed_codes[old_code].remove_user(mac_address)
            if code in self._timed_codes:
                self._timed_codes[code].add_user(mac_address)
            else:
                code_object = Code(code, duration)
                code_object.add_user(mac_address)
                self._timed_codes[code] = code_object # add the code to the list of codes
            self._timed_users.add(mac_address) # add the user to timed users
            self._user_list[mac_address] = code # add the user to the list of all users or update its code value


    # Function called by the timer to update the codes
    def tick(self, connected_users):
        with self._lock:
            expired_codes = [] # list of expired codes
            for code in self._timed_codes.values():
                code.update()
                if code.time_left <= 0: # check if the code has expired
                    self._timed_users.difference_update(code.users) # remove users from the set of users using the code
                    expired_codes.append(code.code) # add the code to the list of expired codes

            self._timed_codes = {code_key: code for code_key, code in self._timed_codes.items() if code.time_left > 0} # remove expired codes from the dictionary of codes
            print(f"Codes: {len(self._timed_codes)} Users: {len(self._timed_users)}")

            # Send the expired codes to callback
            if expired_codes:
                self._on_code_expired_callback(expired_codes)

            # Remove users in timed_users from foreign_users. Necessary to prevent registered users from being blocked.
            self._foreign_users = {mac: time_limit for mac, time_limit in self._foreign_users.items() if mac not in self._timed_users}

            # check if connected_users is not None
            if connected_users is not None:

                # remove timed users from the set of connected users
                connected_users.difference_update(self._timed_users) 

                # remove foreign users that are not in the connected users 
                self._foreign_users = {mac: time_limit for mac, time_limit in self._foreign_users.items() if mac in connected_users}

                # add connected users to the list of foreign users if they are not yet on the list and add a time limit
                self._foreign_users.update({mac: self.FOREIGN_USER_TIME_LIMIT for mac in connected_users if mac not in self._foreign_users})

                # update the time limit of foreign users
                self._foreign_users = {mac: time_limit - 1 for mac, time_limit in self._foreign_users.items() if time_limit > 0}

                # return a list of mac address that have exceeded the time limit
                self.print_status()
                return [mac for mac, time_limit in self._foreign_users.items() if time_limit <= 0]
            else:
                self.print_status()
                print("No connected users found.")
                return None
    
    def delete_code(self, code):
        with self._lock:
            if code in self._timed_codes:
                code_object = self._timed_codes[code]
                self._timed_users.difference_update(code_object.users)
                del self._timed_codes[code]
                self.print_status()

    # Returns the number of users using the code and the time left
    def get_code_info(self, key):
        with self._lock:
            if key in self._timed_codes:
                code = self._timed_codes[key]
                num_users = len(code.users)
                time_left = code.time_left
                return (num_users, time_left)
            else:
                return (0, None)


    # Print contents of each instance variables
    def print_status(self):
        print(f"Timed codes {self._timed_codes}")
        print(f"Timed users {self._timed_users}")
        print(f"Foreign users {self._foreign_users}")
        # pass



