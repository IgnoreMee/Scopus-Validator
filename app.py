import streamlit as st
import pandas as pd
import json
import os
import time
from io import BytesIO
from selenium import webdriver
import undetected_chromedriver as uc
import shutil # <--- THIS IS THE MAGIC PATH-FINDER WE WERE MISSING!
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def is_valid_issn_format(issn):
    """Checks if the input strictly matches the 1234-5678 format."""
    pattern = r"^\d{4}-\d{3}[\dxX]$"
    return bool(re.match(pattern, str(issn).strip()))

# --- SCRAPER ENGINE ---
def run_scraper(issn_to_check):
    # 1. Search for Linux paths (Will return None if on Windows)
    browser_path = shutil.which("chromium-browser") or shutil.which("chromium")
    driver_path = shutil.which("chromedriver")
    
    options = uc.ChromeOptions()
    
    # --- THE NEW FIX: Don't wait for heavy background scripts! ---
    options.page_load_strategy = 'eager' 
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer") # Helps prevent renderer crashes
    options.add_argument("--window-size=1920,1080")
    
    status, coverage = "Unknown", "N/A"
    
    try:
        # 2. THE ENVIRONMENT CHECK
        if browser_path:
            # --- CLOUD MODE ---
            driver = uc.Chrome(
                options=options,
                browser_executable_path=browser_path,
                driver_executable_path=driver_path,
                headless=True,
                use_subprocess=False
            )
        else:
            # --- LOCAL MODE ---
            # We are on your Windows laptop!
            local_options = webdriver.ChromeOptions()
            local_options.page_load_strategy = 'eager'
            
            # 1. THE DISGUISE: Force full HD resolution and a fake human User-Agent
            local_options.add_argument("--window-size=1920,1080")
            local_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            
            # 2. RUN INVISIBLE: Turn headless mode back on!
            local_options.add_argument("--headless=new")
            
            # 3. ANTI-BOT STEALTH FLAGS
            local_options.add_argument("--disable-blink-features=AutomationControlled")
            local_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            local_options.add_experimental_option('useAutomationExtension', False)
            
            driver = webdriver.Chrome(options=local_options)
            
            # 4. Final stealth trick: Delete the 'webdriver' flag inside the browser
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        # Give the driver a strict timeout rule so it never hangs forever
        driver.set_page_load_timeout(30)
        
        driver.get("https://www.scopus.com/sources.uri")
        wait = WebDriverWait(driver, 10)
        
        # Select ISSN dropdown (Using JS click to bypass the cookie banner!)
        dropdown = wait.until(EC.presence_of_element_located((By.ID, "srcResultComboDrp-button")))
        driver.execute_script("arguments[0].click();", dropdown)
        
        time.sleep(1)
        
        issn_option = wait.until(EC.presence_of_element_located((By.ID, "ui-id-4")))
        driver.execute_script("arguments[0].click();", issn_option)
        
        # Search
        search_box = wait.until(EC.element_to_be_clickable((By.ID, "search-term")))
        search_box.send_keys(issn_to_check)
        search_button = driver.find_element(By.ID, "searchTermsSubmit")
        driver.execute_script("arguments[0].click();", search_button)
        
        time.sleep(4)
        no_results = driver.find_elements(By.ID, "noresultsMessage")
        if len(no_results) > 0 and no_results[0].is_displayed():
            return "Invalid", "No sources found"

        # Extract Details
        link = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='sourceResults']//tbody/tr[1]//a")))
        driver.execute_script("arguments[0].click();", link)
        
        time.sleep(3)
        header = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wrapperNoMarginInsidePadding"))).text
        for line in header.split('\n'):
            if "Years currently covered by Scopus" in line:
                coverage = line
                break
        
        status = "Valid" if ("to Present" in coverage or "to 2026" in coverage) else "Invalid (Discontinued)"
    
    except Exception as e:
        if 'driver' in locals():
            driver.save_screenshot("server_debug.png")
        status = "Error"
        coverage = f"Crash Details: {str(e)}"
        
    finally:
        if 'driver' in locals():
            driver.quit()
        
    return status, coverage

# --- STREAMLIT UI ---
st.set_page_config(page_title="PICT Scopus Validator", layout="wide")
st.title("Scopus Data Automation Tool")

tab1, tab2 = st.tabs(["Single Search", "Bulk Excel Upload"])

# TAB 1: SINGLE SEARCH
with tab1:
    with st.form("single_form"):
        single_issn = st.text_input("Enter ISSN (Format: 0000-0000)")
        if st.form_submit_button("Verify"):
            if not is_valid_issn_format(single_issn):
                st.error("Invalid format. Please enter a valid ISSN like '0007-9235'.")
            else:
                with st.spinner("Bot is running..."):
                    res, cov = run_scraper(single_issn)
                    st.write(f"**Result:** {res} | **Details:** {cov}")
                    
                    if res == "Error" and os.path.exists("server_debug.png"):
                        st.warning("📸 The bot crashed. Here is what the server screen looked like at the moment of failure:")
                        st.image("server_debug.png")

# TAB 2: BULK UPLOAD
with tab2:
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file, dtype=str)
        st.write("Preview of Uploaded Data:", df.head())
        
        issn_column = st.selectbox("Select the column containing ISSNs", df.columns)
        
        if st.button("Start Bulk Process"):
            results = []
            progress_bar = st.progress(0)
            
            for index, row in df.iterrows():
                issn = str(row[issn_column])
                st.write(f"Checking {index+1}/{len(df)}: {issn}...")
                
                status, coverage = run_scraper(issn)
                results.append({"Status": status, "Coverage": coverage})
                
                progress_bar.progress((index + 1) / len(df))
            
            res_df = pd.concat([df, pd.DataFrame(results)], axis=1)
            
            output = BytesIO()
            res_df.to_excel(output, index=False)
            st.success("Bulk Processing Complete!")
            st.download_button("Download Processed Excel", data=output.getvalue(), file_name="scopus_results.xlsx")
