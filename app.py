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
# NOVA AGENCY ENTERPRISE v3.2
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
st.sidebar.caption("Nova Agency Enterprise v3.2")

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
        search = st.text_input("Catchii ID veya adınız", placeholder="Örn: 52546533")
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
                        # Doğrudan 'detail' sayfasını okuyoruz
                        df_excel = pd.read_excel(uploaded_file, sheet_name="detail")
                        db = get_db()
                        up_count = 0
                        
                        for _, row in df_excel.iterrows():
                            c_id = str(row["Catchii ID"]).strip()
                            c_hours = float(row["On mic duration(h)"])
                            c_crystals = int(pd.to_numeric(row["Gift-receiving Crystals"], errors='coerce') or 0)
                            c_name = str(row.get("Nickname", "Yayıncı"))
                            
                            publisher = db.query(PublisherDB).filter(PublisherDB.uid == c_id).first()
                            if publisher:
                                publisher.hours = c_hours
                                publisher.crystals = c_crystals
                                tier, commission = tier_calculator(c_crystals)
                                publisher.tier = tier
                                publisher.commission = commission
                                up_count += 1
                            else:
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
