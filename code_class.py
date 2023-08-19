from tick_listener import tick_listener

# Code to be used by users to get access to the service. It uses the tick_listener interface to notify the code manager when the timer is up and the code should be kicked
class Code(tick_listener):
    def __init__(self, code, time_left=60):
        self._code = code
        self._users = set()  # a list of mac addresses using set to avoid duplicates
        self._time_left = time_left  # time left in minutes

    # override equals method
    def __eq__(self, other):
        if isinstance(other, Code):
            return self._code == other._code
        return False
    
    # add user to the list of users using the code
    def add_user(self, user_mac_address):
        self._users.add(user_mac_address)
        print(f"User: {user_mac_address} added to code: {self._code}")

    # remove user from the list of users using the code
    def remove_user(self, user_mac_address):
        self._users.discard(user_mac_address)
        print(f"User: {user_mac_address} removed from code: {self._code}")

    # Removes time from time_left
    def update(self):
        if(self._time_left > 0):
            self._time_left -= 1
        print(f"Code: {self._code} time left: {str(self._time_left)}")
       
    # Returns the amount of time left on the code
    @property
    def time_left(self):
        return self._time_left
    
    # Returns the code string
    @property
    def code(self):
        return self._code
    
    # Returns the list of users using the code
    @property
    def users(self):
        return self._users 