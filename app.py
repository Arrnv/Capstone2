"""
{
  "record_ID": 1,
  "week": "2022/10/31",
  "store_id": 8091,
  "sku_id": 216425,
  "total_price": 199.99,
  "base_price": 150.0,
  "is_featured_sku": 1,
  "is_display_sku": 1
}

"""
import streamlit as st
import sqlite3
import pandas as pd
import joblib
from streamlit_option_menu import option_menu
import plotly.express as px
from datetime import datetime
# Load the pre-trained model
model = joblib.load('best_model.joblib')

# SQLite connection setup
def get_db_connection():
    conn = sqlite3.connect('my_inventory.db') 
    conn.row_factory = sqlite3.Row  
    return conn

# Function to check stock
def check_stock(input_data):
    df_input = pd.DataFrame([input_data])

    df_input[['day', 'month', 'year']] = df_input['week'].str.split('/', expand=True)
    df_input = df_input.drop(['week', 'record_ID'], axis=1)
    df_input[['day', 'month', 'year']] = df_input[['day', 'month', 'year']].astype(int)

    # List of stores and SKUs (just placeholders for now)
    training_stores = [
        8091, 8095, 8094, 8063, 8023, 8058, 8222, 8121, 8218, 8317,
        8319, 8392, 8398, 8400, 8422, 8438, 8555, 8562, 8869, 8991,
        8911, 9001, 9043, 9092, 9112, 9132, 9147, 9164, 9178, 9190,
        9221, 9250, 9273, 9279, 9281, 9328, 9371, 9442, 9430, 9439,
        9425, 9432, 9436, 9456, 9479, 9481, 9490, 9498, 9532, 9578,
        9672, 9611, 9613, 9632, 9680, 9700, 9713, 9731, 9745, 9770,
        9789, 9813, 9823, 9837, 9809, 9845, 9872, 9876, 9879, 9880,
        9881, 9890, 9909, 9954, 9961, 9984
    ]
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

    model_features = ['day', 'month', 'year'] + [f'store_{store}' for store in training_stores] + [f'sku_{sku}' for sku in training_skus]

    # Ensure all required columns are present
    for col in model_features:
        if col not in df_input.columns:
            df_input[col] = 0  # add missing columns as 0

    # Reorder columns
    df_input = df_input[model_features]

    # Predict (dummy prediction for now)
    predicted_units = float(input_data['total_price']) * 0.1  # Placeholder prediction formula

    # Extract sku_id and store_id from input_data
    sku_id = input_data['sku_id']
    store_id = input_data['store_id']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT current_stock, last_updated FROM inventory WHERE product_id = ?', (sku_id,))
        row = cursor.fetchone()

        if row is None:
            return {"message": f"Product with SKU {sku_id} not found in inventory"}

        current_stock = row[0]
        last_updated = row[1]

        units_to_send = min(predicted_units, current_stock)
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if units_to_send > 0:
            new_stock = current_stock - units_to_send
            cursor.execute('UPDATE inventory SET current_stock = ?, last_updated = ? WHERE product_id = ?', (new_stock, current_timestamp, sku_id))
            conn.commit()

            log_data = {
                "store_id": store_id,
                "sku_id": sku_id,
                "units_sent": units_to_send,
                "timestamp": current_timestamp,
                "action": "Forwarded to store"
            }
            log_to_db(log_data)

            return {
                "product_id": sku_id,
                "store_id": store_id,
                "predicted_units_sold": predicted_units,
                "units_sent": units_to_send,
                "new_stock": new_stock,
                "last_updated": current_timestamp
            }
        else:
            new_stock = current_stock * 2
            cursor.execute('UPDATE inventory SET current_stock = ?, last_updated = ? WHERE product_id = ?', (new_stock, current_timestamp, sku_id))
            conn.commit()

            log_data = {
                "store_id": store_id,
                "sku_id": sku_id,
                "units_sent": 0,
                "timestamp": current_timestamp,
                "action": "Stock doubled automatically"
            }
            log_to_db(log_data)

            return {
                "product_id": sku_id,
                "store_id": store_id,
                "predicted_units_sold": predicted_units,
                "units_sent": 0,
                "new_stock": new_stock,
                "last_updated": current_timestamp,
                "message": "Stock was insufficient; inventory doubled automatically."
            }

    except sqlite3.Error as e:
        return {"message": f"Database error: {e}"}
    finally:
        conn.close()

