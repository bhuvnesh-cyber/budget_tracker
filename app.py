import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
import plotly.graph_objects as go
import plotly.express as px

# -----------------------
# PAGE CONFIG
# -----------------------
st.set_page_config(
    page_title="Spend Guard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, minimal design
st.markdown("""
<style>
    /* Main background and text */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* Remove default streamlit styling */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Card style containers */
    .stMetric {
        background: rgba(255, 255, 255, 0.95);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Data frames */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Forms */
    .stForm {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 12px;
        font-weight: 600;
    }
    
    /* Input fields */
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .stNumberInput > div > div > input:focus,
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 12px;
        padding: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: white;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Dividers */
    hr {
        border: none;
        height: 2px;
        background: rgba(255, 255, 255, 0.2);
        margin: 2rem 0;
    }
    
    /* Mobile-specific styles */
    @media (max-width: 768px) {
        .main {
            padding: 1rem;
        }
        
        .stMetric {
            padding: 1rem;
        }
        
        h1 {
            font-size: 2rem !important;
        }
        
        h3 {
            font-size: 1.2rem !important;
        }
        
        /* Hide calculator link on mobile */
        .calculator-link {
            display: none;
        }
        
        /* Make forms more compact */
        .stForm {
            padding: 1rem;
        }
        
        /* Smaller buttons */
        .stButton > button {
            padding: 0.6rem 1.5rem;
            font-size: 0.9rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------
# FILES & CONFIG
# -----------------------
DATA_DIR = "spend_data"
os.makedirs(DATA_DIR, exist_ok=True)

def get_spend_file(month):
    return os.path.join(DATA_DIR, f"spends_{month}.csv")

def get_income_file():
    return os.path.join(DATA_DIR, "income.csv")

CARDS = {
    "Tata Neu RuPay": {"limit": 51000, "cashback": 0.015, "color": "#FF6B6B"},
    "SBI Cashback": {"limit": 80000, "cashback": 0.05, "color": "#4ECDC4"},
    "Debit Card": {"limit": None, "cashback": 0.0, "color": "#95E1D3"}
}

CATEGORIES = ["Rent", "Electricity", "Groceries", "Food & Dining", "Travel", "Subscriptions", "Shopping", "Savings", "Money Lent", "Family", "EMI", "Misc"]

# -----------------------
# HELPER FUNCTIONS
# -----------------------
def get_week_start(d):
    return d - timedelta(days=d.weekday())

def get_week_label(d):
    week_start = get_week_start(d)
    week_end = week_start + timedelta(days=6)
    return f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"

def load_month_spends(month):
    file_path = get_spend_file(month)
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                return pd.DataFrame(columns=["date", "card", "category", "amount", "notes"])
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            # Ensure amount is numeric
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
            df = df.dropna(subset=["amount"])
            # Filter out zero or negative amounts
            df = df[df["amount"] > 0]
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame(columns=["date", "card", "category", "amount", "notes"])
    return pd.DataFrame(columns=["date", "card", "category", "amount", "notes"])

def save_month_spends(df, month):
    df.to_csv(get_spend_file(month), index=False)

def load_income():
    file_path = get_income_file()
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Ensure numeric columns
            df["salary"] = pd.to_numeric(df["salary"], errors="coerce").fillna(0)
            df["other_income"] = pd.to_numeric(df["other_income"], errors="coerce").fillna(0)
            return df
        except Exception as e:
            st.error(f"Error loading income: {e}")
            return pd.DataFrame(columns=["month", "salary", "other_income"])
    return pd.DataFrame(columns=["month", "salary", "other_income"])

def save_income(df):
    df.to_csv(get_income_file(), index=False)

def get_available_months():
    months = []
    if os.path.exists(DATA_DIR):
        for file in os.listdir(DATA_DIR):
            if file.startswith("spends_") and file.endswith(".csv"):
                months.append(file.replace("spends_", "").replace(".csv", ""))
    return sorted(months, reverse=True)

# -----------------------
# HEADER & MONTH SELECTOR
# -----------------------
header_col1, header_col2 = st.columns([6, 1])
with header_col1:
    st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom: 0;'>💸 Spend Guard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.9); font-size: 1.1rem; margin-top: 0;'>Simple. Smart. In Control.</p>", unsafe_allow_html=True)
with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
        <div class="calculator-link">
            <a href="https://www.calculator.net/" target="_blank" style="
                display: inline-block;
                background: rgba(255, 255, 255, 0.95);
                color: #667eea;
                padding: 0.75rem 1.5rem;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            ">🧮 Calculator</a>
        </div>
    """, unsafe_allow_html=True)

# Month selector at top
today = date.today()
current_month = today.strftime("%Y-%m")
available_months = get_available_months()
if current_month not in available_months:
    available_months = [current_month] + available_months

# Detect mobile view based on viewport (simple heuristic)
if 'mobile_view' not in st.session_state:
    st.session_state.mobile_view = False

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    selected_month = st.selectbox(
        "📅 Select Month to Manage",
        options=available_months,
        format_func=lambda x: datetime.strptime(x, "%Y-%m").strftime("%B %Y") + (" ⭐ Current" if x == current_month else ""),
        label_visibility="collapsed",
        help="Switch months to add or view expenses for different months"
    )

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------
# LOAD DATA
# -----------------------
spends_df = load_month_spends(selected_month)
income_df = load_income()
existing_income = income_df[income_df["month"] == selected_month]

# -----------------------
# INCOME SETTING (Compact at top)
# -----------------------
with st.expander("💰 Set Monthly Income", expanded=existing_income.empty):
    inc_col1, inc_col2, inc_col3 = st.columns([2, 2, 1])
    with inc_col1:
        salary = st.number_input("Salary", min_value=0, step=1000, 
                                value=int(existing_income["salary"].iloc[0]) if not existing_income.empty else 0,
                                key=f"sal_{selected_month}", placeholder="Enter salary")
    with inc_col2:
        other_income = st.number_input("Other Income", min_value=0, step=1000,
                                      value=int(existing_income["other_income"].iloc[0]) if not existing_income.empty else 0,
                                      key=f"oth_{selected_month}", placeholder="Other income")
    with inc_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save", use_container_width=True):
            if salary > 0 or other_income > 0:
                income_df = income_df[income_df["month"] != selected_month]
                income_df = pd.concat([income_df, pd.DataFrame([{
                    "month": selected_month, "salary": int(salary), "other_income": int(other_income)
                }])], ignore_index=True)
                save_income(income_df)
                st.success("✅ Saved!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter at least one income value")

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------
# QUICK STATS ROW
# -----------------------
if not existing_income.empty or not spends_df.empty:
    monthly_income = (int(existing_income["salary"].iloc[0]) if not existing_income.empty else 0) + \
                     (int(existing_income["other_income"].iloc[0]) if not existing_income.empty else 0)
    total_spent = spends_df["amount"].sum() if not spends_df.empty else 0
    
    # Calculate savings and money lent separately
    savings_amount = spends_df[spends_df["category"] == "Savings"]["amount"].sum() if not spends_df.empty else 0
    money_lent = spends_df[spends_df["category"] == "Money Lent"]["amount"].sum() if not spends_df.empty else 0
    
    # Total spent excluding savings and money lent for actual expense calculation
    actual_expenses = total_spent - savings_amount - money_lent
    remaining = monthly_income - total_spent
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Income", f"₹{monthly_income:,}")
    with col2:
        st.metric("📤 Spent", f"₹{int(actual_expenses):,}", delta=f"{int(actual_expenses/monthly_income*100) if monthly_income > 0 else 0}% of income", delta_color="inverse")
    with col3:
        st.metric("💵 Remaining", f"₹{int(remaining):,}", delta="Over!" if remaining < 0 else None, delta_color="off" if remaining < 0 else "normal")
    with col4:
        cashback = sum([spends_df[spends_df["card"]==c]["amount"].sum() * CARDS[c]["cashback"] for c in CARDS.keys()]) if not spends_df.empty else 0
        st.metric("🎁 Cashback", f"₹{int(cashback):,}")
    
    st.markdown("<br>", unsafe_allow_html=True)

# -----------------------
# SPEND ENTRY & INSIGHTS (Side by Side)
# -----------------------
col_left, col_right = st.columns([1, 1], gap="large")

# LEFT: Spend Entry
with col_left:
    st.markdown(f"### ➕ Add Spend for {datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')}")
    
    with st.form("spend_form", clear_on_submit=True):
        # Get first and last day of selected month
        selected_year = int(selected_month[:4])
        selected_mo = int(selected_month[5:])
        first_day = date(selected_year, selected_mo, 1)
        if selected_mo == 12:
            last_day = date(selected_year, 12, 31)
        else:
            last_day = date(selected_year, selected_mo + 1, 1) - timedelta(days=1)
        
        # Default date: today if current month, else last day of selected month
        default_date = today if selected_month == current_month else last_day
        
        spend_date = st.date_input("Date", value=default_date, min_value=first_day, max_value=last_day, label_visibility="collapsed")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", CATEGORIES, label_visibility="collapsed", placeholder="Category")
        with col2:
            card = st.selectbox("Card", list(CARDS.keys()), label_visibility="collapsed", placeholder="Card")
        
        amount = st.number_input("Amount", min_value=0, step=50, value=0, label_visibility="collapsed", placeholder="₹ Amount")
        notes = st.text_input("Notes", label_visibility="collapsed", placeholder="Optional notes...")
        
        if st.form_submit_button("💾 Save Spend", use_container_width=True):
            if amount > 0:
                new_spend = pd.DataFrame([{
                    "date": pd.to_datetime(spend_date), 
                    "card": card, 
                    "category": category,
                    "amount": float(amount), 
                    "notes": notes if notes else ""
                }])
                spends_df = pd.concat([spends_df, new_spend], ignore_index=True)
                save_month_spends(spends_df, selected_month)
                st.success(f"✅ ₹{amount:,} saved!")
                st.rerun()
            else:
                st.warning("⚠️ Please enter an amount greater than 0")

# RIGHT: Insights with Tabs
with col_right:
    st.markdown("### 💡 Smart Insights")
    
    # Create tabs for different insights
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "💰 Savings", "🤝 Money Lent"])
    
    with tab1:
        if not existing_income.empty and not spends_df.empty:
            monthly_income = int(existing_income["salary"].iloc[0]) + int(existing_income["other_income"].iloc[0])
            
            if monthly_income == 0:
                st.warning("⚠️ Set your income to see insights")
            else:
                total_spent = spends_df["amount"].sum()
                
                # Exclude savings and money lent from actual expenses
                savings_amount = spends_df[spends_df["category"] == "Savings"]["amount"].sum()
                money_lent = spends_df[spends_df["category"] == "Money Lent"]["amount"].sum()
                actual_expenses = total_spent - savings_amount - money_lent
                remaining = monthly_income - total_spent
            
                # Calculate weeks remaining in month
                if selected_month == current_month:
                    # Calculate days in current month
                    if today.month == 12:
                        days_in_month = 31
                    else:
                        next_month = date(today.year, today.month + 1, 1)
                        last_day = next_month - timedelta(days=1)
                        days_in_month = last_day.day
                    
                    days_remaining = days_in_month - today.day + 1
                    weeks_remaining = max(1, days_remaining / 7)
                    
                    weekly_budget = remaining / weeks_remaining if remaining > 0 else 0
                    daily_budget = remaining / days_remaining if remaining > 0 else 0
                    
                    insight_col1, insight_col2 = st.columns(2)
                    with insight_col1:
                        st.metric("📅 Weekly Budget", f"₹{int(weekly_budget):,}")
                    with insight_col2:
                        st.metric("📆 Daily Budget", f"₹{int(daily_budget):,}")
                    
                    # Average daily spending
                    days_passed = today.day
                    avg_daily = actual_expenses / days_passed if days_passed > 0 else 0
                    projected = avg_daily * days_in_month
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    avg_col1, avg_col2 = st.columns(2)
                    with avg_col1:
                        st.metric("📊 Avg Daily Spend", f"₹{int(avg_daily):,}")
                    with avg_col2:
                        budget_for_expenses = monthly_income - savings_amount - money_lent
                        over_under = projected - budget_for_expenses
                        over_under_text = "over budget" if over_under > 0 else "under budget"
                        st.metric("🎯 Month Projection", f"₹{int(projected):,}",
                                 delta=f"₹{abs(int(over_under)):,} {over_under_text}",
                                 delta_color="inverse" if over_under > 0 else "normal")
                else:
                    # Historical insights
                    selected_year = int(selected_month[:4])
                    selected_mo = int(selected_month[5:])
                    
                    # Calculate days in selected month
                    if selected_mo == 12:
                        days_in_month = 31
                    else:
                        next_month = date(selected_year, selected_mo + 1, 1)
                        last_day = next_month - timedelta(days=1)
                        days_in_month = last_day.day
                    
                    avg_daily = actual_expenses / days_in_month if days_in_month > 0 else 0
                    
                    insight_col1, insight_col2 = st.columns(2)
                    with insight_col1:
                        st.metric("📊 Avg Daily Spend", f"₹{int(avg_daily):,}")
                    with insight_col2:
                        savings_rate = ((monthly_income - actual_expenses) / monthly_income * 100) if monthly_income > 0 else 0
                        st.metric("💰 Savings Rate", f"{savings_rate:.1f}%")
        elif not existing_income.empty:
            st.info("📊 Add some spends to see insights!")
        elif not spends_df.empty:
            st.info("💰 Set your income to see insights!")
        else:
            st.info("📊 Set your income and add spends to see smart insights!")
    
    with tab2:
        # Savings insights
        if not spends_df.empty:
            savings_data = spends_df[spends_df["category"] == "Savings"]
            if not savings_data.empty:
                total_savings = savings_data["amount"].sum()
                num_savings = len(savings_data)
                avg_savings = total_savings / num_savings if num_savings > 0 else 0
                
                st.metric("💰 Total Saved", f"₹{int(total_savings):,}")
                
                sav_col1, sav_col2 = st.columns(2)
                with sav_col1:
                    st.metric("📊 Transactions", f"{num_savings}")
                with sav_col2:
                    st.metric("📈 Avg Amount", f"₹{int(avg_savings):,}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Recent Savings:**")
                for _, row in savings_data.sort_values("date", ascending=False).head(5).iterrows():
                    note_text = f" - {row['notes']}" if row['notes'] and str(row['notes']).strip() and str(row['notes']) != 'nan' else ""
                    st.caption(f"• {row['date'].strftime('%b %d')} - ₹{int(row['amount']):,}{note_text}")
            else:
                st.info("💰 No savings recorded yet. Start saving!")
        else:
            st.info("💰 Add some transactions first")
    
    with tab3:
        # Money Lent insights
        if not spends_df.empty:
            lent_data = spends_df[spends_df["category"] == "Money Lent"]
            if not lent_data.empty:
                total_lent = lent_data["amount"].sum()
                num_lent = len(lent_data)
                avg_lent = total_lent / num_lent if num_lent > 0 else 0
                
                st.metric("🤝 Total Lent", f"₹{int(total_lent):,}")
                
                lent_col1, lent_col2 = st.columns(2)
                with lent_col1:
                    st.metric("📊 Transactions", f"{num_lent}")
                with lent_col2:
                    st.metric("📈 Avg Amount", f"₹{int(avg_lent):,}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Recent Lending:**")
                for _, row in lent_data.sort_values("date", ascending=False).head(5).iterrows():
                    note_text = f" - {row['notes']}" if row['notes'] and str(row['notes']).strip() and str(row['notes']) != 'nan' else ""
                    st.caption(f"• {row['date'].strftime('%b %d')} - ₹{int(row['amount']):,}{note_text}")
            else:
                st.info("🤝 No money lent recorded yet")
        else:
            st.info("🤝 Add some transactions first")

