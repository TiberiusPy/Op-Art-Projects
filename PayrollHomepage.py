import streamlit as st

# 1. გვერდის კონფიგურაცია აუცილებლად თავში უნდა იყოს
st.set_page_config(
    page_title="Op-Art - მართვის სისტემა",
    page_icon="🛋️",
    layout="wide"
)

# 🎨 სტილები
st.markdown("""
<style>
    /* ზედა ცარიელი სივრცის შემცირება */
    .block-container { padding-top: 2.2rem; max-width: 1200px; }

    /* ---------- HERO ---------- */
    .hero {
        background: linear-gradient(120deg, #0F172A 0%, #1E3A8A 55%, #2563EB 100%);
        border-radius: 22px;
        padding: 42px 44px;
        margin-bottom: 34px;
        box-shadow: 0 18px 40px -18px rgba(30, 58, 138, 0.55);
        position: relative;
        overflow: hidden;
    }
    .hero::after {
        content: "";
        position: absolute;
        right: -60px; top: -60px;
        width: 260px; height: 260px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.07);
    }
    .hero::before {
        content: "";
        position: absolute;
        right: 120px; bottom: -90px;
        width: 200px; height: 200px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.05);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.14);
        color: #DBEAFE;
        font-size: 13px;
        font-weight: 600;
        padding: 5px 14px;
        border-radius: 999px;
        margin-bottom: 14px;
        letter-spacing: 0.3px;
    }
    .hero h1 {
        color: #FFFFFF !important;
        font-size: 40px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
        margin: 0 0 10px 0 !important;
        padding: 0 !important;
    }
    .hero p {
        color: #BFDBFE !important;
        font-size: 17px !important;
        margin: 0 !important;
    }

    .section-title {
        font-size: 20px;
        font-weight: 700;
        margin: 4px 0 16px 4px;
        opacity: 0.9;
    }

    /* ---------- ბარათები ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 18px !important;
        border: 1px solid rgba(100, 116, 139, 0.25) !important;
        padding: 6px 8px 4px 8px;
        transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
        background: rgba(148, 163, 184, 0.06);
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 22px 34px -18px rgba(15, 23, 42, 0.35);
        border-color: rgba(37, 99, 235, 0.55) !important;
    }

    .card-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
    .icon-wrap {
        width: 54px; height: 54px;
        border-radius: 15px;
        display: flex; align-items: center; justify-content: center;
        font-size: 28px;
    }
    .pill {
        font-size: 12px; font-weight: 700;
        padding: 4px 11px; border-radius: 999px;
    }
    .pill-live { background: rgba(16, 185, 129, 0.16); color: #059669; }
    .pill-soon { background: rgba(148, 163, 184, 0.22); color: #64748B; }

    .card-title { font-size: 21px; font-weight: 750; margin: 0 0 8px 0; }
    .card-desc  { font-size: 14.5px; line-height: 1.55; opacity: 0.72; min-height: 66px; margin: 0 0 6px 0; }

    /* ღილაკები / ბმულები ბარათებში */
    div[data-testid="stPageLink"] a, div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
        border-radius: 12px !important;
        font-weight: 650 !important;
        min-height: 44px;
    }
    div[data-testid="stPageLink"] a {
        background: linear-gradient(120deg, #1D4ED8, #2563EB);
        color: #FFFFFF !important;
        justify-content: center;
        border: none !important;
        transition: filter 0.2s ease;
    }
    div[data-testid="stPageLink"] a:hover { filter: brightness(1.12); }
    div[data-testid="stPageLink"] a p, div[data-testid="stPageLink"] a span { color: #FFFFFF !important; }

    /* ---------- ფუტერი ---------- */
    .footer { text-align: center; color: #94A3B8; font-size: 13.5px; margin-top: 46px; padding-top: 18px;
              border-top: 1px solid rgba(148, 163, 184, 0.3); }
</style>
""", unsafe_allow_html=True)

# ---------- HERO ----------
st.markdown("""
<div class="hero">
    <div class="hero-badge">🛋️ Op-Art · ERP</div>
    <h1>კომპანიის მართვის ერთიანი სისტემა</h1>
    <p>მოგესალმებით! აირჩიეთ სასურველი სამუშაო მიმართულება.</p>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">სამუშაო მიმართულებები</div>', unsafe_allow_html=True)

# ---------- განყოფილებები ----------
# page = None  →  განყოფილება ჯერ არ არის აწყობილი
SECTIONS = [
    {"icon": "🧑‍🎨", "title": "დიზაინერები", "color": "rgba(37, 99, 235, 0.14)",
     "desc": "დიზაინერების ხელფასები, პროექტები, დაკონტრაქტების % და რეესტრი.",
     "page": "pages/1_Designers.py", "key": "designers"},
    {"icon": "🛒", "title": "მყიდველის შეკვეთები", "color": "rgba(16, 185, 129, 0.15)",
     "desc": "მომხმარებელთა შეკვეთები, სტატუსები და დეტალები.",
     "page": "pages/2_Orders.py", "key": "orders"},
    {"icon": "📐", "title": "კონსტრუქტორები", "color": "rgba(139, 92, 246, 0.15)",
     "desc": "კონსტრუქტორების დატვირთვა და პროექტების მართვა.",
     "page": None, "key": "constructors"},
    {"icon": "🏭", "title": "წარმოება", "color": "rgba(245, 158, 11, 0.17)",
     "desc": "წარმოების პროცესები, ვადები და შესრულებული სამუშაოები.",
     "page": None, "key": "production"},
    {"icon": "🛠️", "title": "მონტაჟი", "color": "rgba(236, 72, 153, 0.15)",
     "desc": "მონტაჟის გრაფიკები, ბრიგადები და ჩაბარება.",
     "page": None, "key": "install"},
    {"icon": "📊", "title": "ბუღალტერია", "color": "rgba(14, 165, 233, 0.15)",
     "desc": "ერთიანი ფინანსური უწყისი, ხელფასები და ანგარიშგება.",
     "page": None, "key": "accounting"},
]


def render_card(sec):
    with st.container(border=True):
        pill = ('<span class="pill pill-live">● მუშაობს</span>' if sec["page"]
                else '<span class="pill pill-soon">მალე</span>')
        st.markdown(f"""
            <div class="card-top">
                <div class="icon-wrap" style="background:{sec['color']};">{sec['icon']}</div>
                {pill}
            </div>
            <div class="card-title">{sec['title']}</div>
            <p class="card-desc">{sec['desc']}</p>
        """, unsafe_allow_html=True)

        if sec["page"]:
            st.page_link(sec["page"], label=f"გახსნა: {sec['title']}", icon="🚀", use_container_width=True)
        else:
            st.button("⏳ მალე დაემატება", disabled=True, use_container_width=True, key=f"btn_{sec['key']}")


# 2 რიგი x 3 სვეტი, ყველა ბარათი ერთნაირი სიმაღლის
for row_start in range(0, len(SECTIONS), 3):
    cols = st.columns(3, gap="large")
    for col, sec in zip(cols, SECTIONS[row_start:row_start + 3]):
        with col:
            render_card(sec)
    st.write("")

st.markdown('<div class="footer">© 2026 Op-Art. ყველა უფლება დაცულია.</div>', unsafe_allow_html=True)