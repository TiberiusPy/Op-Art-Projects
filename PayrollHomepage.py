import streamlit as st

st.set_page_config(
    page_title="Op-Art - მართვის სისტემა",
    page_icon="🛋️",
    layout="wide"
)

# 🎨 თანამედროვე, დახვეწილი CSS სტილები
st.markdown("""
    <style>
        /* მთავარი სათაურის გარანტირებული გადიდება */
        .custom-main-title {
            font-size: 48px !important;
            font-weight: 900 !important;
            color: #0F172A !important;
            margin-bottom: 5px !important;
            letter-spacing: -0.5px;
        }
        .custom-sub-text {
            font-size: 18px !important;
            color: #475569 !important;
            margin-bottom: 35px !important;
        }

        /* ბარათების (Cards) პრემიუმ დიზაინი */
        .card {
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E2E8F0;
            padding: 28px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            margin-bottom: 15px;
            transition: all 0.3s ease-in-out;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            border-color: #94A3B8;
        }

        /* ბარათის შიგნით სათაურები და ტექსტები */
        .card h3 {
            color: #1E293B;
            font-size: 22px;
            margin-bottom: 10px;
        }
        .card p {
            color: #64748B;
            font-size: 15px;
            line-height: 1.5;
            min-height: 45px;
        }

        /* ჰორიზონტალური ხაზი */
        hr {
            margin-top: 10px;
            margin-bottom: 30px;
            border-color: #E2E8F0;
        }
    </style>
""", unsafe_allow_html=True)

# მთავარი გადიდებული სათაური ძლიერი HTML ტეგით
st.markdown('<h1 class="custom-main-title">🛋️ Op-Art - კომპანიის მართვის ერთიანი სისტემა (ERP)</h1>',
            unsafe_allow_html=True)
st.markdown('<p class="custom-sub-text">მოგესალმებით! გთხოვთ აირჩიოთ სასურველი სამუშაო მიმართულება სისტემაში:</p>',
            unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# 6 მიმართულება გადანაწილებული 3 თანაბარ სვეტში
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    # 1. დიზაინერები
    st.markdown("""
        <div class="card">
            <h3>🧑‍🎨 დიზაინერები</h3>
            <p>დიზაინერების ხელფასები, პროექტები, დაკონტრაქტების % და რეესტრი.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: დიზაინერები", use_container_width=True, key="btn_des"):
        st.switch_page("pages/1_🎨_დიზაინერები.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. წარმოება
    st.markdown("""
        <div class="card">
            <h3>🏭 წარმოება</h3>
            <p>წარმოების პროცესები, ვადები და შესრულებული სამუშაოები.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: წარმოება", use_container_width=True, key="btn_prod"):
        st.info("მალე დაემატება...")

with col2:
    # 2. მყიდველის შეკვეთები
    st.markdown("""
        <div class="card">
            <h3>🛒 მყიდველის შეკვეთები</h3>
            <p>მომხმარებელთა შეკვეთები, სტატუსები და დეტალები.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: შეკვეთები", use_container_width=True, key="btn_orders"):
        st.switch_page("pages/2_🛒_მყიდველის_შეკვეთები.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. მონტაჟი
    st.markdown("""
        <div class="card">
            <h3>🛠️ მონტაჟი</h3>
            <p>მონტაჟის გრაფიკები, ბრიგადები და ჩაბარება.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: მონტაჟი", use_container_width=True, key="btn_inst"):
        st.info("მალე დაემატება...")

with col3:
    # 3. კონსტრუქტორები
    st.markdown("""
        <div class="card">
            <h3>📐 კონსტრუქტორები</h3>
            <p>კონსტრუქტორების დატვირთვა და პროექტების მართვა.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: კონსტრუქტორები", use_container_width=True, key="btn_const"):
        st.info("მალე დაემატება...")

    st.markdown("<br>", unsafe_allow_html=True)

    # 6. ბუღალტერია
    st.markdown("""
        <div class="card">
            <h3>📊 ბუღალტერია</h3>
            <p>ერთიანი ფინანსური უწყისი, ხელფასები და ანგარიშგება.</p>
        </div>
    """, unsafe_allow_html=True)
    if st.button("🚀 გადასვლა: ბუღალტერია", use_container_width=True, key="btn_acc"):
        st.info("მალე დაემატება...")

st.markdown("<hr style='margin-top: 50px;'>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8; font-size: 14px;'>© 2026 Op-Art. ყველა უფლება დაცულია.</p>",
            unsafe_allow_html=True)