import streamlit as st
import pandas as pd
import psycopg2
import uuid
from datetime import datetime

st.set_page_config(page_title="Op-Art - მყიდველის შეკვეთები", page_icon="🛒", layout="wide")

# ==================== 🔐 ავტორიზაციის შემოწმება ====================
if "authenticated_orders" not in st.session_state:
    st.session_state["authenticated_orders"] = False

if not st.session_state["authenticated_orders"]:
    st.title("🔐 ავტორიზაცია - მყიდველის შეკვეთები")
    st.markdown("გთხოვთ შეიყვანოთ პაროლი ამ განყოფილებაში შესასვლელად.")

    password_input = st.text_input("პაროლი", type="password", key="orders_pass")

    if st.button("შესვლა", key="orders_login_btn"):
        if password_input == "Orders123":
            st.session_state["authenticated_orders"] = True
            st.success("პაროლი სწორია! იტვირთება სისტემა...")
            st.rerun()
        else:
            st.error("არასწორი პაროლი! სცადეთ თავიდან.")

    st.stop()
# ===================================================================

st.title("🛒 მყიდველის შეკვეთები და პროექტების მართვა")
st.markdown("---")

# PostgreSQL ბაზასთან კავშირი RMS ბაზის პარამეტრებით
DB_USER = "postgres"
DB_PASS = "123qweASD"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "RMS"


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        return None


def load_data():
    designers_df = pd.DataFrame()
    orders_df = pd.DataFrame(columns=["contract_base", "client_fullname", "phone", "email", "address"])
    rooms_df = pd.DataFrame(
        columns=["contract_base", "room_code", "furniture_type", "unit", "quantity", "unit_price", "total_price"])

    conn = get_db_connection()
    if conn is None:
        st.error("ვერ ხერხდება მონაცემთა ბაზასთან დაკავშირება. შეამოწმეთ PostgreSQL სერვერი.")
        return designers_df, orders_df, rooms_df

    try:
        designers_df = pd.read_sql("SELECT * FROM projects", con=conn)
    except Exception as e:
        pass

    try:
        orders_df = pd.read_sql("SELECT * FROM customer_orders", con=conn)
    except Exception as e:
        pass

    try:
        rooms_df = pd.read_sql("SELECT * FROM customer_order_rooms", con=conn)
    except Exception as e:
        pass

    finally:
        conn.close()

    return designers_df, orders_df, rooms_df


designers_data, orders_data, rooms_data = load_data()

if designers_data.empty:
    st.info("ℹ️ დიზაინერების მოდულიდან ჯერ არცერთი პროექტი არ არის გადმოცემული (ან 'projects' ცხრილი ცარიელია).")
