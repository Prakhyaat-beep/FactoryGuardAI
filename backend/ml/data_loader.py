"""Download and load the public AI4I 2020 predictive maintenance dataset."""

from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile

import pandas as pd

PROJECT_BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_BACKEND_DIR / "data"
DATA_FILE = DATA_DIR / "ai4i2020.csv"
SUPPLIED_DATA_FILE = DATA_DIR / "predictive_maintenance.csv"
DATASET_URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"


def download_dataset() -> Path:
    """Download the UCI dataset only when its local CSV is not already present."""
    if DATA_FILE.exists():
        return DATA_FILE
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = DATA_DIR / "ai4i2020.zip"
    try:
        urlretrieve(DATASET_URL, archive_path)
        with ZipFile(archive_path) as archive:
            csv_names = [name for name in archive.namelist() if name.endswith(".csv")]
            if not csv_names:
                raise FileNotFoundError("The downloaded dataset archive contains no CSV file.")
            with archive.open(csv_names[0]) as source, DATA_FILE.open("wb") as destination:
                destination.write(source.read())
    except Exception as error:
        raise RuntimeError(
            "Could not download the AI4I 2020 dataset. Check your internet connection or download it from UCI and place ai4i2020.csv in backend/data/."
        ) from error
    finally:
        if archive_path.exists():
            archive_path.unlink()
    return DATA_FILE


def load_dataset() -> pd.DataFrame:
    """Load the supplied AI4I-compatible CSV when present, otherwise UCI's CSV."""
    dataset_path = SUPPLIED_DATA_FILE if SUPPLIED_DATA_FILE.exists() else download_dataset()
    dataframe = pd.read_csv(dataset_path)
    # The supplied CSV calls the binary target Target; normalize only its name.
    if "Target" in dataframe.columns and "Machine failure" not in dataframe.columns:
        dataframe = dataframe.rename(columns={"Target": "Machine failure"})
    return dataframe
