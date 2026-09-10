"""
Data/model service used by the Django views.

This mirrors the important modeling logic from the supplied notebook:
- Classification target: Enrollment_Status
- Regression target: Matriculation_Score
- 80/20 train/test split
- preprocessing for numeric/categorical columns
- Logistic Regression, Decision Tree, Random Forest,
  KNN and Naive Bayes classifiers
- Linear Regression, Random Forest and Gradient Boosting regressors
"""

from functools import lru_cache
import pickle
import numpy as np
import pandas as pd

from django.conf import settings
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB


SAVED_REGRESSION_MODELS = {
    "linear_regression": ("Linear Regression", "linear_regression.pkl"),
    "random_forest_regressor": (
        "Random Forest Regressor",
        "random_forest_regressor.pkl",
    ),
    "gradient_boosting_regressor": (
        "Gradient Boosting Regressor",
        "gradient_boosting_regressor.pkl",
    ),
}


@lru_cache(maxsize=len(SAVED_REGRESSION_MODELS))
def load_regression_model(model_type):
    """Load one of the supplied, trusted regression pipelines once per process."""
    try:
        _, filename = SAVED_REGRESSION_MODELS[model_type]
    except KeyError as exc:
        raise ValueError("Choose a valid saved regression model.") from exc

    path = settings.BASE_DIR / "saved_models" / filename
    if not path.exists():
        raise FileNotFoundError(f"Saved model not found: {path}")

    with path.open("rb") as model_file:
        return pickle.load(model_file)


