import streamlit as st
import pandas as pd
import json
import os
import time
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

def is_valid_issn_format(issn):
    """Checks if the input strictly matches the 1234-5678 format."""
    # The regex pattern for exactly 4 digits, a hyphen, and 4 digits (or X)
    pattern = r"^\d{4}-\d{3}[\dxX]$"
    return bool(re.match(pattern, str(issn).strip()))

# --- SCRAPER ENGINE ---
def run_scraper(issn_to_check):
    options = webdriver.ChromeOptions()
    
    # 1. Force the invisible browser to be full 1080p desktop size
    options.add_argument("--window-size=1920,1080")
    
    # 2. Disguise the bot as a normal human Chrome user
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 3. THE MAGIC FIX: Run silently in the background!
    options.add_argument("--headless=new") 
    
    # 4. Optional but recommended: Helps prevent crashes when running invisible
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=options)
    status, coverage = "Unknown", "N/A"
    
    try:
        driver.get("https://www.scopus.com/sources.uri")
        wait = WebDriverWait(driver, 10)
        
        # Select ISSN dropdown
        dropdown = wait.until(EC.element_to_be_clickable((By.ID, "srcResultComboDrp-button")))
        dropdown.click()
        time.sleep(1)
        issn_option = wait.until(EC.element_to_be_clickable((By.ID, "ui-id-4")))
        issn_option.click()
        
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
    except:
        status = "Error/Not Found"
    finally:
        driver.quit()
        return status, coverage

# --- STREAMLIT UI ---
st.set_page_config(page_title="PICT Scopus Validator", layout="wide")
st.title("Scopus Data Automation Tool 📊")

tab1, tab2 = st.tabs(["Single Search", "Bulk Excel Upload"])

# TAB 1: SINGLE SEARCH
with tab1:
    with st.form("single_form"):
        single_issn = st.text_input("Enter ISSN (Format: 0000-0000)")
        if st.form_submit_button("Verify"):
            # THE EDGE CASE CHECK:
            if not is_valid_issn_format(single_issn):
                st.error("⚠️ Invalid format. Please enter a valid ISSN like '0007-9235'.")
            else:
                with st.spinner("Bot is running..."):
                    res, cov = run_scraper(single_issn)
                    st.write(f"**Result:** {res} | **Details:** {cov}")

# TAB 2: BULK UPLOAD (New Logic)
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
                
                # Update progress
                progress_bar.progress((index + 1) / len(df))
            
            # Merge results back to dataframe
            res_df = pd.concat([df, pd.DataFrame(results)], axis=1)
            
            # Download Button
            output = BytesIO()
            res_df.to_excel(output, index=False)
            st.success("Bulk Processing Complete!")
            st.download_button("Download Processed Excel", data=output.getvalue(), file_name="scopus_results.xlsx")

           