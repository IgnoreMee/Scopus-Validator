import streamlit as st
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 1. THE SELENIUM BOT ENGINE
# ==========================================
def run_scraper(issn_to_check):
    driver = webdriver.Chrome()
    status = "Unknown"
    coverage_text = "N/A"
    
    try:
        driver.get("https://www.scopus.com/sources.uri")
        wait = WebDriverWait(driver, 10)
        
        # --- Search Phase ---
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, "srcResultComboDrp-button")))
        dropdown.click()
        time.sleep(1) 
        
        issn_option = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-4")))
        issn_option.click() 
        time.sleep(1)
        
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "search-term")))
        search_box.clear()
        search_box.send_keys(issn_to_check)
        
        search_button = wait.until(EC.presence_of_element_located((By.ID, "searchTermsSubmit")))
        driver.execute_script("arguments[0].click();", search_button)
        
        # --- Evaluation Phase ---
        time.sleep(5) 
        no_results = driver.find_elements(By.ID, "noresultsMessage")
        
        if len(no_results) > 0 and no_results[0].is_displayed():
            return "Invalid", "No sources found on Scopus."
            
        # --- Extraction Phase ---
        first_journal_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='sourceResults']//tbody/tr[1]//a")))
        driver.execute_script("arguments[0].click();", first_journal_link)
        
        time.sleep(3) 
        header_block = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wrapperNoMarginInsidePadding")))
        full_text = header_block.text
        
        for line in full_text.split('\n'):
            if "Years currently covered by Scopus" in line:
                coverage_text = line
                break
                
        # --- Logic Phase ---
        if "to Present" in coverage_text or "to 2026" in coverage_text:
            status = "Valid"
        else:
            status = "Invalid (Discontinued)"

    except Exception as e:
        status = "Error"
        coverage_text = f"Bot crashed: {e}"
        
    finally:
        driver.quit()
        return status, coverage_text

# ==========================================
# 2. THE STREAMLIT FRONTEND
# ==========================================
st.set_page_config(page_title="Scopus Validator")
st.title("Scopus Journal Validator")
st.markdown("Enter a journal's details to automatically verify its active status on Scopus.")

with st.form("single_search_form"):
    input_title = st.text_input("Journal Title (Optional)")
    input_issn = st.text_input("ISSN Number (Required)", placeholder="e.g., 0007-9235")
    submitted = st.form_submit_button("Search & Validate")

if submitted:
    if not input_issn:
        st.warning("Please enter an ISSN number.")
    else:
        with st.spinner(f"Firing up the bot... Searching Scopus for {input_issn}..."):
            # Trigger the bot and wait for the results!
            final_status, final_coverage = run_scraper(input_issn)
            
        # Display the results on the web page
        if "Valid" in final_status:
            st.success(f"**Status:** {final_status}")
        else:
            st.error(f"**Status:** {final_status}")
            
        st.info(f"**Extracted Data:** {final_coverage}")

        # Save to JSON Database
        new_record = {
            "Title": input_title,
            "ISSN": input_issn,
            "Status": final_status,
            "Coverage Details": final_coverage
        }
        
        json_filename = "scopus_database.json"
        if os.path.exists(json_filename):
            with open(json_filename, "r") as file:
                data = json.load(file)
        else:
            data = []
            
        data.append(new_record)
        with open(json_filename, "w") as file:
            json.dump(data, file, indent=4)
            
        st.write("Result successfully saved to `scopus_database.json`!")