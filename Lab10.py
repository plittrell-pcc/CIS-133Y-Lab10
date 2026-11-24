# ***************************************************************************
#
# Author: Paul Littrell
# Lab:    CIS-133Y Lab 10
# Date:   November 21, 2026
# Desc:   Self-contained program that prompts for a first name and gender,
#         queries yearly U.S. birth records from the NAMES database via
#         pandas, processes the data, and plots trends.
#
# Input:  First name (letters only) and gender (M or F).
# Output: Console status messages and a matplotlib line chart of annual
#         birth counts and their 5-year rolling average.
# Source: Module 10 Lab 10
# GitHub: https://github.com/plittrell-pcc/CIS-133Y-Lab10
#
# ***************************************************************************

# Added import of warnings module to use in the fetch_name_data function to
# handle the SQLAlchemy warning while running program

import warnings
import pymssql
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, StrMethodFormatter


class Database:
    """Data layer helper managing the shared connection to the NAMES database."""

    __connection = None

    @classmethod
    def connect(cls):
        """Establishes and shares a single connection to the database."""
        if cls.__connection is None:
            cls.__connection = pymssql.connect(
                server="cisdbss.pcc.edu",
                user="275student",
                password="275student",
                database="NAMES",
            )

    @classmethod
    def get_connection(cls):
        """Ensures a connection exists and returns it."""
        cls.connect()
        return cls.__connection


# Input and welcome message
def get_user_input():
    """Prompt for and validate the name and gender to look up."""
    print("======================================================================")
    print("              Welcome to the Name Popularity Explorer!")
    print("This program charts yearly U.S. birth records from the NAMES database.")
    print("======================================================================")

    while True:
        name = input("Enter a first name (letters only, e.g., Olivia): ").strip()
        if name.isalpha():
            name = name.capitalize()
            break
        print("Please enter a first name using letters only.")

    while True:
        gender = input("Enter gender as M (male) or F (female): ").strip().upper()
        if gender in ("M", "F"):
            break
        print("Please enter M for male or F for female.")

    return name, gender


# Database query and pandas processing.
def fetch_name_data(name, gender):
    """Fetch matching records into a pandas DataFrame using read_sql."""
    connection = Database.get_connection()
    query = """
        SELECT Name, Year, Gender, NameCount, Total
        FROM all_data
        WHERE Name = %s AND Gender = %s
        ORDER BY Year;
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="pandas only supports SQLAlchemy connectable",
            category=UserWarning,
        )
        return pd.read_sql(query, connection, params=(name, gender))


def process_data(data):
    """Clean numeric fields and add popularity and smoothed count columns."""
    numeric_columns = ("Year", "NameCount", "Total")
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=numeric_columns)
    data = data[data["Total"] > 0]
    data = data.sort_values("Year").drop_duplicates(
        subset=("Name", "Year", "Gender"),
        keep="last",
    ).copy()

    if data.empty:
        return data

    data["PopularityPercent"] = data["NameCount"] / data["Total"] * 100
    data["NameCountSmoothed"] = data["NameCount"].rolling(
        window=5,
        min_periods=1,
    ).mean()
    return data


# Visualization
def plot_data(data, name, gender):
    """Plot annual name counts and their five-year rolling average."""
    gender_label = "male" if gender == "M" else "female"
    plt.figure(figsize=(10, 6))
    plt.plot(
        data["Year"],
        data["NameCount"],
        marker="o",
        alpha=0.55,
        label="Annual count",
    )
    plt.plot(
        data["Year"],
        data["NameCountSmoothed"],
        linewidth=2.5,
        label="5-year rolling average",
    )
    plt.title(f"Yearly Popularity of {name} ({gender_label})")
    plt.xlabel("Year")
    plt.ylabel("Number of births")
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    plt.gca().yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


def main():
    """Run the interactive name lookup and display its popularity chart."""
    name, gender = get_user_input()

    try:
        data = fetch_name_data(name, gender)
    except (pymssql.Error, pd.errors.DatabaseError) as error:
        print(f"\nUnable to retrieve records from the NAMES database: {error}")
        return

    if data.empty:
        print(f"\nNo records were found for {name} ({gender}).")
        return

    data = process_data(data)
    if data.empty:
        print("\nRecords were found, but none contained usable numeric data.")
        return

    print(f"\nPlotting {len(data)} yearly records for {name} ({gender}).")
    plot_data(data, name, gender)


if __name__ == "__main__":
    main()