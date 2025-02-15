import os

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

options = Options()
# set the path to the actual Chrome Application
options.binary_location = "C:/Program Files (x86)/Google/Chrome Beta/Application/chrome.exe"
# download the relevant Chrome driver:
# https://chromedriver.chromium.org/downloads
# specify the path to the driver
driver = webdriver.Chrome(service = Service("C:/Users/donne/Documents/chromedriver-win64/chromedriver.exe"), options=options)

# navigate to Cash App Taxes and sign in manually
driver.get("https://taxes.cash.app/r/dashboard")


# navigate to Capital Gains input (form 1099 B)
driver.get("https://taxes.cash.app/taxes/CapitalGains.action")

# select spreadsheet option then continue
driver.find_element(By.ID, "sales-type-3").click()
driver.find_element(By.NAME, "continue").click()


def import_trades(csv):
    path = csv.replace(os.sep, '/')
    trades = pd.read_csv(path)

    # Define the required columns
    required_columns = ['Description', 'DtAcq', 'DtSold', 'Proceeds', 'Cost', 'Type', 'Code', 'Covered']

    # Check if each required column is present in the DataFrame
    for col in required_columns:
        assert col in trades.columns, f"Error: missing required column '{col}'"

    return trades


def input_trades(df):
    for i in range(len(df)):

        # increase rows as needed
        nrow_need = len(df)
        table = driver.find_element(By.ID, 'capitalGainsTable')
        while True:
            # determine the number of rows the current table has
            rows = table.find_elements(By.TAG_NAME, 'tr')
            nrow_curr = len(rows) - 2 # rm for header and total row
            if nrow_need < nrow_curr:
                break
            # Find the addRows button to scroll to
            # it's not clickable unless it's in view
            addRows = driver.find_element(By.ID, 'addRows')

            # Scroll to addRows and click
            driver.execute_script("arguments[0].scrollIntoView();", addRows)
            addRows.click()

        # input the sale category
        box = df.loc[i, "Code"]
        trade_type = df.loc[i, "Type"].title()
        is_covered = df.loc[i, "Covered"].lower()
        if is_covered == "uncovered":
            is_covered = "not covered"
        el = Select(driver.find_element(By.NAME, f"capitalGains[{i}].reportingCategory"))
        el.select_by_visible_text(f"Box {box} - {trade_type} {is_covered}")

        # enter the description
        desc = df.loc[i, "Description"]
        driver.find_element(By.NAME, f"capitalGains[{i}].description").clear()
        driver.find_element(By.NAME, f"capitalGains[{i}].description").send_keys(desc)

        # enter acq and sell dates
        acq = df.loc[i, "DtAcq"]
        sold = df.loc[i, "DtSold"]
        driver.find_element(By.NAME, f"capitalGains[{i}].dateAcquired").clear()
        driver.find_element(By.NAME, f"capitalGains[{i}].dateSold").clear()
        driver.find_element(By.NAME, f"capitalGains[{i}].dateAcquired").send_keys(acq)
        driver.find_element(By.NAME, f"capitalGains[{i}].dateSold").send_keys(sold)

        # enter proceeds
        proceeds = df.loc[i, "Proceeds"]
        driver.find_element(By.NAME, f"capitalGains[{i}].salesPrice").clear()
        driver.find_element(By.NAME, f"capitalGains[{i}].salesPrice").send_keys(proceeds)

        # enter cost basis
        cost = df.loc[i, "Cost"]
        driver.find_element(By.NAME, f"capitalGains[{i}].cost").clear()
        driver.find_element(By.NAME, f"capitalGains[{i}].cost").send_keys(cost)


trades338 = import_trades(csv = "C:\\Users\\donne\\Google Drive\\Finance\\Taxes\\2023\\x338_trades.csv")
trades454 = import_trades(csv = "C:\\Users\\donne\\Google Drive\\Finance\\Taxes\\2023\\x454_trades.csv")
trades = pd.concat([trades338, trades454], ignore_index = True)

trades.info()
trades.head()

input_trades(trades)

trades.Proceeds.sum() - trades.Cost.sum()
