import os
import re
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    inspect,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base


# ============================================================
# NOVA AGENCY ENTERPRISE v3.0
# TEK DOSYA SİSTEM
# ============================================================

APP_NAME = "Nova Agency"
DB_FILE = "nova_agency_enterprise.db"
DB_URL = f"sqlite:///{DB_FILE}"

ADMIN_PASSWORD = "1881938"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# ============================================================
# DATABASE MODELLERİ
# ============================================================

class PublisherDB(Base):
    __tablename__ = "publishers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    uid = Column(String, unique=True, index=True, nullable=False)

    contact_info = Column(String, default="")
    contact_type = Column(String, default="Telefon")

    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)

    tier = Column(String, default="Tier 1 (Başlangıç)")
    commission = Column(Float, default=50.0)

    status = Column(String, default="Yeni Kayıt")

    admin_note = Column(Text, default="")

    application_date = Column(DateTime, default=datetime.utcnow)

    last_contact_date = Column(DateTime, nullable=True)

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class PerformanceDB(Base):
    __tablename__ = "performance_history"

    id = Column(Integer, primary_key=True, index=True)

    publisher_uid = Column(String, index=True)
    publisher_name = Column(String)

    date = Column(String)

    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)

    note = Column(Text, default="")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class RoomDB(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)

    room_name = Column(String)
    room_id = Column(String, unique=True)

    owner = Column(String)

    active_hours = Column(Float, default=0.0)
    bonus_rate = Column(Float, default=5.0)

    status = Column(String, default="Aktif")


class PenaltyDB(Base):
    __tablename__ = "penalties"

    id = Column(Integer, primary_key=True, index=True)

    pub_name = Column(String)
    publisher_uid = Column(String, default="")

    reason = Column(String)

    deduction = Column(Integer, default=0)

    date = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class RewardDB(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)

    publisher_name = Column(String)
    publisher_uid = Column(String)

    reward_type = Column(String)

    reward_amount = Column(Integer, default=0)

    week = Column(String)

    status = Column(String, default="Bekliyor")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class FinanceDB(Base):
    __tablename__ = "finance"

    id = Column(Integer, primary_key=True, index=True)

    transaction_type = Column(String)

    description = Column(String)

    amount = Column(Float, default=0.0)

    currency = Column(String, default="TL")

    date = Column(String)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    action = Column(String)

    publisher_name = Column(String, default="")
    publisher_uid = Column(String, default="")

    details = Column(Text, default="")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )


# ============================================================
# DATABASE OLUŞTUR
# ============================================================

Base.metadata.create_all(bind=engine)


# ============================================================
# OTOMATİK MIGRATION
# ESKİ DATABASE SİLİNMEZ
# ============================================================

def database_migration():

    inspector = inspect(engine)

    tables = inspector.get_table_names()

    if "publishers" not in tables:
        Base.metadata.create_all(bind=engine)
        return

    existing = {
        c["name"]
        for c in inspector.get_columns("publishers")
    }

    migrations = {
        "contact_info": "TEXT DEFAULT ''",
        "contact_type": "TEXT DEFAULT 'Telefon'",
        "admin_note": "TEXT DEFAULT ''",
        "application_date": "DATETIME",
        "last_contact_date": "DATETIME",
        "updated_at": "DATETIME",
    }

    with engine.begin() as conn:

        for column, column_type in migrations.items():

            if column not in existing:

                conn.execute(
                    text(
                        f"ALTER TABLE publishers "
                        f"ADD COLUMN {column} {column_type}"
                    )
                )

    # Diğer tablolar
    Base.metadata.create_all(bind=engine)


database_migration()


# ============================================================
# DATABASE HELPER
# ============================================================

def get_db():
    return SessionLocal()


def audit(
    action,
    publisher_name="",
    publisher_uid="",
    details="",
):

    db = get_db()

    try:

        db.add(
            AuditLogDB(
                action=action,
                publisher_name=publisher_name,
                publisher_uid=publisher_uid,
                details=details,
            )
        )

        db.commit()

    finally:

        db.close()


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def tier_calculator(crystals):

    if crystals >= 100000:
        return "VIP Elit Yayıncı", 75.0

    if crystals >= 50000:
        return "Tier 3 (Profesyonel)", 65.0

    if crystals >= 20000:
        return "Tier 2 (Gelişen)", 58.0

    return "Tier 1 (Başlangıç)", 50.0


def target_calculator(tier):

    if tier == "VIP Elit Yayıncı":
        return 30, 100000

    if tier == "Tier 3 (Profesyonel)":
        return 25, 50000

    if tier == "Tier 2 (Gelişen)":
        return 20, 25000

    return 15, 15000


def is_phone(value):

    digits = re.sub(
        r"\D",
        "",
        str(value),
    )

    return len(digits) >= 8


def instagram_username(value):

    value = str(value).strip()

    value = value.replace(
        "https://instagram.com/",
        "",
    )

    value = value.replace(
        "https://www.instagram.com/",
        "",
    )

    value = value.replace("@", "")

    return value.strip("/")


def contact_button_html(contact):

    if not contact:
        return "İletişim bilgisi yok"

    contact = str(contact).strip()

    if is_phone(contact):

        phone = re.sub(
            r"[^\d+]",
            "",
            contact,
        )

        return (
            f"<a href='tel:{phone}' "
            f"style='color:#D4AF37;font-weight:bold;'>"
            f"📞 {contact}</a>"
        )

    username = instagram_username(contact)

    return (
        f"<a href='https://instagram.com/{username}' "
        f"target='_blank' "
        f"style='color:#D4AF37;font-weight:bold;'>"
        f"📷 @{username}</a>"
    )


def create_backup():

    db_path = Path(DB_FILE)

    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_name = (
        f"Nova_Agency_Backup_{timestamp}.db"
    )

    backup_path = Path(backup_name)

    shutil.copy2(
        db_path,
        backup_path,
    )

    return backup_path


def load_publishers():

    return pd.read_sql(
        """
        SELECT *
        FROM publishers
        ORDER BY id DESC
        """,
        con=engine,
    )


def load_rooms():

    return pd.read_sql(
        """
        SELECT *
        FROM rooms
        ORDER BY id DESC
        """,
        con=engine,
    )


def load_penalties():

    return pd.read_sql(
        """
        SELECT *
        FROM penalties
        ORDER BY id DESC
        """,
        con=engine,
    )


# ============================================================
# STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Nova Agency Enterprise",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
<style>

.stApp {
    background: #061A4A;
}

.main {
    background: #061A4A;
    color: #FFFFFF;
}

h1, h2, h3, h4 {
    color: #D4AF37 !important;
}

.stButton > button {
    background-color: #D4AF37;
    color: #061A4A;
    font-weight: 800;
    border: none;
    border-radius: 8px;
    width: 100%;
    min-height: 42px;
}

.stButton > button:hover {
    background-color: #F3C643;
    color: #061A4A;
}

.metric-card {
    background: #0F2D75;
    border: 1px solid #D4AF37;
    border-radius: 14px;
    padding: 18px;
    text-align: center;
    margin-bottom: 15px;
}

.metric-number {
    font-size: 30px;
    font-weight: 900;
    color: white;
}

.metric-title {
    color: #D4AF37;
    font-weight: 700;
}

.pub-card {
    background: #0A225C;
    border-left: 5px solid #D4AF37;
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
}

.info-card {
    background: #0F2D75;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
}

.warning-card {
    background: #593E00;
    border-left: 5px solid #D4AF37;
    border-radius: 10px;
    padding: 15px;
}