# Function to log actions to a log table in DB
def log_to_db(log_data):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_logs (
                store_id INTEGER,
                sku_id INTEGER,
                units_sent INTEGER,
                timestamp TEXT,
                action TEXT
            )
        ''')

        cursor.execute('''
            INSERT INTO stock_logs (store_id, sku_id, units_sent, timestamp, action)
            VALUES (?, ?, ?, ?, ?)
        ''', (log_data['store_id'], log_data['sku_id'], log_data['units_sent'], log_data['timestamp'], log_data['action']))
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

# Streamlit app setup
st.title("Inventory Management System")
st.sidebar.header("Product Information")

# Input form for user to submit
product_form = st.sidebar.form(key="input_form")
record_ID = product_form.number_input("Record ID", min_value=1)
week = product_form.text_input("Week (in MM/DD/YYYY format)", value="01/01/2025")
store_id = product_form.number_input("Store ID", min_value=1)
sku_id = product_form.number_input("SKU ID", min_value=1)
total_price = product_form.number_input("Total Price", min_value=0.0)
base_price = product_form.number_input("Base Price", min_value=0.0)
is_featured_sku = product_form.number_input("Is Featured SKU", min_value=0, max_value=1)
is_display_sku = product_form.number_input("Is Display SKU", min_value=0, max_value=1)

submit_button = product_form.form_submit_button("Check Stock")

if submit_button:
    input_data = {
        "record_ID": record_ID,
        "week": week,
        "store_id": store_id,
        "sku_id": sku_id,
        "total_price": total_price,
        "base_price": base_price,
        "is_featured_sku": is_featured_sku,
        "is_display_sku": is_display_sku
    }

    result = check_stock(input_data)

    # Display the results dynamically
    st.subheader("Prediction and Stock Update Results")
    if "message" in result:
        st.warning(result["message"])
    else:
        st.write(f"**Predicted Units Sold**: {result['predicted_units_sold']:.2f}")
        st.write(f"**Units Sent to Store**: {result['units_sent']:.2f}")
        st.write(f"**New Stock**: {result['new_stock']:.2f}")
        st.write(f"**Last Updated**: {result['last_updated']}")

        # Plotting stock changes
        fig, ax = plt.subplots()
        ax.bar(["Before", "After"], [result['predicted_units_sold'], result['new_stock']])
        ax.set_title(f"Stock Changes for SKU {result['product_id']} at Store {result['store_id']}")
        ax.set_ylabel("Stock")
        st.pyplot(fig)

    # Fetch logs from the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stock_logs ORDER BY timestamp DESC')
    logs = cursor.fetchall()

    # Display logs as a table
    if logs:
        logs_df = pd.DataFrame(logs, columns=["Store ID", "SKU ID", "Units Sent", "Timestamp", "Action"])
        st.subheader("Action Logs")
        st.dataframe(logs_df)

        # Display a chart for units sent
        units_sent_df = logs_df.groupby('Store ID')['Units Sent'].sum().reset_index()
        st.subheader("Units Sent per Store")
        st.bar_chart(units_sent_df.set_index('Store ID')['Units Sent'])
    else:
        st.write("No logs available.")



# --- NAVIGATION TABS ---
# -------------- NAVBAR --------------
page = option_menu(
    "Navigation",
    ["Dashboard", "Manage Products", "Change History"],
    icons=["house", "box-seam", "clock-history"],
    menu_icon="cast",
    default_index=0,
)

# =================== DASHBOARD PAGE ===================

st.title("📦 Inventory Management System")

# ==========================
# DASHBOARD PAGE
# ==========================
if page == "Dashboard":
    if st.button("Show Inventory Dashboard"):
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT product_id, product_name, current_stock, last_updated FROM inventory')
            rows = cursor.fetchall()

            data = []
            for row in rows:
                data.append({
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "current_stock": row["current_stock"],
                    "last_updated": row["last_updated"]
                })

            df_inventory = pd.DataFrame(data)

            if df_inventory.empty:
                st.warning("No inventory data found.")
            else:
                st.subheader("📋 Inventory Table")
                st.dataframe(df_inventory)

                st.markdown("---")
                st.subheader("📊 Dashboard Visualizations")

                col1, col2 = st.columns(2)

                with col1:
                    pie_fig = px.pie(df_inventory, values='current_stock', names='product_name', title='Stock Distribution')
                    st.plotly_chart(pie_fig, use_container_width=True)

                with col2:
                    bar_fig = px.bar(df_inventory, x='product_name', y='current_stock', title='Current Stock by Product')
                    st.plotly_chart(bar_fig, use_container_width=True)

                col3, col4 = st.columns(2)

                with col3:
                    hist_fig = px.histogram(df_inventory, x='current_stock', nbins=10, title='Histogram of Stock Levels')
                    st.plotly_chart(hist_fig, use_container_width=True)

                with col4:
                    box_fig = px.box(df_inventory, y='current_stock', points="all", title='Stock Outlier Detection')
                    st.plotly_chart(box_fig, use_container_width=True)

                col5, col6 = st.columns(2)

                with col5:
                    treemap_fig = px.treemap(df_inventory, path=['product_name'], values='current_stock', title='Treemap Inventory')
                    st.plotly_chart(treemap_fig, use_container_width=True)

                with col6:
                    sunburst_fig = px.sunburst(df_inventory, path=['product_name'], values='current_stock', title='Sunburst Inventory')
                    st.plotly_chart(sunburst_fig, use_container_width=True)

                st.markdown("---")

                st.subheader("🔍 Compare Up to 3 Products")
                product_options = df_inventory['product_name'].tolist()
                selected_products = st.multiselect("Select up to 3 products to compare:", product_options, max_selections=3)

                if selected_products:
                    df_selected = df_inventory[df_inventory['product_name'].isin(selected_products)]

                    compare_col1, compare_col2 = st.columns(2)

                    with compare_col1:
                        compare_fig = px.bar(
                            df_selected,
                            x='product_name',
                            y='current_stock',
                            text='current_stock',
                            title='Selected Products Stock Comparison',
                            color='product_name'
                        )
                        st.plotly_chart(compare_fig, use_container_width=True)

                    with compare_col2:
                        pie_selected_fig = px.pie(
                            df_selected,
                            names='product_name',
                            values='current_stock',
                            title='Stock Distribution (Selected Products)'
                        )
                        st.plotly_chart(pie_selected_fig, use_container_width=True)

                    if df_selected['last_updated'].notnull().all():
                        df_selected['last_updated_dt'] = pd.to_datetime(df_selected['last_updated'])
                        line_fig = px.line(
                            df_selected,
                            x='last_updated_dt',
                            y='current_stock',
                            title='Stock Change Over Time (Last Updated)',
                            markers=True
                        )
                        st.plotly_chart(line_fig, use_container_width=True)
                    else:
                        st.info("No valid 'last_updated' timestamp data to plot stock over time.")
        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
        finally:
            conn.close()






elif page == "Manage Products":
    st.header("🛠️ Manage Products")

    action = st.radio("Select Action:", ["Add Product", "Rename Product", "Delete Product", "Update Stock"])

    if action == "Add Product":
        product_name = st.text_input("Product Name:")
        current_stock = st.number_input("Initial Stock:", min_value=0, value=0)
        if st.button("Add Product"):
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO inventory (product_name, current_stock) VALUES (?, ?)",
                               (product_name, current_stock))
                conn.commit()
                st.success(f"✅ Product '{product_name}' added successfully!")

                # Log change
                cursor.execute("""
                    INSERT INTO stock_changes (product_id, product_name, action, change_detail)
                    VALUES (?, ?, ?, ?)
                """, (cursor.lastrowid, product_name, "Added", f"Initial stock: {current_stock}"))
                conn.commit()
            except sqlite3.Error as e:
                st.error(f"Database error: {e}")
            finally:
                conn.close()

    elif action == "Rename Product":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {row["product_name"]: row["product_id"] for row in products}
        if product_dict:
            selected_product = st.selectbox("Select Product to Rename:", list(product_dict.keys()))
            new_name = st.text_input("New Product Name:")

            if st.button("Rename Product"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("UPDATE inventory SET product_name = ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ?",
                                   (new_name, product_dict[selected_product]))
                    conn.commit()
                    st.success(f"✅ Product renamed to '{new_name}' successfully!")

                    # Log change
                    cursor.execute("""
                        INSERT INTO stock_changes (product_id, product_name, action, change_detail)
                        VALUES (?, ?, ?, ?)
                    """, (product_dict[selected_product], new_name, "Renamed",
                          f"Old name: {selected_product}, New name: {new_name}"))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to rename.")

    elif action == "Delete Product":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {row["product_name"]: row["product_id"] for row in products}
        if product_dict:
            selected_product = st.selectbox("Select Product to Delete:", list(product_dict.keys()))

            if st.button("Delete Product"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("DELETE FROM inventory WHERE product_id = ?", (product_dict[selected_product],))
                    conn.commit()
                    st.success(f"🗑️ Product '{selected_product}' deleted successfully!")

                    # Log change
                    cursor.execute("""
                        INSERT INTO stock_changes (product_id, product_name, action, change_detail)
                        VALUES (?, ?, ?, ?)
                    """, (product_dict[selected_product], selected_product, "Deleted", "Product deleted"))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to delete.")

    elif action == "Update Stock":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name, current_stock FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {f"{row['product_name']} (Current: {row['current_stock']})": (row["product_id"], row["current_stock"]) for row in products}
        if product_dict:
            selected_product_display = st.selectbox("Select Product to Update Stock:", list(product_dict.keys()))
            selected_product_id, old_stock = product_dict[selected_product_display]
            new_stock = st.number_input("New Stock Value:", min_value=0, value=old_stock)

            if st.button("Update Stock"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("UPDATE inventory SET current_stock = ?, last_updated = CURRENT_TIMESTAMP WHERE product_id = ?",
                                   (new_stock, selected_product_id))
                    conn.commit()
                    st.success(f"✅ Stock for '{selected_product_display}' updated to {new_stock}!")

                    # Log change
                    cursor.execute("""
                        INSERT INTO stock_changes (product_id, product_name, action, change_detail)
                        VALUES (?, ?, ?, ?)
                    """, (selected_product_id, selected_product_display.split(' (')[0], "Updated Stock",
                          f"Stock changed from {old_stock} to {new_stock}"))
                    conn.commit()
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to update.")

# =================== CHANGE HISTORY PAGE ===================
elif page == "Change History":
    st.header("📜 Change History")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT change_time, product_name, action, change_detail
        FROM stock_changes
        ORDER BY change_time DESC
    """)
    changes = cursor.fetchall()
    conn.close()

    if changes:
        df_changes = pd.DataFrame(changes, columns=["Time", "Product Name", "Action", "Detail"])
        st.dataframe(df_changes)
    else:
        st.info("No changes logged yet.")

    st.header("🛠️ Manage Products")

    action = st.radio("Select Action:", ["Add Product", "Rename Product", "Delete Product", "Update Stock"])

    if action == "Add Product":
        product_name = st.text_input("Product Name:")
        current_stock = st.number_input("Initial Stock:", min_value=0, value=0)
        if st.button("Add Product"):
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO inventory (product_name, current_stock, last_updated) VALUES (?, ?, datetime('now'))",
                    (product_name, current_stock))
                conn.commit()
                st.success(f"✅ Product '{product_name}' added successfully!")
            except sqlite3.Error as e:
                st.error(f"Database error: {e}")
            finally:
                conn.close()

    elif action == "Rename Product":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {row["product_name"]: row["product_id"] for row in products}
        if product_dict:
            selected_product = st.selectbox("Select Product to Rename:", list(product_dict.keys()))
            new_name = st.text_input("New Product Name:")

            if st.button("Rename Product"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE inventory SET product_name = ? WHERE product_id = ?",
                        (new_name, product_dict[selected_product]))
                    conn.commit()
                    st.success(f"✅ Product renamed to '{new_name}' successfully!")
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to rename.")

    elif action == "Delete Product":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {row["product_name"]: row["product_id"] for row in products}
        if product_dict:
            selected_product = st.selectbox("Select Product to Delete:", list(product_dict.keys()))

            if st.button("Delete Product"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("DELETE FROM inventory WHERE product_id = ?", (product_dict[selected_product],))
                    conn.commit()
                    st.success(f"🗑️ Product '{selected_product}' deleted successfully!")
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to delete.")

    elif action == "Update Stock":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name, current_stock FROM inventory")
        products = cursor.fetchall()
        conn.close()

        product_dict = {f"{row['product_name']} (Current: {row['current_stock']})": row["product_id"] for row in products}
        if product_dict:
            selected_product_display = st.selectbox("Select Product to Update Stock:", list(product_dict.keys()))
            new_stock = st.number_input("New Stock Value:", min_value=0, value=0)

            if st.button("Update Stock"):
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE inventory SET current_stock = ?, last_updated = datetime('now') WHERE product_id = ?",
                        (new_stock, product_dict[selected_product_display]))
                    conn.commit()
                    st.success(f"📦 Stock updated to {new_stock} for '{selected_product_display.split(' (')[0]}'!")
                except sqlite3.Error as e:
                    st.error(f"Database error: {e}")
                finally:
                    conn.close()
        else:
            st.info("No products available to update.")