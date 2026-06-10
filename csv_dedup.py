import pandas as pd
from pathlib import Path


class CSVDeduplicator:
    def __init__(
        self,
        input_csv: str,
        output_csv: str,
        url_column: str = "Broker URL",
    ):
        self.input_csv = Path(input_csv)
        self.output_csv = Path(output_csv)
        self.url_column = url_column

    def remove_duplicate_urls(self) -> None:
        """
        Removes duplicate rows based on the Broker URL column.
        Keeps the first occurrence and removes all subsequent duplicates.
        """
        df = pd.read_csv(self.input_csv)

        if self.url_column not in df.columns:
            raise ValueError(
                f"Column '{self.url_column}' not found in CSV.\n"
                f"Available columns: {list(df.columns)}"
            )

        original_count = len(df)

        # Keep the first occurrence of each URL
        df_clean = df.drop_duplicates(
            subset=[self.url_column],
            keep="first"
        )

        removed_count = original_count - len(df_clean)

        df_clean.to_csv(self.output_csv, index=False)

        print("=" * 50)
        print(f"Input File      : {self.input_csv}")
        print(f"Output File     : {self.output_csv}")
        print(f"Total Rows      : {original_count}")
        print(f"Removed Rows    : {removed_count}")
        print(f"Remaining Rows  : {len(df_clean)}")
        print("=" * 50)


if __name__ == "__main__":
    deduplicator = CSVDeduplicator(
        input_csv="broker_primary_details.csv",
        output_csv="brokers_clean_deduplicated.csv",
        url_column="Broker URL",
    )

    deduplicator.remove_duplicate_urls()