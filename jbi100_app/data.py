import pandas as pd
import os

# Path to the data folder inside your Dash project
DATA_PATH = os.path.join(os.path.dirname(__file__), "data")


# -------------------------------
# LOAD CSV FILES
# -------------------------------
def load_services_weekly():
    return pd.read_csv(os.path.join(DATA_PATH, "services_weekly.csv"))


def load_staff():
    return pd.read_csv(os.path.join(DATA_PATH, "staff.csv"))


def load_staff_schedule():
    return pd.read_csv(os.path.join(DATA_PATH, "staff_schedule.csv"))


def load_patients():
    return pd.read_csv(os.path.join(DATA_PATH, "patients.csv"))


# -------------------------------
# MAIN DATA FUNCTION
# returns: (services_df, patients_df)
# -------------------------------
def get_data():

    # Load all tables
    services = load_services_weekly()
    staff = load_staff()
    schedule = load_staff_schedule()
    patients = load_patients()

    # ----------------------------------------------------------
    # FIX: Column names in your CSV
    # (you showed "available_" earlier; actual column is "available_beds")
    # ----------------------------------------------------------
    if "available_beds" not in services.columns:
        raise KeyError(f"Expected column 'available_beds'. Found: {services.columns.tolist()}")

    # ----------------------------------------------------------
    # MAKE METRICS FOR HEATMAP & SCATTERPLOTS
    # ----------------------------------------------------------

    services["pressure_index"] = (
        services["patients_request"] /
        services["available_beds"].replace(0, 1)
    )

    services["refusal_rate"] = (
        services["patients_refused"] /
        services["patients_request"].replace(0, 1)
    )

    # Staff presence per service-week
    staff_presence = (
        schedule.groupby(["service", "week"])
        .agg(staff_present=("present", "sum"))
        .reset_index()
    )
    services = services.merge(staff_presence, on=["service", "week"], how="left")
    services["staff_present"] = services["staff_present"].fillna(0)

    # ----------------------------------------------------------
    # PATIENT LOS (Length of Stay)
    # ----------------------------------------------------------
    patients["arrival_date"] = pd.to_datetime(patients["arrival_date"], format="ISO8601")
    patients["departure_date"] = pd.to_datetime(patients["departure_date"], format="ISO8601")

    patients["LOS"] = (patients["departure_date"] - patients["arrival_date"]).dt.days

    return services, patients
