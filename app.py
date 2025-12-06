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
        del st.session_state.data[section]
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

# --- Single CSS block (cleaned) ---
st.markdown("""
    <style>
    /* Global container */
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 3.5rem;
        max-width: 600px;
        background: linear-gradient(180deg, #0f0a1e 0%, #1a0b2e 100%);
    }

    h1, h2, h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Summary card */
    .summary-card {
        background: linear-gradient(135deg, rgba(138, 43, 226, 0.15) 0%, rgba(123, 31, 162, 0.1) 100%);
        backdrop-filter: blur(10px);
        border-radius: 18px;
        padding: 18px 16px;
        box-shadow: 0 8px 32px 0 rgba(138, 43, 226, 0.2),
                    inset 0 1px 0 0 rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 18px;
    }

    .summary-grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 10px;
        text-align: center;
    }

    .summary-item {
        display: flex;
        flex-direction: column;
    }

    .summary-label {
        font-size: 0.65rem;
        color: #b794f6;
        text-transform: uppercase;
        letter-spacing: 1.3px;
        margin-bottom: 4px;
        font-weight: 600;
    }

    .summary-value {
        font-size: 1.05rem;
        font-weight: 900;
        color: #f3e7ff;
        text-shadow: 0 0 10px rgba(147, 51, 234, 0.3);
    }

    .positive { 
        color: #4ade80 !important;
        text-shadow: 0 0 15px rgba(74, 222, 128, 0.4);
    }
    .negative { 
        color: #fb7185 !important;
        text-shadow: 0 0 15px rgba(251, 113, 133, 0.4);
    }

    /* Section headers */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: #e9d5ff;
    }

    .section-badge {
        font-size: 0.72rem;
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        padding: 4px 10px;
        border-radius: 16px;
        color: #faf5ff;
        border: 1px solid rgba(168, 85, 247, 0.3);
        font-weight: 700;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        white-space: nowrap;
    }

    /* Expanders */
    .stExpander {
        background-color: transparent !important;
        border: none !important;
    }

    .stExpander > details {
        background: linear-gradient(135deg, rgba(88, 28, 135, 0.2) 0%, rgba(76, 29, 149, 0.15) 100%);
        backdrop-filter: blur(8px);
        border-radius: 14px;
        border: 1px solid rgba(168, 85, 247, 0.2);
        margin-bottom: 10px;
        overflow: hidden;
        transition: all 0.25s ease;
        box-shadow: 0 4px 16px rgba(124, 58, 237, 0.1);
    }

    .stExpander > details:hover {
        border-color: rgba(168, 85, 247, 0.5);
        box-shadow: 0 8px 20px rgba(124, 58, 237, 0.25);
        transform: translateY(-1px);
    }

    .stExpander > details > summary {
        padding: 10px 14px !important;
        background: linear-gradient(135deg, rgba(109, 40, 217, 0.15) 0%, rgba(124, 58, 237, 0.1) 100%) !important;
        border-bottom: 1px solid rgba(168, 85, 247, 0.2);
        font-weight: 600;
        font-size: 0.95rem;
        color: #e9d5ff;
    }

    .stExpander > details > div {
        padding: 14px !important;
        background: linear-gradient(135deg, rgba(76, 29, 149, 0.1) 0%, rgba(88, 28, 135, 0.05) 100%);
    }

    /* Inputs */
    .stNumberInput input {
        background-color: rgba(30, 10, 60, 0.6) !important;
        border: 2px solid rgba(168, 85, 247, 0.3) !important;
        border-radius: 8px !important;
        color: #f3e7ff !important;
        font-weight: 600;
        font-size: 16px !important;
        padding: 4px 8px !important;
    }

    .stNumberInput input:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 16px rgba(168, 85, 247, 0.4) !important;
    }

    .stButton button {
        border-radius: 9px !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        color: white;
        border: none;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);
        padding: 4px 10px !important;
        min-height: 32px !important;
        font-size: 0.9rem !important;
    }

    .stButton button:hover {
        background: linear-gradient(135deg, #8b5cf6 0%, #c084fc 100%);
        box-shadow: 0 6px 16px rgba(139, 92, 246, 0.5);
        transform: translateY(-1px);
    }

    .stButton { margin: 0 !important; }

    div[data-testid="column"] { padding: 0 !important; }

    .element-container { margin-bottom: 0.4rem; }

    /* Progress bar */
    .progress-bg {
        background: rgba(30, 10, 60, 0.6);
        height: 8px;
        border-radius: 10px;
        overflow: hidden;
        margin-top: 8px;
        border: 1px solid rgba(168, 85, 247, 0.2);
    }

    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #4ade80 0%, #22c55e 100%);
        border-radius: 10px;
        box-shadow: 0 0 12px rgba(74, 222, 128, 0.5);
    }

    .progress-fill.warning { 
        background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
        box-shadow: 0 0 12px rgba(251, 191, 36, 0.5);
    }
    .progress-fill.danger { 
        background: linear-gradient(90deg, #fb7185 0%, #f43f5e 100%);
        box-shadow: 0 0 12px rgba(251, 113, 133, 0.5);
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: #c4b5fd !important;
    }

    hr {
        margin: 0.8rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- UI ---
current_month_name = datetime.datetime.now().strftime("%B %Y")
st.markdown(
    f"<h2 style='text-align: center; margin-bottom: 12px;'>💰 {current_month_name}</h2>",
    unsafe_allow_html=True,
)

# --- Top Section: Total Summary & Weekly Spends ---
total_earnings, total_spent, remaining = calculate_totals()
total_budget_all = sum(
    sum(st.session_state.data[k].values()) for k in ["needs", "wants", "savings", "debts"]
)

remaining_color = "positive" if remaining >= 0 else "negative"

st.markdown(
    f"""
    <div class="summary-card">
        <div class="summary-grid">
            <div class="summary-item">
                <span class="summary-label">Remaining</span>
                <span class="summary-value {remaining_color}">₹{int(remaining):,}</span>
            </div>
            <div class="summary-item" style="border-left: 1px solid #32205a; border-right: 1px solid #32205a;">
                <span class="summary-label">Spent</span>
                <span class="summary-value">₹{int(total_spent):,}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Budget</span>
                <span class="summary-value">₹{int(total_budget_all):,}</span>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# Weekly Spends (kept collapsed by default)
with st.expander("📅 Weekly Overview", expanded=False):
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

    st.caption("👉 This view tracks only your Wants spending week by week.")

    if not wants_categories:
        st.caption("Add at least one Wants category to see weekly budgets.")
    else:
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
                "Status": status_icon,
                "Week": f"W{week_num}",
                "Dates": f"{start.strftime('%d')}-{end.strftime('%d')}",
                "Budget": display_budget,
                "Spent": f"₹{int(week_spent):,}"
            })

        st.dataframe(
            pd.DataFrame(weekly_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("", width="small"),
                "Week": st.column_config.TextColumn("Week", width="small"),
                "Dates": st.column_config.TextColumn("Dates", width="medium"),
                "Budget": st.column_config.TextColumn("Budget", width="small"),
                "Spent": st.column_config.TextColumn("Spent", width="small"),
            },
        )