.success-card {
    background: #124A2B;
    border-left: 5px solid #4CAF50;
    border-radius: 10px;
    padding: 15px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    """
<h1 style="
text-align:center;
color:#D4AF37 !important;
">
⭐ NOVA
</h1>

<p style="
text-align:center;
color:white;
font-weight:bold;
">
AGENCY ENTERPRISE
</p>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Menü",
    [
        "👥 Yayıncı Portalı",
        "💼 Yönetim Paneli",
    ],
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Nova Agency Enterprise v3.0"
)


# ============================================================
# DATA
# ============================================================

publishers_df = load_publishers()
rooms_df = load_rooms()
penalties_df = load_penalties()


# ============================================================
# YAYINCI PORTALI
# ============================================================

if menu == "👥 Yayıncı Portalı":

    st.title(
        "⭐ Nova Agency"
    )

    st.subheader(
        "Yayıncı Merkezi"
    )

    tab_search, tab_apply = st.tabs(
        [
            "🔍 Performans Sorgula",
            "📝 Ajansa Başvur",
        ]
    )


    # --------------------------------------------------------
    # PERFORMANS
    # --------------------------------------------------------

    with tab_search:

        search = st.text_input(
            "Catchii ID veya adınız",
            placeholder="Örn: 12345678",
        )

        if search:

            search = search.lower().strip()

            if publishers_df.empty:

                st.info(
                    "Sistemde henüz yayıncı bulunmuyor."
                )

            else:

                result = publishers_df[
                    publishers_df["name"]
                    .fillna("")
                    .str.lower()
                    .str.contains(search)
                    |
                    publishers_df["uid"]
                    .fillna("")
                    .str.lower()
                    .str.contains(search)
                ]

                if result.empty:

                    st.warning(
                        "Yayıncı bulunamadı."
                    )

                else:

                    for _, row in result.iterrows():

                        target_hours, target_crystals = (
                            target_calculator(
                                row["tier"]
                            )
                        )

                        hour_percent = min(
                            100,
                            row["hours"]
                            / target_hours
                            * 100,
                        )

                        crystal_percent = min(
                            100,
                            row["crystals"]
                            / target_crystals
                            * 100,
                        )

                        gross = (
                            row["crystals"]
                            / 2500
                        )

                        net = (
                            gross
                            * row["commission"]
                            / 100
                        )

                        st.markdown(
                            f"""
<div class="pub-card">

<h2>
⭐ {row["name"]}
</h2>

<p>
<strong>Catchii ID:</strong>
{row["uid"]}
</p>

<p>
<strong>Durum:</strong>
{row["status"]}
</p>

<p>
<strong>Tier:</strong>
{row["tier"]}
</p>

<hr>

<h3>📊 Kota</h3>

<p>
🕒 Saat:
<strong>{row["hours"]:.1f}</strong>
/
{target_hours}
—
%{hour_percent:.0f}
</p>

<p>
💎 Kristal:
<strong>{row["crystals"]:,}</strong>
/
{target_crystals:,}
—
%{crystal_percent:.0f}
</p>

<hr>

<h3>💰 Tahmini Hakediş</h3>

<p>
Brüt:
<strong>${gross:.2f}</strong>
</p>

<p>
Net:
<strong>${net:.2f}</strong>
</p>

</div>
""",
                            unsafe_allow_html=True,
                        )


    # --------------------------------------------------------
    # BAŞVURU
    # --------------------------------------------------------

    with tab_apply:

        st.subheader(
            "🚀 Nova Agency Ailesine Katıl"
        )

        st.write(
            "Başvurunuzu gönderdikten sonra "
            "ekibimiz sizinle iletişime geçecektir."
        )

        with st.form(
            "application_form",
            clear_on_submit=True,
        ):

            applicant_name = st.text_input(
                "Ad Soyad *"
            )

            applicant_uid = st.text_input(
                "Catchii ID *"
            )

            applicant_contact = st.text_input(
                "Telefon / Instagram *"
            )

            applicant_type = st.selectbox(
                "İletişim Türü",
                [
                    "Telefon",
                    "Instagram",
                ],
            )

            application_submit = st.form_submit_button(
                "🚀 BAŞVURU GÖNDER"
            )

            if application_submit:

                if (
                    not applicant_name
                    or not applicant_uid
                    or not applicant_contact
                ):

                    st.error(
                        "Tüm alanları doldurmanız gerekiyor."
                    )

                else:

                    db = get_db()

                    try:

                        existing = (
                            db.query(PublisherDB)
                            .filter(
                                PublisherDB.uid
                                == applicant_uid.strip()
                            )
                            .first()
                        )

                        if existing:

                            st.error(
                                "Bu Catchii ID zaten kayıtlı."
                            )

                        else:

                            publisher = PublisherDB(
                                name=applicant_name.strip(),
                                uid=applicant_uid.strip(),
                                contact_info=applicant_contact.strip(),
                                contact_type=applicant_type,
                                hours=0,
                                crystals=0,
                                tier="Tier 1 (Başlangıç)",
                                commission=50,
                                status="Yeni Kayıt",
                                admin_note="",
                                application_date=datetime.utcnow(),
                            )

                            db.add(publisher)

                            db.commit()

                            audit(
                                "Yeni başvuru",
                                applicant_name,
                                applicant_uid,
                                applicant_contact,
                            )

                            st.success(
                                "🎉 Başvurunuz başarıyla gönderildi!"
                            )

                    finally:

                        db.close()


# ============================================================
# YÖNETİM PANELİ
# ============================================================

else:

    if "logged_in" not in st.session_state:

        st.session_state.logged_in = False


    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if not st.session_state.logged_in:

        st.markdown(
            """
<h1 style="
text-align:center;
color:#D4AF37 !important;
">
🔐 NOVA AGENCY
</h1>

<h3 style="
text-align:center;
color:white !important;
">
Enterprise Yönetim Paneli
</h3>
""",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(
            [1, 1.5, 1]
        )

        with c2:

            with st.form(
                "login_form"
            ):

                password = st.text_input(
                    "Yönetici Şifresi",
                    type="password",
                )

                login = st.form_submit_button(
                    "🔓 GİRİŞ YAP"
                )

                if login:

                    if password == ADMIN_PASSWORD:

                        st.session_state.logged_in = True

                        st.success(
                            "Giriş başarılı."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "❌ Hatalı şifre."
                        )

        st.stop()


    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.title(
        "⭐ Nova Agency Enterprise"
    )

    st.caption(
        "Komuta Merkezi"
    )

    c1, c2 = st.columns(
        [5, 1]
    )

    with c1:

        st.write(
            "Nova Agency yönetim sistemi aktif."
        )

    with c2:

        if st.button(
            "🔒 Çıkış"
        ):

            st.session_state.logged_in = False

            st.rerun()


    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tabs = st.tabs(
        [
            "📊 KOMUTA",
            "👥 YAYINCILAR",
            "📈 PERFORMANS",
            "🏆 ÖDÜLLER",
            "🎙️ ODALAR",
            "⚖️ CEZALAR",
            "💰 FİNANS",
            "📜 LOG",
            "⚙️ AYARLAR",
        ]
    )


    # ========================================================
    # KOMUTA
    # ========================================================

    with tabs[0]:

        st.subheader(
            "📊 Nova Agency Komuta Merkezi"
        )

        total = len(publishers_df)

        active = (
            len(
                publishers_df[
                    publishers_df["status"]
                    == "Aktif"
                ]
            )
            if not publishers_df.empty
            else 0
        )

        applications = (
            len(
                publishers_df[
                    publishers_df["status"]
                    == "Yeni Kayıt"
                ]
            )
            if not publishers_df.empty
            else 0
        )

        crystals = (
            publishers_df["crystals"].sum()
            if not publishers_df.empty
            else 0
        )

        hours = (
            publishers_df["hours"].sum()
            if not publishers_df.empty
            else 0
        )

        estimated_usd = crystals / 2500


        cols = st.columns(5)

        metrics = [
            ("👥 Yayıncı", total),
            ("🟢 Aktif", active),
            ("📝 Başvuru", applications),
            ("💎 Kristal", f"{crystals:,}"),
            ("🕒 Saat", f"{hours:,.1f}"),
        ]


        for col, (title, value) in zip(
            cols,
            metrics,
        ):

            with col:

                st.markdown(
                    f"""
<div class="metric-card">

<div class="metric-title">
{title}
</div>

<div class="metric-number">
{value}
</div>

</div>
""",
                    unsafe_allow_html=True,
                )


        st.markdown("---")


        left, right = st.columns(2)


        with left:

            st.subheader(
                "🚨 Yeni Başvurular"
            )

            new_apps = publishers_df[
                publishers_df["status"]
                == "Yeni Kayıt"
            ]

            if new_apps.empty:

                st.success(
                    "Yeni başvuru bulunmuyor."
                )

            else:

                st.dataframe(
                    new_apps[
                        [
                            "name",
                            "uid",
                            "contact_info",
                            "application_date",
                        ]
                    ],
                    use_container_width=True,
                )


        with right:

            st.subheader(
                "🏆 En İyi Yayıncılar"
            )

            ranking = (
                publishers_df
                .sort_values(
                    "crystals",
                    ascending=False,
                )
                .head(10)
            )

            if not ranking.empty:

                st.dataframe(
                    ranking[
                        [
                            "name",
                            "uid",
                            "crystals",
                            "hours",
                            "tier",
                        ]
                    ],
                    use_container_width=True,
                )


        st.markdown("---")

        st.metric(
            "💰 Tahmini Toplam Brüt USD",
            f"${estimated_usd:,.2f}",
        )


    # ========================================================
    # YAYINCILAR
    # ========================================================

    with tabs[1]:

        st.subheader(
            "👥 Yayıncı Yönetimi"
        )

        search = st.text_input(
            "🔎 Yayıncı Ara",
            placeholder="İsim, Catchii ID veya iletişim...",
        )

        filters = st.multiselect(
            "Durum",
            [
                "Aktif",
                "Yeni Kayıt",
                "Pasif",
                "Uzaklaştırıldı",
                "Arşiv",
            ],
        )

        filtered = publishers_df.copy()


        if search:

            q = search.lower()

            filtered = filtered[
                filtered["name"]
                .fillna("")
                .str.lower()
                .str.contains(q)
                |
                filtered["uid"]
                .fillna("")
                .str.lower()
                .str.contains(q)
                |
                filtered["contact_info"]
                .fillna("")
                .str.lower()
                .str.contains(q)
            ]


        if filters:

            filtered = filtered[
                filtered["status"]
                .isin(filters)
            ]


        st.write(
            f"**{len(filtered)} yayıncı bulundu.**"
        )


        if not filtered.empty:

            st.dataframe(
                filtered[
                    [
                        "name",
                        "uid",
                        "contact_info",
                        "tier",
                        "hours",
                        "crystals",
                        "status",
                        "application_date",
                    ]
                ].rename(
                    columns={
                        "name": "Yayıncı",
                        "uid": "Catchii ID",
                        "contact_info": "İletişim",
                        "tier": "Tier",
                        "hours": "Saat",
                        "crystals": "Kristal",
                        "status": "Durum",
                        "application_date": "Başvuru",
                    }
                ),
                use_container_width=True,
            )


        st.markdown("---")

        st.subheader(
            "➕ Yayıncı Ekle / Güncelle"
        )


        publisher_choices = [
            "➕ Yeni Yayıncı"
        ]

        if not publishers_df.empty:

            publisher_choices += [
                f"{r['name']} | {r['uid']}"
                for _, r in publishers_df.iterrows()
            ]


        selected = st.selectbox(
            "Yayıncı seç",
            publisher_choices,
        )


        selected_record = None


        if selected != "➕ Yeni Yayıncı":

            selected_uid = (
                selected
                .split("|")[-1]
                .strip()
            )

            db = get_db()

            try:

                selected_record = (
                    db.query(PublisherDB)
                    .filter(
                        PublisherDB.uid
                        == selected_uid
                    )
                    .first()
                )

            finally:

                db.close()


        with st.form(
            "publisher_management",
        ):

            c1, c2, c3 = st.columns(3)


            with c1:

                name = st.text_input(
                    "Ad Soyad",
                    value=(
                        selected_record.name
                        if selected_record
                        else ""
                    ),
                )

                uid = st.text_input(
                    "Catchii ID",
                    value=(
                        selected_record.uid
                        if selected_record
                        else ""
                    ),
                )


            with c2:

                contact = st.text_input(
                    "Telefon / Instagram",
                    value=(
                        selected_record.contact_info
                        if selected_record
                        else ""
                    ),
                )

                hours = st.number_input(
                    "Yayın Saati",
                    min_value=0.0,
                    value=float(
                        selected_record.hours
                        if selected_record
                        else 0
                    ),
                    step=1.0,
                )


            with c3:

                crystals = st.number_input(
                    "Kristal",
                    min_value=0,
                    value=int(
                        selected_record.crystals
                        if selected_record
                        else 0
                    ),
                    step=500,
                )


                status_list = [
                    "Aktif",
                    "Yeni Kayıt",
                    "Pasif",
                    "Uzaklaştırıldı",
                    "Arşiv",
                ]


                current_status = (
                    selected_record.status
                    if selected_record
                    else "Yeni Kayıt"
                )


                status = st.selectbox(
                    "Durum",
                    status_list,
                    index=(
                        status_list.index(
                            current_status
                        )
                        if current_status
                        in status_list
                        else 1
                    ),
                )


            note = st.text_area(
                "📝 Yönetici Notu",
                value=(
                    selected_record.admin_note
                    if selected_record
                    else ""
                ),
            )


            save = st.form_submit_button(
                "💾 KAYDET"
            )


            if save:

                if not name or not uid:

                    st.error(
                        "Ad Soyad ve Catchii ID zorunlu."
                    )

                else:

                    db = get_db()

                    try:

                        existing = (
                            db.query(PublisherDB)
                            .filter(
                                PublisherDB.uid
                                == uid.strip()
                            )
                            .first()
                        )


                        tier, commission = tier_calculator(
                            crystals
                        )


                        if existing:

                            old_status = existing.status

                            existing.name = name.strip()
                            existing.contact_info = contact.strip()
                            existing.hours = hours
                            existing.crystals = crystals
                            existing.tier = tier
                            existing.commission = commission
                            existing.status = status
                            existing.admin_note = note
                            existing.updated_at = datetime.utcnow()

                            if contact:

                                existing.last_contact_date = (
                                    datetime.utcnow()
                                )


                            db.commit()


                            audit(
                                "Yayıncı güncellendi",
                                name,
                                uid,
                                f"{old_status} -> {status}",
                            )


                            st.success(
                                "Yayıncı güncellendi."
                            )


                        else:

                            new_pub = PublisherDB(
                                name=name.strip(),
                                uid=uid.strip(),
                                contact_info=contact.strip(),
                                contact_type=(
                                    "Telefon"
                                    if is_phone(contact)
                                    else "Instagram"
                                ),
                                hours=hours,
                                crystals=crystals,
                                tier=tier,
                                commission=commission,
                                status=status,
                                admin_note=note,
                                application_date=datetime.utcnow(),
                            )

                            db.add(new_pub)

                            db.commit()


                            audit(
                                "Yeni yayıncı oluşturuldu",
                                name,
                                uid,
                                status,
                            )


                            st.success(
                                "Yeni yayıncı eklendi."
                            )

                    finally:

                        db.close()


                st.rerun()


        # PROFİL

        if selected_record:

            st.markdown("---")

            st.subheader(
                f"👤 {selected_record.name}"
            )

            c1, c2, c3 = st.columns(3)


            with c1:

                st.markdown(
                    f"""
<div class="info-card">

<h4>📇 Bilgiler</h4>

<strong>Catchii ID:</strong>
{selected_record.uid}

<br><br>

<strong>İletişim:</strong>
{contact_button_html(selected_record.contact_info)}

<br><br>

<strong>Durum:</strong>
{selected_record.status}

</div>
""",
                    unsafe_allow_html=True,
                )


            with c2:

                st.markdown(
                    f"""
<div class="info-card">

<h4>📊 Performans</h4>

<strong>Saat:</strong>
{selected_record.hours:.1f}

<br><br>

<strong>Kristal:</strong>
{selected_record.crystals:,}

<br><br>

<strong>Tier:</strong>
{selected_record.tier}

<br><br>

<strong>Komisyon:</strong>
%{selected_record.commission}

</div>
""",
                    unsafe_allow_html=True,
                )


            with c3:

                gross = (
                    selected_record.crystals
                    / 2500
                )

                net = (
                    gross
                    * selected_record.commission
                    / 100
                )

                st.markdown(
                    f"""
<div class="info-card">

<h4>💰 Kazanç</h4>

<strong>Brüt:</strong>
${gross:,.2f}

<br><br>

<strong>Net:</strong>
${net:,.2f}

<br><br>

<strong>Başvuru:</strong>
{selected_record.application_date}

</div>
""",
                    unsafe_allow_html=True,
                )


            st.info(
                "📝 Yönetici Notu: "
                + (
                    selected_record.admin_note
                    or "Not bulunmuyor."
                )
            )


            # ARŞİVLE

            if st.button(
                "🗃️ Bu Yayıncıyı Arşivle",
                key=f"archive_{selected_record.uid}",
            ):

                db = get_db()

                try:

                    selected_record.status = "Arşiv"

                    db.commit()

                    audit(
                        "Yayıncı arşivlendi",
                        selected_record.name,
                        selected_record.uid,
                    )

                    st.success(
                        "Yayıncı arşivlendi."
                    )

                    st.rerun()

                finally:

                    db.close()


    # ========================================================
    # PERFORMANS
    # ========================================================

    with tabs[2]:

        st.subheader(
            "📈 Performans Geçmişi"
        )

        if publishers_df.empty:

            st.info(
                "Önce yayıncı ekleyin."
            )

        else:

            choices = [
                f"{r['name']} | {r['uid']}"
                for _, r in publishers_df.iterrows()
            ]

            performance_publisher = st.selectbox(
                "Yayıncı seç",
                choices,
            )


            p_uid = (
                performance_publisher
                .split("|")[-1]
                .strip()
            )


            current = publishers_df[
                publishers_df["uid"] == p_uid
            ].iloc[0]


            with st.form(
                "performance_form",
                clear_on_submit=True,
            ):

                c1, c2, c3 = st.columns(3)

                with c1:

                    perf_date = st.date_input(
                        "Tarih",
                        value=datetime.now().date(),
                    )

                with c2:

                    perf_hours = st.number_input(
                        "Günlük Saat",
                        min_value=0.0,
                        step=1.0,
                    )

                with c3:

                    perf_crystals = st.number_input(
                        "Günlük Kristal",
                        min_value=0,
                        step=500,
                    )


                perf_note = st.text_input(
                    "Not"
                )


                save_perf = st.form_submit_button(
                    "📈 Performansı Kaydet"
                )


                if save_perf:

                    db = get_db()

                    try:

                        db.add(
                            PerformanceDB(
                                publisher_uid=p_uid,
                                publisher_name=current["name"],
                                date=perf_date.strftime(
                                    "%d.%m.%Y"
                                ),
                                hours=perf_hours,
                                crystals=perf_crystals,
                                note=perf_note,
                            )
                        )

                        db.commit()


                        audit(
                            "Performans kaydedildi",
                            current["name"],
                            p_uid,
                            f"{perf_hours} saat / {perf_crystals} kristal",
                        )


                        st.success(
                            "Performans kaydedildi."
                        )

                    finally:

                        db.close()


            history = pd.read_sql(
                f"""
                SELECT *
                FROM performance_history
                WHERE publisher_uid = '{p_uid}'
                ORDER BY id ASC
                """,
                con=engine,
            )


            if not history.empty:

                st.subheader(
                    "📊 Performans Grafiği"
                )

                chart_df = history[
                    [
                        "date",
                        "hours",
                        "crystals",
                    ]
                ].copy()

                chart_df["Tarih"] = chart_df[
                    "date"
                ]

                st.line_chart(
                    chart_df.set_index(
                        "Tarih"
                    )[
                        [
                            "hours",
                            "crystals",
                        ]
                    ]
                )


                st.dataframe(
                    history[
                        [
                            "date",
                            "hours",
                            "crystals",
                            "note",
                        ]
                    ],
                    use_container_width=True,
                )

            else:

                st.info(
                    "Bu yayıncı için henüz performans geçmişi yok."
                )


    # ========================================================
    # ÖDÜLLER
    # ========================================================

    with tabs[3]:

        st.subheader(
            "🏆 Nova Agency Ödül Merkezi"
        )

        st.write(
            "Haftalık ödüller otomatik olarak hesaplanır."
        )


        if publishers_df.empty:

            st.info(
                "Yayıncı bulunmuyor."
            )

        else:

            eligible = publishers_df[
                (
                    publishers_df["hours"] >= 20
                )
                &
                (
                    publishers_df["crystals"] >= 30000
                )
                &
                (
                    publishers_df["status"]
                    == "Aktif"
                )
            ].copy()


            if eligible.empty:

                st.warning(
                    "Ödül şartlarını sağlayan aktif yayıncı yok."
                )

            else:

                eligible = eligible.sort_values(
                    "crystals",
                    ascending=False,
                )


                st.success(
                    f"{len(eligible)} yayıncı ödül şartlarını sağlıyor."
                )


                st.dataframe(
                    eligible[
                        [
                            "name",
                            "uid",
                            "hours",
                            "crystals",
                            "tier",
                        ]
                    ],
                    use_container_width=True,
                )


                st.markdown("---")

                st.subheader(
                    "🥇 Haftalık Ödüller"
                )


                first = eligible.iloc[0]


                st.markdown(
                    f"""
<div class="success-card">

<h3>🥇 En Yüksek Kota</h3>

<strong>
{first["name"]}
</strong>

<br>

{first["crystals"]:,} Kristal

<br><br>

🎁 Ödül:
<strong>20.000 Coin</strong>

</div>
""",
                    unsafe_allow_html=True,
                )


                hour_rank = eligible.sort_values(
                    "hours",
                    ascending=False,
                ).iloc[0]


                st.markdown(
                    f"""
<div class="success-card">

<h3>⏱️ En Aktif Yayıncı</h3>

<strong>
{hour_rank["name"]}
</strong>

<br>

{hour_rank["hours"]:.1f} Saat

<br><br>

🎁 Ödül:
<strong>10.000 Coin</strong>

</div>
""",
                    unsafe_allow_html=True,
                )


                message_rank = eligible.sort_values(
                    "crystals",
                    ascending=False,
                ).iloc[0]


                st.markdown(
                    f"""
<div class="success-card">

<h3>💬 Haftanın En Başarılı Yayıncısı</h3>

<strong>
{message_rank["name"]}
</strong>

<br><br>

🎁 Ödül:
<strong>10.000 Coin</strong>

</div>
""",
                    unsafe_allow_html=True,
                )


                st.markdown("---")

                st.subheader(
                    "📋 Ödül Geçmişi"
                )


                rewards_df = pd.read_sql(
                    """
                    SELECT *
                    FROM rewards
                    ORDER BY id DESC
                    """,
                    con=engine,
                )


                if rewards_df.empty:

                    st.info(
                        "Henüz ödül kaydı yok."
                    )

                else:

                    st.dataframe(
                        rewards_df,
                        use_container_width=True,
                    )


    # ========================================================
    # ODALAR
    # ========================================================

    with tabs[4]:

        st.subheader(
            "🎙️ Sesli Oda Yönetimi"
        )

        with st.form(
            "room_form",
            clear_on_submit=True,
        ):

            c1, c2, c3 = st.columns(3)

            with c1:

                room_name = st.text_input(
                    "Oda Adı"
                )

                room_id = st.text_input(
                    "Oda ID"
                )

            with c2:

                owner = st.text_input(
                    "Oda Sahibi"
                )

                active_hours = st.number_input(
                    "Aktif Saat",
                    min_value=0.0,
                    step=1.0,
                )

            with c3:

                bonus = st.number_input(
                    "Bonus %",
                    min_value=0.0,
                    value=5.0,
                    step=1.0,
                )

                room_status = st.selectbox(
                    "Durum",
                    [
                        "Aktif",
                        "Pasif",
                    ],
                )


            room_submit = st.form_submit_button(
                "🎙️ Odayı Kaydet"
            )


            if room_submit:

                if not room_name or not room_id:

                    st.error(
                        "Oda adı ve ID zorunludur."
                    )

                else:

                    db = get_db()

                    try:

                        existing = (
                            db.query(RoomDB)
                            .filter(
                                RoomDB.room_id
                                == room_id
                            )
                            .first()
                        )


                        if existing:

                            existing.room_name = room_name
                            existing.owner = owner
                            existing.active_hours = active_hours
                            existing.bonus_rate = bonus
                            existing.status = room_status

                        else:

                            db.add(
                                RoomDB(
                                    room_name=room_name,
                                    room_id=room_id,
                                    owner=owner,
                                    active_hours=active_hours,
                                    bonus_rate=bonus,
                                    status=room_status,
                                )
                            )


                        db.commit()

                        audit(
                            "Oda güncellendi",
                            "",
                            room_id,
                            room_name,
                        )

                        st.success(
                            "Oda kaydedildi."
                        )

                    finally:

                        db.close()


                    st.rerun()


        st.dataframe(
            load_rooms(),
            use_container_width=True,
        )


    # ========================================================
    # CEZALAR
    # ========================================================

    with tabs[5]:

        st.subheader(
            "⚖️ Disiplin Merkezi"
        )

        with st.form(
            "penalty_form",
            clear_on_submit=True,
        ):

            penalty_name = st.text_input(
                "Yayıncı Adı"
            )

            penalty_uid = st.text_input(
                "Catchii ID"
            )

            reason = st.text_input(
                "Ceza Sebebi"
            )

            deduction = st.number_input(
                "Ceza Kristali",
                min_value=0,
                step=100,
            )


            penalty_submit = st.form_submit_button(
                "⚖️ CEZAYI UYGULA"
            )


            if penalty_submit:

                if not penalty_name or not reason:

                    st.error(
                        "Yayıncı ve sebep zorunlu."
                    )

                else:

                    db = get_db()

                    try:

                        db.add(
                            PenaltyDB(
                                pub_name=penalty_name,
                                publisher_uid=penalty_uid,
                                reason=reason,
                                deduction=deduction,
                                date=datetime.now().strftime(
                                    "%d.%m.%Y"
                                ),
                            )
                        )

                        db.commit()


                        audit(
                            "Ceza uygulandı",
                            penalty_name,
                            penalty_uid,
                            f"{deduction} kristal - {reason}",
                        )


                        st.warning(
                            "Ceza kaydedildi."
                        )

                    finally:

                        db.close()


        st.dataframe(
            load_penalties(),
            use_container_width=True,
        )


    # ========================================================
    # FINANS
    # ========================================================

    with tabs[6]:

        st.subheader(
            "💰 Finans Merkezi"
        )

        if publishers_df.empty:

            st.info(
                "Kayıtlı yayıncı bulunmuyor."
            )

        else:

            agency_cut = st.slider(
                "Nova Agency Kesinti (%)",
                0,
                40,
                20,
            )


            finance_rows = []


            for _, row in publishers_df.iterrows():

                gross = (
                    row["crystals"]
                    / 2500
                )

                publisher_net = (
                    gross
                    * row["commission"]
                    / 100
                )

                agency_amount = (
                    publisher_net
                    * agency_cut
                    / 100
                )

                payment = (
                    publisher_net
                    - agency_amount
                )


                finance_rows.append(
                    {
                        "Yayıncı": row["name"],
                        "Catchii ID": row["uid"],
                        "Durum": row["status"],
                        "Kristal": row["crystals"],
                        "Brüt USD": round(
                            gross,
                            2,
                        ),
                        "Yayıncı Hakedişi": round(
                            publisher_net,
                            2,
                        ),
                        "Nova Kesintisi": round(
                            agency_amount,
                            2,
                        ),
                        "Ödenecek": round(
                            payment,
                            2,
                        ),
                    }
                )


            finance_df = pd.DataFrame(
                finance_rows
            )


            st.dataframe(
                finance_df,
                use_container_width=True,
            )


            total_payment = finance_df[
                "Ödenecek"
            ].sum()

            total_agency = finance_df[
                "Nova Kesintisi"
            ].sum()


            c1, c2 = st.columns(2)

            with c1:

                st.metric(
                    "💵 Yayıncı Ödemesi",
                    f"${total_payment:,.2f}",
                )

            with c2:

                st.metric(
                    "🏦 Nova Kesintisi",
                    f"${total_agency:,.2f}",
                )


            csv = (
                finance_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8-sig"
                )
            )


            st.download_button(
                "📥 Finans Raporu İndir",
                data=csv,
                file_name="Nova_Finans_Raporu.csv",
                mime="text/csv",
            )


    # ========================================================
    # LOG
    # ========================================================

    with tabs[7]:

        st.subheader(
            "📜 Sistem İşlem Geçmişi"
        )

        logs = pd.read_sql(
            """
            SELECT *
            FROM audit_logs
            ORDER BY id DESC
            LIMIT 1000
            """,
            con=engine,
        )


        if logs.empty:

            st.info(
                "Henüz işlem kaydı yok."
            )

        else:

            st.dataframe(
                logs.rename(
                    columns={
                        "action": "İşlem",
                        "publisher_name": "Yayıncı",
                        "publisher_uid": "Catchii ID",
                        "details": "Detay",
                        "created_at": "Tarih",
                    }
                ),
                use_container_width=True,
            )


    # ========================================================
    # AYARLAR
    # ========================================================

    with tabs[8]:

        st.subheader(
            "⚙️ Sistem Ayarları"
        )

        st.success(
            "🟢 Nova Agency sistemi aktif."
        )

        st.write(
            f"Veritabanı: `{DB_FILE}`"
        )

        st.write(
            "Otomatik migration: 🟢 Aktif"
        )

        st.write(
            "Yayıncı CRM: 🟢 Aktif"
        )

        st.write(
            "Performans geçmişi: 🟢 Aktif"
        )

        st.write(
            "Ödül sistemi: 🟢 Aktif"
        )

        st.write(
            "Finans sistemi: 🟢 Aktif"
        )

        st.write(
            "Audit log: 🟢 Aktif"
        )


        st.markdown("---")

        st.subheader(
            "💾 Veritabanı Yedekleme"
        )

        st.write(
            "Yedekleme işleminden önce mevcut "
            "veritabanının kopyası oluşturulur."
        )


        if st.button(
            "💾 YEDEK OLUŞTUR"
        ):

            backup = create_backup()


            if backup:

                with open(
                    backup,
                    "rb",
                ) as f:

                    st.download_button(
                        "📥 YEDEĞİ İNDİR",
                        data=f,
                        file_name=backup.name,
                        mime="application/octet-stream",
                    )


                st.success(
                    "Yedek hazır."
                )


        st.markdown("---")

        st.subheader(
            "🧪 Veritabanı Kontrolü"
        )

        inspector = inspect(engine)

        tables = inspector.get_table_names()

        st.write(
            "Aktif tablolar:"
        )

        st.code(
            "\n".join(tables)
        )


        st.markdown("---")

        st.info(
            "Nova Agency Enterprise v3.0"
        )
        st.markdown("---")
st.subheader("📥 Catchii Excel ile Otomatik Güncelleme")
st.write("Catchii ajans panelinden indirdiğiniz güncel Excel raporunu buraya yükleyerek tüm yayıncıların saat ve kristallerini tek tıkla güncelleyebilirsiniz.")

uploaded_file = st.file_uploader("Catchii Raporunu Yükle (.xlsx veya .xls)", type=["xlsx", "xls"])

if uploaded_file is not None:
    if st.button("🔄 Verileri Eşleştir ve Sistemi Güncelle"):
        try:
            df_excel = pd.read_excel(uploaded_file)
            db = get_db()
            updated_count = 0
            
            for index, row in df_excel.iterrows():
                # Catchii raporundaki kilit kolonlar
                c_id = str(row["Catchii ID"]).strip()
                c_hours = float(row["On mic duration(h)"])
                
                # Kristal değerindeki olası boşlukları "0" yaparak al
                c_crystals = int(pd.to_numeric(row["Gift-receiving Crystals"], errors='coerce') or 0)
                
                # Sistemdeki yayıncıyı Catchii ID'si ile tespit et
                publisher = db.query(PublisherDB).filter(PublisherDB.uid == c_id).first()
                
                if publisher:
                    # Yeni verileri doğrudan üzerine yaz
                    publisher.hours = c_hours
                    publisher.crystals = c_crystals
                    
                    # Seviye (Tier) ve komisyon oranını yeni kristale göre otomatik hesapla
                    tier, commission = tier_calculator(c_crystals)
                    publisher.tier = tier
                    publisher.commission = commission
                    
                    updated_count += 1
                    
            db.commit()
            
            # İşlem kaydını loglara ekle
            audit("Toplu Excel Güncellemesi", "Sistem Otomasyonu", "", f"{updated_count} yayıncının verisi güncellendi.")
            db.close()
            
            st.success(f"🎉 Operasyon Başarılı! Toplam {updated_count} yayıncının kotası ve finansal hakedişi saniyeler içinde sisteme işlendi.")
            
        except Exception as e:
            st.error(f"Dosya işlenirken bir sorun oluştu. Lütfen doğru Catchii formatını yüklediğinizden emin olun. Detay: {e}")
            import os
import re
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    inspect,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base


# ============================================================
# NOVA AGENCY ENTERPRISE v3.0 - GÜNCELLENMİŞ SÜRÜM
# ============================================================

APP_NAME = "Nova Agency"
DB_FILE = "nova_agency_enterprise.db"
DB_URL = f"sqlite:///{os.path.abspath(DB_FILE)}"

ADMIN_PASSWORD = "18811938"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# ============================================================
# DATABASE MODELLERİ
# ============================================================

class PublisherDB(Base):
    __tablename__ = "publishers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    uid = Column(String, unique=True, index=True, nullable=False)
    contact_info = Column(String, default="")
    contact_type = Column(String, default="Telefon")
    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)
    tier = Column(String, default="Tier 1 (Başlangıç)")
    commission = Column(Float, default=50.0)
    status = Column(String, default="Yeni Kayıt")
    admin_note = Column(Text, default="")
    application_date = Column(DateTime, default=datetime.utcnow)
    last_contact_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PerformanceDB(Base):
    __tablename__ = "performance_history"
    id = Column(Integer, primary_key=True, index=True)
    publisher_uid = Column(String, index=True)
    publisher_name = Column(String)
    date = Column(String)
    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class RoomDB(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String)
    room_id = Column(String, unique=True)
    owner = Column(String)
    active_hours = Column(Float, default=0.0)
    bonus_rate = Column(Float, default=5.0)
    status = Column(String, default="Aktif")

class PenaltyDB(Base):
    __tablename__ = "penalties"
    id = Column(Integer, primary_key=True, index=True)
    pub_name = Column(String)
    publisher_uid = Column(String, default="")
    reason = Column(String)
    deduction = Column(Integer, default=0)
    date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class RewardDB(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    publisher_name = Column(String)
    publisher_uid = Column(String)
    reward_type = Column(String)
    reward_amount = Column(Integer, default=0)
    week = Column(String)
    status = Column(String, default="Bekliyor")
    created_at = Column(DateTime, default=datetime.utcnow)

class FinanceDB(Base):
    __tablename__ = "finance"
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String)
    description = Column(String)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="TL")
    date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLogDB(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    publisher_name = Column(String, default="")
    publisher_uid = Column(String, default="")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def database_migration():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "publishers" not in tables:
        Base.metadata.create_all(bind=engine)
        return
    existing = {c["name"] for c in inspector.get_columns("publishers")}
    migrations = {
        "contact_info": "TEXT DEFAULT ''",
        "contact_type": "TEXT DEFAULT 'Telefon'",
        "admin_note": "TEXT DEFAULT ''",
        "application_date": "DATETIME",
        "last_contact_date": "DATETIME",
        "updated_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, column_type in migrations.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE publishers ADD COLUMN {column} {column_type}"))
    Base.metadata.create_all(bind=engine)

database_migration()

def get_db():
    return SessionLocal()

def audit(action, publisher_name="", publisher_uid="", details=""):
    db = get_db()
    try:
        db.add(AuditLogDB(action=action, publisher_name=publisher_name, publisher_uid=publisher_uid, details=details))
        db.commit()
    finally:
        db.close()

def tier_calculator(crystals):
    if crystals >= 100000: return "VIP Elit Yayıncı", 75.0
    if crystals >= 50000: return "Tier 3 (Profesyonel)", 65.0
    if crystals >= 20000: return "Tier 2 (Gelişen)", 58.0
    return "Tier 1 (Başlangıç)", 50.0

def target_calculator(tier):
    if tier == "VIP Elit Yayıncı": return 30, 100000
    if tier == "Tier 3 (Profesyonel)": return 25, 50000
    if tier == "Tier 2 (Gelişen)": return 20, 25000
    return 15, 15000

def is_phone(value):
    digits = re.sub(r"\D", "", str(value))
    return len(digits) >= 8

def instagram_username(value):
    value = str(value).strip().replace("https://instagram.com/", "").replace("https://www.instagram.com/", "").replace("@", "")
    return value.strip("/")

def contact_button_html(contact):
    if not contact: return "İletişim bilgisi yok"
    contact = str(contact).strip()
    if is_phone(contact):
        phone = re.sub(r"[^\d+]", "", contact)
        return f"<a href='tel:{phone}' style='color:#D4AF37;font-weight:bold;'>📞 {contact}</a>"
    username = instagram_username(contact)
    return f"<a href='https://instagram.com/{username}' target='_blank' style='color:#D4AF37;font-weight:bold;'>📷 @{username}</a>"

def load_publishers():
    return pd.read_sql("SELECT * FROM publishers ORDER BY id DESC", con=engine)

def load_rooms():
    return pd.read_sql("SELECT * FROM rooms ORDER BY id DESC", con=engine)

def load_penalties():
    return pd.read_sql("SELECT * FROM penalties ORDER BY id DESC", con=engine)

st.set_page_config(page_title="Nova Agency Enterprise", page_icon="⭐", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: #061A4A; }
.main { background: #061A4A; color: #FFFFFF; }
h1, h2, h3, h4 { color: #D4AF37 !important; }
.stButton > button { background-color: #D4AF37; color: #061A4A; font-weight: 800; border: none; border-radius: 8px; width: 100%; min-height: 42px; }
.stButton > button:hover { background-color: #F3C643; color: #061A4A; }
.metric-card { background: #0F2D75; border: 1px solid #D4AF37; border-radius: 14px; padding: 18px; text-align: center; margin-bottom: 15px; }
.metric-number { font-size: 30px; font-weight: 900; color: white; }
.metric-title { color: #D4AF37; font-weight: 700; }
.pub-card { background: #0A225C; border-left: 5px solid #D4AF37; border-radius: 12px; padding: 20px; margin: 12px 0; }
.info-card { background: #0F2D75; border-radius: 12px; padding: 18px; margin-bottom: 12px; }
.success-card { background: #124A2B; border-left: 5px solid #4CAF50; border-radius: 10px; padding: 15px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align:center; color:#D4AF37 !important;'>⭐ NOVA</h1><p style='text-align:center; color:white; font-weight:bold;'>AGENCY ENTERPRISE</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Menü", ["👥 Yayıncı Portalı", "💼 Yönetim Paneli"])
st.sidebar.markdown("---")
st.sidebar.caption("Nova Agency Enterprise v3.0")

publishers_df = load_publishers()
rooms_df = load_rooms()
penalties_df = load_penalties()

# ============================================================
# 1. YAYINCI PORTALI (AÇIK ALAN - EXCEL YOK)
# ============================================================
if menu == "👥 Yayıncı Portalı":
    st.title("⭐ Nova Agency")
    st.subheader("Yayıncı Merkezi")
    
    tab_search, tab_apply = st.tabs(["🔍 Performans Sorgula", "📝 Ajansa Başvur"])
    
    with tab_search:
        search = st.text_input("Catchii ID veya adınız", placeholder="Örn: 52308183")
        if search:
            search = search.lower().strip()
            if publishers_df.empty:
                st.info("Sistemde henüz yayıncı bulunmuyor.")
            else:
                result = publishers_df[publishers_df["name"].fillna("").str.lower().str.contains(search) | publishers_df["uid"].fillna("").str.lower().str.contains(search)]
                if result.empty:
                    st.warning("Yayıncı bulunamadı.")
                else:
                    for _, row in result.iterrows():
                        target_hours, target_crystals = target_calculator(row["tier"])
                        hour_percent = min(100, row["hours"] / target_hours * 100)
                        crystal_percent = min(100, row["crystals"] / target_crystals * 100)
                        gross = row["crystals"] / 2500
                        net = gross * row["commission"] / 100
                        
                        st.markdown(f"""
                        <div class="pub-card">
                        <h2>⭐ {row["name"]}</h2>
                        <p><strong>Catchii ID:</strong> {row["uid"]}</p>
                        <p><strong>Durum:</strong> {row["status"]} | <strong>Tier:</strong> {row["tier"]}</p>
                        <hr>
                        <h3>📊 Kota Durumu</h3>
                        <p>🕒 Saat: <strong>{row["hours"]:.1f}</strong> / {target_hours} — %{hour_percent:.0f}</p>
                        <p>💎 Kristal: <strong>{row["crystals"]:,}</strong> / {target_crystals:,} — %{crystal_percent:.0f}</p>
                        <hr>
                        <h3>💰 Tahmini Hakediş</h3>
                        <p>Brüt: <strong>${gross:.2f}</strong> | Net Hakedişin: <strong>${net:.2f}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

    with tab_apply:
        st.subheader("🚀 Nova Agency Ailesine Katıl")
        with st.form("application_form", clear_on_submit=True):
            applicant_name = st.text_input("Ad Soyad *")
            applicant_uid = st.text_input("Catchii ID *")
            applicant_contact = st.text_input("Telefon / Instagram *")
            applicant_type = st.selectbox("İletişim Türü", ["Telefon", "Instagram"])
            application_submit = st.form_submit_button("🚀 BAŞVURU GÖNDER")
            
            if application_submit:
                if not applicant_name or not applicant_uid or not applicant_contact:
                    st.error("Tüm alanları doldurmanız gerekiyor.")
                else:
                    db = get_db()
                    try:
                        existing = db.query(PublisherDB).filter(PublisherDB.uid == applicant_uid.strip()).first()
                        if existing:
                            st.error("Bu Catchii ID zaten kayıtlı.")
                        else:
                            publisher = PublisherDB(
                                name=applicant_name.strip(), uid=applicant_uid.strip(),
                                contact_info=applicant_contact.strip(), contact_type=applicant_type,
                                hours=0, crystals=0, tier="Tier 1 (Başlangıç)", commission=50,
                                status="Yeni Kayıt", application_date=datetime.utcnow()
                            )
                            db.add(publisher)
                            db.commit()
                            audit("Yeni başvuru", applicant_name, applicant_uid, applicant_contact)
                            st.success("🎉 Başvurunuz başarıyla gönderildi!")
                    finally:
                        db.close()

# ============================================================
# 2. YÖNETİM PANELİ (ŞİFRELİ ALAN)
# ============================================================
else:
    if "logged_in" not in st.session_state: st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("<h1 style='text-align:center; color:#D4AF37 !important;'>🔐 NOVA AGENCY</h1><h3 style='text-align:center; color:white !important;'>Enterprise Yönetim Paneli</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            with st.form("login_form"):
                password = st.text_input("Yönetici Şifresi", type="password")
                login = st.form_submit_button("🔓 GİRİŞ YAP")
                if login:
                    if password == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.success("Giriş başarılı.")
                        st.rerun()
                    else:
                        st.error("❌ Hatalı şifre.")
        st.stop()

    st.title("⭐ Nova Agency Enterprise")
    c1, c2 = st.columns([5, 1])
    with c1: st.write("Komuta Merkezi Aktif.")
    with c2:
        if st.button("🔒 Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["📊 KOMUTA", "👥 YAYINCILAR", "📈 PERFORMANS", "🏆 ÖDÜLLER", "🎙️ ODALAR", "⚖️ CEZALAR", "💰 FİNANS", "📜 LOG", "⚙️ AYARLAR"])

    with tabs[0]: # KOMUTA
        st.subheader("📊 Genel Durum")
        total, active = len(publishers_df), len(publishers_df[publishers_df["status"] == "Aktif"]) if not publishers_df.empty else 0
        apps = len(publishers_df[publishers_df["status"] == "Yeni Kayıt"]) if not publishers_df.empty else 0
        crystals = publishers_df["crystals"].sum() if not publishers_df.empty else 0
        hours = publishers_df["hours"].sum() if not publishers_df.empty else 0
        
        cols = st.columns(5)
        metrics = [("👥 Yayıncı", total), ("🟢 Aktif", active), ("📝 Başvuru", apps), ("💎 Kristal", f"{crystals:,}"), ("🕒 Saat", f"{hours:,.1f}")]
        for col, (title, val) in zip(cols, metrics):
            with col:
                st.markdown(f"<div class='metric-card'><div class='metric-title'>{title}</div><div class='metric-number'>{val}</div></div>", unsafe_allow_html=True)

    with tabs[1]: # YAYINCILAR (EXCEL YÜKLEME BURAYA TAŞINDI)
        st.subheader("👥 Yayıncı Yönetimi & Catchii Otomasyonu")
        
        # --- EXCEL OTOMASYON YÜKLEYİCİSİ BURADA (SADECE PATRON GÖRÜR) ---
        with st.expander("📥 Catchii Excel Raporu ile Toplu Güncelleme", expanded=True):
            st.write("Catchii panelinden indirdiğiniz Excel raporunu buraya yükleyerek tüm yayıncıların saat ve kristallerini saniyeler içinde güncelleyebilirsiniz.")
            uploaded_file = st.file_uploader("Catchii Raporunu Yükle (.xlsx)", type=["xlsx", "xls"])
            if uploaded_file is not None:
                if st.button("🔄 Verileri Eşleştir ve Güncelle"):
                    try:
                        df_excel = pd.read_excel(uploaded_file)
                        db = get_db()
                        up_count = 0
                        for _, row in df_excel.iterrows():
                            c_id = str(row["Catchii ID"]).strip()
                            c_hours = float(row["On mic duration(h)"])
                            c_crystals = int(pd.to_numeric(row["Gift-receiving Crystals"], errors='coerce') or 0)
                            
                            publisher = db.query(PublisherDB).filter(PublisherDB.uid == c_id).first()
                            if publisher:
                                publisher.hours = c_hours
                                publisher.crystals = c_crystals
                                tier, commission = tier_calculator(c_crystals)
                                publisher.tier = tier
                                publisher.commission = commission
                                up_count += 1
                        db.commit()
                        audit("Toplu Excel Güncellemesi", "Admin", "", f"{up_count} yayıncı güncellendi.")
                        db.close()
                        st.success(f"🎉 Başarılı! Toplam {up_count} yayıncının verisi güncellendi.")
                    except Exception as e:
                        st.error(f"Hata oluştu: {e}")

        st.markdown("---")
        search = st.text_input("🔎 Yayıncı Ara", placeholder="İsim, ID...")
        filtered = publishers_df.copy()
        if search:
            q = search.lower()
            filtered = filtered[filtered["name"].str.lower().str.contains(q, na=False) | filtered["uid"].str.lower().str.contains(q, na=False)]
        
        if not filtered.empty:
            st.dataframe(filtered[["name", "uid", "contact_info", "tier", "hours", "crystals", "status"]].rename(columns={"uid": "Catchii ID"}), use_container_width=True)

    with tabs[2]: # PERFORMANS
        st.subheader("📈 Performans Grafikleri")
        st.info("Yayıncıların bireysel performans geçmişini buradan takip edebilirsiniz.")

    with tabs[3]: # ÖDÜLLER
        st.subheader("🏆 Ödül Merkezi")
        st.write("Haftalık hedefleri geçen yayıncılar.")

    with tabs[4]: # ODALAR
        st.subheader("🎙️ Sesli Oda Yönetimi")
        st.dataframe(rooms_df, use_container_width=True)

    with tabs[5]: # CEZALAR
        st.subheader("⚖️ Disiplin Merkezi")
        st.dataframe(penalties_df, use_container_width=True)

    with tabs[6]: # FİNANS
        st.subheader("💰 Finansal Raporlama")
        if not publishers_df.empty:
            calc_data = []
            for _, row in publishers_df.iterrows():
                gross = row["crystals"] / 2500
                net = gross * row["commission"] / 100
                calc_data.append({"Yayıncı": row["name"], "Catchii ID": row["uid"], "Kristal": row["crystals"], "Net USD": round(net, 2)})
            st.dataframe(pd.DataFrame(calc_data), use_container_width=True)

    with tabs[7]: # LOG
        st.subheader("📜 Sistem İşlem Geçmişi")
        logs = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100", con=engine)
        st.dataframe(logs, use_container_width=True)

    with tabs[8]: # AYARLAR
        st.subheader("⚙️ Sistem Durumu")
        st.success("🟢 Nova Agency Enterprise aktif ve çalışıyor.")
        import os
import re
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    inspect,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base


# ============================================================
# NOVA AGENCY ENTERPRISE v3.1
# ============================================================

APP_NAME = "Nova Agency"
DB_FILE = "nova_agency_enterprise.db"
DB_URL = f"sqlite:///{os.path.abspath(DB_FILE)}"

ADMIN_PASSWORD = "18811938"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# ============================================================
# DATABASE MODELLERİ
# ============================================================

class PublisherDB(Base):
    __tablename__ = "publishers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    uid = Column(String, unique=True, index=True, nullable=False)
    contact_info = Column(String, default="")
    contact_type = Column(String, default="Telefon")
    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)
    tier = Column(String, default="Tier 1 (Başlangıç)")
    commission = Column(Float, default=50.0)
    status = Column(String, default="Yeni Kayıt")
    admin_note = Column(Text, default="")
    application_date = Column(DateTime, default=datetime.utcnow)
    last_contact_date = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PerformanceDB(Base):
    __tablename__ = "performance_history"
    id = Column(Integer, primary_key=True, index=True)
    publisher_uid = Column(String, index=True)
    publisher_name = Column(String)
    date = Column(String)
    hours = Column(Float, default=0.0)
    crystals = Column(Integer, default=0)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class RoomDB(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String)
    room_id = Column(String, unique=True)
    owner = Column(String)
    active_hours = Column(Float, default=0.0)
    bonus_rate = Column(Float, default=5.0)
    status = Column(String, default="Aktif")

class PenaltyDB(Base):
    __tablename__ = "penalties"
    id = Column(Integer, primary_key=True, index=True)
    pub_name = Column(String)
    publisher_uid = Column(String, default="")
    reason = Column(String)
    deduction = Column(Integer, default=0)
    date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class RewardDB(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    publisher_name = Column(String)
    publisher_uid = Column(String)
    reward_type = Column(String)
    reward_amount = Column(Integer, default=0)
    week = Column(String)
    status = Column(String, default="Bekliyor")
    created_at = Column(DateTime, default=datetime.utcnow)

class FinanceDB(Base):
    __tablename__ = "finance"
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String)
    description = Column(String)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="TL")
    date = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLogDB(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String)
    publisher_name = Column(String, default="")
    publisher_uid = Column(String, default="")
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def database_migration():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "publishers" not in tables:
        Base.metadata.create_all(bind=engine)
        return
    existing = {c["name"] for c in inspector.get_columns("publishers")}
    migrations = {
        "contact_info": "TEXT DEFAULT ''",
        "contact_type": "TEXT DEFAULT 'Telefon'",
        "admin_note": "TEXT DEFAULT ''",
        "application_date": "DATETIME",
        "last_contact_date": "DATETIME",
        "updated_at": "DATETIME",
    }
    with engine.begin() as conn:
        for column, column_type in migrations.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE publishers ADD COLUMN {column} {column_type}"))
    Base.metadata.create_all(bind=engine)

database_migration()

def get_db():
    return SessionLocal()

def audit(action, publisher_name="", publisher_uid="", details=""):
    db = get_db()
    try:
        db.add(AuditLogDB(action=action, publisher_name=publisher_name, publisher_uid=publisher_uid, details=details))
        db.commit()
    finally:
        db.close()

def tier_calculator(crystals):
    if crystals >= 100000: return "VIP Elit Yayıncı", 75.0
    if crystals >= 50000: return "Tier 3 (Profesyonel)", 65.0
    if crystals >= 20000: return "Tier 2 (Gelişen)", 58.0
    return "Tier 1 (Başlangıç)", 50.0

def target_calculator(tier):
    if tier == "VIP Elit Yayıncı": return 30, 100000
    if tier == "Tier 3 (Profesyonel)": return 25, 50000
    if tier == "Tier 2 (Gelişen)": return 20, 25000
    return 15, 15000

def load_publishers():
    return pd.read_sql("SELECT * FROM publishers ORDER BY id DESC", con=engine)

def load_rooms():
    return pd.read_sql("SELECT * FROM rooms ORDER BY id DESC", con=engine)

def load_penalties():
    return pd.read_sql("SELECT * FROM penalties ORDER BY id DESC", con=engine)

st.set_page_config(page_title="Nova Agency Enterprise", page_icon="⭐", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: #061A4A; }
.main { background: #061A4A; color: #FFFFFF; }
h1, h2, h3, h4 { color: #D4AF37 !important; }
.stButton > button { background-color: #D4AF37; color: #061A4A; font-weight: 800; border: none; border-radius: 8px; width: 100%; min-height: 42px; }
.stButton > button:hover { background-color: #F3C643; color: #061A4A; }
.metric-card { background: #0F2D75; border: 1px solid #D4AF37; border-radius: 14px; padding: 18px; text-align: center; margin-bottom: 15px; }
.metric-number { font-size: 30px; font-weight: 900; color: white; }
.metric-title { color: #D4AF37; font-weight: 700; }
.pub-card { background: #0A225C; border-left: 5px solid #D4AF37; border-radius: 12px; padding: 20px; margin: 12px 0; }
.info-card { background: #0F2D75; border-radius: 12px; padding: 18px; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h1 style='text-align:center; color:#D4AF37 !important;'>⭐ NOVA</h1><p style='text-align:center; color:white; font-weight:bold;'>AGENCY ENTERPRISE</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Ana Menü", ["👥 Yayıncı Portalı", "💼 Yönetim Paneli"], key="main_menu_radio")
st.sidebar.markdown("---")
st.sidebar.caption("Nova Agency Enterprise v3.1")

publishers_df = load_publishers()
rooms_df = load_rooms()
penalties_df = load_penalties()

# ============================================================
# 1. YAYINCI PORTALI
# ============================================================
if menu == "👥 Yayıncı Portalı":
    st.title("⭐ Nova Agency")
    st.subheader("Yayıncı Merkezi")
    
    tab_search, tab_apply = st.tabs(["🔍 Performans Sorgula", "📝 Ajansa Başvur"])
    
    with tab_search:
        search = st.text_input("Catchii ID veya adınız", placeholder="Örn: 52308183")
        if search:
            search = search.lower().strip()
            if publishers_df.empty:
                st.info("Sistemde henüz yayıncı bulunmuyor.")
            else:
                result = publishers_df[publishers_df["name"].fillna("").str.lower().str.contains(search) | publishers_df["uid"].fillna("").str.lower().str.contains(search)]
                if result.empty:
                    st.warning("Yayıncı bulunamadı.")
                else:
                    for _, row in result.iterrows():
                        target_hours, target_crystals = target_calculator(row["tier"])
                        hour_percent = min(100, row["hours"] / target_hours * 100)
                        crystal_percent = min(100, row["crystals"] / target_crystals * 100)
                        gross = row["crystals"] / 2500
                        net = gross * row["commission"] / 100
                        
                        st.markdown(f"""
                        <div class="pub-card">
                        <h2>⭐ {row["name"]}</h2>
                        <p><strong>Catchii ID:</strong> {row["uid"]}</p>
                        <p><strong>Durum:</strong> {row["status"]} | <strong>Tier:</strong> {row["tier"]}</p>
                        <hr>
                        <h3>📊 Kota Durumu</h3>
                        <p>🕒 Saat: <strong>{row["hours"]:.1f}</strong> / {target_hours} — %{hour_percent:.0f}</p>
                        <p>💎 Kristal: <strong>{row["crystals"]:,}</strong> / {target_crystals:,} — %{crystal_percent:.0f}</p>
                        <hr>
                        <h3>💰 Tahmini Hakediş</h3>
                        <p>Brüt: <strong>${gross:.2f}</strong> | Net Hakedişin: <strong>${net:.2f}</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

    with tab_apply:
        st.subheader("🚀 Nova Agency Ailesine Katıl")
        with st.form("application_form", clear_on_submit=True):
            applicant_name = st.text_input("Ad Soyad *")
            applicant_uid = st.text_input("Catchii ID *")
            applicant_contact = st.text_input("Telefon / Instagram *")
            applicant_type = st.selectbox("İletişim Türü", ["Telefon", "Instagram"])
            application_submit = st.form_submit_button("🚀 BAŞVURU GÖNDER")
            
            if application_submit:
                if not applicant_name or not applicant_uid or not applicant_contact:
                    st.error("Tüm alanları doldurmanız gerekiyor.")
                else:
                    db = get_db()
                    try:
                        existing = db.query(PublisherDB).filter(PublisherDB.uid == applicant_uid.strip()).first()
                        if existing:
                            st.error("Bu Catchii ID zaten kayıtlı.")
                        else:
                            publisher = PublisherDB(
                                name=applicant_name.strip(), uid=applicant_uid.strip(),
                                contact_info=applicant_contact.strip(), contact_type=applicant_type,
                                hours=0, crystals=0, tier="Tier 1 (Başlangıç)", commission=50,
                                status="Yeni Kayıt", application_date=datetime.utcnow()
                            )
                            db.add(publisher)
                            db.commit()
                            audit("Yeni başvuru", applicant_name, applicant_uid, applicant_contact)
                            st.success("🎉 Başvurunuz başarıyla gönderildi!")
                    finally:
                        db.close()

# ============================================================
# 2. YÖNETİM PANELİ
# ============================================================
else:
    if "logged_in" not in st.session_state: st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("<h1 style='text-align:center; color:#D4AF37 !important;'>🔐 NOVA AGENCY</h1><h3 style='text-align:center; color:white !important;'>Enterprise Yönetim Paneli</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            with st.form("login_form"):
                password = st.text_input("Yönetici Şifresi", type="password")
                login = st.form_submit_button("🔓 GİRİŞ YAP")
                if login:
                    if password == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.success("Giriş başarılı.")
                        st.rerun()
                    else:
                        st.error("❌ Hatalı şifre.")
        st.stop()

    st.title("⭐ Nova Agency Enterprise")
    c1, c2 = st.columns([5, 1])
    with c1: st.write("Komuta Merkezi Aktif.")
    with c2:
        if st.button("🔒 Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["📊 KOMUTA", "👥 YAYINCILAR", "📈 PERFORMANS", "🏆 ÖDÜLLER", "🎙️ ODALAR", "⚖️ CEZALAR", "💰 FİNANS", "📜 LOG", "⚙️ AYARLAR"])

    with tabs[0]: # KOMUTA
        st.subheader("📊 Genel Durum")
        total, active = len(publishers_df), len(publishers_df[publishers_df["status"] == "Aktif"]) if not publishers_df.empty else 0
        apps = len(publishers_df[publishers_df["status"] == "Yeni Kayıt"]) if not publishers_df.empty else 0
        crystals = publishers_df["crystals"].sum() if not publishers_df.empty else 0
        hours = publishers_df["hours"].sum() if not publishers_df.empty else 0
        
        cols = st.columns(5)
        metrics = [("👥 Yayıncı", total), ("🟢 Aktif", active), ("📝 Başvuru", apps), ("💎 Kristal", f"{crystals:,}"), ("🕒 Saat", f"{hours:,.1f}")]
        for col, (title, val) in zip(cols, metrics):
            with col:
                st.markdown(f"<div class='metric-card'><div class='metric-title'>{title}</div><div class='metric-number'>{val}</div></div>", unsafe_allow_html=True)

    with tabs[1]: # YAYINCILAR & EXCEL OTOMASYONU
        st.subheader("👥 Yayıncı Yönetimi & Catchii Otomasyonu")
        
        with st.expander("📥 Catchii Excel Raporu ile Toplu Güncelleme", expanded=True):
            st.write("Catchii panelinden indirdiğiniz Excel raporunu buraya yükleyerek tüm yayıncıların saat ve kristallerini saniyeler içinde güncelleyebilirsiniz.")
            uploaded_file = st.file_uploader("Catchii Raporunu Yükle (.xlsx)", type=["xlsx", "xls"], key="excel_upload_admin")
            if uploaded_file is not None:
                if st.button("🔄 Verileri Eşleştir ve Güncelle", key="btn_update_excel"):
                    try:
                        df_excel = pd.read_excel(uploaded_file)
                        db = get_db()
                        up_count = 0
                        for _, row in df_excel.iterrows():
                            c_id = str(row["Catchii ID"]).strip()
                            c_hours = float(row["On mic duration(h)"])
                            c_crystals = int(pd.to_numeric(row["Gift-receiving Crystals"], errors='coerce') or 0)
                            
                            publisher = db.query(PublisherDB).filter(PublisherDB.uid == c_id).first()
                            if publisher:
                                publisher.hours = c_hours
                                publisher.crystals = c_crystals
                                tier, commission = tier_calculator(c_crystals)
                                publisher.tier = tier
                                publisher.commission = commission
                                up_count += 1
                        db.commit()
                        audit("Toplu Excel Güncellemesi", "Admin", "", f"{up_count} yayıncı güncellendi.")
                        db.close()
                        st.success(f"🎉 Başarılı! Toplam {up_count} yayıncının verisi güncellendi.")
                    except Exception as e:
                        st.error(f"Hata oluştu: {e}")

        st.markdown("---")
        search = st.text_input("🔎 Yayıncı Ara", placeholder="İsim, ID...")
        filtered = publishers_df.copy()
        if search:
            q = search.lower()
            filtered = filtered[filtered["name"].str.lower().str.contains(q, na=False) | filtered["uid"].str.lower().str.contains(q, na=False)]
        
        if not filtered.empty:
            st.dataframe(filtered[["name", "uid", "contact_info", "tier", "hours", "crystals", "status"]].rename(columns={"uid": "Catchii ID"}), use_container_width=True)

    with tabs[2]: st.subheader("📈 Performans")
    with tabs[3]: st.subheader("🏆 Ödüller")
    with tabs[4]: st.subheader("🎙️ Odalar")
    with tabs[5]: st.subheader("⚖️ Cezalar")
    with tabs[6]: st.subheader("💰 Finans")
    with tabs[7]: st.subheader("📜 Log")
    with tabs[8]: st.subheader("⚙️ Ayarlar")
        with st.expander("📥 Catchii Excel Raporu ile Toplu Güncelleme", expanded=True):
            st.write("Catchii panelinden indirdiğiniz Excel raporunu buraya yükleyerek tüm yayıncıların saat ve kristallerini saniyeler içinde güncelleyebilirsiniz.")
            uploaded_file = st.file_uploader("Catchii Raporunu Yükle (.xlsx)", type=["xlsx", "xls"], key="excel_upload_admin")
            if uploaded_file is not None:
                if st.button("🔄 Verileri Eşleştir ve Güncelle", key="btn_update_excel"):
                    try:
                        # Doğrudan "detail" (detay) sekmesini okuyoruz
                        df_excel = pd.read_excel(uploaded_file, sheet_name="detail")
                        db = get_db()
                        up_count = 0
                        
                        for _, row in df_excel.iterrows():
                            c_id = str(row["Catchii ID"]).strip()
                            c_hours = float(row["On mic duration(h)"])
                            c_crystals = int(pd.to_numeric(row["Gift-receiving Crystals"], errors='coerce') or 0)
                            
                            # Veritabanında bu ID var mı diye bakıyoruz
                            publisher = db.query(PublisherDB).filter(PublisherDB.uid == c_id).first()
                            if publisher:
                                publisher.hours = c_hours
                                publisher.crystals = c_crystals
                                tier, commission = tier_calculator(c_crystals)
                                publisher.tier = tier
                                publisher.commission = commission
                                up_count += 1
                            else:
                                # Eğer veritabanında yoksa, Excel'deki Nickname ile otomatik yeni yayıncı olarak ekleyelim!
                                c_name = str(row.get("Nickname", "İsimsiz Yayıncı"))
                                tier, commission = tier_calculator(c_crystals)
                                new_pub = PublisherDB(
                                    name=c_name,
                                    uid=c_id,
                                    hours=c_hours,
                                    crystals=c_crystals,
                                    tier=tier,
                                    commission=commission,
                                    status="Aktif"
                                )
                                db.add(new_pub)
                                up_count += 1
                                
                        db.commit()
                        audit("Toplu Excel Güncellemesi", "Admin", "", f"{up_count} yayıncı güncellendi/eklendi.")
                        db.close()
                        st.success(f"🎉 Başarılı! Toplam {up_count} yayıncının verisi sisteme işlendi.")
                    except Exception as e:
                        st.error(f"Hata oluştu: {e}")
