import pyotp
import time
import datetime
import json
import requests

from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

with open('config.json', 'r') as json_file:
    credentials = json.load(json_file)

headOption = webdriver.FirefoxOptions()
headOption.add_argument("--headless")


def chekckin_uu(code) :
    driver = webdriver.Firefox(options=headOption)
    driver.get("https://bookings.uu.nl/r/checkin")

    # Login required each time, since we use a clean browser
    try :
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#s-lc-code"))
        )
        element.send_keys(code)
        driver.find_element(By.ID, "s-lc-checkin-button").click()
    except:
        print("checkin failed")
        return -1
    driver.quit()
    return 1


def get_checkin_code_from_mail():
    driver = webdriver.Firefox(options=headOption)
    # driver = webdriver.Firefox()
    driver.get("https://outlook.office.com/mail/")

    # Login required each time, since we use a clean browser
    try :
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="loginfmt"]'))
        )
        element.send_keys(credentials["UU-email"])
        driver.find_element(By.CSS_SELECTOR, 'input[type=submit][value="Next"]').click()
        print("checkin:  Microsoft login")
    except:
        print("email login not working")
        driver.quit()
        return

    try :
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#Ecom_User_ID"))
        )
        time.sleep(1)
        if (driver.current_url == "https://login.uu.nl/nidp/saml2/sso"):
            username = driver.find_element(By.NAME, "Ecom_User_ID")
            username.clear()
            username.send_keys(credentials["UU-email"])
            password = driver.find_element(By.NAME, "Ecom_Password")
            password.send_keys(credentials["UU-password"])
            driver.find_element(By.ID, "loginButton2").click()
        else:
            print("this should not happen")
        print("checkin:  UU login")
    except:
        print("uu login not working")
        driver.quit()
        return

    try :
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#nffc"))
        )
        totp = pyotp.TOTP(credentials["UU-TOTP"])
        element.send_keys(totp.now())
        driver.find_element(By.NAME, "loginButton2").click()
        print("checkin:  MFA")
    except: 
        driver.quit()
        print("mfa failed")
        return

    try:
        element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//span[contains(text(), "Booking Confirmation")]'))
        )
        element = driver.find_element(By.XPATH, '//span[contains(text(), "Booking Confirmation")]');
        driver.execute_script("arguments[0].click();", element)
        print("checkin:  Code")
    except Exception as e:
        print(e)
        print("no booking confirmation mail found")
        driver.quit()
        return

    try:
        print("waiting for checkin code")
        element = WebDriverWait(driver, 100).until(
            EC.presence_of_element_located((By.XPATH, '//b[starts-with(text(), "Use the following code to check in")]/following-sibling::strong'))
            #EC.presence_of_element_located(By.XPATH('//b[starts-with(text(), "Use the following code to check in")]/following-sibling::strong'))
        )
        checkin_code = element.text
        driver.quit()
        print("checkin code found: " + checkin_code)
        return checkin_code 
    except Exception as e:
        print("Start exception")
        print(e)
        print("No checkin code found in mail")
        driver.quit()
        return
    




# Removes bookings from the past
def clean_bookings_file():
    with open('bookings.json', 'r+') as bookings_file:
        data = json.load(bookings_file)
        for booking in data:
            cur_date = datetime.datetime.now().strftime("%d-%m-%Y")
            if (booking["date"] < cur_date):
                print("removing booking from the past")
                data.remove(booking)
        bookings_file.truncate(0)
        bookings_file.seek(0)
        bookings_file.write(json.dumps(data, indent=4))


