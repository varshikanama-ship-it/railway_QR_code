import streamlit as st
import sqlite3
import qrcode
import uuid
import random
import io
import base64
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image

# ─────────────────────────────────────────
# DATA
# ─────────────────────────────────────────

CITIES = [
    "Hyderabad", "Bengaluru", "Chennai", "Pune", "Ahmedabad",
    "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Visakhapatnam",
    "Bhopal", "Patna", "Vadodara", "Ludhiana", "Agra",
    "Nashik", "Meerut", "Rajkot", "Varanasi", "Srinagar",
    "Amritsar", "Ranchi", "Coimbatore", "Madurai", "Thiruvananthapuram",
    "Jodhpur", "Kochi", "Indore", "Guwahati", "Chandigarh",
    "Mysuru", "Vijayawada", "Tiruchirappalli", "Dehradun", "Udaipur",
]

TRAINS = [
    {"no": "12001", "name": "Shatabdi Express",    "type": "Superfast"},
    {"no": "12301", "name": "Rajdhani Express",    "type": "Premium"},
    {"no": "12951", "name": "Mumbai Rajdhani",     "type": "Premium"},
    {"no": "12002", "name": "Bhopal Shatabdi",     "type": "Superfast"},
    {"no": "22691", "name": "Rajdhani Express",    "type": "Premium"},
    {"no": "12431", "name": "Thiruvananthapuram Rajdhani", "type": "Premium"},
    {"no": "12627", "name": "Karnataka Express",   "type": "Express"},
    {"no": "12621", "name": "Tamil Nadu Express",  "type": "Express"},
    {"no": "11301", "name": "Udyan Express",       "type": "Express"},
    {"no": "16591", "name": "Hampi Express",       "type": "Express"},
    {"no": "12028", "name": "Chennai Shatabdi",    "type": "Superfast"},
    {"no": "12009", "name": "Shatabdi Express",    "type": "Superfast"},
    {"no": "19301", "name": "Yesvantpur Express",  "type": "Express"},
    {"no": "12721", "name": "Dakshin Express",     "type": "Express"},
    {"no": "12215", "name": "Garib Rath Express",  "type": "Superfast"},
]

COACHES = {
    "Sleeper (SL)":       {"multiplier": 1.0,  "seats": 72},
    "AC 3-Tier (3A)":     {"multiplier": 2.0,  "seats": 64},
    "AC 2-Tier (2A)":     {"multiplier": 3.0,  "seats": 48},
    "AC First Class (1A)":{"multiplier": 5.0,  "seats": 24},
    "Chair Car (CC)":     {"multiplier": 1.5,  "seats": 78},
    "Executive Chair (EC)":{"multiplier": 2.5, "seats": 56},
}

DISTANCE_MAP = {}

def get_distance(city_a: str, city_b: str) -> int:
    key = tuple(sorted([city_a, city_b]))
    if key not in DISTANCE_MAP:
        random.seed(hash(key))
        DISTANCE_MAP[key] = random.randint(150, 2200)
    return DISTANCE_MAP[key]

FARE_PER_KM = 1.5
GST_RATE    = 0.05

# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────