def load_data():
    path = settings.DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Copy the CSV into the project's data/ folder."
        )

    df = pd.read_csv(path)
    df = df.drop_duplicates().reset_index(drop=True)

    numeric_cols = [
        "Age",
        "Matriculation_Score",
        "Number_of_Siblings",
        "Family_Monthly_Income_MMK",
        "Extracurricular_Score",
        "Distance_to_University_km",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Notebook feature engineering
    if "Family_Monthly_Income_MMK" in df and "Number_of_Siblings" in df:
        df["Income_Log"] = np.log1p(df["Family_Monthly_Income_MMK"])
        df["Income_Per_Sibling"] = (
            df["Family_Monthly_Income_MMK"] / (df["Number_of_Siblings"] + 1)
        )

    if "Matriculation_Score" in df:
        df["Score_Band"] = pd.cut(
            df["Matriculation_Score"],
            bins=[-np.inf, 299, 349, 399, np.inf],
            labels=["Low", "Medium", "High", "Very High"],
        )

    return df


def _preprocessor(X):
    numeric = X.select_dtypes(include=["int64", "float64", "int32", "float32"]).columns.tolist()
    categorical = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer([
        ("num", numeric_transformer, numeric),
        ("cat", categorical_transformer, categorical),
    ])


@lru_cache(maxsize=1)
def build_dashboard():
    data = load_data()

    # ---------- Overview ----------
    enrollment = data["Enrollment_Status"].value_counts().to_dict()

    # ---------- Classification ----------
    excluded = [
        "Student_ID",
        "Enrollment_Status",
        "Preferred_University_Type",
        "Preferred_University_Code",
        "Chosen_Field_of_Study",
        "Scholarship_Received",
    ]
    X = data.drop(columns=[c for c in excluded if c in data.columns])
    y = data["Enrollment_Status"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    classifiers = {
        "Logistic Regression": LogisticRegression(max_iter=2000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42, max_depth=10),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, random_state=42, n_jobs=-1
        ),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=7),
        "Naive Bayes": GaussianNB(),
    }

    clf_rows = []
    fitted_classifiers = {}
    for name, model in classifiers.items():
        pipe = Pipeline([("preprocessor", _preprocessor(X)), ("model", model)])
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        fitted_classifiers[name] = pipe
        clf_rows.append({
            "model": name,
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, average="weighted", zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, pred, average="weighted", zero_division=0)), 4),
        })

    clf_rows.sort(key=lambda x: x["f1"], reverse=True)
    best_clf_name = clf_rows[0]["model"]
    best_clf = fitted_classifiers[best_clf_name]

    # Permutation importance on original feature columns.
    from sklearn.inspection import permutation_importance
    perm = permutation_importance(
        best_clf,
        X_test,
        y_test,
        n_repeats=5,
        random_state=42,
        scoring="f1_weighted",
        n_jobs=-1,
    )
    importance = pd.DataFrame({
        "feature": X_test.columns,
        "importance": perm.importances_mean,
    }).sort_values("importance", ascending=False).head(15)
    importance_rows = [
        {"feature": str(r.feature), "importance": round(float(r.importance), 5)}
        for r in importance.itertuples()
    ]

    # ---------- Regression ----------
    # A regression target cannot be missing. Keep the full dataset for dashboard
    # summaries, but train and evaluate score models only on complete targets.
    regression_data = data.dropna(subset=["Matriculation_Score"])
    reg_excluded = [
        "Student_ID",
        "Matriculation_Score",
        "Preferred_University_Type",
        "Preferred_University_Code",
        "Chosen_Field_of_Study",
        "Enrollment_Status",
    ]
    Xr = regression_data.drop(
        columns=[c for c in reg_excluded if c in regression_data.columns]
    )
    yr = regression_data["Matriculation_Score"]

    Xr_train, Xr_test, yr_train, yr_test = train_test_split(
        Xr, yr, test_size=0.20, random_state=42
    )

    regressors = {
        "Linear Regression": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=200, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting Regressor": GradientBoostingRegressor(
            n_estimators=200, random_state=42
        ),
    }

    reg_rows = []
    for name, model in regressors.items():
        pipe = Pipeline([("preprocessor", _preprocessor(Xr)), ("model", model)])
        pipe.fit(Xr_train, yr_train)
        pred = pipe.predict(Xr_test)
        reg_rows.append({
            "model": name,
            "mae": round(float(mean_absolute_error(yr_test, pred)), 4),
            "rmse": round(float(mean_squared_error(yr_test, pred) ** 0.5), 4),
            "r2": round(float(r2_score(yr_test, pred)), 4),
        })
    reg_rows.sort(key=lambda x: x["r2"], reverse=True)

    # ---------- Dashboard distributions ----------
    score_hist = []
    counts, edges = np.histogram(
        data["Matriculation_Score"].dropna(), bins=12
    )
    for count, left, right in zip(counts, edges[:-1], edges[1:]):
        score_hist.append({
            "label": f"{left:.0f}-{right:.0f}",
            "count": int(count),
        })

    region_enrollment = (
        pd.crosstab(data["Region"], data["Enrollment_Status"])
        .reset_index()
        .fillna(0)
    )
    region_rows = []
    for _, row in region_enrollment.iterrows():
        item = {"region": str(row["Region"])}
        for status in enrollment.keys():
            item[str(status)] = int(row.get(status, 0))
        region_rows.append(item)

    field_counts = (
        data["Chosen_Field_of_Study"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    field_counts.columns = ["field", "count"]
    field_rows = [
        {"field": str(r.field), "count": int(r.count)}
        for r in field_counts.itertuples()
    ]

    income_score = (
        data[["Family_Monthly_Income_MMK", "Matriculation_Score"]]
        .dropna()
        .sample(min(500, len(data)), random_state=42)
    )
    scatter_rows = [
        {
            "income": float(r.Family_Monthly_Income_MMK),
            "score": float(r.Matriculation_Score),
        }
        for r in income_score.itertuples()
    ]

    return {
        "overview": {
            "students": int(len(data)),
            "enrolled": int((data["Enrollment_Status"] == "Enrolled").sum()),
            "not_enrolled": int((data["Enrollment_Status"] != "Enrolled").sum()),
            "enrollment_rate": round(
                float((data["Enrollment_Status"] == "Enrolled").mean() * 100), 2
            ),
            "missing_cells": int(data.isna().sum().sum()),
            "duplicate_rows_removed": int(len(pd.read_csv(settings.DATASET_PATH)) - len(data)),
        },
        "enrollment": [
            {"status": str(k), "count": int(v)} for k, v in enrollment.items()
        ],
        "classification": clf_rows,
        "regression": reg_rows,
        "best_classifier": best_clf_name,
        "best_regressor": reg_rows[0]["model"],
        "feature_importance": importance_rows,
        "score_hist": score_hist,
        "region_enrollment": region_rows,
        "field_counts": field_rows,
        "income_score": scatter_rows,
        "classes": [str(c) for c in best_clf.classes_],
        "_classifier": best_clf,
        "_classification_columns": X.columns.tolist(),
    }


def clear_cache():
    build_dashboard.cache_clear()


def predict_student(payload):
    model_type = payload.get("model_type")
    if model_type not in SAVED_REGRESSION_MODELS:
        raise ValueError("Choose a valid saved regression model.")

    model = load_regression_model(model_type)
    model_name, _ = SAVED_REGRESSION_MODELS[model_type]
    numeric_fields = {
        "Age", "Number_of_Siblings", "Family_Monthly_Income_MMK",
        "Extracurricular_Score", "Distance_to_University_km",
    }
    row = {
        field: (payload.get(field) or np.nan)
        for field in model.feature_names_in_
        if field not in numeric_fields
    }
    for field in numeric_fields:
        row[field] = pd.to_numeric(payload.get(field), errors="coerce")

    income = row["Family_Monthly_Income_MMK"]
    siblings = row["Number_of_Siblings"]
    row["Income_Log"] = np.log1p(income) if pd.notna(income) else np.nan
    row["Income_Per_Sibling"] = (
        income / (siblings + 1)
        if pd.notna(income) and pd.notna(siblings) and siblings >= 0
        else np.nan
    )
    row["Distance_Band"] = pd.cut(
        [row["Distance_to_University_km"]],
        bins=[-np.inf, 5, 15, 30, np.inf],
        labels=["Very Near", "Near", "Far", "Very Far"],
    )[0]
    row["Extracurricular_Band"] = pd.cut(
        [row["Extracurricular_Score"]],
        bins=[-np.inf, 3, 6, 8, np.inf],
        labels=["Low", "Moderate", "High", "Very High"],
    )[0]

    parent_scores = {
        "No Formal Education": 0, "Primary School": 1, "Middle School": 2,
        "High School": 3, "University Graduate": 4,
    }
    english_scores = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    yes_no_score = lambda value: 1 if value == "Yes" else 0
    row["Parent_Education_Score"] = parent_scores.get(row["Parent_Education_Level"], 0)
    row["English_Score"] = english_scores.get(row["English_Proficiency_Level"], 0)
    row["Internet_Score"] = yes_no_score(row["Internet_Access_At_Home"])
    row["Family_Graduate_Score"] = yes_no_score(row["Family_Member_University_Graduate"])
    row["Test_Prep_Score"] = yes_no_score(row["Test_Prep_Course"])
    row["Academic_Support_Index"] = sum(
        row[field] for field in [
            "Parent_Education_Score", "English_Score", "Internet_Score",
            "Family_Graduate_Score", "Test_Prep_Score",
        ]
    )
    row["Scholarship_Application_Score"] = yes_no_score(row["Scholarship_Applied"])
    row["Scholarship_Received_Score"] = yes_no_score(row["Scholarship_Received"])
    row["Financial_Support_Index"] = (
        row["Income_Log"] + row["Scholarship_Application_Score"]
        + row["Scholarship_Received_Score"]
    )

    frame = pd.DataFrame([row], columns=model.feature_names_in_)
    prediction = float(model.predict(frame)[0])
    return {
        "model_type": model_type,
        "model_name": model_name,
        "prediction": round(prediction, 2),
    }
