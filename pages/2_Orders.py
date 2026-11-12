import re
import uuid
from datetime import datetime, date
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

MAX_STAGES = 4
STAGE_PART_TITLES = {1: "1-ლი", 2: "მე-2", 3: "მე-3", 4: "მე-4"}
STAGE_HEADERS = {1: "პირველი", 2: "მეორე", 3: "მესამე", 4: "მეოთხე"}
PAYMENT_TYPES = ["BOG", "TBC", "PROC", "ტერმინალი", "სალარო 1", "სალარო 2"]

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
        cur.execute("ALTER TABLE customer_orders ADD COLUMN IF NOT EXISTS client_id_code VARCHAR(50);")
        cur.execute("ALTER TABLE customer_orders ADD COLUMN IF NOT EXISTS payment_stages INTEGER;")
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
        cur.execute("ALTER TABLE customer_order_rooms ADD COLUMN IF NOT EXISTS delivery_date DATE;")
        cur.execute("ALTER TABLE customer_order_rooms ADD COLUMN IF NOT EXISTS unit2 VARCHAR(50);")
        cur.execute("ALTER TABLE customer_order_rooms ADD COLUMN IF NOT EXISTS quantity2 NUMERIC;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_order_payment_plan (
                id SERIAL PRIMARY KEY,
                contract_base VARCHAR(50),
                stage_no INTEGER,
                planned_amount NUMERIC,
                planned_date DATE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customer_order_payments (
                id SERIAL PRIMARY KEY,
                contract_base VARCHAR(50),
                stage_no INTEGER,
                amount NUMERIC,
                paid_date DATE,
                payment_type VARCHAR(50)
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
    orders_df = pd.DataFrame(columns=["contract_base", "client_fullname", "phone", "email", "address",
                                      "client_id_code", "payment_stages"])
    rooms_df = pd.DataFrame(
        columns=["contract_base", "room_code", "furniture_type", "unit", "quantity", "unit_price", "total_price",
                 "delivery_date"])
    plan_df = pd.DataFrame(columns=["contract_base", "stage_no", "planned_amount", "planned_date"])
    pay_df = pd.DataFrame(columns=["contract_base", "stage_no", "amount", "paid_date", "payment_type"])

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

    try:
        plan_df = pd.read_sql("SELECT * FROM customer_order_payment_plan ORDER BY stage_no, id", con=engine)
    except Exception as e:
        st.error(f"გადახდის გრაფიკის წაკითხვის შეცდომა: {e}")

    try:
        pay_df = pd.read_sql("SELECT * FROM customer_order_payments ORDER BY stage_no, id", con=engine)
    except Exception as e:
        st.error(f"ჩარიცხვების წაკითხვის შეცდომა: {e}")

    return projects_df, orders_df, rooms_df, plan_df, pay_df


# ---------------- 🧰 დამხმარე ფუნქციები ----------------
def _txt(v):
    return "" if v is None or pd.isnull(v) else str(v)


def num(v):
    try:
        return float(v) if v is not None and pd.notnull(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def to_date(v):
    """ბაზიდან წამოსული მნიშვნელობა -> datetime.date ან None."""
    if v is None:
        return None
    try:
        if pd.isnull(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, pd.Timestamp):
        return v.date()
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def fmt_money(x):
    """10000 -> '10 000,00'"""
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


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
designers_data, orders_data, rooms_data, plan_data, pay_data = load_data()

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
            existing_client_id_code = ""
            existing_phone = ""
            existing_email = ""
            existing_address = ""
            existing_stages = None

            if not orders_data.empty and 'contract_base' in orders_data.columns:
                match_row = orders_data[orders_data['contract_base'] == selected_contract]
                if not match_row.empty:
                    if pd.notna(match_row.iloc[0].get('client_fullname')):
                        existing_client_fullname = match_row.iloc[0]['client_fullname']
                    existing_client_id_code = _txt(match_row.iloc[0].get('client_id_code'))
                    existing_phone = _txt(match_row.iloc[0].get('phone'))
                    existing_email = _txt(match_row.iloc[0].get('email'))
                    existing_address = _txt(match_row.iloc[0].get('address'))
                    _st = match_row.iloc[0].get('payment_stages')
                    if _st is not None and pd.notna(_st):
                        existing_stages = int(_st)

            # დამკვეთისა და საკონტაქტო მონაცემები
            st.markdown(f"### დამკვეთისა და საკონტაქტო მონაცემები: {selected_contract}")
            col1, col2 = st.columns(2)
            with col1:
                manual_client_fullname = st.text_input("დამკვეთი", value=existing_client_fullname,
                                                       key=f"client_fn_{selected_contract}")
                manual_client_id_code = st.text_input("პ/ნ ან საიდენტიფიკაციო კოდი", value=existing_client_id_code,
                                                      key=f"client_idc_{selected_contract}")
                manual_phone = st.text_input("Tel (საკონტაქტო ნომერი)", value=existing_phone,
                                             key=f"phone_{selected_contract}")
            with col2:
                manual_email = st.text_input("E-mail", value=existing_email, key=f"email_{selected_contract}")
                manual_address = st.text_input("მისამართი", value=existing_address, key=f"addr_{selected_contract}")

            st.markdown("---")
            st.markdown("#### 🗄️ პროდუქტების დეტალური ჩაშლა")

            # სესიის ინიციალიზაცია პროდუქტებისთვის
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
                            "quantity": num(r.get("quantity")),
                            "unit_price": num(r.get("unit_price")),
                            "delivery_date": to_date(r.get("delivery_date")),
                            "unit2": _txt(r.get("unit2")) or "კვ. მ.",
                            "quantity2": num(r.get("quantity2")),
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
                    "unit_price": 0.0,
                    "delivery_date": None,
                    "unit2": "კვ. მ.",
                    "quantity2": 0.0,
                })
                st.rerun()

            updated_rooms = []
            row_to_delete = None
            total_rooms_amount = 0.0

            for i, room in enumerate(st.session_state[session_key]):
                row_id = room["id"]
                st.markdown(f"**ოთახი / პროექტი #{i + 1}**")
                (rc_col, ft_col, un_col, qty_col, pr_col, tot_col, dl_col, del_col) = st.columns(
                    [1.8, 1.8, 1.2, 1, 1.2, 1.2, 1.5, 0.8])

                rc_key = f"rc_{selected_contract}_{row_id}"
                ft_key = f"ft_{selected_contract}_{row_id}"
                un_key = f"un_{selected_contract}_{row_id}"
                qty_key = f"qty_{selected_contract}_{row_id}"
                pr_key = f"pr_{selected_contract}_{row_id}"
                dl_key = f"dl_{selected_contract}_{row_id}"
                un2_key = f"un2_{selected_contract}_{row_id}"
                qty2_key = f"qty2_{selected_contract}_{row_id}"

                if un2_key not in st.session_state:
                    st.session_state[un2_key] = room.get("unit2") or "კვ. მ."
                if qty2_key not in st.session_state:
                    st.session_state[qty2_key] = float(room.get("quantity2", 0.0))
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
                    unit2_opts = ["კვ. მ.", "გრძ. მ."]
                    curr_unit2 = st.session_state[un2_key]
                    u2_idx = unit2_opts.index(curr_unit2) if curr_unit2 in unit2_opts else 0
                    unit2 = st.selectbox("ერთეული 2", unit2_opts, index=u2_idx, key=un2_key)
                with qty_col:
                    qty = st.number_input("რაოდენობა", min_value=0.0, step=1.0, format="%.2f", key=qty_key)
                    qty2 = st.number_input("რაოდენობა 2", min_value=0.0, step=1.0, format="%.2f", key=qty2_key)
                with pr_col:
                    price = st.number_input("ერთ. ფასი (₾)", min_value=0.0, step=10.0, format="%.2f", key=pr_key)
                with tot_col:
                    total = qty * price
                    total_rooms_amount += total
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.metric("ჯამური (₾)", f"{total:,.2f}")
                with dl_col:
                    delivery_dt = st.date_input("ჩაბარების თარიღი", value=room.get("delivery_date"),
                                                key=dl_key, format="DD.MM.YYYY")
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
                    "total_price": total,
                    "delivery_date": delivery_dt,
                    "unit2": unit2,
                    "quantity2": qty2,
                })
                st.markdown("---")

            if row_to_delete is not None:
                st.session_state[session_key] = [r for r in st.session_state[session_key] if r["id"] != row_to_delete]
                for k in [f"rc_{selected_contract}_{row_to_delete}", f"ft_{selected_contract}_{row_to_delete}",
                          f"un_{selected_contract}_{row_to_delete}", f"qty_{selected_contract}_{row_to_delete}",
                          f"pr_{selected_contract}_{row_to_delete}", f"dl_{selected_contract}_{row_to_delete}",
                          f"un2_{selected_contract}_{row_to_delete}", f"qty2_{selected_contract}_{row_to_delete}"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

            remaining_amount = allowed_contract_amount - total_rooms_amount

            st.markdown(
                f"**პროდუქტების ჯამური ღირებულება:** `{total_rooms_amount:,.2f} ₾` / **დასაშვები ლიმიტი:** `{allowed_contract_amount:,.2f} ₾` / **ასათვისებელი დარჩენილი თანხა:** `{remaining_amount:,.2f} ₾`")

            # ==================== 💰 ფინანსური ინფორმაცია ====================
            st.markdown("---")
            st.markdown("### 💰 ფინანსური ინფორმაცია")

            # ბაზიდან ჩატვირთული გრაფიკი ამ ხელშეკრულებისთვის
            plan_init = {}
            if not plan_data.empty and 'contract_base' in plan_data.columns:
                for _, pr_ in plan_data[plan_data['contract_base'] == selected_contract].iterrows():
                    plan_init[int(pr_['stage_no'])] = (num(pr_.get('planned_amount')), to_date(pr_.get('planned_date')))

            stages_key = f"fin_stages_{selected_contract}"
            pay_list_key = f"fin_pay_{selected_contract}"

            if stages_key not in st.session_state:
                init_stages = existing_stages if existing_stages else (max(plan_init) if plan_init else 1)
                st.session_state[stages_key] = min(max(int(init_stages), 1), MAX_STAGES)

            if pay_list_key not in st.session_state:
                loaded_pays = []
                if not pay_data.empty and 'contract_base' in pay_data.columns:
                    for _, p_ in pay_data[pay_data['contract_base'] == selected_contract].iterrows():
                        loaded_pays.append({
                            "id": str(uuid.uuid4()),
                            "stage": int(p_['stage_no']),
                            "amount": num(p_.get('amount')),
                            "date": to_date(p_.get('paid_date')),
                            "type": _txt(p_.get('payment_type')) or PAYMENT_TYPES[0],
                        })
                st.session_state[pay_list_key] = loaded_pays

            n_stages = st.selectbox("რამდენ ეტაპად ხდება თანხის გადახდა?", list(range(1, MAX_STAGES + 1)),
                                    key=stages_key)

            plan_out = []  # [{"stage", "amount", "date"}]
            payments_out = []  # [{"stage", "amount", "date", "type"}]
            pay_to_delete = None
            add_pay_stage = None

            for n in range(1, n_stages + 1):
                with st.container(border=True):
                    plan_col, pay_col = st.columns([1.2, 3])

                    # ---- მარცხენა მხარე: გრაფიკით გადასახდელი ნაწილი ----
                    with plan_col:
                        st.markdown(f"**გადასახდელი თანხის {STAGE_PART_TITLES[n]} ნაწილი**")
                        pa_key = f"plan_amt_{selected_contract}_{n}"
                        pd_key = f"plan_dt_{selected_contract}_{n}"
                        if pa_key not in st.session_state:
                            st.session_state[pa_key] = plan_init.get(n, (0.0, None))[0]
                        planned_amt = st.number_input("თანხა (₾)", min_value=0.0, step=100.0, format="%.2f",
                                                      key=pa_key)
                        planned_dt = st.date_input("ჩარიცხვის თარიღი", value=plan_init.get(n, (0.0, None))[1],
                                                  key=pd_key, format="DD.MM.YYYY")
                    plan_out.append({"stage": n, "amount": planned_amt, "date": planned_dt})

                    # ---- მარჯვენა მხარე: ბუღალტრის სამუშაო ველი ----
                    with pay_col:
                        st.markdown("**🧾 ბუღალტერია - ფაქტიური ჩარიცხვები**")
                        stage_pays = [p for p in st.session_state[pay_list_key] if p["stage"] == n]
                        for p in stage_pays:
                            pid = p["id"]
                            pamt_key = f"payamt_{selected_contract}_{pid}"
                            pdt_key = f"paydt_{selected_contract}_{pid}"
                            ptp_key = f"paytp_{selected_contract}_{pid}"
                            if pamt_key not in st.session_state:
                                st.session_state[pamt_key] = float(p["amount"])
                            if ptp_key not in st.session_state:
                                st.session_state[ptp_key] = p["type"] if p["type"] in PAYMENT_TYPES else \
                                    PAYMENT_TYPES[0]

                            a_col, d_col, t_col, x_col = st.columns([1.2, 1.2, 1.2, 0.5])
                            with a_col:
                                p_amt = st.number_input("თანხა (₾)", min_value=0.0, step=100.0, format="%.2f",
                                                        key=pamt_key)
                            with d_col:
                                p_dt = st.date_input("თარიღი", value=p["date"], key=pdt_key, format="DD.MM.YYYY")
                            with t_col:
                                p_tp = st.selectbox("ტიპი", PAYMENT_TYPES, key=ptp_key)
                            with x_col:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("🗑️", key=f"paydel_{selected_contract}_{pid}"):
                                    pay_to_delete = pid
                            payments_out.append({"stage": n, "amount": p_amt, "date": p_dt, "type": p_tp})

                        if st.button("➕ ჩარიცხვის დამატება", key=f"payadd_{selected_contract}_{n}"):
                            add_pay_stage = n

            # "+" ღილაკი -> ახალი ჩარიცხვის სტრიქონი
            if add_pay_stage is not None:
                st.session_state[pay_list_key].append({
                    "id": str(uuid.uuid4()),
                    "stage": add_pay_stage,
                    "amount": 0.0,
                    "date": TODAY,
                    "type": PAYMENT_TYPES[0],
                })
                st.rerun()

            # ჩარიცხვის წაშლა
            if pay_to_delete is not None:
                st.session_state[pay_list_key] = [p for p in st.session_state[pay_list_key]
                                                  if p["id"] != pay_to_delete]
                for k in [f"payamt_{selected_contract}_{pay_to_delete}", f"paydt_{selected_contract}_{pay_to_delete}",
                          f"paytp_{selected_contract}_{pay_to_delete}"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

            # ---- გადანაწილების შეტყობინება ----
            planned_total = sum(x["amount"] for x in plan_out)
            if allowed_contract_amount > 0:
                diff = allowed_contract_amount - planned_total
                if abs(diff) < 0.005:
                    st.success(
                        f"✅ {allowed_contract_amount:,.2f} ₾ ღირებულების ხელშეკრულებიდან {planned_total:,.2f} ₾ "
                        f"სრულად გადანაწილებულია {n_stages} ტრანშში.")
                elif diff > 0:
                    st.warning(
                        f"⚠️ {allowed_contract_amount:,.2f} ₾ ღირებულების ხელშეკრულებიდან გადანაწილებულია "
                        f"{planned_total:,.2f} ₾. გადასანაწილებელი დარჩა: {diff:,.2f} ₾.")
                else:
                    st.error(
                        f"❌ გადანაწილებული თანხა ({planned_total:,.2f} ₾) აჭარბებს ხელშეკრულების თანხას "
                        f"({allowed_contract_amount:,.2f} ₾) {-diff:,.2f} ₾-ით.")
            else:
                st.info("ℹ️ ხელშეკრულების თანხა ვერ განისაზღვრა (დაკონტრაქტების ჩანაწერის თანხა 0-ია).")

            paid_total = sum(x["amount"] for x in payments_out)

            # ---- შემაჯამებელი ცხრილი (ცოცხლად ახლდება) ----
            st.markdown("##### 📊 გადახდების შემაჯამებელი ცხრილი")

            fin_cols = [("", "პროექტი / სახელი"), ("", "ჯამური პროექტის თანხა"),
                        ("", "გადახდილი თანხა"), ("", "დარჩენილი თანხა")]
            for s in range(1, MAX_STAGES + 1):
                fin_cols.append((STAGE_HEADERS[s], "თანხა (გრაფიკით)"))
                fin_cols.append((STAGE_HEADERS[s], "თანხა (ფაქტიური)"))

            left_amount = allowed_contract_amount - paid_total
            project_label = f"{selected_contract} - {manual_client_fullname}".strip(" -")
            fin_row = [
                project_label,
                fmt_money(allowed_contract_amount),
                fmt_money(paid_total) if paid_total else "-",
                fmt_money(left_amount) if abs(left_amount) >= 0.005 else "-",
            ]
            for s in range(1, MAX_STAGES + 1):
                if s <= n_stages:
                    s_plan = next((x["amount"] for x in plan_out if x["stage"] == s), 0.0)
                    s_fact = sum(x["amount"] for x in payments_out if x["stage"] == s)
                    fin_row.append(fmt_money(s_plan) if s_plan else "-")
                    fin_row.append(fmt_money(s_fact) if s_fact else "-")
                else:
                    fin_row.append("")
                    fin_row.append("")

            fin_df = pd.DataFrame([fin_row], columns=pd.MultiIndex.from_tuples(fin_cols))
            st.dataframe(fin_df, use_container_width=True, hide_index=True)
            st.caption("ცხრილი ცოცხლად ახლდება. ბაზაში ჩასაწერად დააჭირეთ ქვემოთ „ცვლილებების შენახვა ბაზაში“.")

            # შენახვის ღილაკი
            if st.button("💾 ცვლილებების შენახვა ბაზაში", key=f"save_btn_{selected_contract}"):
                _codes = [_txt(r['room_code']).strip() for r in updated_rooms if is_valid_code(r['room_code'])]
                _dups = sorted({c for c in _codes if _codes.count(c) > 1})
                _hidden_pays = [p for p in st.session_state[pay_list_key] if p["stage"] > n_stages]
                if _dups:
                    st.error(f"❌ ერთი და იგივე 6-ნიშნა კოდი განმეორებულია: {', '.join(_dups)}")
                elif allowed_contract_amount > 0 and total_rooms_amount > allowed_contract_amount:
                    st.error(
                        f"❌ შეცდომა: პროდუქტების ჯამური თანხა ({total_rooms_amount:,.2f} ₾) აჭარბებს დაკონტრაქტების ლიმიტს ({allowed_contract_amount:,.2f} ₾)!")
                elif allowed_contract_amount > 0 and planned_total > allowed_contract_amount + 0.005:
                    st.error(
                        f"❌ შეცდომა: გადახდის გრაფიკის ჯამი ({planned_total:,.2f} ₾) აჭარბებს ხელშეკრულების თანხას ({allowed_contract_amount:,.2f} ₾)!")
                elif _hidden_pays:
                    st.error(
                        f"❌ ეტაპების რაოდენობა შემცირებულია, მაგრამ მოხსნილ ეტაპებზე უკვე არის ჩარიცხვები "
                        f"({len(_hidden_pays)} ცალი). გაზარდეთ ეტაპების რაოდენობა ან ჯერ წაშალეთ ის ჩარიცხვები.")
                else:
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()

                            cursor.execute("""
                                INSERT INTO customer_orders
                                    (contract_base, client_fullname, client_id_code, phone, email, address, payment_stages)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (contract_base) DO UPDATE SET
                                    client_fullname = EXCLUDED.client_fullname,
                                    client_id_code = EXCLUDED.client_id_code,
                                    phone = EXCLUDED.phone,
                                    email = EXCLUDED.email,
                                    address = EXCLUDED.address,
                                    payment_stages = EXCLUDED.payment_stages
                            """, (selected_contract, manual_client_fullname, manual_client_id_code, manual_phone,
                                  manual_email, manual_address, n_stages))

                            cursor.execute("DELETE FROM customer_order_rooms WHERE contract_base = %s",
                                           (selected_contract,))
                            for r in updated_rooms:
                                cursor.execute("""
                                    INSERT INTO customer_order_rooms
                                        (contract_base, room_code, furniture_type, unit, quantity, unit_price, total_price,
                                         delivery_date, unit2, quantity2)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (selected_contract, r['room_code'], r['furniture_type'], r['unit'], r['quantity'],
                                      r['unit_price'], r['total_price'], r['delivery_date'], r['unit2'],
                                      r['quantity2']))

                            cursor.execute("DELETE FROM customer_order_payment_plan WHERE contract_base = %s",
                                           (selected_contract,))
                            for x in plan_out:
                                cursor.execute("""
                                    INSERT INTO customer_order_payment_plan
                                        (contract_base, stage_no, planned_amount, planned_date)
                                    VALUES (%s, %s, %s, %s)
                                """, (selected_contract, x['stage'], x['amount'], x['date']))

                            cursor.execute("DELETE FROM customer_order_payments WHERE contract_base = %s",
                                           (selected_contract,))
                            for x in payments_out:
                                if x['amount'] > 0:
                                    cursor.execute("""
                                        INSERT INTO customer_order_payments
                                            (contract_base, stage_no, amount, paid_date, payment_type)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (selected_contract, x['stage'], x['amount'], x['date'], x['type']))

                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success("✅ დამკვეთის, პროდუქტების და ფინანსური მონაცემები წარმატებით შეინახა ბაზაში!")
                        except Exception as ex:
                            try:
                                conn.rollback()
                                conn.close()
                            except Exception:
                                pass
                            st.error(f"შეცდომა შენახვისას: {ex}")
                    else:
                        st.error("ბაზასთან კავშირი ვერ მოხერხდა.")