DB_PATH = "railway_tickets.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id      TEXT PRIMARY KEY,
            passenger_name TEXT NOT NULL,
            passenger_age  INTEGER NOT NULL,
            passenger_email TEXT NOT NULL,
            train_no       TEXT NOT NULL,
            train_name     TEXT NOT NULL,
            train_type     TEXT NOT NULL,
            from_city      TEXT NOT NULL,
            to_city        TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time   TEXT NOT NULL,
            journey_date   TEXT NOT NULL,
            coach_type     TEXT NOT NULL,
            seat_number    TEXT NOT NULL,
            distance_km    INTEGER NOT NULL,
            base_fare      REAL NOT NULL,
            gst_amount     REAL NOT NULL,
            total_fare     REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_id     TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'Active',
            booked_at      TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def insert_ticket(data: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO tickets VALUES (
            :ticket_id, :passenger_name, :passenger_age, :passenger_email,
            :train_no, :train_name, :train_type,
            :from_city, :to_city, :departure_time, :arrival_time, :journey_date,
            :coach_type, :seat_number,
            :distance_km, :base_fare, :gst_amount, :total_fare,
            :payment_method, :payment_id, :status, :booked_at
        )
    """, data)
    conn.commit()
    conn.close()

def get_ticket(ticket_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)
    ).fetchone()
    conn.close()
    if row:
        cols = [d[0] for d in conn.description] if False else [
            "ticket_id","passenger_name","passenger_age","passenger_email",
            "train_no","train_name","train_type",
            "from_city","to_city","departure_time","arrival_time","journey_date",
            "coach_type","seat_number",
            "distance_km","base_fare","gst_amount","total_fare",
            "payment_method","payment_id","status","booked_at"
        ]
        return dict(zip(cols, row))
    return None

def mark_used(ticket_id: str):
    conn = get_conn()
    conn.execute("UPDATE tickets SET status='Used' WHERE ticket_id=?", (ticket_id,))
    conn.commit()
    conn.close()

def all_tickets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tickets ORDER BY booked_at DESC").fetchall()
    conn.close()
    cols = [
        "ticket_id","passenger_name","passenger_age","passenger_email",
        "train_no","train_name","train_type",
        "from_city","to_city","departure_time","arrival_time","journey_date",
        "coach_type","seat_number",
        "distance_km","base_fare","gst_amount","total_fare",
        "payment_method","payment_id","status","booked_at"
    ]
    return [dict(zip(cols, r)) for r in rows]

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def make_ticket_id() -> str:
    return "TKT-" + uuid.uuid4().hex[:10].upper()

def make_payment_id(method: str) -> str:
    prefixes = {"UPI": "UPI", "Card": "CARD", "Net Banking": "NETB"}
    prefix = prefixes.get(method, "PAY")
    return prefix + uuid.uuid4().hex[:12].upper()

def make_seat(coach_type: str, coach_letter: str = "B") -> str:
    max_seats = COACHES[coach_type]["seats"]
    seat_no   = random.randint(1, max_seats)
    return f"{coach_letter}{seat_no}"

def calc_fare(distance_km: int, coach_type: str):
    multiplier = COACHES[coach_type]["multiplier"]
    base_fare  = round(distance_km * FARE_PER_KM * multiplier, 2)
    gst_amount = round(base_fare * GST_RATE, 2)
    total_fare = round(base_fare + gst_amount, 2)
    return base_fare, gst_amount, total_fare

def random_times(journey_date: str):
    hour  = random.randint(4, 22)
    minute= random.choice([0, 15, 30, 45])
    dep   = datetime.strptime(journey_date, "%Y-%m-%d") + timedelta(hours=hour, minutes=minute)
    dur   = random.randint(3, 28)
    arr   = dep + timedelta(hours=dur)
    return dep.strftime("%d-%b-%Y %H:%M"), arr.strftime("%d-%b-%Y %H:%M")

def make_qr_image(ticket_id: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=8,
        border=2,
    )
    qr.add_data(f"TICKET:{ticket_id}")
    qr.make(fit=True)
    return qr.make_image(fill_color="#1a3c6e", back_color="white").convert("RGB")

def pil_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

def qr_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ─────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────

def generate_pdf(t: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontSize=20, textColor=colors.HexColor("#1a3c6e"),
        spaceAfter=2, alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#666666"),
        alignment=TA_CENTER, spaceAfter=6,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontSize=11, textColor=colors.white,
        backColor=colors.HexColor("#1a3c6e"),
        spaceBefore=8, spaceAfter=4,
        leftIndent=4, rightIndent=4,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#555555"),
    )
    value_style = ParagraphStyle(
        "value", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#111111"),
        fontName="Helvetica-Bold",
    )
    status_color = colors.HexColor("#27ae60") if t["status"] == "Active" else colors.HexColor("#e74c3c")

    story = []

    # ── Header ──────────────────────────
    story.append(Paragraph("🚂 Indian Railways", title_style))
    story.append(Paragraph("e-Ticket / Travel Document", sub_style))

    # status badge row
    status_data = [[
        Paragraph(f"Ticket ID: <b>{t['ticket_id']}</b>", styles["Normal"]),
        Paragraph(
            f"<font color='{'#27ae60' if t['status']=='Active' else '#e74c3c'}'><b>● {t['status'].upper()}</b></font>",
            ParagraphStyle("s", parent=styles["Normal"], alignment=TA_RIGHT)
        )
    ]]
    status_tbl = Table(status_data, colWidths=[90*mm, 90*mm])
    status_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#f0f4ff")),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
    ]))
    story.append(status_tbl)
    story.append(Spacer(1, 6))

    # ── Journey Banner ───────────────────
    journey_data = [[
        Paragraph(f"<b>{t['from_city']}</b>", ParagraphStyle("fc", parent=styles["Normal"], fontSize=16, alignment=TA_CENTER)),
        Paragraph("➤", ParagraphStyle("arrow", parent=styles["Normal"], fontSize=20, alignment=TA_CENTER, textColor=colors.HexColor("#f39c12"))),
        Paragraph(f"<b>{t['to_city']}</b>", ParagraphStyle("tc", parent=styles["Normal"], fontSize=16, alignment=TA_CENTER)),
    ]]
    journey_tbl = Table(journey_data, colWidths=[70*mm, 40*mm, 70*mm])
    journey_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#1a3c6e")),
        ("TEXTCOLOR",   (0,0), (-1,-1), colors.white),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
    ]))
    story.append(journey_tbl)
    story.append(Spacer(1, 8))

    def info_table(rows_data):
        tbl = Table(rows_data, colWidths=[50*mm, 80*mm])
        tbl.setStyle(TableStyle([
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
            ("BACKGROUND",  (0,0), (0,-1), colors.HexColor("#f7f9fc")),
            ("TOPPADDING",  (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]))
        return tbl

    # ── Passenger ────────────────────────
    story.append(Paragraph("  Passenger Details", section_style))
    story.append(info_table([
        [Paragraph("Name", label_style),  Paragraph(t["passenger_name"],  value_style)],
        [Paragraph("Age",  label_style),  Paragraph(str(t["passenger_age"]), value_style)],
        [Paragraph("Email",label_style),  Paragraph(t["passenger_email"], value_style)],
    ]))
    story.append(Spacer(1, 6))

    # ── Train ─────────────────────────────
    story.append(Paragraph("  Train Details", section_style))
    story.append(info_table([
        [Paragraph("Train No.",   label_style), Paragraph(t["train_no"],   value_style)],
        [Paragraph("Train Name",  label_style), Paragraph(t["train_name"], value_style)],
        [Paragraph("Train Type",  label_style), Paragraph(t["train_type"], value_style)],
        [Paragraph("Journey Date",label_style), Paragraph(t["journey_date"], value_style)],
        [Paragraph("Departure",   label_style), Paragraph(t["departure_time"], value_style)],
        [Paragraph("Arrival",     label_style), Paragraph(t["arrival_time"], value_style)],
        [Paragraph("Distance",    label_style), Paragraph(f"{t['distance_km']} km", value_style)],
    ]))
    story.append(Spacer(1, 6))

    # ── Seat ──────────────────────────────
    story.append(Paragraph("  Seat & Coach", section_style))
    story.append(info_table([
        [Paragraph("Coach Type",  label_style), Paragraph(t["coach_type"],  value_style)],
        [Paragraph("Seat Number", label_style), Paragraph(t["seat_number"], value_style)],
    ]))
    story.append(Spacer(1, 6))

    # ── Fare ──────────────────────────────
    story.append(Paragraph("  Fare Details", section_style))
    fare_data = [
        [Paragraph("Base Fare",    label_style), Paragraph(f"Rs. {t['base_fare']:.2f}", value_style)],
        [Paragraph("GST (5%)",     label_style), Paragraph(f"Rs. {t['gst_amount']:.2f}", value_style)],
        [Paragraph("TOTAL FARE",   ParagraphStyle("tot", parent=label_style, fontName="Helvetica-Bold")),
         Paragraph(f"Rs. {t['total_fare']:.2f}", ParagraphStyle("totv", parent=value_style, fontSize=12, textColor=colors.HexColor("#1a3c6e")))],
    ]
    fare_tbl = Table(fare_data, colWidths=[50*mm, 80*mm])
    fare_tbl.setStyle(TableStyle([
        ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("BACKGROUND",  (0,0), (0,-1), colors.HexColor("#f7f9fc")),
        ("BACKGROUND",  (0,2), (-1,2), colors.HexColor("#e8f0fe")),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(fare_tbl)
    story.append(Spacer(1, 6))

    # ── Payment ───────────────────────────
    story.append(Paragraph("  Payment Details", section_style))
    story.append(info_table([
        [Paragraph("Payment Method", label_style), Paragraph(t["payment_method"], value_style)],
        [Paragraph("Payment ID",     label_style), Paragraph(t["payment_id"],     value_style)],
        [Paragraph("Payment Status", label_style), Paragraph("CONFIRMED", ParagraphStyle("ps", parent=value_style, textColor=colors.HexColor("#27ae60")))],
        [Paragraph("Booked At",      label_style), Paragraph(t["booked_at"],      value_style)],
    ]))
    story.append(Spacer(1, 8))

    # ── QR Code ───────────────────────────
    qr_img_pil = make_qr_image(t["ticket_id"])
    qr_bytes   = qr_to_bytes(qr_img_pil)
    qr_rl      = RLImage(io.BytesIO(qr_bytes), width=40*mm, height=40*mm)

    qr_note = Paragraph(
        f"<b>Scan QR to verify ticket</b><br/>Ticket ID: {t['ticket_id']}",
        ParagraphStyle("qrn", parent=styles["Normal"], fontSize=8,
                       alignment=TA_CENTER, textColor=colors.HexColor("#555555"))
    )
    qr_outer = Table([[qr_rl], [qr_note]], colWidths=[180*mm])
    qr_outer.setStyle(TableStyle([
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("BACKGROUND",  (0,0), (-1,-1), colors.HexColor("#f0f4ff")),
    ]))
    story.append(qr_outer)
    story.append(Spacer(1, 8))

    # ── Footer ────────────────────────────
    story.append(Paragraph(
        "This is a computer-generated ticket. No physical signature required. "
        "Please carry a valid photo ID during travel.",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.HexColor("#888888"), alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────

st.set_page_config(
    page_title="🚂 Railway Ticketing System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── CSS ──────────────────────────────────
st.markdown("""
<style>
    :root { --primary: #1a3c6e; --accent: #f39c12; --success: #27ae60; --danger: #e74c3c; }
    .main { background: #f5f7fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background: #e8ecf4; border-radius: 10px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: #1a3c6e !important; color: white !important; }
    .ticket-card {
        background: white; border-radius: 14px; padding: 24px;
        box-shadow: 0 4px 20px rgba(26,60,110,0.10);
        border-left: 5px solid #1a3c6e; margin-bottom: 16px;
    }
    .fare-box {
        background: linear-gradient(135deg, #1a3c6e, #2563c4);
        color: white; border-radius: 12px; padding: 18px; text-align: center;
    }
    .status-active  { background:#e8f8f0; color:#27ae60; border-radius:20px; padding:3px 14px; font-weight:700; display:inline-block; }
    .status-used    { background:#fdecea; color:#e74c3c; border-radius:20px; padding:3px 14px; font-weight:700; display:inline-block; }
    .section-header { color:#1a3c6e; font-weight:700; font-size:1.05em; border-bottom:2px solid #e0e7ef; padding-bottom:4px; margin-bottom:12px; }
    .info-row       { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px; }
    .info-item      { flex:1; min-width:140px; background:#f7f9fc; border-radius:8px; padding:10px 14px; }
    .info-label     { font-size:0.75em; color:#888; font-weight:600; text-transform:uppercase; letter-spacing:.5px; }
    .info-value     { font-size:1em; color:#1a3c6e; font-weight:700; margin-top:2px; }
    .journey-banner { background:linear-gradient(90deg,#1a3c6e,#2563c4); color:white; border-radius:12px; padding:16px 24px; text-align:center; margin-bottom:12px; }
    .pay-btn        { background:#1a3c6e !important; color:white !important; border-radius:8px !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────
with st.sidebar:
    st.markdown("### 🚂 Railway Ticketing")
    st.markdown("---")
    total_tickets = len(all_tickets())
    active = sum(1 for t in all_tickets() if t["status"] == "Active")
    used   = total_tickets - active
    st.metric("Total Tickets", total_tickets)
    st.metric("Active",  active,  delta_color="normal")
    st.metric("Used",    used,    delta_color="off")
    st.markdown("---")
    st.markdown("**Fare Formula**")
    st.markdown("Base = Distance × ₹1.5 × Coach Multiplier")
    st.markdown("GST = 5% of Base Fare")
    st.markdown("**Coach Multipliers**")
    for coach, info in COACHES.items():
        st.markdown(f"- {coach}: **{info['multiplier']}×**")

# ── Tabs ─────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎫 Book Ticket", "🔍 Verify Ticket", "📋 All Tickets"])

# ═══════════════════════════════════════════
# TAB 1 — BOOK TICKET
# ═══════════════════════════════════════════
with tab1:
    st.markdown("## 🎫 Book Your Train Ticket")

    with st.form("booking_form"):
        # ── Passenger ──
        st.markdown('<div class="section-header">👤 Passenger Details</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            p_name  = st.text_input("Full Name *", placeholder="e.g. Arjun Sharma")
        with c2:
            p_age   = st.number_input("Age *", min_value=1, max_value=120, value=28)
        with c3:
            p_email = st.text_input("Email *", placeholder="arjun@example.com")

        st.markdown("---")
        # ── Journey ──
        st.markdown('<div class="section-header">🗺️ Journey Details</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            from_city = st.selectbox("From City *", CITIES, index=0)
        with c2:
            to_choices = [c for c in CITIES if c != from_city]
            to_city    = st.selectbox("To City *", to_choices, index=4)
        with c3:
            journey_date = st.date_input(
                "Journey Date *",
                value=datetime.today() + timedelta(days=1),
                min_value=datetime.today(),
            )

        st.markdown("---")
        # ── Train ──
        st.markdown('<div class="section-header">🚂 Train Selection</div>', unsafe_allow_html=True)
        train_options = [f"{t['no']} — {t['name']} ({t['type']})" for t in TRAINS]
        train_sel = st.selectbox("Select Train *", train_options)
        train_idx = train_options.index(train_sel)
        train_obj = TRAINS[train_idx]

        st.markdown("---")
        # ── Coach / Seat ──
        st.markdown('<div class="section-header">💺 Coach & Seat</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            coach_type = st.selectbox("Coach Type *", list(COACHES.keys()))
        with c2:
            coach_letter = st.selectbox("Coach Letter", ["A","B","C","D","E","F","G","H"])

        # ── Fare Preview ──
        dist = get_distance(from_city, to_city)
        base, gst, total = calc_fare(dist, coach_type)
        st.markdown(f"""
        <div class="fare-box">
            <b>💰 Estimated Fare</b><br/>
            <span style="font-size:0.85em;opacity:0.85">
              Distance: {dist} km &nbsp;|&nbsp; Base: ₹{base:.2f} &nbsp;|&nbsp; GST 5%: ₹{gst:.2f}
            </span><br/>
            <span style="font-size:1.8em;font-weight:800">₹{total:.2f}</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        # ── Payment ──
        st.markdown('<div class="section-header">💳 Payment Method</div>', unsafe_allow_html=True)
        payment_method = st.radio(
            "Choose Payment", ["UPI", "Card", "Net Banking"], horizontal=True
        )
        if payment_method == "UPI":
            st.text_input("UPI ID", placeholder="yourname@upi")
        elif payment_method == "Card":
            cc1, cc2, cc3 = st.columns(3)
            with cc1: st.text_input("Card Number", placeholder="**** **** **** ****", max_chars=19)
            with cc2: st.text_input("Expiry", placeholder="MM/YY", max_chars=5)
            with cc3: st.text_input("CVV", placeholder="***", max_chars=3, type="password")
        else:
            st.selectbox("Bank", ["State Bank of India","HDFC Bank","ICICI Bank","Axis Bank","Kotak Bank","Punjab National Bank"])

        submitted = st.form_submit_button("✅ Confirm & Pay ₹{:.2f}".format(total), use_container_width=True)

    if submitted:
        # Validation
        errors = []
        if not p_name.strip():    errors.append("Passenger name is required.")
        if not p_email.strip():   errors.append("Email is required.")
        if from_city == to_city:  errors.append("Source and destination cannot be the same.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            journey_date_str = journey_date.strftime("%d-%b-%Y")
            dep_time, arr_time = random_times(journey_date.strftime("%Y-%m-%d"))
            seat_no    = make_seat(coach_type, coach_letter)
            ticket_id  = make_ticket_id()
            payment_id = make_payment_id(payment_method)

            ticket_data = {
                "ticket_id":       ticket_id,
                "passenger_name":  p_name.strip(),
                "passenger_age":   int(p_age),
                "passenger_email": p_email.strip(),
                "train_no":        train_obj["no"],
                "train_name":      train_obj["name"],
                "train_type":      train_obj["type"],
                "from_city":       from_city,
                "to_city":         to_city,
                "departure_time":  dep_time,
                "arrival_time":    arr_time,
                "journey_date":    journey_date_str,
                "coach_type":      coach_type,
                "seat_number":     seat_no,
                "distance_km":     dist,
                "base_fare":       base,
                "gst_amount":      gst,
                "total_fare":      total,
                "payment_method":  payment_method,
                "payment_id":      payment_id,
                "status":          "Active",
                "booked_at":       datetime.now().strftime("%d-%b-%Y %H:%M:%S"),
            }
            insert_ticket(ticket_data)

            # ── Success Display ──────────────────
            st.success("🎉 Ticket Booked Successfully! Payment Confirmed.")

            t = ticket_data
            qr_img = make_qr_image(ticket_id)
            qr_b64  = pil_to_b64(qr_img)

            st.markdown(f"""
            <div class="ticket-card">
              <div class="journey-banner">
                <span style="font-size:1.5em;font-weight:800">{t['from_city']}</span>
                &nbsp; ✈ &nbsp;
                <span style="font-size:1.5em;font-weight:800">{t['to_city']}</span>
                <br/><span style="opacity:0.8;font-size:0.85em">{t['departure_time']} → {t['arrival_time']}</span>
              </div>

              <div class="info-row">
                <div class="info-item"><div class="info-label">Ticket ID</div><div class="info-value">{t['ticket_id']}</div></div>
                <div class="info-item"><div class="info-label">Passenger</div><div class="info-value">{t['passenger_name']}, {t['passenger_age']}y</div></div>
                <div class="info-item"><div class="info-label">Train</div><div class="info-value">{t['train_no']} {t['train_name']}</div></div>
              </div>
              <div class="info-row">
                <div class="info-item"><div class="info-label">Coach / Seat</div><div class="info-value">{t['coach_type'].split('(')[1].rstrip(')')} / {t['seat_number']}</div></div>
                <div class="info-item"><div class="info-label">Distance</div><div class="info-value">{t['distance_km']} km</div></div>
                <div class="info-item"><div class="info-label">Total Fare</div><div class="info-value">₹{t['total_fare']:.2f}</div></div>
              </div>
              <div class="info-row">
                <div class="info-item"><div class="info-label">Payment</div><div class="info-value">{t['payment_method']} — {t['payment_id']}</div></div>
                <div class="info-item"><div class="info-label">Status</div><div class="info-value"><span class="status-active">ACTIVE</span></div></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col_qr, col_dl = st.columns([1, 2])
            with col_qr:
                st.markdown("**Your QR Code**")
                st.image(qr_img, width=200, caption=ticket_id)
            with col_dl:
                st.markdown("**Download your e-Ticket PDF**")
                pdf_bytes = generate_pdf(t)
                st.download_button(
                    label="📥 Download PDF Ticket",
                    data=pdf_bytes,
                    file_name=f"ticket_{ticket_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.info(f"📧 Ticket confirmation sent to **{t['passenger_email']}**  \n🆔 Save your Ticket ID: **{ticket_id}**")

# ═══════════════════════════════════════════
# TAB 2 — VERIFY TICKET
# ═══════════════════════════════════════════
with tab2:
    st.markdown("## 🔍 Verify Ticket")
    st.markdown("Enter your Ticket ID to verify status and mark as used.")

    verify_id = st.text_input("Ticket ID", placeholder="TKT-XXXXXXXXXX").strip().upper()

    col_v1, col_v2 = st.columns([1, 1])
    with col_v1:
        do_verify = st.button("🔍 Verify Ticket", use_container_width=True)
    with col_v2:
        do_mark   = st.button("✅ Mark as Used", use_container_width=True, type="secondary")

    if do_verify or do_mark:
        if not verify_id:
            st.warning("Please enter a Ticket ID.")
        else:
            t = get_ticket(verify_id)
            if not t:
                st.error(f"❌ No ticket found with ID: **{verify_id}**")
            else:
                if do_mark:
                    if t["status"] == "Used":
                        st.warning("Ticket is already marked as Used.")
                    else:
                        mark_used(verify_id)
                        t = get_ticket(verify_id)
                        st.success("Ticket marked as **Used**.")

                status_cls = "status-active" if t["status"] == "Active" else "status-used"
                qr_img = make_qr_image(t["ticket_id"])

                st.markdown(f"""
                <div class="ticket-card">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <span style="font-size:1.1em;font-weight:700;color:#1a3c6e">Ticket {t['ticket_id']}</span>
                    <span class="{status_cls}">{t['status'].upper()}</span>
                  </div>
                  <div class="journey-banner">
                    <span style="font-size:1.4em;font-weight:800">{t['from_city']}</span>
                    &nbsp; → &nbsp;
                    <span style="font-size:1.4em;font-weight:800">{t['to_city']}</span>
                    <br/><span style="opacity:0.8;font-size:0.85em">{t['departure_time']} → {t['arrival_time']}</span>
                  </div>
                  <div class="info-row">
                    <div class="info-item"><div class="info-label">Passenger</div><div class="info-value">{t['passenger_name']}, {t['passenger_age']}y</div></div>
                    <div class="info-item"><div class="info-label">Email</div><div class="info-value">{t['passenger_email']}</div></div>
                  </div>
                  <div class="info-row">
                    <div class="info-item"><div class="info-label">Train</div><div class="info-value">{t['train_no']} — {t['train_name']}</div></div>
                    <div class="info-item"><div class="info-label">Type</div><div class="info-value">{t['train_type']}</div></div>
                    <div class="info-item"><div class="info-label">Journey Date</div><div class="info-value">{t['journey_date']}</div></div>
                  </div>
                  <div class="info-row">
                    <div class="info-item"><div class="info-label">Coach</div><div class="info-value">{t['coach_type']}</div></div>
                    <div class="info-item"><div class="info-label">Seat</div><div class="info-value">{t['seat_number']}</div></div>
                    <div class="info-item"><div class="info-label">Distance</div><div class="info-value">{t['distance_km']} km</div></div>
                  </div>
                  <div class="info-row">
                    <div class="info-item"><div class="info-label">Base Fare</div><div class="info-value">&#8377;{t['base_fare']:.2f}</div></div>
                    <div class="info-item"><div class="info-label">GST (5%)</div><div class="info-value">&#8377;{t['gst_amount']:.2f}</div></div>
                    <div class="info-item"><div class="info-label">Total Paid</div><div class="info-value">&#8377;{t['total_fare']:.2f}</div></div>
                  </div>
                  <div class="info-row">
                    <div class="info-item"><div class="info-label">Payment</div><div class="info-value">{t['payment_method']}</div></div>
                    <div class="info-item"><div class="info-label">Payment ID</div><div class="info-value">{t['payment_id']}</div></div>
                    <div class="info-item"><div class="info-label">Booked At</div><div class="info-value">{t['booked_at']}</div></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.image(qr_img, width=180, caption="QR Code")
                with col_b:
                    pdf_bytes = generate_pdf(t)
                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_bytes,
                        file_name=f"ticket_{t['ticket_id']}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

# ═══════════════════════════════════════════
# TAB 3 — ALL TICKETS
# ═══════════════════════════════════════════
with tab3:
    st.markdown("## 📋 All Tickets")

    tickets = all_tickets()
    if not tickets:
        st.info("No tickets booked yet. Go to **Book Ticket** to get started!")
    else:
        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            filter_status = st.selectbox("Filter by Status", ["All", "Active", "Used"])
        with f2:
            filter_city = st.selectbox("Filter by City", ["All"] + sorted(CITIES))
        with f3:
            search_name = st.text_input("Search by Name", placeholder="Passenger name...")

        filtered = tickets
        if filter_status != "All":
            filtered = [t for t in filtered if t["status"] == filter_status]
        if filter_city != "All":
            filtered = [t for t in filtered if t["from_city"] == filter_city or t["to_city"] == filter_city]
        if search_name.strip():
            filtered = [t for t in filtered if search_name.lower() in t["passenger_name"].lower()]

        st.markdown(f"**{len(filtered)} ticket(s) found**")

        for t in filtered:
            status_cls = "status-active" if t["status"] == "Active" else "status-used"
            with st.expander(f"🎫 {t['ticket_id']}  |  {t['from_city']} → {t['to_city']}  |  {t['passenger_name']}  |  ₹{t['total_fare']:.2f}"):
                st.markdown(f"""
                <div class="info-row">
                  <div class="info-item"><div class="info-label">Status</div><div class="info-value"><span class="{status_cls}">{t['status']}</span></div></div>
                  <div class="info-item"><div class="info-label">Train</div><div class="info-value">{t['train_no']} {t['train_name']}</div></div>
                  <div class="info-item"><div class="info-label">Journey Date</div><div class="info-value">{t['journey_date']}</div></div>
                </div>
                <div class="info-row">
                  <div class="info-item"><div class="info-label">Departure</div><div class="info-value">{t['departure_time']}</div></div>
                  <div class="info-item"><div class="info-label">Arrival</div><div class="info-value">{t['arrival_time']}</div></div>
                  <div class="info-item"><div class="info-label">Coach / Seat</div><div class="info-value">{t['coach_type']} / {t['seat_number']}</div></div>
                </div>
                <div class="info-row">
                  <div class="info-item"><div class="info-label">Base Fare</div><div class="info-value">&#8377;{t['base_fare']:.2f}</div></div>
                  <div class="info-item"><div class="info-label">GST</div><div class="info-value">&#8377;{t['gst_amount']:.2f}</div></div>
                  <div class="info-item"><div class="info-label">Total</div><div class="info-value">&#8377;{t['total_fare']:.2f}</div></div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    pdf_bytes = generate_pdf(t)
                    st.download_button(
                        "📥 PDF",
                        data=pdf_bytes,
                        file_name=f"ticket_{t['ticket_id']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{t['ticket_id']}",
                        use_container_width=True,
                    )
                with c2:
                    if t["status"] == "Active":
                        if st.button("✅ Mark Used", key=f"use_{t['ticket_id']}", use_container_width=True):
                            mark_used(t["ticket_id"])
                            st.rerun()
