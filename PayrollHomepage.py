import streamlit as st

st.set_page_config(
    page_title="Op-Art - მართვის სისტემა",
    page_icon="🛋️",
    layout="wide"
)

# ☁️ დიზაინი C: მინიმალისტური, ღია, სიის (რიგების) სტილი
st.markdown("""
<style>
    .stApp { background: #FAFAF7; }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #F1F0EA; }
    .block-container { padding-top: 3rem; max-width: 980px; }

    .top-line { font-size: 13px; font-weight: 700; letter-spacing: 2px; color: #B45309; margin-bottom: 10px; }
    .big-title {
        font-size: 44px; font-weight: 800; color: #111827; line-height: 1.15; margin: 0 0 10px 0;
        letter-spacing: -0.8px;
    }
    .sub-title { font-size: 17px; color: #6B7280; margin: 0 0 34px 0; }

    /* რიგები */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border: 1px solid #E7E5DE !important;
        border-radius: 16px !important;
        padding: 10px 14px;
        margin-bottom: 4px;
        transition: all 0.2s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #111827 !important;
        box-shadow: 0 10px 24px -14px rgba(17,24,39,0.35);
        transform: translateX(4px);
    }

    .num { font-size: 13px; font-weight: 800; color: #B45309; letter-spacing: 1px; margin-bottom: 6px; }
    .icon-wrap {
        width: 52px; height: 52px; border-radius: 14px; font-size: 26px;
        display:flex; align-items:center; justify-content:center;
    }
    .row-title { font-size: 19px; font-weight: 750; color: #111827; margin: 0 0 3px 0; }
    .row-desc  { font-size: 14.5px; color: #6B7280; margin: 0; line-height: 1.5; }
    .pill { font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px; margin-left: 8px; vertical-align: middle; }
    .pill-live { background: #DCFCE7; color: #15803D; }
    .pill-soon { background: #F3F4F6; color: #9CA3AF; }

    div[data-testid="stPageLink"] a {
        background: #111827; border-radius: 999px !important; min-height: 42px;
        justify-content: center; border: none !important; transition: background 0.2s ease;
    }
    div[data-testid="stPageLink"] a:hover { background: #B45309; }
    div[data-testid="stPageLink"] a p, div[data-testid="stPageLink"] a span { color: #FFFFFF !important; font-weight: 650; }
    .stButton > button:disabled {
        background: #F3F4F6 !important; color: #9CA3AF !important; border: 1px solid #E5E7EB !important;
        border-radius: 999px !important; min-height: 42px;
    }

    .footer { text-align:center; color:#9CA3AF; font-size:13.5px; margin-top:40px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="top-line">OP-ART · ERP</div>
<div class="big-title">კომპანიის მართვის ერთიანი სისტემა</div>
<p class="sub-title">მოგესალმებით! აირჩიეთ სასურველი სამუშაო მიმართულება.</p>
""", unsafe_allow_html=True)

# page = None → განყოფილება ჯერ არ არის აწყობილი
SECTIONS = [
    {"icon": "🧑‍🎨", "title": "დიზაინერები", "color": "#E0E7FF",
     "desc": "დიზაინერების ხელფასები, პროექტები, დაკონტრაქტების % და რეესტრი.",
     "page": "pages/1_Designers.py", "key": "designers"},
    {"icon": "🛒", "title": "მყიდველის შეკვეთები", "color": "#D1FAE5",
     "desc": "მომხმარებელთა შეკვეთები, სტატუსები და დეტალები.",
     "page": "pages/2_Orders.py", "key": "orders"},
    {"icon": "📐", "title": "კონსტრუქტორები", "color": "#EDE9FE",
     "desc": "კონსტრუქტორების დატვირთვა და პროექტების მართვა.",
     "page": None, "key": "constructors"},
    {"icon": "🏭", "title": "წარმოება", "color": "#FEF3C7",
     "desc": "წარმოების პროცესები, ვადები და შესრულებული სამუშაოები.",
     "page": None, "key": "production"},
    {"icon": "🛠️", "title": "მონტაჟი", "color": "#FCE7F3",
     "desc": "მონტაჟის გრაფიკები, ბრიგადები და ჩაბარება.",
     "page": None, "key": "install"},
    {"icon": "📊", "title": "ბუღალტერია", "color": "#E0F2FE",
     "desc": "ერთიანი ფინანსური უწყისი, ხელფასები და ანგარიშგება.",
     "page": None, "key": "accounting"},
]

for i, sec in enumerate(SECTIONS, start=1):
    with st.container(border=True):
        c_icon, c_text, c_btn = st.columns([0.9, 5, 2.3], vertical_alignment="center", gap="medium")
        with c_icon:
            st.markdown(f'<div class="icon-wrap" style="background:{sec["color"]};">{sec["icon"]}</div>',
                        unsafe_allow_html=True)
        with c_text:
            pill = ('<span class="pill pill-live">მუშაობს</span>' if sec["page"]
                    else '<span class="pill pill-soon">მალე</span>')
            st.markdown(f"""
                <div class="num">{i:02d}</div>
                <div class="row-title">{sec['title']}{pill}</div>
                <p class="row-desc">{sec['desc']}</p>
            """, unsafe_allow_html=True)
        with c_btn:
            if sec["page"]:
                st.page_link(sec["page"], label="გახსნა", icon="→", use_container_width=True)
            else:
                st.button("მალე", disabled=True, use_container_width=True, key=f"btn_{sec['key']}")

st.markdown('<div class="footer">© 2026 Op-Art. ყველა უფლება დაცულია.</div>', unsafe_allow_html=True)