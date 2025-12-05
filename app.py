import streamlit as st
import pandas as pd
import json
import os
import datetime
import calendar
import altair as alt

# --- Constants & Configuration ---
DATA_FILE = "budget_data.json"
st.set_page_config(page_title="Budget Tracker", page_icon="💰", layout="centered")

# --- Data Handling ---
def load_data():
    default_data = {
        "earnings": 0.0,
        "needs": {},
        "wants": {},
        "savings": {},
        "debts": {},
        "expenses": [],
        "last_month": datetime.datetime.now().month
    }

    if not os.path.exists(DATA_FILE):
        return default_data

    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)

            # Migration for old structure
            if "budgets" in data:
                data["needs"] = data.get("budgets", {})
                del data["budgets"]

            # Ensure all keys exist
            for key in default_data:
                if key not in data:
                    data[key] = default_data[key]

            # Check for Month Reset
            current_month = datetime.datetime.now().month
            if data["last_month"] != current_month:
                data["expenses"] = []
                data["last_month"] = current_month

            return data
    except json.JSONDecodeError:
        return default_data

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize Session State
if "data" not in st.session_state:
    st.session_state.data = load_data()

# --- Helper Functions ---
def get_current_month_dates():
    now = datetime.datetime.now()
    _, num_days = calendar.monthrange(now.year, now.month)
    return now, num_days

def calculate_totals():
    total_earnings = st.session_state.data["earnings"]

    # Get all active categories to filter out orphaned expenses
    active_cats = set()
    for section in ["needs", "wants", "savings", "debts"]:
        active_cats.update(st.session_state.data[section].keys())

    # Get debt categories
    debt_cats = list(st.session_state.data["debts"].keys())
    expenses = st.session_state.data["expenses"]

    # Filter expenses to only include active categories
    valid_expenses = [x for x in expenses if x["Category"] in active_cats]

    # Calculate spending in non-debt categories
    spent_non_debt = sum(x["Amount"] for x in valid_expenses if x["Category"] not in debt_cats)

    # Calculate debt spending (actual payments made)
    debt_spent_total = sum(x["Amount"] for x in valid_expenses if x["Category"] in debt_cats)

    # For debt calculation:
    # Deduction should be the budgeted debt amounts (total liability)
    debt_budget_total = sum(st.session_state.data["debts"].values())

    # Remaining = Earnings - Non-debt spending - Total debt budget
    remaining = total_earnings - spent_non_debt - debt_budget_total

    # Total Spent includes both non-debt spending AND debt payments
    total_spent = spent_non_debt + debt_spent_total

    return total_earnings, total_spent, remaining

def update_spent_callback(cat, key):
    new_total = st.session_state.get(key)
    if new_total is None:
        return

    # Calculate current total for this category
    current_total = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] == cat)
    diff = new_total - current_total

    if diff != 0:
        new_expense = {
            "Category": cat,
            "Amount": int(diff),
            "Date": str(datetime.date.today()),
            "Note": "Manual Update"
        }
        st.session_state.data["expenses"].append(new_expense)
        save_data(st.session_state.data)

def set_max_spent(cat, budget, input_key):
    current_total = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] == cat)
    diff = budget - current_total
    if diff != 0:
        new_expense = {
            "Category": cat,
            "Amount": int(diff),
            "Date": str(datetime.date.today()),
            "Note": "Max Button"
        }
        st.session_state.data["expenses"].append(new_expense)
        save_data(st.session_state.data)
        st.session_state[input_key] = int(budget)

def add_category(section, name, budget):
    if name and name.strip():
        name = name.strip()
        if name not in st.session_state.data[section]:
            st.session_state.data[section][name] = budget
            save_data(st.session_state.data)
            return True
    return False

def delete_category(section, name):
    if name in st.session_state.data[section]:
        del st.session_state.data[section][name]
        st.session_state.data["expenses"] = [
            x for x in st.session_state.data["expenses"] 
            if x["Category"] != name
        ]
        save_data(st.session_state.data)

def get_weeks_in_month(year, month):
    """Returns a list of (start_date, end_date) tuples for each week in the month."""
    cal = calendar.monthcalendar(year, month)
    weeks = []
    for week in cal:
        days = [d for d in week if d != 0]
        if not days:
            continue
        start_day = days[0]
        end_day = days[-1]
        start_date = datetime.date(year, month, start_day)
        end_date = datetime.date(year, month, end_day)
        weeks.append((start_date, end_date))
    return weeks

