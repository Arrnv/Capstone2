import pandas as pd
import joblib

# Load model
model = joblib.load('best_model.joblib')

# Define input as dict (replace these values as needed)
input_data = {
    'record_ID': 1,
    'week': '17/01/11',
    'store_id': 8091,
    'sku_id': 216418,
    'total_price': 99.0375,
    'base_price': 111.8625,
    'is_featured_sku': 0,
    'is_display_sku': 0
}

# Convert to DataFrame
df_input = pd.DataFrame([input_data])

# Process 'week' into day, month, year
df_input[['day', 'month', 'year']] = df_input['week'].str.split('/', expand=True)

# Drop 'week' and 'record_ID'
df_input = df_input.drop(['week', 'record_ID'], axis=1)

# Cast day, month, year to numeric
df_input[['day', 'month', 'year']] = df_input[['day', 'month', 'year']].astype(int)

# Example → Columns during training
training_stores = [8091]  # replace with actual store IDs used in training
training_skus = [216418, 216419, 216425, 216233, 217390, 219009, 219029, 223245, 223153, 300021,
                 219844, 222087, 320485, 378934, 222765, 245387, 245338, 547934, 300291, 217217,
                 217777, 398721, 679023, 546789, 600934, 545621, 673209, 327492]

# One-hot encode 'store_id'
for store in training_stores:
    df_input[f'store_{store}'] = 1 if df_input['store_id'].iloc[0] == store else 0
df_input = df_input.drop('store_id', axis=1)

# One-hot encode 'sku_id'
for sku in training_skus:
    df_input[f'sku_{sku}'] = 1 if df_input['sku_id'].iloc[0] == sku else 0
df_input = df_input.drop('sku_id', axis=1)

# ⚠ Ensure all training columns are present
model_features = model.feature_names_in_ if hasattr(model, 'feature_names_in_') else list(df_input.columns)

for col in model_features:
    if col not in df_input.columns:
        df_input[col] = 0  # add missing columns as 0

# Reorder columns
df_input = df_input[model_features]

# Predict
prediction = model.predict(df_input)

print(f"Predicted units sold: {prediction[0]:.2f}")
