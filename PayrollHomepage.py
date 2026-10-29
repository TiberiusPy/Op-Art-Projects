import streamlit as st

st.set_page_config(
    page_title="Op-Art - მართვის სისტემა",
    page_icon="🛋️",
    layout="wide"
)

# 🌙 დიზაინი B: მუქი, "მინის" ბარათები, ნეონური აქცენტები
st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at 15% 0%, #1E1B4B 0%, #0B1020 45%, #070A14 100%);
    }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #0B1020; border-right: 1px solid rgba(255,255,255,0.07); }
    [data-testid="stSidebarNav"] span, [data-testid="stSidebarNav"] a { color: #CBD5E1 !important; }
    .block-container { padding-top: 2.4rem; max-width: 1200px; }

    .hero { margin-bottom: 38px; }
    .hero-tag {
        display: inline-block; font-size: 12.5px; font-weight: 700; letter-spacing: 1.4px;
        color: #A5B4FC; background: rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.35);
        padding: 5px 14px; border-radius: 999px; margin-bottom: 18px;
    }
    .hero h1 {
        font-size: 46px !important; font-weight: 800 !important; line-height: 1.15 !important;
        margin: 0 0 12px 0 !important; padding: 0 !important;
        background: linear-gradient(90deg, #FFFFFF 0%, #C4B5FD 55%, #67E8F9 100%);
        -webkit-background-clip: text; background-clip: text; color: transparent !important;
    }
    .hero p { color: #94A3B8 !important; font-size: 17px !important; margin: 0 !important; }

    /* ბარათები */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,0.045);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 20px !important;
        padding: 8px 10px 6px 10px;
        transition: all 0.25s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px);
        border-color: rgba(167,139,250,0.7) !important;
        box-shadow: 0 0 0 1px rgba(167,139,250,0.25), 0 22px 40px -18px rgba(124,58,237,0.55);
    }

    .card-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
    .icon-wrap {
        width: 56px; height: 56px; border-radius: 16px; font-size: 28px;
        display:flex; align-items:center; justify-content:center;
        border: 1px solid rgba(255,255,255,0.12);
    }
    .pill { font-size: 12px; font-weight: 700; padding: 4px 11px; border-radius: 999px; }
    .pill-live { background: rgba(52,211,153,0.15); color: #6EE7B7; border: 1px solid rgba(52,211,153,0.35); }
    .pill-soon { background: rgba(148,163,184,0.12); color: #94A3B8; border: 1px solid rgba(148,163,184,0.25); }

    .card-title { font-size: 21px; font-weight: 750; color: #F8FAFC; margin: 0 0 8px 0; }
    .card-desc  { font-size: 14.5px; line-height: 1.55; color: #94A3B8; min-height: 66px; margin: 0 0 6px 0; }

    /* ღილაკები */
    div[data-testid="stPageLink"] a {
        background: linear-gradient(120deg, #7C3AED, #06B6D4);
        border: none !important; border-radius: 12px !important; min-height: 44px;
        justify-content: center; font-weight: 650 !important; transition: filter 0.2s ease;
    }
    div[data-testid="stPageLink"] a:hover { filter: brightness(1.15); }
    div[data-testid="stPageLink"] a p, div[data-testid="stPageLink"] a span { color: #FFFFFF !important; }
    .stButton > button:disabled {
        background: rgba(255,255,255,0.05) !important; color: #64748B !important;
        border: 1px dashed rgba(255,255,255,0.15) !important; border-radius: 12px !important; min-height: 44px;
    }

    .footer { text-align:center; color:#64748B; font-size:13.5px; margin-top:46px; padding-top:18px;
              border-top: 1px solid rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-tag">OP-ART · ERP</div>
    <h1>კომპანიის მართვის<br>ერთიანი სისტემა</h1>
    <p>მოგესალმებით! აირჩიეთ სასურველი სამუშაო მიმართულება.</p>
</div>
""", unsafe_allow_html=True)

# page = None → განყოფილება ჯერ არ არის აწყობილი
SECTIONS = [
    {"icon": "🧑‍🎨", "title": "დიზაინერები", "color": "rgba(99,102,241,0.25)",
     "desc": "დიზაინერების ხელფასები, პროექტები, დაკონტრაქტების % და რეესტრი.",
     "page": "pages/1_Designers.py", "key": "designers"},
    {"icon": "🛒", "title": "მყიდველის შეკვეთები", "color": "rgba(16,185,129,0.22)",
     "desc": "მომხმარებელთა შეკვეთები, სტატუსები და დეტალები.",
     "page": "pages/2_Orders.py", "key": "orders"},
    {"icon": "📐", "title": "კონსტრუქტორები", "color": "rgba(168,85,247,0.25)",
     "desc": "კონსტრუქტორების დატვირთვა და პროექტების მართვა.",
     "page": None, "key": "constructors"},
    {"icon": "🏭", "title": "წარმოება", "color": "rgba(245,158,11,0.22)",
     "desc": "წარმოების პროცესები, ვადები და შესრულებული სამუშაოები.",
     "page": None, "key": "production"},
    {"icon": "🛠️", "title": "მონტაჟი", "color": "rgba(236,72,153,0.22)",
     "desc": "მონტაჟის გრაფიკები, ბრიგადები და ჩაბარება.",
     "page": None, "key": "install"},
    {"icon": "📊", "title": "ბუღალტერია", "color": "rgba(14,165,233,0.22)",
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


for row_start in range(0, len(SECTIONS), 3):
    cols = st.columns(3, gap="large")
    for col, sec in zip(cols, SECTIONS[row_start:row_start + 3]):
        with col:
            render_card(sec)
    st.write("")

st.markdown('<div class="footer">© 2026 Op-Art. ყველა უფლება დაცულია.</div>', unsafe_allow_html=True)