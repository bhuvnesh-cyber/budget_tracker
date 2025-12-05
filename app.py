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
                # Reset expenses for new month
                data["expenses"] = []
                # Reset spent amounts in session state keys if they exist (will be handled by rerun)
                data["last_month"] = current_month
                # We could also archive old data here if needed, but user asked to just reset
                
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
    
    # Separate expenses into Debt and Non-Debt
    debt_cats = list(st.session_state.data["debts"].keys())
    expenses = st.session_state.data["expenses"]
    
    # Filter expenses to only include active categories
    valid_expenses = [x for x in expenses if x["Category"] in active_cats]
    
    spent_non_debt = sum(x["Amount"] for x in valid_expenses if x["Category"] not in debt_cats)
    
    # Calculate Debt Deduction (Liability) per category
    # Liability = max(Budget, Spent) for EACH debt category
    # This ensures we reserve the budget for unpaid debts, but account for overspending on paid debts.
    debt_deduction = 0
    debt_spent_total = 0
    
    for debt_cat, budget in st.session_state.data["debts"].items():
        # Calculate spent for this specific debt category
        cat_spent = sum(x["Amount"] for x in valid_expenses if x["Category"] == debt_cat)
        debt_spent_total += cat_spent
        debt_deduction += max(cat_spent, budget)
        
    remaining = total_earnings - spent_non_debt - debt_deduction
    
    # Total Spent should reflect ALL spending (including debt payments)
    total_spent = spent_non_debt + debt_spent_total
    
    return total_earnings, total_spent, remaining

def update_spent_callback(cat, key):
    new_total = st.session_state.get(key)
    if new_total is None:
        return # Should not happen with min_value=0
        
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
        # Update the input key to reflect the new total (which is the budget)
        st.session_state[input_key] = int(budget)

def add_category(section, name, budget):
    if name:
        st.session_state.data[section][name] = budget
        save_data(st.session_state.data)

def delete_category(section, name):
    if name in st.session_state.data[section]:
        del st.session_state.data[section][name]
        # Remove expenses for this category to keep totals accurate
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
        # week is a list of 7 days, 0 means day belongs to other month
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
    
    # Exclude 'debts' from plot as requested
    for section in ["needs", "wants", "savings"]:
        # Budget/Total
        budget = sum(st.session_state.data[section].values())
        
        # Spent/Paid
        # Get categories in this section
        section_cats = st.session_state.data[section].keys()
        spent = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] in section_cats)
        
        # Calculate Percentage of Total Earnings
        # "percentage calculation in plots should be out of total income"
        pct_spent = (spent / total_earnings * 100) if total_earnings > 0 else 0
        
        summary_data.append({"Category": section.capitalize(), "Type": "Spent %", "Percentage": pct_spent, "Amount": spent, "Budget": budget})
    
    df_plot = pd.DataFrame(summary_data)
    
    if not df_plot.empty:
        # Create Bar Chart
        base = alt.Chart(df_plot).encode(
            x=alt.X('Category', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('Percentage', axis=alt.Axis(title='% of Income')),
            color=alt.Color('Category', legend=None),
            tooltip=['Category', 'Percentage', 'Amount', 'Budget']
        )

        chart = base.mark_bar().properties(
            title="Spending as % of Income",
            height=200
        )
        
        st.altair_chart(chart, use_container_width=True)

# --- UI ---
current_month_name = datetime.datetime.now().strftime("%B %Y")
st.title(f"💰 Budget Tracker - {current_month_name}")

# --- Top Section: Total Summary & Weekly Spends ---
total_earnings, total_spent, remaining = calculate_totals()
total_budget_all = sum(sum(st.session_state.data[k].values()) for k in ["needs", "wants", "savings", "debts"])

st.subheader("Total Summary")
m1, m2, m3 = st.columns(3)
m1.metric("Remaining Funds", f"₹{int(remaining):,}")
m2.metric("Total Spent", f"₹{int(total_spent):,}")
m3.metric("Total Budgeted", f"₹{int(total_budget_all):,}")

st.divider()

# Weekly Spends
st.header("Weekly Spends")
now = datetime.datetime.now()
weeks = get_weeks_in_month(now.year, now.month)

# Calculate Totals for Dynamic Budgeting (Using values from calculate_totals where possible, but need raw spent for remaining calculation logic if different)
# Actually remaining from calculate_totals includes debt subtraction. 
# The previous weekly budget logic used: remaining_funds = total_earnings - total_spent_all (without debt?)
# Let's check previous code: remaining_funds = total_earnings - total_spent_all. 
# And calculate_totals: remaining = total_earnings - total_spent - total_debt.
# If user wants weekly budget to be based on "Remaining Funds" (which usually implies disposable income), 
# we should probably use the 'remaining' from calculate_totals which accounts for debt.
# User said: "weekly spends budget should be calculayted based on Remaining Funds"
# So I will use the 'remaining' variable from calculate_totals.

# Calculate weeks remaining (including current week)
current_week_idx = -1
for i, (start, end) in enumerate(weeks):
    if start <= now.date() <= end:
        current_week_idx = i
        break

# If month is over or not started, handle gracefully
if current_week_idx == -1:
    if now.day > 15: # End of month
        weeks_remaining = 0
    else: # Start of month
        weeks_remaining = len(weeks)
else:
    weeks_remaining = len(weeks) - current_week_idx

# Dynamic Weekly Budget
dynamic_weekly_budget = remaining / weeks_remaining if weeks_remaining > 0 else 0

# Get Wants categories for filtering
wants_categories = list(st.session_state.data["wants"].keys())

# Display Weeks
# Display Weeks
weekly_data = []
for i, (start, end) in enumerate(weeks):
    week_num = i + 1
    
    # Filter expenses for this week AND belongs to Wants
    week_expenses = [
        x for x in st.session_state.data["expenses"] 
        if start <= datetime.datetime.strptime(x["Date"], "%Y-%m-%d").date() <= end
        and x["Category"] in wants_categories
    ]
    week_spent = sum(x["Amount"] for x in week_expenses)
    
    # Status
    is_past = end < now.date()
    is_current = start <= now.date() <= end
    
    status_icon = "🔒" if is_past else ("👉" if is_current else "📅")
    
    # Determine budget to show
    if is_past:
        display_budget = "-" 
    else:
        display_budget = f"₹{int(dynamic_weekly_budget):,}"
        
    weekly_data.append({
        "Status": status_icon,
        "Week": f"Week {week_num}",
        "Dates": f"{start.strftime('%d %b')} - {end.strftime('%d %b')}",
        "Budget": display_budget,
        "Spent": f"₹{int(week_spent):,}"
    })

st.dataframe(
    pd.DataFrame(weekly_data),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Status": st.column_config.TextColumn("Status", width="small"),
        "Week": st.column_config.TextColumn("Week", width="small"),
        "Dates": st.column_config.TextColumn("Dates", width="medium"),
        "Budget": st.column_config.TextColumn("Budget", width="small"),
        "Spent": st.column_config.TextColumn("Spent", width="small"),
    }
)