# Chart (collapsed by default)
with st.expander("📊 Analytics", expanded=False):
    render_summary_plot()

# Monthly Income (collapsed by default)
with st.expander("💵 Monthly Income", expanded=False):
    new_earnings = st.number_input(
        "Income Amount",
        value=int(st.session_state.data["earnings"]),
        step=100,
        min_value=0,
        format="%d",
    )
    if new_earnings != st.session_state.data["earnings"]:
        st.session_state.data["earnings"] = new_earnings
        save_data(st.session_state.data)
        st.rerun()

st.markdown("---")

# --- Reusable Section Renderer ---
def render_section(title, section_key):
    section_total = sum(st.session_state.data[section_key].values())
    earnings = st.session_state.data["earnings"]

    if section_key == "debts":
        col2_header = "Total Debt"
        col3_header = "Paid"
        display_badge = f"₹{int(section_total):,}"
    else:
        percentage = (section_total / earnings * 100) if earnings > 0 else 0
        col2_header = "Budget"
        col3_header = "Spent"
        display_badge = f"₹{int(section_total):,} • {percentage:.1f}%"

    # Header
    st.markdown(
        f"""
        <div class="section-header">
            <span>{title}</span>
            <span class="section-badge">{display_badge}</span>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Add Category ABOVE list
    with st.expander(f"➕ Add {title}", expanded=(section_total == 0)):
        with st.form(f"add_{section_key}"):
            new_name = st.text_input("Category Name")
            new_bud = st.number_input(col2_header, min_value=0, step=50, value=0)
            if st.form_submit_button("Add Category", use_container_width=True):
                if add_category(section_key, new_name, new_bud):
                    st.rerun()
                else:
                    st.error("Category already exists or invalid name")

    categories = list(st.session_state.data[section_key].keys())

    if not categories:
        st.caption(f"No categories yet in {title}. Add one above to start tracking.")

    for cat in categories:
        budget = st.session_state.data[section_key][cat]
        spent_so_far = sum(
            x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] == cat
        )

        # Progress Bar Logic
        pct = (spent_so_far / budget * 100) if budget > 0 else 0
        progress_class = "progress-fill"
        if pct > 100:
            progress_class += " danger"
        elif pct > 85:
            progress_class += " warning"

        header_text = f"{cat} · ₹{int(spent_so_far):,} / ₹{int(budget):,}"

        with st.expander(header_text, expanded=False):
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px; color:#aaa;">
                    <span>₹{int(spent_so_far):,} / ₹{int(budget):,}</span>
                    <span>{int(pct)}%</span>
                </div>
                <div class="progress-bg">
                    <div class="{progress_class}" style="width: {min(pct, 100)}%;"></div>
                </div>
                <div style="margin-bottom: 10px;"></div>
            """,
                unsafe_allow_html=True,
            )

            col_bud, col_spent = st.columns(2)

            with col_bud:
                st.caption(col2_header.upper())
                new_budget = st.number_input(
                    col2_header,
                    value=int(budget),
                    min_value=0,
                    step=50,
                    key=f"bud_{section_key}_{cat}",
                    format="%d",
                    label_visibility="collapsed",
                )
                if new_budget != budget:
                    st.session_state.data[section_key][cat] = new_budget
                    save_data(st.session_state.data)
                    st.rerun()

            with col_spent:
                st.caption(col3_header.upper())

                col_input, col_max = st.columns([4, 1])

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
                    "label_visibility": "collapsed",
                }

                with col_input:
                    st.number_input(**input_kwargs)

                with col_max:
                    st.button(
                        "📍",
                        key=f"max_{section_key}_{cat}",
                        help="Max",
                        on_click=set_max_spent,
                        args=(cat, int(budget), spent_key),
                    )

            st.markdown("---")
            if st.button(
                "Delete Category",
                key=f"del_{section_key}_{cat}",
                type="primary",
                use_container_width=True,
            ):
                delete_category(section_key, cat)
                st.rerun()

# Render Sections
render_section("Needs", "needs")
render_section("Wants", "wants")
render_section("Savings", "savings")
render_section("Debts", "debts")