else:
    # ---------------- 🔍 ფილტრაცია: ვტოვებთ მხოლოდ იმ პროექტებს, რომლებსაც აქვთ დაკონტრაქტება (ტირეიანი ნომრები) ----------------
    designers_data['root_contract'] = designers_data['contract_no'].astype(str).apply(lambda x: x.split('-')[0])

    # ვპოულობთ ყველა იმ root_contract-ს, რომელსაც აქვს მინიმუმ ერთი ქვე-ხელშეკრულება (მაგ: 261001-1)
    contract_has_subcontract = designers_data[designers_data['contract_no'].astype(str).str.contains('-')][
        'root_contract'].unique()

    # ვფილტრავთ ბაზას ისე, რომ აჩვენოს მხოლოდ დაკონტრაქტებული პროექტები
    active_contract_df = designers_data[designers_data['root_contract'].isin(contract_has_subcontract)].copy()

    if active_contract_df.empty:
        st.info(
            "ℹ️ ამ მომენტისთვის არცერთ დიზაინის პროექტზე არ არის გაფორმებული დაკონტრაქტება (ქვე-ხელშეკრულება). მყიდველის შეკვეთები გამოჩნდება მხოლოდ დაკონტრაქტების შექმნის შემდეგ.")
    else:
        # ---------------- 🔔 შეტყობინება შეუსრულებელი/ახალი დაკონტრაქტებული პროექტების შესახებ ----------------
        all_roots = active_contract_df['root_contract'].unique().tolist()

        unfilled_projects = []
        for root in all_roots:
            rooms_count = 0
            if not rooms_data.empty and 'contract_base' in rooms_data.columns:
                rooms_count = len(rooms_data[rooms_data['contract_base'] == root])

            if rooms_count == 0:
                unfilled_projects.append(root)

        if unfilled_projects:
            unfilled_str = ", ".join([f"**{p}**" for p in unfilled_projects])
            st.warning(
                f"⚠️ **ყურადღება:** შემდეგი დაკონტრაქტებული პროექტი / ხელშეკრულება(ები) საჭიროებს ოთახებისა და დეტალების შევსებას: {unfilled_str}")
        # ------------------------------------------------------------------------------------------------------

        st.subheader("📋 აქტიური დაკონტრაქტებული ხელშეკრულებების რეესტრი (მთავარი ნომრები)")

        grouped_summary = active_contract_df.groupby('root_contract').agg({
            'designer_name': 'first',
            'client_name': 'first',
            'product_type': 'first',
            'amount': 'sum'
        }).reset_index()

        grouped_summary.columns = ['ხელშეკრულების N', 'დიზაინერი', 'დამკვეთი', 'პროდუქციის ტიპი', 'ჯამური თანხა']
        grouped_summary.index = range(1, len(grouped_summary) + 1)

        styled_grouped = grouped_summary.style.format({
            'ჯამური თანხა': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
        }).set_properties(**{'text-align': 'left'})

        st.dataframe(styled_grouped, use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ შეკვეთის დეტალიზაცია და ოთახების ჩაშლა")

        root_contract_list = active_contract_df['root_contract'].unique().tolist()
        selected_contract = st.selectbox("აირჩიეთ ხელშეკრულების ძირითადი ნომერი:", root_contract_list)

        if selected_contract:
            sub_contracts = designers_data[designers_data['root_contract'] == selected_contract].copy()

            st.write(f"**არჩეული ხელშეკრულების ყველა კომპონენტი ({selected_contract}):**")

            cols_to_drop = ['id', 'saved_design_fee_pct', 'saved_commission_pct', 'root_contract']
            for col in cols_to_drop:
                if col in sub_contracts.columns:
                    sub_contracts = sub_contracts.drop(columns=[col])

            column_name_mapping = {
                'created_at': 'შექმნის თარიღი',
                'contract_type': 'ხელშეკრულების ტიპი',
                'contract_no': 'ხელშეკრულების №',
                'client_name': 'დამკვეთი',
                'amount': 'თანხა',
                'product_type': 'პროდუქციის ტიპი',
                'designer_name': 'დიზაინერი'
            }
            sub_contracts = sub_contracts.rename(columns=column_name_mapping)
            sub_contracts.index = range(1, len(sub_contracts) + 1)

            styled_sub_contracts = sub_contracts.style.format({
                'თანხა': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
            }, na_rep="-").set_properties(**{'text-align': 'left'})

            st.dataframe(styled_sub_contracts, use_container_width=True)

            sub_contracts_filtered = designers_data[(designers_data['root_contract'] == selected_contract) & (
                        designers_data['contract_type'] == "დაკონტრაქტება")]
            allowed_contract_amount = sub_contracts_filtered[
                'amount'].sum() if not sub_contracts_filtered.empty else 0.0

            st.info(
                f"💡 ამ ხელშეკრულების მიხედვით დასაკონტრაქტებელი (საწარმოო) ლიმიტი არის: **{allowed_contract_amount:,.2f} ₾** (დიზაინის თანხა გამოკლებულია)")

            default_client_name = ""
            match_designer_row = designers_data[designers_data['root_contract'] == selected_contract]
            if not match_designer_row.empty and 'client_name' in match_designer_row.columns:
                default_client_name = match_designer_row.iloc[0]['client_name']

            existing_client_fullname = default_client_name
            existing_phone = ""
            existing_email = ""
            existing_address = ""

            if not orders_data.empty and 'contract_base' in orders_data.columns:
                match_row = orders_data[orders_data['contract_base'] == selected_contract]
                if not match_row.empty:
                    if 'client_fullname' in match_row.columns and pd.notna(match_row.iloc[0]['client_fullname']):
                        existing_client_fullname = match_row.iloc[0]['client_fullname']
                    existing_phone = match_row.iloc[0]['phone'] if 'phone' in match_row.columns and pd.notna(
                        match_row.iloc[0]['phone']) else ""
                    existing_email = match_row.iloc[0]['email'] if 'email' in match_row.columns and pd.notna(
                        match_row.iloc[0]['email']) else ""
                    existing_address = match_row.iloc[0]['address'] if 'address' in match_row.columns and pd.notna(
                        match_row.iloc[0]['address']) else ""

            # დამკვეთისა და საკონტაქტო მონაცემები
            st.markdown(f"### დამკვეთისა და საკონტაქტო მონაცემები: {selected_contract}")
            col1, col2 = st.columns(2)
            with col1:
                manual_client_fullname = st.text_input("დამკვეთის სახელი და გვარი", value=existing_client_fullname,
                                                       key=f"client_fn_{selected_contract}")
                manual_phone = st.text_input("Tel (საკონტაქტო ნომერი)", value=existing_phone,
                                             key=f"phone_{selected_contract}")
            with col2:
                manual_email = st.text_input("E-mail", value=existing_email, key=f"email_{selected_contract}")
                manual_address = st.text_input("მისამართი", value=existing_address, key=f"addr_{selected_contract}")

            st.markdown("---")
            st.markdown("#### 🗄️ ოთახებისა და ქვე-პროექტების დეტალური ჩაშლა")

            # სესიის ინიციალიზაცია ოთახებისთვის
            session_key = f"rooms_list_{selected_contract}"
            if session_key not in st.session_state:
                if not rooms_data.empty and 'contract_base' in rooms_data.columns:
                    existing_rooms = rooms_data[rooms_data['contract_base'] == selected_contract]
                    if not existing_rooms.empty:
                        loaded_list = []
                        for _, r in existing_rooms.iterrows():
                            loaded_list.append({
                                "id": str(uuid.uuid4()),
                                "room_code": r.get("room_code", ""),
                                "furniture_type": r.get("furniture_type", ""),
                                "unit": r.get("unit", "კვ. მ."),
                                "quantity": float(r.get("quantity", 0.0)),
                                "unit_price": float(r.get("unit_price", 0.0))
                            })
                        st.session_state[session_key] = loaded_list
                    else:
                        st.session_state[session_key] = []
                else:
                    st.session_state[session_key] = []

            # ➕ ოთახის დამატების ღილაკი
            if st.button("➕ ოთახის / პროექტის დამატება", key=f"add_room_btn_{selected_contract}"):
                st.session_state[session_key].append({
                    "id": str(uuid.uuid4()),
                    "room_code": "",
                    "furniture_type": "",
                    "unit": "კვ. მ.",
                    "quantity": 0.0,
                    "unit_price": 0.0
                })
                st.rerun()

            updated_rooms = []
            row_to_delete = None
            total_rooms_amount = 0.0

            for i, room in enumerate(st.session_state[session_key]):
                row_id = room["id"]
                st.markdown(f"**ოთახი / პროექტი #{i + 1}**")
                rc_col, ft_col, un_col, qty_col, pr_col, tot_col, del_col = st.columns([2, 2, 1.3, 1, 1.3, 1.3, 0.8])

                rc_key = f"rc_{selected_contract}_{row_id}"
                ft_key = f"ft_{selected_contract}_{row_id}"
                un_key = f"un_{selected_contract}_{row_id}"
                qty_key = f"qty_{selected_contract}_{row_id}"
                pr_key = f"pr_{selected_contract}_{row_id}"

                if rc_key not in st.session_state:
                    st.session_state[rc_key] = room.get("room_code", "")
                if ft_key not in st.session_state:
                    st.session_state[ft_key] = room.get("furniture_type", "")
                if un_key not in st.session_state:
                    st.session_state[un_key] = room.get("unit", "კვ. მ.")
                if qty_key not in st.session_state:
                    st.session_state[qty_key] = float(room.get("quantity", 0.0))
                if pr_key not in st.session_state:
                    st.session_state[pr_key] = float(room.get("unit_price", 0.0))

                with rc_col:
                    r_code = st.text_input("ინდივიდუალური კოდი", key=rc_key)
                with ft_col:
                    f_type = st.text_input("ავეჯის ტიპი", key=ft_key)
                with un_col:
                    unit_opts = ["კვ. მ.", "გრძ. მ.", "ცალი"]
                    curr_unit = st.session_state[un_key]
                    u_idx = unit_opts.index(curr_unit) if curr_unit in unit_opts else 0
                    unit = st.selectbox("ერთეული", unit_opts, index=u_idx, key=un_key)
                with qty_col:
                    qty = st.number_input("რაოდენობა", min_value=0.0, step=1.0, format="%.2f", key=qty_key)
                with pr_col:
                    price = st.number_input("ერთ. ფასი (₾)", min_value=0.0, step=10.0, format="%.2f", key=pr_key)
                with tot_col:
                    total = qty * price
                    total_rooms_amount += total
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.metric("ჯამური (₾)", f"{total:,.2f}")
                with del_col:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ წაშლა", key=f"del_{selected_contract}_{row_id}"):
                        row_to_delete = row_id

                updated_rooms.append({
                    "id": row_id,
                    "room_code": r_code,
                    "furniture_type": f_type,
                    "unit": unit,
                    "quantity": qty,
                    "unit_price": price,
                    "total_price": total
                })
                st.markdown("---")

            if row_to_delete is not None:
                st.session_state[session_key] = [r for r in st.session_state[session_key] if r["id"] != row_to_delete]
                for k in [f"rc_{selected_contract}_{row_to_delete}", f"ft_{selected_contract}_{row_to_delete}",
                          f"un_{selected_contract}_{row_to_delete}", f"qty_{selected_contract}_{row_to_delete}",
                          f"pr_{selected_contract}_{row_to_delete}"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

            remaining_amount = allowed_contract_amount - total_rooms_amount

            st.markdown(
                f"**ოთახების ჯამური ღირებულება:** `{total_rooms_amount:,.2f} ₾` / **დასაშვები ლიმიტი:** `{allowed_contract_amount:,.2f} ₾` / **ასათვისებელი დარჩენილი თანხა:** `{remaining_amount:,.2f} ₾`")

            # შენახვის ღილაკი
            if st.button("💾 ცვლილებების შენახვა ბაზაში", key=f"save_btn_{selected_contract}"):
                if allowed_contract_amount > 0 and total_rooms_amount > allowed_contract_amount:
                    st.error(
                        f"❌ შეცდომა: ოთახების ჯამური თანხა ({total_rooms_amount:,.2f} ₾) აჭარბებს დაკონტრაქტების ლიმიტს ({allowed_contract_amount:,.2f} ₾)!")
                else:
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()

                            cursor.execute("""
                                CREATE TABLE IF NOT EXISTS customer_orders (
                                    contract_base VARCHAR(50) PRIMARY KEY,
                                    client_fullname VARCHAR(255),
                                    phone VARCHAR(50),
                                    email VARCHAR(100),
                                    address TEXT
                                );
                            """)

                            cursor.execute("""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name='customer_orders' and column_name='client_fullname';
                            """)
                            if not cursor.fetchone():
                                cursor.execute("ALTER TABLE customer_orders ADD COLUMN client_fullname VARCHAR(255);")
                                conn.commit()

                            cursor.execute("""
                                CREATE TABLE IF NOT EXISTS customer_order_rooms (
                                    id SERIAL PRIMARY KEY,
                                    contract_base VARCHAR(50),
                                    room_code VARCHAR(100),
                                    furniture_type VARCHAR(255),
                                    unit VARCHAR(50),
                                    quantity NUMERIC,
                                    unit_price NUMERIC,
                                    total_price NUMERIC
                                );
                            """)

                            cursor.execute("SELECT COUNT(*) FROM customer_orders WHERE contract_base = %s",
                                           (selected_contract,))
                            if cursor.fetchone()[0] > 0:
                                cursor.execute("""
                                    UPDATE customer_orders 
                                    SET client_fullname = %s, phone = %s, email = %s, address = %s 
                                    WHERE contract_base = %s
                                """, (manual_client_fullname, manual_phone, manual_email, manual_address,
                                      selected_contract))
                            else:
                                cursor.execute("""
                                    INSERT INTO customer_orders (contract_base, client_fullname, phone, email, address)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (selected_contract, manual_client_fullname, manual_phone, manual_email,
                                      manual_address))

                            cursor.execute("DELETE FROM customer_order_rooms WHERE contract_base = %s",
                                           (selected_contract,))
                            for r in updated_rooms:
                                cursor.execute("""
                                    INSERT INTO customer_order_rooms (contract_base, room_code, furniture_type, unit, quantity, unit_price, total_price)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, (selected_contract, r['room_code'], r['furniture_type'], r['unit'], r['quantity'],
                                      r['unit_price'], r['total_price']))

                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success("✅ დამკვეთისა და ოთახების დეტალური მონაცემები წარმატებით შეინახა ბაზაში!")
                        except Exception as ex:
                            st.error(f"შეცდომა შენახვისას: {ex}")
                    else:
                        st.error("ბაზასთან კავშირი ვერ მოხერხდა.")