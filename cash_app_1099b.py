from pathlib import Path

import polars as pl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

options = Options()
# set the path to the actual Chrome Application
options.binary_location = (
    "C:/Program Files (x86)/Google/Chrome Beta/Application/chrome.exe"
)
# download the relevant Chrome driver:
# https://chromedriver.chromium.org/downloads
# specify the path to the driver
driver = webdriver.Chrome(
    service=Service(
        Path.home() / "Documents" / "chromedriver-win64" / "chromedriver.exe"
    ),
    options=options,
)

# navigate to Cash App Taxes and sign in manually
driver.get("https://taxes.cash.app/r/dashboard")

# navigate to Capital Gains input (form 1099 B)
driver.get("https://taxes.cash.app/taxes/CapitalGains.action")

# select spreadsheet option then continue
driver.find_element(By.XPATH, '//label[div[text()="Spreadsheet entry"]]').click()
driver.find_element(By.XPATH, '//button[contains(., "Continue")]').click()


def import_trades(path: Path) -> pl.DataFrame:
    trades = pl.read_csv(path)

    trades = trades.rename(
        {
            "Description of property (Example 100 sh. XYZ Co.)": "Description",
            "Date acquired": "DtAcq",
            "Date sold or disposed": "DtSold",
            "Cost or other basis": "Cost",
            "Short-Term gain loss Long-term gain or loss Ordinary": "Type",
            "Form 8949 Code": "Code",
            "Check if noncovered security": "Covered",
        },
        strict=True,
    ).with_columns(pl.col("Covered").replace("Uncovered", "Not Covered"))

    excl_trades = trades.filter(pl.col("Code").eq("X"))
    if not excl_trades.is_empty():
        print("Excluded trades:")
        print(excl_trades.select("Description", "Cost"))
        trades = trades.filter(pl.col("Code").ne("X"))

    # Define the required columns
    required_columns = [
        "Description",
        "DtAcq",
        "DtSold",
        "Proceeds",
        "Cost",
        "Type",
        "Code",
        "Covered",
    ]

    # Check if each required column is present in the DataFrame
    for col in required_columns:
        assert col in trades.columns, f"Error: missing required column '{col}'"

    return trades


def input_trades(df: pl.DataFrame) -> None:
    nrow_need = len(df)
    table = driver.find_element(By.XPATH, '//table[@role="table"]')
    # increase rows as needed
    while True:
        # determine the number of rows the current table has
        rows = table.find_elements(By.TAG_NAME, "tr")
        nrow_curr = len(rows) - 2  # rm for header and total row
        if nrow_need <= nrow_curr:
            break
        # Find the addRows button to scroll to
        # it's not clickable unless it's in view
        addRows = driver.find_element(
            By.XPATH, '//button[normalize-space()="Add Rows"]'
        )
        # Scroll to addRows and click
        driver.execute_script("arguments[0].scrollIntoView();", addRows)
        addRows.click()

    i = 0
    for row in df.iter_rows(named=True):
        # input the sale category
        el = Select(
            driver.find_element(By.NAME, f"capitalGains[{i}].reportingCategory")
        )
        el.select_by_visible_text(
            f"Box {row['Code']} - {row['Type'].title()} {row['Covered'].lower()}"
        )

        # enter the description
        desc = driver.find_element(By.NAME, f"capitalGains[{i}].description")
        desc.clear()
        desc.send_keys(row["Description"])

        # enter acq and sell dates
        dtaq = driver.find_element(By.NAME, f"capitalGains[{i}].dateAcquired")
        dtaq.clear()
        dtaq.send_keys(row["DtAcq"])

        dtsl = driver.find_element(By.NAME, f"capitalGains[{i}].dateSold")
        dtsl.clear()
        dtsl.send_keys(row["DtSold"])

        # # enter proceeds
        proceeds = driver.find_element(By.NAME, f"capitalGains[{i}].salesPrice")
        proceeds.clear()
        proceeds.send_keys(row["Proceeds"])

        # # enter cost basis
        cost = driver.find_element(By.NAME, f"capitalGains[{i}].cost")
        cost.clear()
        cost.send_keys(row["Cost"])

        i += 1


trade_data_path = Path("G:/") / "My Drive" / "Finance" / "Taxes" / "2024"
trades338 = import_trades(path=trade_data_path / "x338_trades.csv")
trades454 = import_trades(path=trade_data_path / "x454_trades.csv")
trades = pl.concat([trades338, trades454])

trades.describe()

input_trades(trades)

trades.select(pl.col("Proceeds") - pl.col("Cost")).sum()
trades.select(pl.col("Proceeds").round() - pl.col("Cost").round()).sum()
