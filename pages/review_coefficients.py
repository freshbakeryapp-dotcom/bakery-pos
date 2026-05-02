import streamlit as st
import pandas as pd
from utils.coefficients import calculate_monthly_coefficients
from db import get_db

st.set_page_config(page_title="Usage Review - Artisan Crumb", layout="wide")
conn = get_db()
conn.row_factory = sqlite3.Row

st.markdown('<h1 style="font-family: \'Playfair Display\', serif;">📊 Monthly Usage Review</h1>', unsafe_allow_html=True)

# Month selector
months = [row[0] for row in conn.execute("SELECT DISTINCT month FROM monthly_usage_coeffs ORDER BY month DESC").fetchall()]
if not months:
    st.info("🔄 No data yet. Run a production batch or click 'Calculate Now' to generate first coefficients.")
    if st.button("Calculate Current Month", type="primary"):
        calculate_monthly_coefficients()
        st.rerun()
    st.stop()

selected_month = st.selectbox("Review Month", months)

# Load data
df = pd.DataFrame(conn.execute("""
    SELECT c.product_id, c.ingredient_id, c.coefficient, c.confidence, c.data_points,
           i.name as ingredient_name, p.name as product_name, r.coefficient_grams as recipe_grams
    FROM monthly_usage_coeffs c
    JOIN ingredients i ON c.ingredient_id = i.id
    JOIN products p ON c.product_id = p.id
    JOIN recipes r ON c.product_id = r.product_id AND c.ingredient_id = r.ingredient_id
    WHERE c.month = ?
    ORDER BY c.confidence DESC
""", (selected_month,)).fetchall())

if df.empty:
    st.info("No coefficients for this month.")
    st.stop()

# Display table
st.subheader(f"Adjustments for {selected_month}")
display_df = df[["product_name", "ingredient_name", "recipe_grams", "coefficient", "confidence", "data_points"]].copy()
display_df["adjustment"] = display_df["coefficient"].apply(lambda x: f"{int((x-1)*100)}%")
display_df.rename(columns={
    "product_name": "Product",
    "ingredient_name": "Ingredient",
    "recipe_grams": "Recipe (g/unit)",
    "coefficient": "Multiplier",
    "confidence": "Confidence",
    "data_points": "Units Baked"
}, inplace=True)

st.dataframe(display_df, use_container_width=True, hide_index=True)

# Override controls
st.subheader("✏️ Review & Override")
for idx, row in df.iterrows():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.markdown(f"**{row['product_name']}** → {row['ingredient_name']}")
    with col2:
        st.markdown(f"Multiplier: `{row['coefficient']}`")
    with col3:
        custom = st.number_input(
            "Override", 
            value=row["coefficient"], 
            step=0.01, 
            min_value=0.8, 
            max_value=1.5,
            key=f"override_{row['product_id']}_{row['ingredient_id']}"
        )
    with col4:
        if st.button("Apply", key=f"apply_{row['product_id']}_{row['ingredient_id']}"):
            conn.execute("""
                UPDATE monthly_usage_coeffs 
                SET coefficient = ?, confidence = 1.0 
                WHERE product_id=? AND ingredient_id=? AND month=?
            """, (custom, row["product_id"], row["ingredient_id"], selected_month))
            conn.commit()
            st.success("Updated!")
            st.rerun()

st.markdown("---")
st.info("💡 Adjustments are automatically applied to next month's purchase orders. Confidence < 0.5? Bake more to improve accuracy.")

conn.close()