# creates booking online and registers in booking.json  
def makeBooking(presses) :
    driver = webdriver.Firefox(options=headOption)
    driver.get("https://bookings.uu.nl/seat/97376")

    # Login required each time, since we use a clean browser
    try :
        element = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#Ecom_User_ID"))
        )
    finally: 
        time.sleep(1)
        if (driver.current_url == "https://login.uu.nl/nidp/saml2/sso"):
            username = driver.find_element(By.NAME, "Ecom_User_ID")
            username.clear()
            username.send_keys(credentials["UU-email"])
            password = driver.find_element(By.NAME, "Ecom_Password")
            password.send_keys(credentials["UU-password"])
            driver.find_element(By.ID, "loginButton2").click()

    try :
        element = WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".fc-next-button"))
        )
    finally: 
        if (presses == 1) :
            driver.find_element(By.CLASS_NAME, "fc-next-button").click()
        if (presses == 2) :
            driver.find_element(By.CLASS_NAME, "fc-next-button").click()
            driver.find_element(By.CLASS_NAME, "fc-next-button").click()

    try:
        driver.find_element(By.XPATH, '//a[starts-with(@title, "9:00")]').click()
    except:
        print("no 9:00 option, so we book 10:00 since its weekend")
        try: 
            driver.find_element(By.XPATH, '//a[starts-with(@title, "10:00")]').click()
        except:
            print("no 10:00 option")
            driver.quit()
            return -1

    try :
        driver.find_element(By.XPATH, '//option[contains(@value, "17:00")]').click()
        driver.find_element(By.ID, "submit_times").click()
    except:
        print("no 17:00 option")
        driver.quit()
        return -1


    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "terms_accept"))
        )
        element.click()
    except:
        print("No terms-accept button present")

    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "btn-form-submit"))
        )
        element.click()
    except:
        print("No terms-accept button present")


    # wait for checkin code to arrive
    time.sleep(10)
    code = get_checkin_code_from_mail()

    # open json file and write booking to it
    try:
        with open('bookings.json', 'r+') as bookings_file:
            data = json.load(bookings_file)
            booking_date = datetime.datetime.now() + datetime.timedelta(days=presses)
            data.append({
                "date": booking_date.strftime("%d-%m-%Y"),
                "checkin_code": code,
                "checked_in": "false"
            })
            bookings_file.seek(0)
            bookings_file.write(json.dumps(data, indent=4))
    except Exception as e:
        print("Error occurred while writing to bookings.json:", e)
    print("booking is submitted and stored")
    driver.quit()
    return 1

# cron job monday through saturday
# check if booked for today, tommorow and day after tommorow
# if not, make booking
# for any existing bookings check if we can check in already
print("cleaning bookings")
clean_bookings_file()
print("done cleaning bookings")

candidates = [] # datetime format

if (datetime.datetime.now().weekday() <= 3): # monday - thursday
    candidates.append(datetime.datetime.now() + datetime.timedelta(days=2))
    candidates.append(datetime.datetime.now() + datetime.timedelta(days=1))
    candidates.append(datetime.datetime.now())
elif (datetime.datetime.now().weekday() == 4): # friday
    candidates.append(datetime.datetime.now() + datetime.timedelta(days=1))
    candidates.append(datetime.datetime.now())
elif (datetime.datetime.now().weekday() == 5): # saturday
    candidates.append(datetime.datetime.now() + datetime.timedelta(days=2))
    candidates.append(datetime.datetime.now())
elif (datetime.datetime.now().weekday() == 0): # sunday
    print("sunday")
print("Number of candidates: " + str(len(candidates)))

print("Checking for internet")

elapsed_time = 0
while(elapsed_time < 120): # wait for internet connection for at most two minutes (actually four considering timeout)
    try:
        requests.get("https://bookings.uu.nl/seat/97376", timeout=5)
        break
    except:
        print("No internet connection, sleeping for 5 and retrying")
        elapsed_time += 5
        time.sleep(5)
print("Connection found")


for candidate in candidates:
    candidate_string = candidate.strftime("%d-%m-%Y")
    with open('bookings.json', 'r+') as bookings_file:
        data = json.load(bookings_file)
        exists = False 
        for booking in data:
            if (booking["date"] == candidate_string):
                exists = True
                break
        
        if (exists == False):
            print("no booking found for " + candidate_string)
            print(candidate)
            print(datetime.datetime.now())
            presses = (candidate - datetime.datetime.now()).days + 1
            if (makeBooking(presses) != 1):
                print("FAILED to make booking for " + candidate_string)
                continue


with open('bookings.json', 'r+') as bookings_file:
    data = json.load(bookings_file)
    for booking in data:
        if (booking["checked_in"] == "false"):
            if (booking["date"] == datetime.datetime.now().strftime("%d-%m-%Y")):
                # check if day is saturday
                if (datetime.datetime.now().weekday() == 5):
                    if (datetime.datetime.now().hour >= 10):
                        if (chekckin_uu(booking["checkin_code"]) == -1):
                            #remove booking
                            data.remove(booking)
                        else:
                            booking["checked_in"] = "true"

                        bookings_file.truncate(0)
                        bookings_file.seek(0)
                        bookings_file.write(json.dumps(data, indent=4))
                        print("checked in for " + booking["date"])
                elif (datetime.datetime.now().hour >= 9):
                    if (chekckin_uu(booking["checkin_code"]) == -1):
                        #remove booking
                        data.remove(booking)
                    else:
                        booking["checked_in"] = "true"

                    bookings_file.truncate(0)
                    bookings_file.seek(0)
                    bookings_file.write(json.dumps(data, indent=4))
                    print("checked in for " + booking["date"])