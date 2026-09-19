import streamlit as st
import pandas as pd
import joblib

st.set_page_config(page_title="Undertrial Case Triage", layout="wide")

BASE = r"C:\Users\manth\SIH PROJECT"

@st.cache_resource
def load_model():
    model = joblib.load(f"{BASE}\\triage_model_lgbm.pkl")
    encoders = joblib.load(f"{BASE}\\feature_encoders.pkl")
    return model, encoders

@st.cache_data
def load_priority_list():
    return pd.read_csv(f"{BASE}\\priority_list.csv")

model, encoders = load_model()
priority_df = load_priority_list()

st.title("Undertrial Case Triage - Karnataka 2018")
st.caption("Predicts which pending cases are at risk of becoming long-pending (Complex), before they get buried in the backlog.")

tab1, tab2 = st.tabs(["Priority List", "Try a Prediction"])

with tab1:
    st.subheader(f"High-risk pending cases ({len(priority_df):,} flagged as Complex)")

    col1, col2 = st.columns(2)
    with col1:
        dist_filter = st.selectbox(
            "Filter by district code",
            options=["All"] + sorted(priority_df["dist_code"].unique().tolist())
        )
    with col2:
        top_n = st.slider("Show top N cases (by risk score)", 10, 200, 50)

    display_df = priority_df.copy()
    if dist_filter != "All":
        display_df = display_df[display_df["dist_code"] == dist_filter]

    display_df = display_df.sort_values("complex_risk_score", ascending=False).head(top_n)

    st.dataframe(
        display_df[["ddl_case_id", "dist_code", "court_no", "judge_position",
                     "type_name_label", "purpose_name_label", "days_pending_so_far",
                     "complex_risk_score"]],
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download this list as CSV",
        display_df.to_csv(index=False),
        file_name="filtered_priority_list.csv"
    )

with tab2:
    st.subheader("Predict risk for a new case")

    type_val = st.selectbox("Case type", options=sorted(encoders["type_name_label"].classes_))
    purpose_val = st.selectbox("Purpose", options=sorted(encoders["purpose_name_label"].classes_))
    judge_val = st.selectbox("Judge position", options=sorted(encoders["judge_position"].classes_))
    dist_val = st.selectbox("District code", options=sorted(encoders["dist_code"].classes_))
    court_val = st.selectbox("Court number", options=sorted(encoders["court_no"].classes_))

    if st.button("Predict"):
        row = {}
        for col, val in zip(
            ["type_name_label", "purpose_name_label", "judge_position", "dist_code", "court_no"],
            [type_val, purpose_val, judge_val, dist_val, court_val]
        ):
            row[col] = encoders[col].transform([str(val)])[0]

        X_input = pd.DataFrame([row])
        pred = model.predict(X_input)[0]
        proba = model.predict_proba(X_input)[0]
        complex_idx = list(model.classes_).index("Complex")

        st.markdown(f"### Predicted bucket: **{pred}**")
        st.metric("Complex risk score", f"{proba[complex_idx]:.1%}")

        proba_df = pd.DataFrame({
            "Bucket": model.classes_,
            "Probability": proba
        }).sort_values("Probability", ascending=False)
        st.bar_chart(proba_df.set_index("Bucket"))
