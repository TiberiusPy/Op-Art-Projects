import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import psycopg2
from datetime import datetime

st.set_page_config(page_title="Op-Art - დიზაინერების ხელფასები და დეშბორდი", layout="wide")

# ==================== 🔐 ავტორიზაციის შემოწმება ====================
if "authenticated_designer" not in st.session_state:
    st.session_state["authenticated_designer"] = False

if not st.session_state["authenticated_designer"]:
    st.title("🔐 ავტორიზაცია - დიზაინერების დეშბორდი")
    st.markdown("გთხოვთ შეიყვანოთ პაროლი ამ განყოფილებაში შესასვლელად.")

    password_input = st.text_input("პაროლი", type="password")

    if st.button("შესვლა"):
        if password_input == "Design123":
            st.session_state["authenticated_designer"] = True
            st.success("პაროლი სწორია! იტვირთება სისტემა...")
            st.rerun()
        else:
            st.error("არასწორი პაროლი! სცადეთ თავიდან.")

    st.stop()
# ===================================================================

# PostgreSQL ბაზასთან მიერთება
DB_USER = "postgres"
DB_PASS = "123qweASD"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "RMS"

db_url = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)


# მონაცემების წამოღება და ბაზის სტრუქტურის შემოწმება
def get_data():
    try:
        conn_check = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        cur_check = conn_check.cursor()

        cur_check.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='designers' AND column_name='design_fee_pct';")
        if not cur_check.fetchone():
            cur_check.execute("ALTER TABLE designers ADD COLUMN design_fee_pct NUMERIC DEFAULT 0.50;")
            conn_check.commit()

        cur_check.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='designers' AND column_name='commission_pct';")
        if not cur_check.fetchone():
            cur_check.execute("ALTER TABLE designers ADD COLUMN commission_pct NUMERIC DEFAULT 0.02;")
            conn_check.commit()

        cur_check.execute("""
            CREATE TABLE IF NOT EXISTS managers (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(150),
                manager_pct NUMERIC DEFAULT 0.0035
            );
        """)
        conn_check.commit()

        cur_check.execute("""
            CREATE TABLE IF NOT EXISTS manager_history (
                id SERIAL PRIMARY KEY,
                manager_name VARCHAR(150),
                old_manager_pct NUMERIC,
                manager_pct NUMERIC,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn_check.commit()

        cur_check.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='manager_history' AND column_name='old_manager_pct';")
        if not cur_check.fetchone():
            cur_check.execute("ALTER TABLE manager_history ADD COLUMN old_manager_pct NUMERIC;")
            conn_check.commit()

        cur_check.execute("SELECT * FROM managers WHERE full_name = 'ია პირტახია';")
        if not cur_check.fetchone():
            cur_check.execute("INSERT INTO managers (full_name, manager_pct) VALUES ('ია პირტახია', 0.0035);")
            cur_check.execute(
                "INSERT INTO manager_history (manager_name, old_manager_pct, manager_pct) VALUES ('ია პირტახია', NULL, 0.0035);")
            conn_check.commit()

        cur_check.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='projects' AND column_name='saved_design_fee_pct';")
        if not cur_check.fetchone():
            cur_check.execute("ALTER TABLE projects ADD COLUMN saved_design_fee_pct NUMERIC DEFAULT 0.50;")
            cur_check.execute("ALTER TABLE projects ADD COLUMN saved_commission_pct NUMERIC DEFAULT 0.02;")
            conn_check.commit()

        new_columns = [
            ("project_source", "VARCHAR(50) DEFAULT 'Op-Art'"),
            ("delivery_date_str", "VARCHAR(50)"),
            ("outsource_designer_name", "VARCHAR(150)"),
            ("outsource_contract_no", "VARCHAR(50)"),
            ("outsource_commission_pct", "NUMERIC DEFAULT 0.0"),
            ("outsource_installments", "INTEGER DEFAULT 1"),
            ("project_category", "VARCHAR(50) DEFAULT 'ინდივიდუალური'"),
            ("contract_file_data", "BYTEA"),
            ("contract_file_name", "VARCHAR(255)")
        ]
        for col_name, col_type in new_columns:
            cur_check.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='projects' AND column_name='{col_name}';")
            if not cur_check.fetchone():
                cur_check.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type};")
                conn_check.commit()

        cur_check.execute("""
            CREATE TABLE IF NOT EXISTS designer_history (
                id SERIAL PRIMARY KEY,
                designer_name VARCHAR(150),
                old_design_fee_pct NUMERIC,
                design_fee_pct NUMERIC,
                old_commission_pct NUMERIC,
                commission_pct NUMERIC,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn_check.commit()

        cur_check.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='designer_history' AND column_name='old_design_fee_pct';")
        if not cur_check.fetchone():
            cur_check.execute("ALTER TABLE designer_history ADD COLUMN old_design_fee_pct NUMERIC;")
            cur_check.execute("ALTER TABLE designer_history ADD COLUMN old_commission_pct NUMERIC;")
            conn_check.commit()

        cur_check.close()
        conn_check.close()
    except Exception as e:
        pass

    try:
        df_projects = pd.read_sql(
            "SELECT id, contract_type, contract_no, project_category, client_name, amount, product_type, designer_name, saved_design_fee_pct, saved_commission_pct, created_at, project_source, delivery_date_str, outsource_designer_name, outsource_contract_no, outsource_commission_pct, outsource_installments, contract_file_name, (contract_file_data IS NOT NULL) AS has_file FROM projects ORDER BY created_at DESC;",
            con=engine)
        df_designers = pd.read_sql("SELECT * FROM designers;", con=engine)
        df_managers = pd.read_sql("SELECT * FROM managers;", con=engine)
        df_products = pd.read_sql("SELECT * FROM product_types;", con=engine)
        df_history = pd.read_sql("SELECT * FROM designer_history ORDER BY changed_at DESC;", con=engine)
        df_m_history = pd.read_sql("SELECT * FROM manager_history ORDER BY changed_at DESC;", con=engine)

        if not df_projects.empty:
            df_projects['created_at'] = pd.to_datetime(df_projects['created_at'])
            df_projects['month_year'] = df_projects['created_at'].dt.strftime('%b.%y')
            df_projects['year'] = df_projects['created_at'].dt.year
        return df_projects, df_designers, df_managers, df_products, df_history, df_m_history
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


df, designers_df, managers_df, products_df, history_df, manager_history_df = get_data()

# 🎨 Custom CSS ღილაკებისა და ბარათების კონტურების მართვისთვის
st.markdown("""
    <style>
    .stButton > button {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        padding: 0.35rem 0.75rem;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:hover {
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛋️ Op-Art - დიზაინერების ხელფასები და დეშბორდი")

# მენიუ / ტაბები (4 ჩანართი)
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 დეშბორდი და დამატება",
    "✏️ ჩანაწერების რედაქტირება / წაშლა",
    "⚙️ ცნობარების მართვა",
    "📋 Outsource რეესტრი"
])

all_designers = designers_df['full_name'].tolist() if not designers_df.empty else ["თათა კუხალაშვილი",
                                                                                   "მარიამ ტაბატაძე", "გოჩა მუსერიძე"]
designer_options = [d for d in all_designers if d != "ია პირტახია"]

product_options = ["ავეჯი", "კარი"]
contract_type_options = ["დიზაინი", "დაკონტრაქტება"]
project_category_options = ["ინდივიდუალური", "კორპორატიული"]

# ავტომატური რიგითი ხელშეკრულების ნომრის გენერაცია
suggested_contract_no = "261001"
if not df.empty and 'contract_no' in df.columns:
    try:
        last_no = df.iloc[0]['contract_no']
        if last_no and '-' not in str(last_no):
            suggested_contract_no = str(int(last_no) + 1)
        elif last_no:
            parts = str(last_no).split('-')
            if parts[0].isdigit():
                suggested_contract_no = str(int(parts[0]) + 1)
    except:
        pass

with tab1:
    st.sidebar.header("➕ ახალი ჩანაწერის დამატება")

    project_source = st.sidebar.selectbox("პროექტის წყარო", ["Op-Art", "Outsource"], key="proj_source_sel")

    if project_source == "Op-Art":
        product_type = st.sidebar.selectbox("პროდუქცია", product_options, index=None, placeholder="აირჩიე",
                                            key="prod_type_sidebar_sel")

        with st.sidebar.form("add_form", clear_on_submit=True):
            contract_type = st.selectbox("ხელშეკრულების ტიპი", contract_type_options, index=None, placeholder="აირჩიე")
            contract_no = st.text_input("ხელშეკრულების №", value=suggested_contract_no)
            project_category = st.selectbox("პროექტის კატეგორია", project_category_options, index=None,
                                            placeholder="აირჩიე")
            client_name = st.text_input("დამკვეთი")

            amount = st.number_input("ხელშეკრულების თანხა (₾)", min_value=0.0, step=100.0, value=0.0, format="%.2f")

            if product_type == "კარი":
                designer_name = st.selectbox("დიზაინერი", ["ია პირტახია"])
            else:
                designer_name = st.selectbox("დიზაინერი", designer_options, index=None, placeholder="აირჩიე")

            d_date = st.date_input("ჩაბარების თარიღი", value=datetime.now())
            delivery_date_str = d_date.strftime("%d %b, %Y")

            submit = st.form_submit_button("💾 შენახვა ბაზაში")

            if submit:
                if not contract_type or not contract_no or not project_category or not client_name or not product_type or not designer_name or amount <= 0:
                    st.sidebar.error("გთხოვთ, ბოლომდე შეავსეთ ყველა ველი!")
                else:
                    try:
                        des_rec = designers_df[
                            designers_df['full_name'] == designer_name] if not designers_df.empty else pd.DataFrame()
                        current_des_fee_pct = float(des_rec.iloc[0][
                                                        'design_fee_pct']) if not des_rec.empty and 'design_fee_pct' in des_rec.columns and pd.notnull(
                            des_rec.iloc[0]['design_fee_pct']) else 0.50
                        current_com_pct = float(des_rec.iloc[0][
                                                    'commission_pct']) if not des_rec.empty and 'commission_pct' in des_rec.columns and pd.notnull(
                            des_rec.iloc[0]['commission_pct']) else 0.02

                        new_data = pd.DataFrame([{
                            "contract_type": contract_type,
                            "contract_no": contract_no.strip(),
                            "project_category": project_category,
                            "client_name": client_name.strip(),
                            "amount": amount,
                            "product_type": product_type,
                            "designer_name": designer_name,
                            "saved_design_fee_pct": current_des_fee_pct,
                            "saved_commission_pct": current_com_pct,
                            "project_source": project_source,
                            "delivery_date_str": delivery_date_str
                        }])
                        new_data.to_sql("projects", con=engine, if_exists="append", index=False)
                        st.sidebar.success("წარმატებით დაემატა!")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"შეცდომა: {e}")
    else:
        outsource_design_type = st.sidebar.selectbox("დიზაინი", ["დიზაინით", "დიზაინის გარეშე"],
                                                     key="outsource_design_type_sel")
        product_type = st.sidebar.selectbox("პროდუქცია", product_options, index=None, placeholder="აირჩიე",
                                            key="prod_type_outsource_sel")

        if outsource_design_type == "დიზაინით":
            with st.sidebar.form("add_outsource_design_form", clear_on_submit=True):
                outsource_designer_name = st.text_input("Outsource დიზაინერის სახელი და გვარი")
                outsource_contract_no = st.text_input("Outsource დიზაინერის ხელშეკრულების №")
                outsource_commission_pct = st.number_input("Outsource დიზაინერის საკომისიო (%)", min_value=0.0,
                                                           max_value=100.0, value=2.0, step=0.5)
                outsource_installments = st.number_input("საკომისიოს რამდენ ნაწილად ვაძლევთ", min_value=1, max_value=12,
                                                         value=1, step=1)

                contract_no = st.text_input("ხელშეკრულების №", value=suggested_contract_no)
                project_category = st.selectbox("პროექტის კატეგორია", project_category_options, index=None,
                                                placeholder="აირჩიე")
                client_name = st.text_input("დამკვეთი")
                amount = st.number_input("ხელშეკრულების თანხა (₾)", min_value=0.0, step=100.0, value=0.0, format="%.2f")

                designer_name = st.selectbox("დიზაინერი", ["ია პირტახია"])

                d_date = st.date_input("ჩაბარების თარიღი", value=datetime.now())
                delivery_date_str = d_date.strftime("%d %b, %Y")

                submit_outsource = st.form_submit_button("💾 შენახვა ბაზაში (Outsource)")

                if submit_outsource:
                    if not outsource_designer_name or not outsource_contract_no or not contract_no or not project_category or not client_name or not product_type or amount <= 0:
                        st.sidebar.error("გთხოვთ, ბოლომდე შეავსეთ ყველა ველი!")
                    else:
                        try:
                            new_data = pd.DataFrame([{
                                "contract_type": "დაკონტრაქტება",
                                "contract_no": contract_no.strip(),
                                "project_category": project_category,
                                "client_name": client_name.strip(),
                                "amount": amount,
                                "product_type": product_type,
                                "designer_name": designer_name,
                                "saved_design_fee_pct": 0.0,
                                "saved_commission_pct": outsource_commission_pct / 100.0,
                                "project_source": "Outsource - დიზაინით",
                                "delivery_date_str": delivery_date_str,
                                "outsource_designer_name": outsource_designer_name.strip(),
                                "outsource_contract_no": outsource_contract_no.strip(),
                                "outsource_commission_pct": outsource_commission_pct / 100.0,
                                "outsource_installments": int(outsource_installments)
                            }])
                            new_data.to_sql("projects", con=engine, if_exists="append", index=False)
                            st.sidebar.success("Outsource პროექტი წარმატებით დაემატა!")
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"შეცდომა: {e}")
        else:
            with st.sidebar.form("add_outsource_nodesign_form", clear_on_submit=True):
                outsource_designer_name = st.text_input("Outsource დიზაინერის სახელი და გვარი")
                outsource_contract_no = st.text_input("Outsource დიზაინერის ხელშეკრულების №")
                outsource_commission_pct = st.number_input("Outsource დიზაინერის საკომისიო (%)", min_value=0.0,
                                                           max_value=100.0, value=2.0, step=0.5)
                outsource_installments = st.number_input("საკომისიოს რამდენ ნაწილად ვაძლევთ", min_value=1, max_value=12,
                                                         value=1, step=1)

                contract_type = st.selectbox("ხელშეკრულების ტიპი", contract_type_options, index=None,
                                             placeholder="აირჩიე")
                contract_no = st.text_input("ხელშეკრულების №", value=suggested_contract_no)
                project_category = st.selectbox("პროექტის კატეგორია", project_category_options, index=None,
                                                placeholder="აირჩიე")
                client_name = st.text_input("დამკვეთი")
                amount = st.number_input("ხელშეკრულების თანხა (₾)", min_value=0.0, step=100.0, value=0.0, format="%.2f")

                if product_type == "კარი":
                    designer_name = st.selectbox("დიზაინერი", ["ია პირტახია"])
                else:
                    designer_name = st.selectbox("დიზაინერი", designer_options, index=None, placeholder="აირჩიე")

                d_date = st.date_input("ჩაბარების თარიღი", value=datetime.now())
                delivery_date_str = d_date.strftime("%d %b, %Y")

                submit_outsource_nd = st.form_submit_button("💾 შენახვა ბაზაში (Outsource - დიზაინის გარეშე)")

                if submit_outsource_nd:
                    if not outsource_designer_name or not outsource_contract_no or not contract_type or not contract_no or not project_category or not client_name or not product_type or not designer_name or amount <= 0:
                        st.sidebar.error("გთხოვთ, ბოლომდე შეავსეთ ყველა ველი!")
                    else:
                        try:
                            des_rec = designers_df[
                                designers_df[
                                    'full_name'] == designer_name] if not designers_df.empty else pd.DataFrame()
                            current_des_fee_pct = float(des_rec.iloc[0][
                                                            'design_fee_pct']) if not des_rec.empty and 'design_fee_pct' in des_rec.columns and pd.notnull(
                                des_rec.iloc[0]['design_fee_pct']) else 0.50
                            current_com_pct = float(des_rec.iloc[0][
                                                        'commission_pct']) if not des_rec.empty and 'commission_pct' in des_rec.columns and pd.notnull(
                                des_rec.iloc[0]['commission_pct']) else 0.02

                            new_data = pd.DataFrame([{
                                "contract_type": contract_type,
                                "contract_no": contract_no.strip(),
                                "project_category": project_category,
                                "client_name": client_name.strip(),
                                "amount": amount,
                                "product_type": product_type,
                                "designer_name": designer_name,
                                "saved_design_fee_pct": current_des_fee_pct,
                                "saved_commission_pct": current_com_pct,
                                "project_source": "Outsource - დიზაინის გარეშე",
                                "delivery_date_str": delivery_date_str,
                                "outsource_designer_name": outsource_designer_name.strip(),
                                "outsource_contract_no": outsource_contract_no.strip(),
                                "outsource_commission_pct": outsource_commission_pct / 100.0,
                                "outsource_installments": int(outsource_installments)
                            }])
                            new_data.to_sql("projects", con=engine, if_exists="append", index=False)
                            st.sidebar.success("Outsource (დიზაინის გარეშე) პროექტი წარმატებით დაემატა!")
                            st.rerun()
                        except Exception as e:
                            st.sidebar.error(f"შეცდომა: {e}")

    if not df.empty:
        calculated_rows = []

        for idx, row in df.iterrows():
            c_type = row['contract_type']
            c_no = row['contract_no']
            amt = row['amount']
            designer = row['designer_name']
            rec_date = row['created_at']
            p_type = row.get('product_type', '')
            p_source = row.get('project_source', 'Op-Art')

            salary_designer = 0
            salary_ia = 0

            ia_pct = 0.0035
            if not managers_df.empty:
                ia_row = managers_df[managers_df['full_name'] == "ია პირტახია"]
                if not ia_row.empty and pd.notnull(ia_row.iloc[0]['manager_pct']):
                    ia_pct = float(ia_row.iloc[0]['manager_pct'])

            current_month_df = df[df['created_at'].dt.strftime('%Y-%m') == rec_date.strftime('%Y-%m')]
            month_total_turnover = current_month_df['amount'].sum()
            salary_ia = month_total_turnover * ia_pct

            if p_source == "Outsource - დიზაინით":
                out_com_pct = float(
                    row['outsource_commission_pct']) if 'outsource_commission_pct' in row and pd.notnull(
                    row['outsource_commission_pct']) else 0.02
                salary_designer = amt * out_com_pct
            else:
                base_design_no = c_no.split('-')[0] if '-' in c_no else None
                design_match = df[df['contract_no'] == base_design_no] if base_design_no else pd.DataFrame()
                design_amount = design_match.iloc[0]['amount'] if not design_match.empty else 0

                des_row = designers_df[
                    designers_df['full_name'] == designer] if not designers_df.empty else pd.DataFrame()

                if 'saved_design_fee_pct' in row and pd.notnull(row['saved_design_fee_pct']):
                    des_fee_pct = float(row['saved_design_fee_pct'])
                else:
                    des_fee_pct = float(des_row.iloc[0][
                                            'design_fee_pct']) if not des_row.empty and 'design_fee_pct' in des_row.columns and pd.notnull(
                        des_row.iloc[0]['design_fee_pct']) else 0.50

                if 'saved_commission_pct' in row and pd.notnull(row['saved_commission_pct']):
                    designer_pct = float(row['saved_commission_pct'])
                else:
                    designer_pct = float(des_row.iloc[0][
                                             'commission_pct']) if not des_row.empty and 'commission_pct' in des_row.columns and pd.notnull(
                        des_row.iloc[0]['commission_pct']) else 0.02

                if p_type == "კარი":
                    salary_designer = 0
                else:
                    if c_type == "დიზაინი":
                        base_no = c_no
                        contract_match = df[
                            (df['contract_type'] == "დაკონტრაქტება") & (df['contract_no'] == base_no + "-1")]

                        if not contract_match.empty and contract_match.iloc[0]['created_at'].strftime(
                                '%Y-%m') == rec_date.strftime('%Y-%m'):
                            salary_designer = 0
                        else:
                            salary_designer = amt * des_fee_pct

                    elif c_type == "დაკონტრაქტება":
                        if not design_match.empty:
                            design_date = design_match.iloc[0]['created_at']
                            hist_des_fee = float(design_match.iloc[0][
                                                     'saved_design_fee_pct']) if 'saved_design_fee_pct' in design_match.columns and pd.notnull(
                                design_match.iloc[0]['saved_design_fee_pct']) else des_fee_pct

                            if design_date.strftime('%Y-%m') == rec_date.strftime('%Y-%m'):
                                salary_designer = (amt + design_amount) * designer_pct
                            else:
                                salary_designer = ((amt + design_amount) * designer_pct) - (
                                        design_amount * hist_des_fee)
                        else:
                            salary_designer = amt * designer_pct

            row['salary_designer'] = round(salary_designer, 2)
            row['salary_ia'] = round(salary_ia, 2)
            calculated_rows.append(row)

        calc_df = pd.DataFrame(calculated_rows)

        col_title, col_year_sel, col_btn = st.columns([2, 1, 1])
        with col_title:
            st.subheader("📊 თვიური რეპორტი და ხელფასების უწყისი")

        db_years = calc_df['year'].unique().tolist() if 'year' in calc_df.columns else []
        default_years = [2026, 2027, 2028]
        available_years = sorted(list(set(db_years + default_years)))

        current_year = datetime.now().year
        default_index = available_years.index(current_year) if current_year in available_years else 0

        with col_year_sel:
            selected_year = st.selectbox("📅 აირჩიეთ წელი", available_years, index=default_index)

        filtered_calc_df = calc_df[calc_df['year'] == selected_year] if 'year' in calc_df.columns else pd.DataFrame(
            columns=calc_df.columns)

        year_short = str(selected_year)[-2:]
        month_names_eng = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        all_months_sorted = [f"{m}.{year_short}" for m in month_names_eng]

        st.markdown("#### 🧑‍🎨 დიზაინერები (ხელფასები)")
        designers_data = []
        designers_to_show = [d for d in all_designers if d != "ია პირტახია"] + ["ია პირტახია"]
        for d in designers_to_show:
            row_dict = {"სახელი და გვარი": d}
            for m in all_months_sorted:
                m_filtered = filtered_calc_df[
                    filtered_calc_df['month_year'] == m] if not filtered_calc_df.empty else pd.DataFrame()
                if d == "ია პირტახია":
                    val = m_filtered['salary_ia'].max() if not m_filtered.empty else 0
                else:
                    furniture_m_filtered = m_filtered[m_filtered.get('product_type', '') != 'კარი']
                    val = furniture_m_filtered[furniture_m_filtered['designer_name'] == d][
                        'salary_designer'].sum() if not furniture_m_filtered.empty else 0
                row_dict[m] = round(val, 2) if val > 0 else 0.0
            designers_data.append(row_dict)

        df_des_table = pd.DataFrame(designers_data)
        df_des_table.index = range(1, len(df_des_table) + 1)

        styled_des = df_des_table.style.format(
            {m: (lambda x: f"{x:,.2f}" if x > 0 else "-") for m in all_months_sorted}, na_rep="-"
        ).set_properties(**{'text-align': 'right'})
        st.dataframe(styled_des, use_container_width=True)
        st.write("")

        st.markdown("#### 🎨 დიზაინი")
        furniture_calc_df = filtered_calc_df[
            filtered_calc_df.get('product_type', '') != 'კარი'] if not filtered_calc_df.empty else pd.DataFrame()

        d_count_dict = {"სახელი და გვარი": "დიზაინი (რ-ბა)"}
        for m in all_months_sorted:
            cnt = len(furniture_calc_df[(furniture_calc_df['month_year'] == m) & (
                    furniture_calc_df['contract_type'] == "დიზაინი")]) if not furniture_calc_df.empty else 0
            d_count_dict[m] = int(cnt)

        d_sum_dict = {"სახელი და გვარი": "დიზაინი (თანხა)"}
        for m in all_months_sorted:
            s = furniture_calc_df[
                (furniture_calc_df['month_year'] == m) & (furniture_calc_df['contract_type'] == "დიზაინი")][
                'amount'].sum() if not furniture_calc_df.empty else 0
            d_sum_dict[m] = round(float(s), 2)

        df_design_info = pd.DataFrame([d_count_dict, d_sum_dict])
        df_design_info.index = ["🔢", "💰"]

        styled_design = df_design_info.style.format(
            {m: (lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) and x > 0 else ("-" if x == 0 else f"{x:,d}")) for
             m in all_months_sorted}, na_rep="-"
        ).set_properties(**{'text-align': 'right'})
        st.dataframe(styled_design, use_container_width=True)
        st.write("")

        st.markdown("#### 🤝 დაკონტრაქტება")

        c_count_dict = {"სახელი და გვარი": "დაკონტრაქტება (რ-ბა)"}
        for m in all_months_sorted:
            cnt = len(furniture_calc_df[(furniture_calc_df['month_year'] == m) & (
                    furniture_calc_df['contract_type'] == "დაკონტრაქტება")]) if not furniture_calc_df.empty else 0
            c_count_dict[m] = int(cnt)

        c_sum_dict = {"სახელი და გვარი": "დაკონტრაქტება (თანხა)"}
        for m in all_months_sorted:
            s = furniture_calc_df[
                (furniture_calc_df['month_year'] == m) & (furniture_calc_df['contract_type'] == "დაკონტრაქტება")][
                'amount'].sum() if not furniture_calc_df.empty else 0
            c_sum_dict[m] = round(float(s), 2)

        df_contract_info = pd.DataFrame([c_count_dict, c_sum_dict])
        df_contract_info.index = ["🤝", "💵"]

        styled_contract = df_contract_info.style.format(
            {m: (lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) and x > 0 else ("-" if x == 0 else f"{x:,d}")) for
             m in all_months_sorted}, na_rep="-"
        ).set_properties(**{'text-align': 'right'})
        st.dataframe(styled_contract, use_container_width=True)
        st.write("")

        st.markdown("#### 📈 დაკონტრაქტების % (ინდივიდუალური და გუნდური)")

        kpi_rows = []
        for d in designer_options:
            des_kpi_dict = {"სახელი და გვარი": f"{d} - დაკონტრაქტების %"}
            for m in all_months_sorted:
                m_data = furniture_calc_df[(furniture_calc_df['month_year'] == m) & (
                        furniture_calc_df['designer_name'] == d)] if not furniture_calc_df.empty else pd.DataFrame()
                d_cnt = len(m_data[m_data['contract_type'] == "დიზაინი"]) if not m_data.empty else 0
                c_cnt = len(m_data[m_data['contract_type'] == "დაკონტრაქტება"]) if not m_data.empty else 0
                if d_cnt > 0:
                    kpi = (c_cnt / d_cnt) * 100
                    des_kpi_dict[m] = f"{kpi:.1f}%"
                else:
                    des_kpi_dict[m] = "-"
            kpi_rows.append(des_kpi_dict)

        team_kpi_dict = {"სახელი და გვარი": "🌟 გუნდური დაკონტრაქტების %"}
        for m in all_months_sorted:
            m_data = furniture_calc_df[
                furniture_calc_df['month_year'] == m] if not furniture_calc_df.empty else pd.DataFrame()
            d_cnt = len(m_data[m_data['contract_type'] == "დიზაინი"]) if not m_data.empty else 0
            c_cnt = len(m_data[m_data['contract_type'] == "დაკონტრაქტება"]) if not m_data.empty else 0
            if d_cnt > 0:
                kpi = (c_cnt / d_cnt) * 100
                team_kpi_dict[m] = f"{kpi:.1f}%"
            else:
                team_kpi_dict[m] = "-"
        kpi_rows.append(team_kpi_dict)

        df_kpi = pd.DataFrame(kpi_rows)
        kpi_emojis = ["🔹", "🔸", "▪️", "▫️", "🔹", "🔸"]
        df_kpi.index = [kpi_emojis[i % len(kpi_emojis)] + (" " * i) for i in range(len(designer_options))] + ["🌟"]

        styled_kpi = df_kpi.style.set_properties(**{'text-align': 'right'})
        st.dataframe(styled_kpi, use_container_width=True)

        final_report_df = pd.concat([df_des_table, df_design_info, df_contract_info, df_kpi])

        csv_data_report = final_report_df.to_csv(index=True, sep=';').encode('utf-8-sig')
        col_btn.download_button(
            label="📥 ექსპორტი Excel-ში",
            data=csv_data_report,
            file_name=f"salary_report_{selected_year}.csv",
            mime="text/csv",
            key="download_report"
        )

        st.markdown("---")

        st.write("### 📋 ყველა შეყვანილი პროექტის დეტალური ბაზა და რეესტრი")

        col_search1, col_search2, col_search3, col_search4 = st.columns(4)
        with col_search1:
            search_source = st.selectbox("🔍 ძებნა წყაროთი", ["ყველა"] + df[
                'project_source'].unique().tolist() if 'project_source' in df.columns else ["ყველა"])
        with col_search2:
            search_cat = st.selectbox("🔍 ძებნა კატეგორიით", ["ყველა", "ინდივიდუალური", "კორპორატიული"])
        with col_search3:
            search_client = st.text_input("🔍 ძებნა დამკვეთით", value="")
        with col_search4:
            search_designer = st.text_input("🔍 ძებნა დიზაინერით", value="")

        col_date_filter, col_metric = st.columns([2, 1])
        with col_date_filter:
            date_range = st.date_input("📅 ფილტრი თარიღებით (საწყისი - საბოლოო)", value=())

        filtered_export_base = filtered_calc_df.copy()

        if search_source != "ყველა":
            filtered_export_base = filtered_export_base[filtered_export_base['project_source'] == search_source]
        if search_cat != "ყველა":
            filtered_export_base = filtered_export_base[filtered_export_base['project_category'] == search_cat]
        if search_client.strip():
            filtered_export_base = filtered_export_base[
                filtered_export_base['client_name'].str.contains(search_client.strip(), case=False, na=False)]
        if search_designer.strip():
            filtered_export_base = filtered_export_base[
                filtered_export_base['designer_name'].str.contains(search_designer.strip(), case=False, na=False)]

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_export_base = filtered_export_base[
                (filtered_export_base['created_at'].dt.date >= start_date) &
                (filtered_export_base['created_at'].dt.date <= end_date)
                ]

        total_turnover = filtered_export_base['amount'].sum() if not filtered_export_base.empty else 0.0
        with col_metric:
            st.metric(label="💰 ჯამური ნავაჭრი (მოფილტრული)", value=f"{total_turnover:,.2f} ₾")

        filtered_export_base['file_status'] = filtered_export_base['has_file'].apply(
            lambda x: "✅ ატვირთულია" if x else "❌ არ არის")

        detailed_export_df = filtered_export_base[
            ['id', 'created_at', 'project_source', 'product_type', 'contract_type', 'contract_no', 'project_category',
             'client_name', 'amount',
             'designer_name', 'salary_designer', 'delivery_date_str', 'file_status']
        ].copy() if not filtered_calc_df.empty else pd.DataFrame(
            columns=['id', 'created_at', 'project_source', 'product_type', 'contract_type', 'contract_no',
                     'project_category', 'client_name',
                     'amount', 'designer_name', 'salary_designer', 'delivery_date_str', 'file_status'])

        if not detailed_export_df.empty:
            detailed_export_df.columns = [
                'ID',
                'შექმნის თარიღი',
                'პროექტის წყარო',
                'პროდუქცია',
                'ხელშეკრულების ტიპი',
                'ხელშეკრულების №',
                'პროექტის კატეგორია',
                'დამკვეთი',
                'თანხა',
                'დიზაინერი',
                'დიზაინერის ხელფასი',
                'ჩაბარების თარიღი',
                'ფაილი'
            ]
            detailed_export_df.index = range(1, len(detailed_export_df) + 1)

        styled_detailed = detailed_export_df.style.format({
            'თანხა': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-",
            'დიზაინერის ხელფასი': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
        }, na_rep="-").set_properties(**{'text-align': 'right'})

        st.dataframe(styled_detailed, use_container_width=True)

        # 📎 ხელშეკრულების ფაილის ატვირთვა / გადმოწერა / წაშლა
        st.write("#### 📎 ხელშეკრულების ფაილის ატვირთვა / ჩამოტვირთვა")
        if not detailed_export_df.empty:
            col_doc1, col_doc2 = st.columns(2)
            with col_doc1:
                selected_proj_no = st.selectbox("აირჩიეთ ხელშეკრულების № ფაილის მართვისთვის",
                                                detailed_export_df['ხელშეკრულების №'].tolist())

                # ვამოწმებთ სესიის ცვლადს ფაილის ველის გასასუფთავებლად
                if "file_uploader_key" not in st.session_state:
                    st.session_state["file_uploader_key"] = 0

                uploaded_file = st.file_uploader("ატვირთეთ ხელშეკრულების ფაილი (PDF, Word, PNG, JPG)",
                                                 type=['pdf', 'docx', 'doc', 'png', 'jpg'],
                                                 key=f"contract_file_uploader_{st.session_state['file_uploader_key']}")

                if st.button("📤 ფაილის ატვირთვა"):
                    if uploaded_file and selected_proj_no:
                        file_bytes = uploaded_file.read()
                        file_name = uploaded_file.name
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE projects SET contract_file_data = %s, contract_file_name = %s WHERE contract_no = %s",
                                (psycopg2.Binary(file_bytes), file_name, selected_proj_no))
                            conn.commit()
                            cur.close()
                            conn.close()

                            # ვცვლით გასაღებს, რომ ფაილის ასატვირთი ველი სრულად განულდეს
                            st.session_state["file_uploader_key"] += 1

                            st.success(f"ფაილი '{file_name}' წარმატებით მიება ხელშეკრულებას № {selected_proj_no}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"შეცდომა ფაილის ატვირთვისას: {e}")
                    else:
                        st.warning("გთხოვთ აირჩიოთ ფაილი!")

            with col_doc2:
                if selected_proj_no:
                    target_row = df[df['contract_no'] == selected_proj_no]
                    if not target_row.empty and target_row.iloc[0]['has_file']:
                        st.write(f"📄 **არსებული ფაილი:** {target_row.iloc[0]['contract_file_name']}")
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()
                            cur.execute(
                                "SELECT contract_file_data, contract_file_name FROM projects WHERE contract_no = %s",
                                (selected_proj_no,))
                            f_data, f_name = cur.fetchone()
                            cur.close()
                            conn.close()
                            if f_data:
                                st.download_button(
                                    label=f"📥 გადმოწერა ({f_name})",
                                    data=bytes(f_data),
                                    file_name=f_name,
                                    mime="application/octet-stream",
                                    key=f"dl_file_{selected_proj_no}"
                                )

                                # --- 🗑️ ფაილის წაშლის დასტურის მექანიზმი ---
                                st.write("")
                                with st.popover("🗑️ ფაილის წაშლა"):
                                    st.warning("ნამდვილად გსურთ ატვირთული ფაილის წაშლა?")
                                    col_del_yes, col_del_no = st.columns(2)

                                    with col_del_yes:
                                        if st.button("დიახ", key=f"yes_del_{selected_proj_no}"):
                                            try:
                                                conn_del = psycopg2.connect(dbname=DB_NAME, user=DB_USER,
                                                                            password=DB_PASS, host=DB_HOST,
                                                                            port=DB_PORT)
                                                cur_del = conn_del.cursor()
                                                cur_del.execute(
                                                    "UPDATE projects SET contract_file_data = NULL, contract_file_name = NULL WHERE contract_no = %s",
                                                    (selected_proj_no,))
                                                conn_del.commit()
                                                cur_del.close()
                                                conn_del.close()
                                                st.success("ფაილი წარმატებით წაიშალა!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"შეცდომა წაშლისას: {e}")

                                    with col_del_no:
                                        if st.button("არა", key=f"no_del_{selected_proj_no}"):
                                            st.rerun()
                                # --------------------------------------------

                        except Exception as e:
                            st.error(f"შეცდომა ფაილის წამოღებისას: {e}")
                    else:
                        st.info("ამ ხელშეკრულებაზე ფაილი ჯერ ატვირთული არ არის.")

        csv_data_detailed = detailed_export_df.to_csv(index=True, sep=';').encode('utf-8-sig')
        st.download_button(
            label="📥 დეტალური რეესტრის ექსპორტი Excel-ში",
            data=csv_data_detailed,
            file_name=f"detailed_projects_{selected_year}.csv",
            mime="text/csv",
            key="download_detailed"
        )

    else:
        st.info("ბაზაში მონაცემები ჯერ არ არის. გამოიყენეთ მარცხენა პანელი პირველი პროექტის დასამატებლად.")

# ---------------- 2. ჩანაწერების რედაქტირება / წაშლა ----------------
with tab2:
    st.subheader("✏️ ჩანაწერების რედაქტირება / წაშლა")
    if not df.empty:
        selected_contract = st.selectbox("აირჩიეთ ხელშეკრულების ნომერი რედაქტირებისთვის", df['contract_no'].tolist())
        record_to_edit = df[df['contract_no'] == selected_contract].iloc[0]
        record_id = int(record_to_edit['id']) if 'id' in record_to_edit else None

        with st.form("edit_form"):
            curr_c_type = record_to_edit['contract_type']
            e_contract_type = st.selectbox("ხელშეკრულების ტიპი", contract_type_options,
                                           index=contract_type_options.index(
                                               curr_c_type) if curr_c_type in contract_type_options else 0)

            e_contract_no = st.text_input("ხელშეკრულების №", value=str(record_to_edit['contract_no']))

            curr_category = record_to_edit.get('project_category', 'ინდივიდუალური')
            e_project_category = st.selectbox("პროექტის კატეგორია", project_category_options,
                                              index=project_category_options.index(
                                                  curr_category) if curr_category in project_category_options else 0)

            e_client = st.text_input("დამკვეთი", value=str(record_to_edit['client_name']))

            curr_prod = record_to_edit['product_type']
            e_product_type = st.selectbox("პროდუქცია", product_options,
                                          index=product_options.index(curr_prod) if curr_prod in product_options else 0)

            e_amount = st.number_input("თანხა (₾)", value=float(record_to_edit['amount']), step=100.0, format="%.2f")

            curr_designer = record_to_edit['designer_name']

            if e_product_type == "კარი" or record_to_edit.get('project_source', '') == "Outsource - დიზაინით":
                e_designer = st.selectbox("დიზაინერი", ["ია პირტახია"])
            else:
                e_designer = st.selectbox("დიზაინერი", designer_options, index=designer_options.index(
                    curr_designer) if curr_designer in designer_options else 0)

            curr_delivery_str = record_to_edit.get('delivery_date_str', '')
            try:
                parsed_delivery_date = datetime.strptime(curr_delivery_str,
                                                         "%d %b, %Y") if curr_delivery_str else datetime.now()
            except:
                parsed_delivery_date = datetime.now()

            e_delivery_date = st.date_input("ჩაბარების თარიღი", value=parsed_delivery_date)
            e_delivery_date_str = e_delivery_date.strftime("%d %b, %Y")

            st.info(f"📅 შექმნის თარიღი (უცვლელი): {record_to_edit['created_at']}")

            col1, col2 = st.columns(2)
            update_btn = col1.form_submit_button("🔄 განახლება")
            delete_btn = col2.form_submit_button("🗑️ ჩანაწერის წაშლა")

            if update_btn:
                try:
                    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE projects 
                        SET contract_type = %s, contract_no = %s, project_category = %s, client_name = %s, product_type = %s, amount = %s, designer_name = %s, delivery_date_str = %s 
                        WHERE id = %s
                    """, (e_contract_type, e_contract_no.strip(), e_project_category, e_client.strip(), e_product_type,
                          e_amount,
                          e_designer, e_delivery_date_str, record_id))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("მონაცემები წარმატებით განახლდა!")
                    st.rerun()
                except Exception as e:
                    st.error(f"შეცდომა განახლებისას: {e}")

            if delete_btn:
                try:
                    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM projects WHERE id = %s", (record_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.warning("ჩანაწერი წაშლილია!")
                    st.rerun()
                except Exception as e:
                    st.error(f"შეცდომა წაშლისას: {e}")
    else:
        st.info("რედაქტირებისთვის მონაცემები არ მოიძებნა.")

# ---------------- 3. ცნობარების მართვა ----------------
with tab3:
    st.subheader("⚙️ ცნობარების მართვა")

    col_des_top, col_mgr_top = st.columns(2)

    with col_des_top:
        st.markdown("### 🧑‍🎨 დიზაინერების მართვა და პირობები")
        if not designers_df.empty:
            display_des = designers_df.copy()
            if not display_des.empty:
                if 'design_fee_pct' not in display_des.columns:
                    display_des['design_fee_pct'] = 0.50
                if 'commission_pct' not in display_des.columns:
                    display_des['commission_pct'] = 0.02

                display_des['დიზაინის %'] = display_des['design_fee_pct'].apply(lambda x: f"{float(x) * 100:.2f}%")
                display_des['დაკონტრაქტების %'] = display_des['commission_pct'].apply(
                    lambda x: f"{float(x) * 100:.2f}%")

                display_des_table = display_des[['full_name', 'დიზაინის %', 'დაკონტრაქტების %']].reset_index(drop=True)
                display_des_table.index = range(1, len(display_des_table) + 1)
                st.dataframe(display_des_table, use_container_width=True)
            else:
                st.info("დიზაინერები არ მოიძებნა.")
        else:
            st.info("დიზაინერები არ მოიძებნა.")

    with col_mgr_top:
        st.markdown("### 📋 მენეჯერების მართვა და პირობები")
        if not managers_df.empty:
            display_mgr = managers_df.copy()
            pct_col_name = 'manager_pct' if 'manager_pct' in display_mgr.columns else display_mgr.columns[2]
            display_mgr['ნავაჭრის %'] = display_mgr[pct_col_name].apply(
                lambda x: f"{float(x) * 100:.2f}%" if pd.notnull(x) else "0.00%")
            display_mgr_table = display_mgr[['full_name', 'ნავაჭრის %']].reset_index(drop=True)
            display_mgr_table.columns = ['მენეჯერი', 'ჯამური ნავაჭრის %']
            display_mgr_table.index = range(1, len(display_mgr_table) + 1)
            st.dataframe(display_mgr_table, use_container_width=True)
        else:
            st.info("მენეჯერები არ მოიძებნა.")

    st.markdown("---")

    col_des_add, col_mgr_add = st.columns(2)

    with col_des_add:
        with st.form("add_designer_form", clear_on_submit=True):
            st.write("➕ **ახალი დიზაინერის დამატება**")
            new_designer_name = st.text_input("სახელი და გვარი", value="")
            des_pct_input = st.number_input("დიზაინის პროცენტი (%)", min_value=0.0, max_value=100.0, value=0.0,
                                            step=5.0)
            contract_pct_input = st.number_input("დაკონტრაქტების პროცენტი (%)", min_value=0.0, max_value=100.0,
                                                 value=0.0, step=0.5)

            add_des_btn = st.form_submit_button("➕ დამატება")

            if add_des_btn:
                if not new_designer_name.strip():
                    st.error("გთხოვთ შეიყვანოთ სახელი და გვარი!")
                else:
                    try:
                        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                port=DB_PORT)
                        cur = conn.cursor()

                        des_fee_decimal = des_pct_input / 100.0
                        contract_decimal = contract_pct_input / 100.0

                        cur.execute(
                            "INSERT INTO designers (full_name, design_fee_pct, commission_pct) VALUES (%s, %s, %s)",
                            (new_designer_name.strip(), des_fee_decimal, contract_decimal))
                        cur.execute(
                            "INSERT INTO designer_history (designer_name, old_design_fee_pct, design_fee_pct, old_commission_pct, commission_pct) VALUES (%s, %s, %s, %s, %s)",
                            (new_designer_name.strip(), None, des_fee_decimal, None, contract_decimal))

                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("დიზაინერი წარმატებით დაემატა!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"შეცდომა: {e}")

    with col_mgr_add:
        with st.form("add_manager_form", clear_on_submit=True):
            st.write("➕ **ახალი მენეჯერის დამატება**")
            new_mgr_name = st.text_input("მენეჯერის სახელი და გვარი", value="")
            mgr_pct_input = st.number_input("ჯამური ნავაჭრის პროცენტი (%)", min_value=0.0, max_value=100.0, value=0.0,
                                            step=0.05, format="%.2f")

            add_mgr_btn = st.form_submit_button("➕ მენეჯერის დამატება")

            if add_mgr_btn:
                if not new_mgr_name.strip():
                    st.error("გთხოვთ შეიყვანოთ სახელი და გვარი!")
                else:
                    try:
                        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                port=DB_PORT)
                        cur = conn.cursor()

                        mgr_decimal = mgr_pct_input / 100.0

                        cur.execute("INSERT INTO managers (full_name, manager_pct) VALUES (%s, %s)",
                                    (new_mgr_name.strip(), mgr_decimal))
                        cur.execute(
                            "INSERT INTO manager_history (manager_name, old_manager_pct, manager_pct) VALUES (%s, %s, %s)",
                            (new_mgr_name.strip(), None, mgr_decimal))

                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("მენეჯერი წარმატებით დაემატა!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"შეცდომა: {e}")

    col_des_edit, col_mgr_edit = st.columns(2)

    with col_des_edit:
        st.write("✏️ **არსებული დიზაინერის პროცენტების შეცვლა**")
        if not designers_df.empty:
            edit_options = designers_df['full_name'].tolist()
            if edit_options:
                des_to_edit = st.selectbox("აირჩიეთ დიზაინერი", edit_options, key="sel_des_to_edit")

                curr_row = designers_df[designers_df['full_name'] == des_to_edit].iloc[0]
                curr_des_pct = float(curr_row['design_fee_pct']) * 100 if 'design_fee_pct' in curr_row and pd.notnull(
                    curr_row['design_fee_pct']) else 50.0
                curr_com_pct = float(curr_row['commission_pct']) * 100 if 'commission_pct' in curr_row and pd.notnull(
                    curr_row['commission_pct']) else 2.0

                with st.form("edit_designer_form"):
                    new_des_pct = st.number_input("ახალი დიზაინის პროცენტი (%)", min_value=0.0, max_value=100.0,
                                                  value=curr_des_pct, step=5.0)
                    new_com_pct = st.number_input("ახალი დაკონტრაქტების პროცენტი (%)", min_value=0.0, max_value=100.0,
                                                  value=curr_com_pct, step=0.5)

                    update_des_btn = st.form_submit_button("🔄 პროცენტების განახლება")

                    if update_des_btn:
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()

                            old_des_fee_val = float(
                                curr_row['design_fee_pct']) if 'design_fee_pct' in curr_row and pd.notnull(
                                curr_row['design_fee_pct']) else None
                            old_com_val = float(
                                curr_row['commission_pct']) if 'commission_pct' in curr_row and pd.notnull(
                                curr_row['commission_pct']) else None

                            cur.execute("""
                                UPDATE designers 
                                SET design_fee_pct = %s, commission_pct = %s 
                                WHERE full_name = %s
                            """, (new_des_pct / 100.0, new_com_pct / 100.0, des_to_edit))

                            cur.execute("""
                                INSERT INTO designer_history (designer_name, old_design_fee_pct, design_fee_pct, old_commission_pct, commission_pct) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (des_to_edit, old_des_fee_val, new_des_pct / 100.0, old_com_val, new_com_pct / 100.0))

                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"'{des_to_edit}' პროცენტები განახლდა და ჩაიწერა ისტორიაში!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"შეცდომა განახლებისას: {e}")

    with col_mgr_edit:
        st.write("✏️ **არსებული მენეჯერის პროცენტის შეცვლა**")
        if not managers_df.empty:
            mgr_options = managers_df['full_name'].tolist()
            if mgr_options:
                mgr_to_edit = st.selectbox("აირჩიეთ მენეჯერი", mgr_options, key="sel_mgr_to_edit")

                curr_m_row = managers_df[managers_df['full_name'] == mgr_to_edit].iloc[0]
                curr_m_pct = float(curr_m_row['manager_pct']) * 100 if 'manager_pct' in curr_m_row and pd.notnull(
                    curr_m_row['manager_pct']) else 0.35

                with st.form("edit_manager_form"):
                    new_m_pct = st.number_input("ახალი ნავაჭრის პროცენტი (%)", min_value=0.0, max_value=100.0,
                                                value=curr_m_pct, step=0.05, format="%.2f")

                    update_mgr_btn = st.form_submit_button("🔄 მენეჯერის პროცენტის განახლება")

                    if update_mgr_btn:
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()

                            old_m_pct_val = float(
                                curr_m_row['manager_pct']) if 'manager_pct' in curr_m_row and pd.notnull(
                                curr_m_row['manager_pct']) else None

                            cur.execute("""
                                UPDATE managers 
                                SET manager_pct = %s 
                                WHERE full_name = %s
                            """, (new_m_pct / 100.0, mgr_to_edit))

                            cur.execute("""
                                INSERT INTO manager_history (manager_name, old_manager_pct, manager_pct) 
                                VALUES (%s, %s, %s)
                            """, (mgr_to_edit, old_m_pct_val, new_m_pct / 100.0))

                            conn.commit()
                            cur.close()
                            conn.close()
                            st.success(f"'{mgr_to_edit}' პროცენტი განახლდა და ჩაიწერა ისტორიაში!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"შეცდომა განახლებისას: {e}")

    col_des_del, col_mgr_del = st.columns(2)

    with col_des_del:
        if not designers_df.empty:
            del_designer_options = designers_df['full_name'].tolist()
            if del_designer_options:
                with st.form("delete_designer_form", clear_on_submit=True):
                    st.write("🗑️ **არსებული დიზაინერის წაშლა**")
                    des_to_delete = st.selectbox("აირჩიეთ დიზაინერი წაშლისთვის", del_designer_options)
                    delete_des_btn = st.form_submit_button("🗑️ დიზაინერის წაშლა")

                    if delete_des_btn:
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()
                            cur.execute("DELETE FROM designers WHERE full_name = %s", (des_to_delete,))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.warning(f"დიზაინერი '{des_to_delete}' წაშლილია!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"შეცდომა წაშლისას: {e}")

    with col_mgr_del:
        if not managers_df.empty:
            del_mgr_options = managers_df['full_name'].tolist()
            if del_mgr_options:
                with st.form("delete_manager_form", clear_on_submit=True):
                    st.write("🗑️ **არსებული მენეჯერის წაშლა**")
                    mgr_to_delete = st.selectbox("აირჩიეთ მენეჯერი წაშლისთვის", del_mgr_options)
                    delete_mgr_btn = st.form_submit_button("🗑️ მენეჯერის წაშლა")

                    if delete_mgr_btn:
                        try:
                            conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST,
                                                    port=DB_PORT)
                            cur = conn.cursor()
                            cur.execute("DELETE FROM managers WHERE full_name = %s", (mgr_to_delete,))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.warning(f"მენეჯერი '{mgr_to_delete}' წაშლილია!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"შეცდომა წაშლისას: {e}")

    st.markdown("---")
    st.markdown("### 📜 დიზაინერებისა და მენეჯერების პროცენტების ცვლილების ისტორია")

    col_hist1, col_hist2 = st.columns(2)
    with col_hist1:
        st.markdown("#### 🧑‍🎨 დიზაინერების ისტორია")
        if not history_df.empty:
            display_hist = pd.DataFrame()
            display_hist['ID'] = history_df['id']
            display_hist['დიზაინერი'] = history_df['designer_name']

            display_hist['დიზაინის % (ძველი ➔ ახალი)'] = history_df.apply(
                lambda r: f"{float(r['old_design_fee_pct']) * 100:.2f}% ➔ {float(r['design_fee_pct']) * 100:.2f}%"
                if 'old_design_fee_pct' in r and pd.notnull(r['old_design_fee_pct'])
                else f"საწყისი ➔ {float(r['design_fee_pct']) * 100:.2f}%", axis=1
            )

            display_hist['დაკონტრაქტების % (ძველი ➔ ახალი)'] = history_df.apply(
                lambda r: f"{float(r['old_commission_pct']) * 100:.2f}% ➔ {float(r['commission_pct']) * 100:.2f}%"
                if 'old_commission_pct' in r and pd.notnull(r['old_commission_pct'])
                else f"საწყისი ➔ {float(r['commission_pct']) * 100:.2f}%", axis=1
            )

            display_hist['ცვლილების თარიღი'] = history_df['changed_at']
            display_hist.index = range(1, len(display_hist) + 1)
            st.dataframe(display_hist, use_container_width=True)
        else:
            st.info("დიზაინერების ისტორია ცარიელია.")

    with col_hist2:
        st.markdown("#### 📋 მენეჯერების ისტორია")
        if not manager_history_df.empty:
            display_m_hist = pd.DataFrame()
            display_m_hist['ID'] = manager_history_df['id']
            display_m_hist['მენეჯერი'] = manager_history_df['manager_name']

            pct_col_name = 'manager_pct' if 'manager_pct' in manager_history_df.columns else manager_history_df.columns[
                2]

            display_m_hist['ნავაჭრის % (ძველი ➔ ახალი)'] = manager_history_df.apply(
                lambda r: f"{float(r['old_manager_pct']) * 100:.2f}% ➔ {float(r[pct_col_name]) * 100:.2f}%"
                if 'old_manager_pct' in r and pd.notnull(r['old_manager_pct'])
                else f"საწყისი ➔ {float(r[pct_col_name]) * 100:.2f}%" if pd.notnull(r[pct_col_name]) else "-", axis=1
            )

            display_m_hist['ცვლილების თარიღი'] = manager_history_df['changed_at']
            display_m_hist.index = range(1, len(display_m_hist) + 1)
            st.dataframe(display_m_hist, use_container_width=True)
        else:
            st.info("მენეჯერების ისტორია ცარიელია.")

# ---------------- 4. Outsource რეესტრი (ახალი ჩანართი) ----------------
with tab4:
    st.subheader("📋 Outsource ხელშეკრულებებისა და პროექტების რეესტრი")
    if not df.empty and 'project_source' in df.columns:
        outsource_df = df[df['project_source'].str.contains("Outsource", na=False)].copy()
        if not outsource_df.empty:
            outsource_display = outsource_df[[
                'created_at', 'project_source', 'outsource_designer_name', 'outsource_contract_no',
                'outsource_commission_pct', 'outsource_installments', 'product_type',
                'contract_no', 'project_category', 'client_name', 'amount', 'delivery_date_str'
            ]].copy()

            outsource_display['outsource_commission_pct'] = outsource_display['outsource_commission_pct'].apply(
                lambda x: f"{float(x) * 100:.2f}%" if pd.notnull(x) else "-")
            outsource_display.columns = [
                'შექმნის თარიღი', 'წყარო', 'Outsource დიზაინერი', 'Outsource ხელშეკრულების №',
                'საკომისიო (%)', 'ნაწილების რ-ბა', 'პროდუქცია', 'ხელშეკრულების №',
                'პროექტის კატეგორია', 'დამკვეთი', 'თანხა (₾)', 'ჩაბარების თარიღი'
            ]
            outsource_display.index = range(1, len(outsource_display) + 1)

            styled_outsource = outsource_display.style.format({
                'თანხა (₾)': lambda x: f"{x:,.2f}" if pd.notnull(x) else "-"
            }, na_rep="-").set_properties(**{'text-align': 'right'})

            st.dataframe(styled_outsource, use_container_width=True)

            csv_outsource = outsource_display.to_csv(index=True, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Outsource რეესტრის ექსპორტი Excel-ში",
                data=csv_outsource,
                file_name="outsource_registry.csv",
                mime="text/csv",
                key="download_outsource_reg"
            )
        else:
            st.info("Outsource პროექტები ჯერ არ არის დამატებული.")
    else:
        st.info("ბაზაში მონაცემები არ მოიძებნა.")