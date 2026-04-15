# 🚂 QR-Based Railway Ticketing System

A full-featured Streamlit app for booking train tickets with QR code generation, PDF download, and SQLite persistence.

## Features

- **Book Ticket** — Passenger details, train selection, coach/seat picker, fare calculator with GST
- **Payment Simulation** — UPI, Card, Net Banking
- **QR Code** — Generated per ticket, embedded in PDF
- **SQLite Storage** — All ticket data persisted locally in `railway_tickets.db`
- **Ticket Verification** — Active / Used status, mark as used
- **PDF Download** — Full ticket with passenger, journey, train, timings, seat, fare, GST, payment status and QR

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

## Fare Formula

```
Base Fare  = Distance (km) × ₹1.5 × Coach Multiplier
GST        = 5% of Base Fare
Total Fare = Base Fare + GST
```

### Coach Multipliers
| Coach | Multiplier |
|-------|-----------|
| Sleeper (SL) | 1.0× |
| AC 3-Tier (3A) | 2.0× |
| AC 2-Tier (2A) | 3.0× |
| AC First Class (1A) | 5.0× |
| Chair Car (CC) | 1.5× |
| Executive Chair (EC) | 2.5× |

## Cities Covered
35 Indian districts/cities including Hyderabad, Bengaluru, Chennai, Pune, Ahmedabad, Jaipur, Lucknow, and more.

## Trains
15 named trains including Rajdhani Express, Shatabdi Express, Karnataka Express, Tamil Nadu Express, and more.