st.divider()

# Summary Plot
render_summary_plot()

st.divider()

# 1. Earnings
st.subheader("Monthly Income")
new_earnings = st.number_input(
    "Earnings", 
    value=int(st.session_state.data["earnings"]), 
    step=100,
    min_value=0,
    format="%d",
    label_visibility="collapsed"
)
if new_earnings != st.session_state.data["earnings"]:
    st.session_state.data["earnings"] = new_earnings
    save_data(st.session_state.data)
    st.rerun()

st.divider()

# --- Reusable Section Renderer ---
def render_section(title, section_key):
    # Calculate Total for Section
    section_total = sum(st.session_state.data[section_key].values())
    earnings = st.session_state.data["earnings"]
    
    # Determine Title with Percentage (if not Debt)
    if section_key == "debts":
        display_title = title
        col2_header = "Total Debt"
        col3_header = "Paid"
    else:
        percentage = (section_total / earnings * 100) if earnings > 0 else 0
        display_title = f"{title} ({percentage:.1f}%)"
        col2_header = "Budget"
        col3_header = "Spent"

    st.header(display_title)
    
    # Headers
    h1, h2, h3 = st.columns([2, 1.5, 2])
    h1.markdown("**Category**")
    h2.markdown(f"**{col2_header}**")
    h3.markdown(f"**{col3_header}**")
    
    categories = list(st.session_state.data[section_key].keys())
    
    if not categories:
        st.info(f"No categories in {title}. Add one below.")

    for cat in categories:
        budget = st.session_state.data[section_key][cat]
        spent_so_far = sum(x["Amount"] for x in st.session_state.data["expenses"] if x["Category"] == cat)
        
        c1, c_del, c2, c3 = st.columns([2, 0.5, 1.5, 2])
        
        # Col 1: Name
        c1.write(f"**{cat}**")
        
        # Col Del: Delete Button
        if c_del.button("🗑️", key=f"del_{section_key}_{cat}", help="Delete Category"):
            delete_category(section_key, cat)
            st.rerun()
        
        # Col 2: Budget / Total Debt
        new_budget = c2.number_input(
            col2_header, value=int(budget), min_value=0, step=50, key=f"bud_{section_key}_{cat}", label_visibility="collapsed", format="%d"
        )
        if new_budget != budget:
            st.session_state.data[section_key][cat] = new_budget
            save_data(st.session_state.data)
            st.rerun()
            
        # Col 3: Spent / Paid + Max
        sc1, sc2 = c3.columns([3, 1])
        spent_key = f"spent_{section_key}_{cat}"
        
        # Ensure key exists in session state for correct updates
        if spent_key not in st.session_state:
            st.session_state[spent_key] = int(spent_so_far)
            
        # Determine max_value for input (only for debts)
        input_max = None
        if section_key == "debts":
            input_max = int(budget)
            # Ensure current value doesn't exceed max (visual clamp)
            if st.session_state[spent_key] > input_max:
                st.session_state[spent_key] = input_max
        
        # Use key only, no value argument to avoid conflicts
        # Construct kwargs to avoid passing 'value' if key exists
        input_kwargs = {
            "label": col3_header,
            "step": 10,
            "min_value": 0,
            "max_value": input_max,
            "key": spent_key,
            "label_visibility": "collapsed",
            "format": "%d",
            "on_change": update_spent_callback,
            "args": (cat, spent_key)
        }
        
        if spent_key not in st.session_state:
            # Only set value if key doesn't exist (though we set it above, so this might be redundant but safe)
            input_kwargs["value"] = int(spent_so_far)
            
        sc1.number_input(**input_kwargs)
        sc2.button(
            "📍", 
            key=f"max_{section_key}_{cat}", 
            help=f"Set {col3_header} to {col2_header}", 
            on_click=set_max_spent, 
            args=(cat, int(new_budget), spent_key)
        )

    # Add Category to Section
    with st.expander(f"➕ Add to {title}"):
        with st.form(f"add_{section_key}"):
            ac1, ac2 = st.columns([2, 1])
            new_name = ac1.text_input("Name")
            new_bud = ac2.number_input(col2_header, min_value=0, step=50)
            if st.form_submit_button("Add"):
                add_category(section_key, new_name, new_bud)
                st.rerun()



# 2. Sections
render_section("Needs", "needs")
st.divider()
render_section("Wants", "wants")
st.divider()
render_section("Savings", "savings")
st.divider()
render_section("Debts", "debts")
st.divider()


