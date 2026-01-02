"""
Data loading and preprocessing for Hospital Operations Dashboard
JBI100 Visualization - Group 25
"""

import pandas as pd
import os

# Path to data folder
DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


def load_services_weekly():
    """Load weekly service metrics data."""
    return pd.read_csv(os.path.join(DATA_PATH, "services_weekly.csv"))


def load_patients():
    """Load patient records data."""
    return pd.read_csv(os.path.join(DATA_PATH, "patients.csv"))


def load_staff():
    """Load staff information."""
    return pd.read_csv(os.path.join(DATA_PATH, "staff.csv"))


def load_staff_schedule():
    """Load staff schedule data."""
    return pd.read_csv(os.path.join(DATA_PATH, "staff_schedule.csv"))


def get_services_data():
    """
    Load and preprocess services data with derived metrics.
    
    Returns:
        pd.DataFrame: Services data with additional computed columns
    """
    df = load_services_weekly()
    
    # Acceptance rate - use pre-computed if exists, else compute
    if "acceptance_rate" not in df.columns:
        df["acceptance_rate"] = (
            df["patients_admitted"] / df["patients_request"].replace(0, 1) * 100
        ).round(1)
    
    # Refusal rate
    if "refusal_rate" not in df.columns:
        df["refusal_rate"] = (
            df["patients_refused"] / df["patients_request"].replace(0, 1) * 100
        ).round(1)
    
    # Bed utilization
    if "utilization_rate" not in df.columns:
        df["utilization_rate"] = (
            df["patients_admitted"] / df["available_beds"].replace(0, 1) * 100
        ).round(1)
    
    # Pressure index (demand vs capacity)
    if "pressure_index" not in df.columns:
        df["pressure_index"] = (
            df["patients_request"] / df["available_beds"].replace(0, 1)
        ).round(2)
    
    return df


def get_patients_data():
    """
    Load and preprocess patient data with derived metrics.
    
    Returns:
        pd.DataFrame: Patient data with additional computed columns
    """
    df = load_patients()
    
    # Convert dates
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    df["departure_date"] = pd.to_datetime(df["departure_date"])
    
    # Length of stay
    df["length_of_stay"] = (df["departure_date"] - df["arrival_date"]).dt.days
    
    # Arrival week
    df["arrival_week"] = df["arrival_date"].dt.isocalendar().week.astype(int)
    
    return df


def get_staff_schedule_data():
    """
    Load staff schedule data.
    
    Returns:
        pd.DataFrame: Staff schedule data
    """
    return load_staff_schedule()


def get_all_data():
    """
    Load all datasets with preprocessing.
    
    Returns:
        tuple: (services_df, patients_df, staff_df, schedule_df)
    """
    services = get_services_data()
    patients = get_patients_data()
    staff = load_staff()
    schedule = get_staff_schedule_data()
    
    return services, patients, staff, schedule


def build_week_data_store(df):
    """
    Build a dictionary of week data for client-side access.
    Used for fast tooltip lookups.
    
    Args:
        df: Services dataframe
        
    Returns:
        dict: Nested dict {week: {service: {metric: value}}}
    """
    data_store = {}
    
    for week in range(1, 53):
        week_data = df[df["week"] == week]
        data_store[week] = {
            row["service"]: {
                "satisfaction": int(row["patient_satisfaction"]),
                "acceptance": round(row["acceptance_rate"], 1),
                "morale": int(row["staff_morale"]),
                "beds": int(row["available_beds"]),
                "admitted": int(row["patients_admitted"]),
                "refused": int(row["patients_refused"])
            }
            for _, row in week_data.iterrows()
        }
    
    return data_store
