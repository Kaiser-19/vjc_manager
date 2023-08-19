import re
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config import router_password

ROUTER_LOGIN_PAGE = "http://192.168.0.1/webpages/index.html?t=29dee038"
NETWORK_MAP_PAGE = "http://192.168.0.1/webpages/index.html?t=29dee038#networkMap"
BLOCKLIST_PAGE = "http://192.168.0.1/webpages/index.html?t=29dee038#accessControl"
WIFI_SETTINGS_PAGE = "http://192.168.0.1/webpages/index.html?t=29dee038#guestNetworkAdv"
TIME_OUT_DURATION = 10
ADMIN_MAC = "04-ED-33-CE-C5-43"

class Router:

    def __init__(self):
        self._chrome_options = Options()
        self._chrome_options.add_argument("--headless")
        # self._chrome_options.add_argument('--no-sandbox')
        self._chrome_options.add_experimental_option("detach", True)
        self._browser = webdriver.Chrome(options=self._chrome_options)
        self._browser.maximize_window()
        self._browser.get(ROUTER_LOGIN_PAGE)

    def login(self):
        WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.ID, "local-login-pwd")))
        password_field = self._browser.find_elements(By.CSS_SELECTOR, '#local-login-pwd > div.widget-wrap-outer.text-wrap-outer.password-wrap-outer.allow-visible > div.widget-wrap.text-wrap.password-wrap > span.text-wrap-inner.password-wrap > input.text-text.password-text.password-hidden')[0]
        password_field.send_keys(router_password)
        password_field.send_keys(Keys.RETURN)

    def redirect_to_page(self, page_url):
        # attempt to go to the target page
        if self._browser.current_url != page_url:
            print(f"Browser not in {page_url} page, redirecting...")
            self._browser.get(page_url)
            # check if the browser is in the login page
            if self._browser.current_url == ROUTER_LOGIN_PAGE:
                print(f"Browser needs login, signing in...")
                self.login()
                self._browser.get(page_url)

    def get_all_connected_devices(self):
        self.redirect_to_page(NETWORK_MAP_PAGE)

        try:
            # wait for clients tab to load
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.ID, "map-clients")))
            clients_button = self._browser.find_element(By.ID, "map-clients")
            if clients_button.is_enabled():
                clients_button.click()

            # wait for clients to load
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.CLASS_NAME, "grid-content-data")))
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_all_elements_located((By.XPATH, '//td[contains(@class, "s-hide")]//div[@class="mac"]')))
        
            # time.sleep(1)
            mac_elements = self._browser.find_elements(By.XPATH, '//td[contains(@class, "s-hide")]//div[@class="mac"]')
            print(f"Devices connected: {len(mac_elements)}")

            # compile mac addresses to a set
            users = set()
            for mac_element in mac_elements:
                outer_html = mac_element.get_attribute('outerHTML')
                mac_address = re.search(r'(?<=<div class="mac">)[\w\d-]+(?=</div>)', outer_html)
                if mac_address:
                    mac_address = mac_address.group(0).strip()
                    if not mac_address:
                        print(f"Found empty mac address: {mac_address}, skipping...")
                    else:
                        if mac_address != ADMIN_MAC:
                            users.add(mac_address)
            return users
        except Exception as e:
            print(f"Could not find any connected devices. Error: {e}")
            # self.login()
            return None

    # Get a connected device's mac address
    def get_one_connected_device(self, ip_address):
        # check if the browser is in the networkmap page
        self.redirect_to_page(NETWORK_MAP_PAGE)

        try:
            # wait for clients tab to load
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.ID, "map-clients")))
            clients_button = self._browser.find_element(By.ID, "map-clients")
            if clients_button.is_enabled():
                clients_button.click()

            # wait for clients to load
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.CLASS_NAME, "grid-content-data")))
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_all_elements_located((By.XPATH, '//td[contains(@class, "s-hide")]//div[@class="mac"]')))
        
            ip_elements = self._browser.find_elements(By.XPATH, '//td[contains(@class, "s-hide")]//div[@class="ip"]')

            for ip in ip_elements:
                ip_outer_html = ip.get_attribute('outerHTML')
                ip_text = re.search(r'(?<=<div class="ip">)[\d.]+(?=</div>)', ip_outer_html).group(0).strip()
                if ip_text:
                    if ip_text == ip_address:
                        mac_element = ip.find_element(By.XPATH, './preceding-sibling::div[@class="mac"]')
                        mac_outer_html = mac_element.get_attribute('outerHTML')
                        mac_address = re.search(r'(?<=<div class="mac">)[\w\d-]+(?=</div>)', mac_outer_html).group(0).strip()
                        if mac_address:
                            return mac_address

            print(f"Could not find device with IP address: {ip_address}")
            return None
        except Exception as e:
            print(f"Error trying to find device with IP address: {ip_address}. Error: {e}")
            return None   

    # Block devices from the router
    def block_device(self, device):
        self.redirect_to_page(NETWORK_MAP_PAGE)

        try:
            # wait for clients tab to load
            clients_button = WebDriverWait(self._browser, TIME_OUT_DURATION).until(
                EC.presence_of_element_located((By.ID, "map-clients")))
            if clients_button.is_enabled():
                clients_button.click()
        except Exception as e:
            print(f"Could not find clients button. Error: {e}")

        # remove all non-alphanumeric characters from the string and strip white spaces
        device = re.sub('[\W_]+', '', device)
        device = device.strip()

        # Check if the resulting string is empty
        if not device:
            print("Could not block device. Invalid MAC address.")
        else:
            try:
                # wait for the block icon's td element to exist
                td_element = WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.ID, f'connected-clients-grid_tr_{device}_td_9')))
                block_action_link = WebDriverWait(td_element, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.TAG_NAME, 'a')))
                # click the block button if it is enabled
                if block_action_link.is_enabled():
                    # block_action_link.click()
                    self._browser.execute_script("arguments[0].click();", block_action_link)
                    # confirm blocking the device
                    confirm_block_button = WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.XPATH, '//*[@id="block-confirm-msg-btn-ok"]/div[2]/div[1]/a')))
                    if confirm_block_button.is_enabled():
                        confirm_block_button.click()
                        print (f"Blocked device with MAC address: {device}")
            except Exception as e:
                print(f"An error occurred while trying to block the device with MAC address {device}: {e}")
       
    # Unblock all devices from the router
    def unblock_all_devices(self):
        self.redirect_to_page(BLOCKLIST_PAGE)
        # wait for block list container to load
        try:
            WebDriverWait(self._browser, TIME_OUT_DURATION-7).until(EC.presence_of_element_located((By.XPATH, '//*[@id="grid-blacklist-panel"]/div/div/div/div[4]')))
            # wait for all the unblock all button to appear
            WebDriverWait(self._browser, TIME_OUT_DURATION-7).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'btn-delete')))
        except:
            print("No devices to unblock.")
            return None
        try:
            device_unblock_buttons = WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'btn-delete')))
            print(f"Devices currently blocked: {len(device_unblock_buttons)}")
            # click all the unblock all buttons
            for button in device_unblock_buttons:
                if button.is_enabled():
                    parent_div = button.find_element(By.XPATH, '..')
                    # get the value of the "data-key" attribute of the parent "div" element
                    data_key_value = parent_div.get_attribute('data-key')
                    button.click()
                    print(f"Unblocking device with MAC address: {data_key_value}")
                time.sleep(2)
        except Exception as e:
            print(f"An error occurred while trying to unblock devices: {e}")

    # Change the router's password for the guest network
    def change_router_password(self, new_password):
        self.redirect_to_page(NETWORK_MAP_PAGE)
        WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.ID, "map-clients")))
        self.redirect_to_page(WIFI_SETTINGS_PAGE)
        try:
            WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#wpa-cfg-content input")))
            
            password_input = self._browser.find_element(By.CSS_SELECTOR, "#wpa-cfg-content input")
            self._browser.execute_script("arguments[0].scrollIntoView();", password_input)
            
            self._browser.execute_script("arguments[0].click();", password_input)
            self._browser.execute_script("arguments[0].value = '';", password_input)
            
            # simulate a manual keypress by typing each character with a delay in between
            action_chains = ActionChains(self._browser)
            for char in new_password:
                action_chains.send_keys(char)
                self._browser.execute_script("arguments[0].click();", password_input)
                # Trigger the input event so save button appears in headless mode
                self._browser.execute_script("arguments[0].dispatchEvent(new Event('input'));", password_input)
                self._browser.execute_script("arguments[0].dispatchEvent(new Event('change'));", password_input)
                self._browser.execute_script("arguments[0].value = arguments[1];", password_input, new_password)
                time.sleep(0.5)
            action_chains.perform()
            
            self._browser.execute_script("arguments[0].value = '';", password_input)
            self._browser.execute_script("arguments[0].value = arguments[1];", password_input, new_password)

            
            
            save_button = WebDriverWait(self._browser, TIME_OUT_DURATION).until(EC.presence_of_element_located((By.XPATH, '//*[@id="save-data"]/div[2]/div[1]/a')))
            if save_button.is_enabled():
                # save_button.click()
                self._browser.execute_script("arguments[0].click();", save_button)
                print("Password changed successfully.")
                return True
            
            return False
        except Exception as e:
            print(f"An error occurred while trying to change the router password: {e}")
            return False


    # Quits the browser
    def quit(self):
        self._browser.quit()