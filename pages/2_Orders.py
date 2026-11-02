import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import psycopg2
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

st.set_page_config(page_title="Op-Art - მყიდველის შეკვეთები", page_icon="🛒", layout="wide")

# ==================== 🔐 ავტორიზაციის შემოწმება ====================
if "authenticated_orders" not in st.session_state:
    st.session_state["authenticated_orders"] = False

if not st.session_state["authenticated_orders"]:
    st.title("🔐 ავტორიზაცია - მყიდველის შეკვეთები")
    st.markdown("გთხოვთ შეიყვანოთ პაროლი ამ განყოფილებაში შესასვლელად.")

    password_input = st.text_input("პაროლი", type="password", key="orders_pass")

    if st.button("შესვლა", key="orders_login_btn"):
        try:
            expected_password = st.secrets["ORDERS_PASSWORD"]
        except Exception:
            st.error("Secrets-ში ORDERS_PASSWORD არ არის ჩაწერილი.")
            st.stop()

        if password_input == expected_password:
            st.session_state["authenticated_orders"] = True
            st.success("პაროლი სწორია! იტვირთება სისტემა...")
            st.rerun()
        else:
            st.error("არასწორი პაროლი! სცადეთ თავიდან.")

    st.stop()
# ===================================================================

st.title("🛒 მყიდველის შეკვეთები და პროექტების მართვა")
st.markdown("---")

# ---------------- ⚙️ პარამეტრები ----------------
ALERT_DAYS = 10  # რამდენი დღით ადრე დაიწყოს ჩაბარების ვადის შეტყობინება
STATUS_DONE = "დასრულებული"
STATUS_ONGOING = "მიმდინარე"
TODAY = datetime.now(ZoneInfo("Asia/Tbilisi")).date()

# ---------------- 🗄️ ბაზასთან კავშირი (Supabase, secrets-იდან) ----------------
db_url = st.secrets["db"]["url"]
engine = create_engine(db_url, pool_pre_ping=True)
_u = make_url(db_url)
DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME = (
    _u.username, _u.password, _u.host, _u.port, _u.database
)


def get_db_connection():
    try:
        return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT)
    except Exception as e:
        st.error(f"ბაზასთან კავშირი ვერ მოხერხდა: {e}")
        return None


def ensure_tables():
    conn = get_db_connection()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_orders (
                contract_base VARCHAR(50) PRIMARY KEY,
                client_fullname VARCHAR(255),
                phone VARCHAR(50),
                email VARCHAR(100),
                address TEXT
            );
        """)
        cur.execute("ALTER TABLE customer_orders ADD COLUMN IF NOT EXISTS client_fullname VARCHAR(255);")
        cur.execute("""
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
        conn.commit()
        cur.close()
    except Exception as e:
        st.error(f"ცხრილების შემოწმების შეცდომა: {e}")
    finally:
        conn.close()


PROJECT_COLUMNS = (
    "id, project_status, contract_type, contract_no, project_category, client_name, amount, product_type, "
    "designer_name, created_at, project_source, delivery_date_str, outsource_designer_name, "
    "outsource_contract_no, outsource_commission_pct, outsource_installments, contract_file_name, "
    "(contract_file_data IS NOT NULL) AS has_file"
)


def load_data():
    ensure_tables()
    projects_df = pd.DataFrame()
    orders_df = pd.DataFrame(columns=["contract_base", "client_fullname", "phone", "email", "address"])
    rooms_df = pd.DataFrame(
        columns=["contract_base", "room_code", "furniture_type", "unit", "quantity", "unit_price", "total_price"])

    try:
        projects_df = pd.read_sql(f"SELECT {PROJECT_COLUMNS} FROM projects ORDER BY created_at", con=engine)
    except Exception:
        # დიზაინერების გვერდს ახალი ველები ჯერ რომ არ დაუმატებია, სრული ცხრილი (ფაილის გარეშე) ავიღოთ
        try:
            projects_df = pd.read_sql("SELECT * FROM projects ORDER BY created_at", con=engine)
            projects_df = projects_df.drop(columns=['contract_file_data'], errors='ignore')
        except Exception as e:
            st.error(f"პროექტების წაკითხვის შეცდომა: {e}")

    try:
        orders_df = pd.read_sql("SELECT * FROM customer_orders", con=engine)
    except Exception as e:
        st.error(f"შეკვეთების წაკითხვის შეცდომა: {e}")

    try:
        rooms_df = pd.read_sql("SELECT * FROM customer_order_rooms ORDER BY id", con=engine)
    except Exception as e:
        st.error(f"პროდუქტების წაკითხვის შეცდომა: {e}")

    return projects_df, orders_df, rooms_df


# ---------------- 🧰 დამხმარე ფუნქციები ----------------
def _txt(v):
    return "" if v is None or pd.isnull(v) else str(v)


