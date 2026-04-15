from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def validate_issn(issn_to_check):
    print(f"\nSTARTING SCAN FOR ISSN: {issn_to_check}")
    driver = webdriver.Chrome()
    status = "Unknown"
    coverage_text = "N/A"
    
    try:
        driver.get("https://www.scopus.com/sources.uri")
        wait = WebDriverWait(driver, 10)
        
        # --- 1. SEARCHING ---
        print("Setting dropdown to ISSN...")
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, "srcResultComboDrp-button")))
        dropdown.click()
        time.sleep(1) 
        
        issn_option = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-4")))
        issn_option.click() 
        time.sleep(1)
        
        print("Typing and Searching...")
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "search-term")))
        search_box.clear()
        search_box.send_keys(issn_to_check)
        
        search_button = wait.until(EC.presence_of_element_located((By.ID, "searchTermsSubmit")))
        driver.execute_script("arguments[0].click();", search_button)
        
        # --- 2. EVALUATING RESULTS ---
        print("Analyzing search results...")
        time.sleep(2) # Give the results page plenty of time to load
        
        # Path A: The Ghost Town (No Results)
        no_results = driver.find_elements(By.ID, "noresultsMessage")
        
        # THE FIX: Check if the element exists AND if it is actually visible on the screen!
        if len(no_results) > 0 and no_results[0].is_displayed():
            print("RESULT: No sources found. Marking as INVALID.")
            status = "Invalid"
            return status, coverage_text
            
        # Path B: The Jackpot (Found it!)
        print("Journal found! Clicking into details...")
        
        # THE FIX: Changed td[1]/a to //a to automatically find the first hyperlink in the row!
        first_journal_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='sourceResults']//tbody/tr[1]//a")))
        driver.execute_script("arguments[0].click();", first_journal_link)
        
        # --- 3. EXTRACTING THE DATA ---
        print("Reading coverage years...")
        time.sleep(3) # Let the details page load
        
        # Grabbing the massive text block from the blue header you found
        header_block = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wrapperNoMarginInsidePadding")))
        full_text = header_block.text
        
        # Finding the specific line with the years
        for line in full_text.split('\n'):
            if "Years currently covered by Scopus" in line:
                coverage_text = line
                print(f"Extracted Text: '{coverage_text}'")
                break
                
        # --- 4. THE LOGIC ---
        if "to Present" in coverage_text or "to 2026" in coverage_text:
            print("STATUS: VALID (Currently Active)")
            status = "Valid"
        else:
            print("STATUS: INVALID (Discontinued or missing coverage data)")
            status = "Invalid"

    except Exception as e:
        print(f"ERROR: Bot crashed or element not found. Details: {e}")
        status = "Error"
        
    finally:
        print("Scan complete. Closing browser.")
        driver.quit()
        return status, coverage_text

# Let's test it with the real ISSN you found!
validate_issn("0007-9235")