st.markdown("<hr>", unsafe_allow_html=True)

# -----------------------
# DATA VISUALIZATION
# -----------------------
if not spends_df.empty:
    spends_df["week_start"] = spends_df["date"].apply(lambda x: get_week_start(x.date()))
    
    # Category Breakdown
    st.markdown("### 📊 Category Breakdown")
    cat_summary = spends_df.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
    
    if not cat_summary.empty:
        # Show top 2 on mobile, top 4 on desktop
        num_cols = 2 if st.session_state.get('mobile_view', False) else min(len(cat_summary), 4)
        cols = st.columns(num_cols)
        for idx, (_, row) in enumerate(cat_summary.head(num_cols).iterrows()):
            with cols[idx]:
                pct = (row["amount"] / spends_df["amount"].sum() * 100)
                st.metric(row["category"], f"₹{int(row['amount']):,}", delta=f"{pct:.1f}%")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Weekly Timeline
    st.markdown("### 📅 Weekly Timeline")
    week_summary = spends_df.groupby("week_start")["amount"].agg(["sum", "count"]).reset_index()
    week_summary.columns = ["week_start", "total", "transactions"]
    week_summary = week_summary.sort_values("week_start")
    
    current_week = get_week_start(today) if selected_month == current_month else None
    
    if not week_summary.empty:
        for _, row in week_summary.iterrows():
            is_current = (current_week and row["week_start"] == current_week)
            week_label = get_week_label(row["week_start"])
        
        
        with st.expander(f"{'⭐ ' if is_current else ''}{week_label} • ₹{int(row['total']):,} • {int(row['transactions'])} transactions", expanded=is_current):
            week_data = spends_df[spends_df["week_start"] == row["week_start"]].sort_values("date", ascending=False)
            
            for idx, spend_row in week_data.iterrows():
                # Mobile-friendly layout: stack vertically
                if st.session_state.get('mobile_view', False):
                    col_main, col_del = st.columns([10, 1])
                    with col_main:
                        st.markdown(f"**{spend_row['date'].strftime('%b %d')}** • {spend_row['category']}")
                        st.markdown(f"{spend_row['card']} • **₹{int(spend_row['amount']):,}**")
                    with col_del:
                        if st.button("🗑️", key=f"del_{idx}", help="Delete"):
                            spends_df = spends_df.drop(idx)
                            save_month_spends(spends_df, selected_month)
                            st.rerun()
                else:
                    # Desktop layout: horizontal
                    col_date, col_cat, col_card, col_amt, col_del = st.columns([1.5, 2, 2.5, 1.5, 0.5])
                    
                    with col_date:
                        st.markdown(f"**{spend_row['date'].strftime('%b %d')}**")
                    with col_cat:
                        st.markdown(f"{spend_row['category']}")
                    with col_card:
                        st.markdown(f"{spend_row['card']}")
                    with col_amt:
                        st.markdown(f"**₹{int(spend_row['amount']):,}**")
                    with col_del:
                        if st.button("🗑️", key=f"del_{idx}", help="Delete"):
                            spends_df = spends_df.drop(idx)
                            save_month_spends(spends_df, selected_month)
                            st.rerun()
                
                # Show notes on new line if present
                if spend_row['notes'] and str(spend_row['notes']).strip() and str(spend_row['notes']) != 'nan':
                    st.caption(f"📝 {spend_row['notes']}")
                
                if idx != week_data.index[-1]:
                    st.markdown("<hr style='margin: 0.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Card Usage
    st.markdown("### 💳 Card Usage")
    if not spends_df.empty:
        # Show cards in single column on mobile, 3 columns on desktop
        num_card_cols = 1 if st.session_state.get('mobile_view', False) else len(CARDS)
        card_cols = st.columns(num_card_cols)
        
        for idx, (card_name, meta) in enumerate(CARDS.items()):
            col_idx = 0 if num_card_cols == 1 else idx
            with card_cols[col_idx]:
                spend = spends_df[spends_df["card"] == card_name]["amount"].sum()
                util = f"{spend/meta['limit']*100:.1f}%" if meta["limit"] else "—"
                cashback = spend * meta["cashback"]
                
                st.markdown(f"**{card_name}**")
                st.metric("Spent", f"₹{int(spend):,}", delta=util)
                st.caption(f"🎁 Cashback: ₹{int(cashback):,}")
                
                # Add spacing between cards on mobile
                if num_card_cols == 1 and idx < len(CARDS) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No card usage data yet")
else:
    st.info("👋 No spends yet. Add your first transaction above!")
