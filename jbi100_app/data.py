"""
Data loading and preprocessing for Hospital Dashboard
"""

import pandas as pd
import os

# Path to data folder inside the Dash project
DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


def load_services_weekly():
    return pd.read_csv(os.path.join(DATA_PATH, "services_weekly.csv"))


def load_patients():
    return pd.read_csv(os.path.join(DATA_PATH, "patients.csv"))


def load_staff():
    return pd.read_csv(os.path.join(DATA_PATH, "staff.csv"))


def load_staff_schedule():
    return pd.read_csv(os.path.join(DATA_PATH, "staff_schedule.csv"))


def get_data():
    """
    Load and preprocess all data.
    Returns: (services_df, patients_df)
    """
    services = load_services_weekly()
    patients = load_patients()
    
    # --- Services metrics ---
    services["refusal_rate"] = (
        services["patients_refused"] / services["patients_request"].replace(0, 1) * 100
    ).round(1)
    
    services["utilization_rate"] = (
        services["patients_admitted"] / services["available_beds"].replace(0, 1) * 100
    ).round(1)
    
    services["pressure_index"] = (
        services["patients_request"] / services["available_beds"].replace(0, 1)
    ).round(2)
    
    # --- Patients metrics ---
    patients["arrival_date"] = pd.to_datetime(patients["arrival_date"])
    patients["departure_date"] = pd.to_datetime(patients["departure_date"])
    patients["length_of_stay"] = (patients["departure_date"] - patients["arrival_date"]).dt.days
    patients["arrival_week"] = patients["arrival_date"].dt.isocalendar().week.astype(int)
    
    return services, patients