# --- Plotting ---
def render_summary_plot():
    summary_data = []
    total_earnings = st.session_state.data["earnings"]

    for section in ["needs", "wants", "savings"]:
        budget = sum(st.session_state.data[section].values())
        section_cats = st.session_state.data[section].keys()
        spent = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] in section_cats)
        pct_spent = (spent / total_earnings * 100) if total_earnings > 0 else 0

        summary_data.append({
            "Category": section.capitalize(), 
            "Type": "Spent %", 
            "Percentage": pct_spent, 
            "Amount": spent, 
            "Budget": budget
        })

    df_plot = pd.DataFrame(summary_data)

    if not df_plot.empty and total_earnings > 0:
        base = alt.Chart(df_plot).encode(
            x=alt.X('Category', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Percentage', axis=alt.Axis(title='% of Income')),
            color=alt.Color('Category', legend=None)
        )

        bars = base.mark_bar()

        text = base.mark_text(
            align='center',
            baseline='bottom',
            dy=-5
        ).encode(
            text=alt.Text('Percentage', format='.1f')
        )

        chart = (bars + text).properties(
            title="Spending as % of Income",
            height=200
        )

        st.altair_chart(chart, use_container_width=True)

# --- Mobile-optimized CSS ---
st.markdown("""
    <style>
    /* Reduce overall padding */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Summary cards */
    .summary-container {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        background-color: #1E1E1E;
        padding: 10px 6px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #333;
    }
    .summary-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        flex: 1;
    }
    .summary-label {
        font-size: 0.65rem;
        color: #aaa;
        margin-bottom: 2px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .summary-value {
        font-size: 0.95rem;
        font-weight: bold;
        color: #fff;
    }
    .summary-value.positive { color: #4CAF50; }
    .summary-value.negative { color: #FF5252; }
    
    /* Compact category cards */
    .cat-card {
        background-color: #1a1a1a;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 8px;
        border: 1px solid #2a2a2a;
    }
    
    .cat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    
    .cat-name {
        font-size: 1rem;
        font-weight: 600;
        flex: 1;
    }
    
    .cat-summary {
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 8px;
    }
    
    /* Make inputs mobile-friendly */
    .stNumberInput > div > div > input {
        font-size: 16px !important;
        padding: 6px 8px !important;
    }
    
    /* Compact buttons */
    .stButton > button {
        padding: 4px 8px;
        font-size: 0.9rem;
        min-height: 32px;
        height: 32px;
    }
    
    /* Remove extra spacing from button containers */
    .stButton {
        margin: 0;
    }
    
    div[data-testid="column"] {
        padding: 0 !important;
    }
    
    /* Reduce spacing between elements */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Compact expanders */
    .streamlit-expanderHeader {
        font-size: 0.9rem;
        padding: 8px 12px;
    }
    
    /* Compact dividers */
    hr {
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- UI ---
current_month_name = datetime.datetime.now().strftime("%B %Y")
st.title(f"💰 {current_month_name}")

# --- Top Section: Total Summary ---
total_earnings, total_spent, remaining = calculate_totals()
total_budget_all = sum(sum(st.session_state.data[k].values()) for k in ["needs", "wants", "savings", "debts"])

remaining_color = "positive" if remaining >= 0 else "negative"

st.markdown(f"""
    <div class="summary-container">
        <div class="summary-item">
            <span class="summary-label">Remaining</span>
            <span class="summary-value {remaining_color}">₹{int(remaining):,}</span>
        </div>
        <div class="summary-item" style="border-left: 1px solid #333; border-right: 1px solid #333;">
            <span class="summary-label">Spent</span>
            <span class="summary-value">₹{int(total_spent):,}</span>
        </div>
        <div class="summary-item">
            <span class="summary-label">Budget</span>
            <span class="summary-value">₹{int(total_budget_all):,}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Weekly Spends - Collapsible
with st.expander("📅 Weekly Breakdown", expanded=False):
    now = datetime.datetime.now()
    weeks = get_weeks_in_month(now.year, now.month)

    current_week_idx = -1
    for i, (start, end) in enumerate(weeks):
        if start <= now.date() <= end:
            current_week_idx = i
            break

    if current_week_idx == -1:
        weeks_remaining = 0 if now.day > 15 else len(weeks)
    else:
        weeks_remaining = len(weeks) - current_week_idx

    dynamic_weekly_budget = remaining / weeks_remaining if weeks_remaining > 0 else 0

    wants_categories = list(st.session_state.data["wants"].keys())

    weekly_data = []
    for i, (start, end) in enumerate(weeks):
        week_num = i + 1
        week_expenses = [
            x for x in st.session_state.data["expenses"] 
            if start <= datetime.datetime.strptime(x["Date"], "%Y-%m-%d").date() <= end
            and x["Category"] in wants_categories
        ]
        week_spent = sum(x["Amount"] for x in week_expenses)

        is_past = end < now.date()
        is_current = start <= now.date() <= end

        status_icon = "🔒" if is_past else ("👉" if is_current else "📅")
        display_budget = "-" if is_past else f"₹{int(dynamic_weekly_budget):,}"

        weekly_data.append({
            "": status_icon,
            "Week": f"W{week_num}",
            "Dates": f"{start.strftime('%d')}-{end.strftime('%d')}",
            "Budget": display_budget,
            "Spent": f"₹{int(week_spent):,}"
        })

    st.dataframe(
        pd.DataFrame(weekly_data),
        use_container_width=True,
        hide_index=True,
        height=200
    )

# Chart - Collapsible
with st.expander("📊 Spending Chart", expanded=False):
    render_summary_plot()

st.divider()

# Monthly Income
with st.expander("💵 Monthly Income", expanded=False):
    new_earnings = st.number_input(
        "Income Amount", 
        value=int(st.session_state.data["earnings"]), 
        step=100,
        min_value=0,
        format="%d"
    )
    if new_earnings != st.session_state.data["earnings"]:
        st.session_state.data["earnings"] = new_earnings
        save_data(st.session_state.data)
        st.rerun()

# --- Reusable Section Renderer ---
def render_section(title, section_key, icon):
    section_total = sum(st.session_state.data[section_key].values())
    earnings = st.session_state.data["earnings"]

    if section_key == "debts":
        display_title = f"{icon} {title}"
        col2_header = "Debt"
        col3_header = "Paid"
    else:
        percentage = (section_total / earnings * 100) if earnings > 0 else 0
        display_title = f"{icon} {title} ({percentage:.0f}%)"
        col2_header = "Budget"
        col3_header = "Spent"

    st.subheader(display_title)

    categories = list(st.session_state.data[section_key].keys())

    if not categories:
        st.caption(f"No {title.lower()} yet. Add one below ⬇️")

    for cat in categories:
        budget = st.session_state.data[section_key][cat]
        spent_so_far = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] == cat)

        # Minimized state tracking
        minimize_key = f"minimize_{section_key}_{cat}"
        if minimize_key not in st.session_state:
            st.session_state[minimize_key] = True  # Default to minimized

        # Compact card with toggle - cleaner layout
        col1, col2, col3 = st.columns([0.4, 5.8, 0.4])
        
        with col1:
            icon = "▶" if st.session_state[minimize_key] else "▼"
            st.button(icon, key=f"toggle_{section_key}_{cat}", help="Expand", use_container_width=True)
            if st.session_state.get(f"toggle_{section_key}_{cat}"):
                st.session_state[minimize_key] = not st.session_state[minimize_key]
                st.rerun()
        
        with col2:
            progress_pct = (spent_so_far / budget * 100) if budget > 0 else 0
            # Add some spacing to align with buttons
            st.markdown(f"<div style='padding-top: 4px;'><b>{cat}</b> · ₹{int(spent_so_far):,} / ₹{int(budget):,} ({progress_pct:.0f}%)</div>", unsafe_allow_html=True)
        
        with col3:
            st.button("🗑️", key=f"del_{section_key}_{cat}", help="Delete", use_container_width=True)
            if st.session_state.get(f"del_{section_key}_{cat}"):
                delete_category(section_key, cat)
                st.rerun()

        # Expanded view - much cleaner layout
        if not st.session_state[minimize_key]:
            st.markdown("---")
            
            # Budget row
            col_label1, col_input1 = st.columns([2, 4])
            with col_label1:
                st.markdown(f"**{col2_header}:**")
            with col_input1:
                new_budget = st.number_input(
                    col2_header, 
                    value=int(budget), 
                    min_value=0, 
                    step=50, 
                    key=f"bud_{section_key}_{cat}", 
                    format="%d",
                    label_visibility="collapsed"
                )
                if new_budget != budget:
                    st.session_state.data[section_key][cat] = new_budget
                    save_data(st.session_state.data)
                    st.rerun()

            # Spent row with max button
            col_label2, col_input2, col_max = st.columns([2, 3, 1])
            
            with col_label2:
                st.markdown(f"**{col3_header}:**")
            
            spent_key = f"spent_{section_key}_{cat}"

            if spent_key not in st.session_state:
                st.session_state[spent_key] = int(spent_so_far)

            input_max = None
            if section_key == "debts":
                input_max = int(budget)
                if st.session_state[spent_key] > input_max:
                    st.session_state[spent_key] = input_max

            input_kwargs = {
                "label": col3_header,
                "step": 10,
                "min_value": 0,
                "max_value": input_max,
                "key": spent_key,
                "format": "%d",
                "on_change": update_spent_callback,
                "args": (cat, spent_key),
                "label_visibility": "collapsed"
            }

            if spent_key not in st.session_state:
                input_kwargs["value"] = int(spent_so_far)

            with col_input2:
                st.number_input(**input_kwargs)

            with col_max:
                st.button(
                    "Max", 
                    key=f"max_{section_key}_{cat}",
                    help="Set to maximum budget",
                    on_click=set_max_spent, 
                    args=(cat, int(budget), spent_key),
                    use_container_width=True
                )

    # Add Category
    with st.expander(f"➕ Add {title}", expanded=False):
        with st.form(f"add_{section_key}", clear_on_submit=True):
            new_name = st.text_input("Category Name")
            new_bud = st.number_input(col2_header, min_value=0, step=50, value=0)
            if st.form_submit_button("Add"):
                if add_category(section_key, new_name, new_bud):
                    st.rerun()
                else:
                    st.error("Category already exists or invalid name")

# Render Sections
render_section("Needs", "needs", "🏠")
st.divider()
render_section("Wants", "wants", "🎯")
st.divider()
render_section("Savings", "savings", "💎")
st.divider()
render_section("Debts", "debts", "💳")