def parse_delivery(s):
    """დიზაინერების გვერდზე თარიღი ინახება როგორც '20 Feb, 2027'."""
    s = _txt(s).strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%d %b, %Y").date()
    except ValueError:
        return None


def is_valid_code(v):
    return re.fullmatch(r"\d{6}", _txt(v).strip()) is not None


def build_root_summary(projects):
    """თითო მთავარი ხელშეკრულებისთვის: სტატუსი, ჩაბარების ვადა და ა.შ."""
    rows = []
    for root, g in projects.groupby('root_contract', sort=False):
        # ვადა და სტატუსი ითვლება დაკონტრაქტების ჩანაწერებით (თუ არსებობს)
        contract_rows = g[g['contract_type'] == "დაკონტრაქტება"]
        base = contract_rows if not contract_rows.empty else g

        if 'delivery_date_str' in base.columns:
            dates = [d for d in base['delivery_date_str'].apply(parse_delivery) if d is not None]
        else:
            dates = []
        deadline = min(dates) if dates else None

        statuses = base['project_status'] if 'project_status' in base.columns else pd.Series([STATUS_ONGOING])
        done = bool((statuses.fillna(STATUS_ONGOING) == STATUS_DONE).all())

        first = g.iloc[0]
        rows.append({
            "root": root,
            "designer": _txt(first.get('designer_name')),
            "client": _txt(first.get('client_name')),
            "product": _txt(first.get('product_type')),
            "source": _txt(first.get('project_source')) or "Op-Art",
            "category": _txt(first.get('project_category')),
            "amount": g['amount'].sum(),
            "done": done,
            "deadline": deadline,
            "days_left": (deadline - TODAY).days if (deadline and not done) else None,
        })
    return rows


# ---------------- 📥 მონაცემების ჩატვირთვა ----------------
designers_data, orders_data, rooms_data = load_data()

if designers_data.empty:
    st.info("ℹ️ დიზაინერების მოდულიდან ჯერ არცერთი პროექტი არ არის გადმოცემული (ან 'projects' ცხრილი ცარიელია).")
