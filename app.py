import streamlit as st
import pandas as pd
import os
import time
from io import BytesIO
import re
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import traceback

def is_valid_issn_format(issn):
    """Checks if the input strictly matches the 1234-5678 format."""
    pattern = r"^\d{4}-\d{3}[\dxX]$"
    return bool(re.match(pattern, str(issn).strip()))

# --- SCRAPER ENGINE (LOCAL WINDOWS OPTIMIZED) ---
def run_scraper(search_term, search_type="ISSN"):
    options = webdriver.ChromeOptions()
   
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    options.add_argument("--headless=new")
   
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
   
    status, coverage = "Unknown", "N/A"
   
    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(45)
       
        driver.get("https://www.scopus.com/sources.uri")
        wait = WebDriverWait(driver, 15)
       
        time.sleep(3)
       
        # 1. NUKE all generic popups/banners via JS
        try:
            driver.execute_script("""
                document.querySelectorAll('.pendo-overlay, [id^="onetrust"], [class*="popup"], [class*="banner"]').forEach(el => el.remove());
            """)
            time.sleep(1)
        except:
            pass
       
        # 2. Open dropdown with REAL click
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, "srcResultComboDrp-button")))
        dropdown.click()
        time.sleep(1)
       
        # 3. Select Title or ISSN with REAL click
        target_id = "ui-id-4" if search_type == "ISSN" else "ui-id-2"
        type_option = wait.until(EC.element_to_be_clickable((By.ID, target_id)))
        type_option.click()
        time.sleep(1)
       
        # Grab old top link text to track staleness
        try:
            old_link = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='sourceResults']//tbody/tr[1]//a")))
        except:
            old_link = None
       
        search_box = wait.until(EC.presence_of_element_located((By.ID, "search-term")))
       
        # A. Send an ESCAPE key press to clear active modal popups
        webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)

        # B. Destroy "Institution Access" popup
        try:
            driver.execute_script("""
                Array.from(document.querySelectorAll('div')).forEach(el => {
                    if (el.innerText && el.innerText.includes('access Scopus remotely')) {
                        el.style.display = 'none';
                    }
                });
            """)
        except:
            pass

        # C. JS Focus and Clear
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_box)
        driver.execute_script("arguments[0].focus();", search_box)
        driver.execute_script("arguments[0].value = '';", search_box)
       
        # 4. Type the Search Term
        for char in str(search_term):
            search_box.send_keys(char)
            time.sleep(0.05)
           
        time.sleep(1)
       
        # 5. Hit ENTER directly on the keyboard
        search_box.send_keys(Keys.ENTER)
       
        # Wait for the old table to physically disappear (ensures search executed)
        if old_link:
            try:
                wait.until(EC.staleness_of(old_link))
            except:
                pass
                
        time.sleep(2) 
       
        # Check for 'No Results'
        no_results = driver.find_elements(By.ID, "noresultsMessage")
        if len(no_results) > 0 and no_results[0].is_displayed():
            return "Invalid", "No sources found"

        # 6. Extract details (Flawed safety check removed!)
        try:
            new_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='sourceResults']//tbody/tr[1]//a")))
            new_link.click()
        except:
            return "Invalid", "No sources found"
       
        time.sleep(4)
       
        header = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wrapperNoMarginInsidePadding"))).text
        for line in header.split('\n'):
            if "Years currently covered by Scopus" in line:
                coverage = line
                break
       
        status = "Valid" if ("to Present" in coverage or "to 2026" in coverage) else "Invalid (Discontinued)"
   
    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("local_error.png")
        status = "Error"
        error_type = type(e).__name__
        coverage = f"Crash ({error_type}): Elements not found or page timed out."
        print(f"Full traceback for console: {traceback.format_exc()}")
       
    finally:
        if 'driver' in locals():
            driver.quit()
           
    return status, coverage


# --- STREAMLIT UI ---
st.set_page_config(page_title="Scopus Validator", layout="wide")
st.title("Scopus Data Automation Tool")

tab1, tab2 = st.tabs(["Single Search", "Bulk Excel Upload"])

# TAB 1: SINGLE SEARCH
with tab1:
    with st.form("single_form"):
        search_type_single = st.radio("Search by:", ["Title", "ISSN"], horizontal=True)
        search_term_single = st.text_input(f"Enter Journal {search_type_single}")
       
        if st.form_submit_button("Verify"):
            if search_type_single == "ISSN" and not is_valid_issn_format(search_term_single):
                st.error("Invalid format. Please enter a valid ISSN like '0007-9235'.")
            elif not search_term_single.strip():
                st.error("Please enter a value to search.")
            else:
                with st.spinner("Bot is running invisibly in the background..."):
                    res, cov = run_scraper(search_term_single, search_type_single)
                    st.write(f"**Result:** {res} | **Details:** {cov}")
                   
                    if res == "Error" and os.path.exists("local_error.png"):
                        st.warning("The bot crashed. Here is the screenshot:")
                        st.image("local_error.png")

# TAB 2: BULK UPLOAD
with tab2:
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file, dtype=str)
        st.write("Preview of Uploaded Data:", df.head())
        
        # --- THE FIX: Let the user define what they are searching by in Bulk ---
        search_type_bulk = st.radio("Search Bulk List by:", ["Title", "ISSN"], horizontal=True)
        search_column = st.selectbox(f"Select the column containing the {search_type_bulk}s", df.columns)
        
        if st.button("Start Bulk Process"):
            results = []
            progress_bar = st.progress(0)
            
            for index, row in df.iterrows():
                search_term = str(row[search_column])
                st.write(f"Checking {index+1}/{len(df)}: {search_term}...")
                
                # Pass both the term AND the type to the scraper engine
                status, coverage = run_scraper(search_term, search_type_bulk)
                results.append({"Status": status, "Coverage": coverage})
                
                progress_bar.progress((index + 1) / len(df))
            
            res_df = pd.concat([df, pd.DataFrame(results)], axis=1)
            
            output = BytesIO()
            res_df.to_excel(output, index=False) 
            st.success("Bulk Processing Complete!")
            st.download_button("Download Processed Excel", data=output.getvalue(), file_name="scopus_results.xlsx")