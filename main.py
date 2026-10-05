from __future__ import annotations   # <-- ADD THIS LINE (must be first)

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="Skin Clinic Campaign Analysis API")

CSV_PATH = "skin_clinic_campaign.csv"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["Response_to_Campaign"] = df["Response_to_Campaign"].str.strip().str.title()
    df["Gender"] = df["Gender"].str.strip().str.title()
    df["AgeGroup"] = df["AgeGroup"].str.strip()
    df["Purchase_Last_Quarter"] = df["Purchase_Last_Quarter"].str.strip().str.title()
    return df


def response_rate_table(df: pd.DataFrame, group_col: str, order=None):
    grp = (df.groupby(group_col)["Response_to_Campaign"]
             .agg(Total="count",
                  Responded=lambda s: (s == "Yes").sum())
             .reset_index())
    grp["Response_Rate_%"] = (grp["Responded"] / grp["Total"] * 100).round(2)
    if order:
        grp[group_col] = pd.Categorical(grp[group_col], categories=order, ordered=True)
        grp = grp.sort_values(group_col)
    else:
        grp = grp.sort_values(group_col)
    return grp.rename(columns={group_col: "Segment"}).to_dict(orient="records")


@app.get("/")
def root():
    return {"message": "Skin Clinic Campaign Analysis API",
            "endpoint": "/campaign-analysis"}


@app.get("/campaign-analysis")
def campaign_analysis():
    df = load_data()

    def band(n):
        if n <= 4:
            return "1-4"
        elif n <= 8:
            return "5-8"
        return ">8"

    df["ProductBand"] = df["Unique_Products_Purchased"].apply(band)

    result = {
        "gender_vs_response": response_rate_table(df, "Gender"),
        "age_group_vs_response": response_rate_table(
            df, "AgeGroup", order=["<30", "30-50", ">50"]),
        "purchase_last_quarter_vs_response": response_rate_table(
            df, "Purchase_Last_Quarter", order=["Yes", "No"]),
        "product_usage_vs_response": response_rate_table(
            df, "ProductBand", order=["1-4", "5-8", ">8"]),
    }
    return JSONResponse(content=result)


@app.get("/campaign-analysis/csv", response_class=PlainTextResponse)
def campaign_analysis_csv():
    df = load_data()

    def band(n):
        return "1-4" if n <= 4 else ("5-8" if n <= 8 else ">8")
    df["ProductBand"] = df["Unique_Products_Purchased"].apply(band)

    frames = []
    for title, col, order in [
        ("Gender", "Gender", None),
        ("AgeGroup", "AgeGroup", ["<30", "30-50", ">50"]),
        ("Purchase_Last_Quarter", "Purchase_Last_Quarter", ["Yes", "No"]),
        ("ProductBand", "ProductBand", ["1-4", "5-8", ">8"]),
    ]:
        t = response_rate_table(df, col, order)
        tmp = pd.DataFrame(t)
        tmp.insert(0, "Analysis", title)
        frames.append(tmp)

    out = pd.concat(frames, ignore_index=True)
    return out.to_csv(index=False)