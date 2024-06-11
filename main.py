import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from multiprocessing import Pool, Process
from typing import List, Optional
import os
import shutil
import csv
import time


# Function to set up ChromeOptions for the ChromeDriver
def setup_chrome_options():
    chrome_options = uc.ChromeOptions()
    prefs = {"profile.default_content_setting_values.notifications": 1}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument(r'--no-sandbox')
    return chrome_options


# Function to initialize the ChromeDriver
def init_chrome_driver(exec_path: str = 'chromedriver'):
    driver = uc.Chrome(executable_path=exec_path, options=setup_chrome_options())
    wait = WebDriverWait(driver, 10)
    return driver, wait


# Function to get the sessionID cookie for a TikTok account
def get_sessionID_cookie(username: str, password: str) -> Optional[str]:
    chrome_options = setup_chrome_options()
    print("\nGetting sessionID cookie for {}.....".format(username))
    driver, wait = init_chrome_driver()
    driver.get('https://www.tiktok.com')

    try:
        # Find the header login button and click on it
        header_login_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[1]/div/div[3]/button'))
        )
        header_login_btn.click()
        print("Clicked on header login button")
    except ElementClickInterceptedException:
        pass

    # Click on the 'Use phone / email / username' button  and choose 'login with email or username'
    use_username_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//div[normalize-space(text())="Use phone / email / username"]'))
    )

    use_username_btn.click()
    print("Clicked on 'Use phone / email / username' button")

    login_with_username_l = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//a[text()="Log in with email or username"]'))
    )

    login_with_username_l.click()
    print("Clicked on 'Log in with email or username' link")

    time.sleep(2)

    # Finding the login button & input elements for email and password and send 'email' and 'pass' keys
    username_input = driver.find_element(By.CLASS_NAME, 'css-11to27l-InputContainer')
    username_input.send_keys(f"{username}")

    password_input = driver.find_element(By.CLASS_NAME, 'css-wv3bkt-InputContainer')
    password_input.send_keys(f"{password}")

    main_login_btn = driver.find_element(By.XPATH, '//button[@data-e2e="login-button"]')
    main_login_btn.click()

    # Waiting for the captcha to be solved
    input("Press Enter after solving captcha")
    time.sleep(5)

    # Gett sessionID cookie value from all cookies
    all_cookies = driver.get_cookies()
    session_id_value = next((item['value'] for item in all_cookies if item['name'] == 'sessionid'), None)
    print("Got sessionID cookie value\n")

    driver.quit()
    return session_id_value


# Function to get the sessionID cookie for all TikTok accounts
def get_sessionID_cookie_for_all_accounts(accounts_creds_filepath: str) -> None:
    accounts = []
    with open(f"{accounts_creds_filepath}", mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row['usernames']
            password = row['password']
            accounts.append(f'{username}:{password.strip("\n")}')

    with open('account_sessionID_cookies.txt', 'w') as f:
        for account in accounts:
            username, password = account.split(':')
            session_id = get_sessionID_cookie(username, password)
            f.write(f'{username}:{session_id}\n')


# Function to get the number of TikTok accounts to be logged in
def get_num_accounts(account_cookies_filepath: str) -> int:
    with open(account_cookies_filepath, 'r') as file:
        return sum(1 for _ in file)


# Function to read and get the sessionID cookies and the respective usernames from a file
def read_session_id_cookies(file_path):
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
    usernames = [line.split(':')[0] for line in lines]
    session_ids = [line.split(':')[1] for line in lines]
    return usernames, session_ids


# Function to make copies of ChromeDriver executable to ensure that each process has its own copy
def copyChromeDriver(num_accounts: List[str], original_chrome_driver_path: str) -> None:
    for i in range(len(num_accounts)):
        # Path to the original and copied ChromeDriver executable
        original_path = f'./{original_chrome_driver_path}{".exe" if os.name == "nt" else ""}'
        copied_path = f'./{original_chrome_driver_path + str(i)}{".exe" if os.name == "nt" else ""}'
        # Using shutil.copyfile to make a copy
        shutil.copyfile(original_path, copied_path)
        # make the copied file executable
        os.chmod(copied_path, 0o755) if os.name == "nt" else None
        print(f"ChromeDriver copied from {original_path} to {copied_path}")
    print()


# Function to remove the copied ChromeDriver executables after the processing is done
def removeChromeDiver(num_accounts: List[str], original_chrome_driver_path: str) -> None:
    for i in range(len(num_accounts)):
        copied_path = f'./{original_chrome_driver_path + str(i)}{".exe" if os.name == "nt" else ""}'
        os.remove(copied_path)
        print(f"ChromeDriver {copied_path} removed")


# Function to create a Chrome instance for each account
def create_chrome_instance(idx: int, original_chrome_driver_path: str) -> uc.Chrome:
    chrome_options = setup_chrome_options()
    driver_path = f'./{original_chrome_driver_path + str(idx)}{".exe" if os.name == "nt" else ""}'
    driver, _ = init_chrome_driver(driver_path)
    return driver


chrome_instances = []
number_of_accounts = get_num_accounts('account_sessionID_cookies.txt')
sessionIDs = read_session_id_cookies('account_sessionID_cookies.txt')[1]
print(f"Number of accounts: {number_of_accounts}\n")
print(f"Number of sessionIDs: {len(sessionIDs)}\n")


# Function to log in to a TikTok account using the sessionID cookie
def login_account_with_session_id_cookie(driver: uc.Chrome, session_id: str) -> None:
    driver.get('https://www.tiktok.com')
    print("SessionID cookie added")
    driver.add_cookie({'name': 'sessionid', 'value': session_id, 'domain': '.tiktok.com'})
    driver.refresh()
    chrome_instances.append(driver)


# Main function to run the script
def main():
    # Convert range to list of strings for ChromeDriver indices
    chrome_driver_indices = [str(i) for i in range(number_of_accounts)]

    # Make copies of ChromeDriver executable for each account
    copyChromeDriver(chrome_driver_indices, 'chromedriver')

    #  Create and store multiple Chrome instances in a list
    for i in range(len(sessionIDs)):
        print(f"Creating Chrome instance # {i + 1}.....")
        driver = create_chrome_instance(i, 'chromedriver')
        print(f"Chrome instance {i + 1} created\n")
        chrome_instances.append(driver)
    print("-" * 30)

    # Open each instance one by one and perform actions
    for n, (driver, session_id) in enumerate(zip(chrome_instances, sessionIDs)):
        print(f"Logging in account # {n + 1}.....")
        login_account_with_session_id_cookie(driver, session_id)
        print(f"Account {n + 1} # logged in\n")
        print("-" * 30)

    print("All accounts logged in successfully\n")

    # Remove all the copied ChromeDriver executables after the processing is done
    removeChromeDiver(chrome_driver_indices, 'chromedriver')


if __name__ == '__main__':
    main()
    for chrome_instance in chrome_instances:
        try:
            chrome_instance.quit()
        except OSError as e:
            print(f"Failed to quit driver gracefully: {e}")