else:
    if 'project_status' in designers_data.columns:
        designers_data['project_status'] = designers_data['project_status'].fillna(STATUS_ONGOING)
    else:
        designers_data['project_status'] = STATUS_ONGOING

    # ---------------- 🔍 ფილტრაცია: მხოლოდ დაკონტრაქტებული პროექტები (ტირეიანი ნომრები) ----------------
    designers_data['root_contract'] = designers_data['contract_no'].astype(str).apply(lambda x: x.split('-')[0])

    # ყველა root_contract, რომელსაც აქვს მინიმუმ ერთი ჩანაწერი ტიპით "დაკონტრაქტება"
    contract_has_subcontract = designers_data[designers_data['contract_type'] == "დაკონტრაქტება"][
        'root_contract'].unique()

    active_contract_df = designers_data[designers_data['root_contract'].isin(contract_has_subcontract)].copy()

    if active_contract_df.empty:
        st.info(
            "ℹ️ ამ მომენტისთვის არცერთ დიზაინის პროექტზე არ არის გაფორმებული დაკონტრაქტება (ქვე-ხელშეკრულება). მყიდველის შეკვეთები გამოჩნდება მხოლოდ დაკონტრაქტების შექმნის შემდეგ.")
    else:
        root_rows = build_root_summary(active_contract_df)
        all_roots = [r["root"] for r in root_rows]
        client_by_root = {r["root"]: r["client"] for r in root_rows}

        # ---------------- ⏰ ჩაბარების ვადის შეტყობინება (10 დღით ადრე) ----------------
        due_soon = [r for r in root_rows if r["days_left"] is not None and r["days_left"] <= ALERT_DAYS]
        due_soon.sort(key=lambda r: r["deadline"])
        if due_soon:
            lines = []
            for r in due_soon:
                d = r["days_left"]
                date_txt = r["deadline"].strftime("%d.%m.%Y")
                who = f"**{r['root']}** ({r['client']})" if r["client"] else f"**{r['root']}**"
                if d < 0:
                    lines.append(f"🔴 {who}: ჩაბარების ვადა **გადაცილებულია {-d} დღით** ({date_txt})")
                elif d == 0:
                    lines.append(f"🔴 {who}: ჩაბარების ვადა **დღეს არის** ({date_txt})")
                else:
                    lines.append(f"🟠 {who}: ჩაბარებამდე დარჩენილია **{d} დღე** ({date_txt})")
            msg = f"⏰ **ჩაბარების ვადის შეხსენება** ({ALERT_DAYS} დღით ადრე):\n\n" + "\n\n".join(lines)
            if min(r["days_left"] for r in due_soon) <= 0:
                st.error(msg)
            else:
                st.warning(msg)

        # ---------------- 🔢 6-ნიშნა კოდის შემოწმება ----------------
        invalid_codes = {}
        if not rooms_data.empty and 'contract_base' in rooms_data.columns:
            for root in all_roots:
                rr = rooms_data[rooms_data['contract_base'] == root]
                if rr.empty:
                    continue
                bad_count = int((~rr['room_code'].apply(is_valid_code)).sum())
                if bad_count:
                    invalid_codes[root] = bad_count

        if invalid_codes:
            code_lines = ", ".join([f"**{root}** ({cnt} პროდუქტი)" for root, cnt in invalid_codes.items()])
            st.error(
                f"🔢 **6-ნიშნა ინდივიდუალური კოდი ჩაწერილი არ არის** (ან არ არის 6 ციფრი) შემდეგ ხელშეკრულებებზე. "
                f"გთხოვთ ჩაწეროთ: {code_lines}")

        # ---------------- 🔔 შეუვსებელი პროდუქტები ----------------
        unfilled_projects = []
        for root in all_roots:
            rooms_count = 0
            if not rooms_data.empty and 'contract_base' in rooms_data.columns:
                rooms_count = len(rooms_data[rooms_data['contract_base'] == root])
            if rooms_count == 0:
                unfilled_projects.append(root)

        if unfilled_projects:
            unfilled_str = ", ".join([f"**{p}**" for p in unfilled_projects])
            st.error(
                f"🔢 **6-ნიშნა კოდი ჩაწერილი არ არის!** შემდეგ ხელშეკრულებებზე პროდუქტები ჯერ არ არის ჩაშლილი. "
                f"გთხოვთ ჩაშალოთ პროდუქტებად და თითოეულს ჩაუწეროთ 6-ნიშნა კოდი (მაგ. 001546): {unfilled_str}")

        # ---------------- 📋 რეესტრი ----------------
        st.subheader("📋 აქტიური დაკონტრაქტებული ხელშეკრულებების რეესტრი (მთავარი ნომრები)")

        grouped_summary = pd.DataFrame([{
            'ხელშეკრულების N': r["root"],
            'სტატუსი': "✅ დასრულებული" if r["done"] else "🛠️ მიმდინარე",
            'დიზაინერი': r["designer"],
            'დამკვეთი': r["client"],
            'პროდუქციის ტიპი': r["product"],
            'პროექტის წყარო': r["source"],
            'კატეგორია': r["category"],
            'ჩაბარების ვადა': r["deadline"].strftime("%d.%m.%Y") if r["deadline"] else "-",
            'დარჩენილი დღე': r["days_left"] if r["days_left"] is not None else "-",
            'ჯამური თანხა': r["amount"],
        } for r in root_rows])
        grouped_summary.index = range(1, len(grouped_summary) + 1)

        styled_grouped = grouped_summary.style.format({
            'ჯამური თანხა': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
        }).set_properties(**{'text-align': 'left'})

        st.dataframe(styled_grouped, use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ შეკვეთის დეტალიზაცია და პროდუქტების დეტალური ჩაშლა")

        selected_contract = st.selectbox("აირჩიეთ ხელშეკრულების ძირითადი ნომერი:", all_roots)

        if selected_contract:
            sub_contracts = designers_data[designers_data['root_contract'] == selected_contract].copy()

            st.write(f"**არჩეული ხელშეკრულების ყველა კომპონენტი ({selected_contract}):**")

            sub_contracts['status_display'] = sub_contracts['project_status'].apply(
                lambda x: "✅ დასრულებული" if x == STATUS_DONE else "🛠️ მიმდინარე")
            sub_contracts['file_display'] = sub_contracts['has_file'].apply(
                lambda x: "✅ ატვირთულია" if x else "❌ არ არის") if 'has_file' in sub_contracts.columns else "-"

            detail_columns = [
                ('status_display', 'სტატუსი'),
                ('created_at', 'შექმნის თარიღი'),
                ('project_source', 'პროექტის წყარო'),
                ('contract_type', 'ხელშეკრულების ტიპი'),
                ('contract_no', 'ხელშეკრულების №'),
                ('project_category', 'პროექტის კატეგორია'),
                ('client_name', 'დამკვეთი'),
                ('product_type', 'პროდუქციის ტიპი'),
                ('amount', 'თანხა'),
                ('designer_name', 'დიზაინერი'),
                ('delivery_date_str', 'ჩაბარების თარიღი'),
                ('outsource_designer_name', 'Outsource დიზაინერი'),
                ('outsource_contract_no', 'Outsource ხელშეკრულების №'),
                ('outsource_commission_pct', 'Outsource საკომისიო'),
                ('outsource_installments', 'ნაწილების რ-ბა'),
                ('file_display', 'ფაილი'),
            ]
            detail_columns = [(src, dst) for src, dst in detail_columns if src in sub_contracts.columns]
            sub_view = sub_contracts[[src for src, _ in detail_columns]].copy()
            sub_view.columns = [dst for _, dst in detail_columns]

            # Outsource სვეტები ჩანს მხოლოდ მაშინ, თუ ამ ხელშეკრულებაში Outsource პროექტია
            if 'Outsource დიზაინერი' in sub_view.columns and sub_view['Outsource დიზაინერი'].isna().all():
                sub_view = sub_view.drop(columns=[c for c in
                                                  ['Outsource დიზაინერი', 'Outsource ხელშეკრულების №',
                                                   'Outsource საკომისიო', 'ნაწილების რ-ბა'] if c in sub_view.columns])
            if 'Outsource საკომისიო' in sub_view.columns:
                sub_view['Outsource საკომისიო'] = sub_view['Outsource საკომისიო'].apply(
                    lambda x: f"{float(x) * 100:.2f}%" if pd.notnull(x) else "-")
            sub_view.index = range(1, len(sub_view) + 1)

            styled_sub_contracts = sub_view.style.format({
                'თანხა': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
            }, na_rep="-").set_properties(**{'text-align': 'left'})

            st.dataframe(styled_sub_contracts, use_container_width=True)

            sub_contracts_filtered = designers_data[(designers_data['root_contract'] == selected_contract) & (
                    designers_data['contract_type'] == "დაკონტრაქტება")]
            allowed_contract_amount = sub_contracts_filtered[
                'amount'].sum() if not sub_contracts_filtered.empty else 0.0

            st.info(
                f"💡 ამ ხელშეკრულების მიხედვით დასაკონტრაქტებელი (საწარმოო) ლიმიტი არის: **{allowed_contract_amount:,.2f} ₾** (დიზაინის თანხა გამოკლებულია)")

            existing_client_fullname = client_by_root.get(selected_contract, "")
            existing_phone = ""
            existing_email = ""
            existing_address = ""

            if not orders_data.empty and 'contract_base' in orders_data.columns:
                match_row = orders_data[orders_data['contract_base'] == selected_contract]
                if not match_row.empty:
                    if pd.notna(match_row.iloc[0].get('client_fullname')):
                        existing_client_fullname = match_row.iloc[0]['client_fullname']
                    existing_phone = _txt(match_row.iloc[0].get('phone'))
                    existing_email = _txt(match_row.iloc[0].get('email'))
                    existing_address = _txt(match_row.iloc[0].get('address'))

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
            st.markdown("#### 🗄️ პროდუქტების დეტალური ჩაშლა")

            # სესიის ინიციალიზაცია ოთახებისთვის
            session_key = f"rooms_list_{selected_contract}"
            if session_key not in st.session_state:
                loaded_list = []
                if not rooms_data.empty and 'contract_base' in rooms_data.columns:
                    existing_rooms = rooms_data[rooms_data['contract_base'] == selected_contract]
                    for _, r in existing_rooms.iterrows():
                        loaded_list.append({
                            "id": str(uuid.uuid4()),
                            "room_code": _txt(r.get("room_code")),
                            "furniture_type": _txt(r.get("furniture_type")),
                            "unit": _txt(r.get("unit")) or "კვ. მ.",
                            "quantity": float(r.get("quantity") if pd.notnull(r.get("quantity")) else 0.0),
                            "unit_price": float(r.get("unit_price") if pd.notnull(r.get("unit_price")) else 0.0)
                        })
                st.session_state[session_key] = loaded_list

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
                    r_code = st.text_input("ინდივიდუალური კოდი (6 ციფრი)", key=rc_key, max_chars=6)
                    if not is_valid_code(r_code):
                        st.caption("⚠️ ჩაწერეთ 6-ნიშნა კოდი")
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
                _codes = [_txt(r['room_code']).strip() for r in updated_rooms if is_valid_code(r['room_code'])]
                _dups = sorted({c for c in _codes if _codes.count(c) > 1})
                if _dups:
                    st.error(f"❌ ერთი და იგივე 6-ნიშნა კოდი განმეორებულია: {', '.join(_dups)}")
                elif allowed_contract_amount > 0 and total_rooms_amount > allowed_contract_amount:
                    st.error(
                        f"❌ შეცდომა: ოთახების ჯამური თანხა ({total_rooms_amount:,.2f} ₾) აჭარბებს დაკონტრაქტების ლიმიტს ({allowed_contract_amount:,.2f} ₾)!")
                else:
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()

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
                            st.success("✅ დამკვეთისა და პროდუქტების დეტალური მონაცემები წარმატებით შეინახა ბაზაში!")
                        except Exception as ex:
                            st.error(f"შეცდომა შენახვისას: {ex}")
                    else:
                        st.error("ბაზასთან კავშირი ვერ მოხერხდა.")