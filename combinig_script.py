import re
import pandas as pd
from pathlib import Path


def clean_postcode(value):
    """
    Converts:
        ="0846" -> 0846
        846 -> 0846
        0846 -> 0846
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    # Extract digits only
    digits = re.findall(r"\d+", value)

    if not digits:
        return ""

    postcode = "".join(digits)

    # Keep last 4 digits if longer
    postcode = postcode[-4:]

    # Ensure 4 digits with leading zeros
    return postcode.zfill(4)


def combine_and_clean_urls(
    csv1: str,
    csv2: str,
    output_csv: str
):
    """
    Combines 2 CSVs,
    Cleans PostCode column,
    Removes duplicate Broker URLs.
    """

    print("Reading files...")

    df1 = pd.read_csv(csv1, dtype=str).fillna("")
    df2 = pd.read_csv(csv2, dtype=str).fillna("")

    print(f"CSV1 Rows: {len(df1)}")
    print(f"CSV2 Rows: {len(df2)}")

    # Combine
    df = pd.concat(
        [df1, df2],
        ignore_index=True
    )

    print(f"Combined Rows: {len(df)}")

    # Clean PostCode
    if "PostCode" in df.columns:
        df["PostCode"] = df["PostCode"].apply(
            clean_postcode
        )

    # Clean URLs before dedupe
    if "Broker URL" in df.columns:

        df["Broker URL"] = (
            df["Broker URL"]
            .astype(str)
            .str.strip()
        )

        before = len(df)

        df = df.drop_duplicates(
            subset=["Broker URL"],
            keep="first"
        )

        removed = before - len(df)

        print(
            f"Removed {removed} duplicate Broker URLs"
        )

    df.to_csv(
        output_csv,
        index=False
    )

    print(
        f"Saved URL-cleaned CSV: {output_csv}"
    )
    print(
        f"Final Rows: {len(df)}"
    )


def combine_and_clean_emails(
    csv1: str,
    csv2: str,
    output_csv: str
):
    """
    Combines 2 CSVs,
    Removes duplicate Email rows.
    Keeps first occurrence.
    """

    print("Reading files...")

    df1 = pd.read_csv(csv1, dtype=str).fillna("")
    df2 = pd.read_csv(csv2, dtype=str).fillna("")

    print(f"CSV1 Rows: {len(df1)}")
    print(f"CSV2 Rows: {len(df2)}")

    # Combine
    df = pd.concat(
        [df1, df2],
        ignore_index=True
    )

    print(f"Combined Rows: {len(df)}")

    if "Email" in df.columns:

        # Normalize emails
        df["Email"] = (
            df["Email"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # Remove empty emails from dedupe check
        df_non_empty = df[
            df["Email"] != ""
        ].copy()

        df_empty = df[
            df["Email"] == ""
        ].copy()

        before = len(df_non_empty)

        df_non_empty = df_non_empty.drop_duplicates(
            subset=["Email"],
            keep="first"
        )

        removed = before - len(df_non_empty)

        # Add back rows with blank emails
        df = pd.concat(
            [df_non_empty, df_empty],
            ignore_index=True
        )

        print(
            f"Removed {removed} duplicate Emails"
        )

    df.to_csv(
        output_csv,
        index=False
    )

    print(
        f"Saved Email-cleaned CSV: {output_csv}"
    )
    print(
        f"Final Rows: {len(df)}"
    )


if __name__ == "__main__":

    CSV_1 = "brokers_clean_primary_details.csv"
    CSV_2 = "brokers_clean_primary_details_v2.csv"

    CSV_3 = "broker_complete_details_v2.csv"
    CSV_4 = "brokers_complete_details_v2.csv"

    # Output 1:
    combine_and_clean_urls(
        csv1=CSV_1,
        csv2=CSV_2,
        output_csv="Total_Unique_Urls.csv"
    )

    # Output 2:
    combine_and_clean_emails(
        csv1=CSV_1,
        csv2=CSV_2,
        output_csv="Total_unique_emails.csv"
    )