# app.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
import calendar
import altair as alt

# -------------------------
# Configuration & Constants
# -------------------------
DATA_FILE = "budget_data.json"
APP_TITLE = "💰 Compact Budget"
st.set_page_config(page_title="Compact Budget", page_icon="💰", layout="centered")

# -------------------------
# Utility: Data persistence
# -------------------------
def default_data():
    return {
        "earnings": 0.0,
        "needs": {},
        "wants": {},
        "savings": {},
        "debts": {},
        "expenses": [],
        "last_month": datetime.datetime.now().month
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        return default_data()
    try:
        with open(DATA_FILE, "r") as f:
            d = json.load(f)
    except Exception:
        return default_data()

    # Migrate old key names if necessary
    if "budgets" in d and "needs" not in d:
        d["needs"] = d.get("budgets", {})
        d.pop("budgets", None)

    # Ensure keys exist
    base = default_data()
    for k, v in base.items():
        if k not in d:
            d[k] = v

    # Reset monthly expenses if month changed
    current_month = datetime.datetime.now().month
    if d.get("last_month") != current_month:
        # Optionally archive previous month (left simple)
        d["expenses"] = []
        d["last_month"] = current_month
        save_data(d)
    return d

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=4)

# -------------------------
# Load / Session State Init
# -------------------------
if "data" not in st.session_state:
    st.session_state.data = load_data()

# Keep derived values cached per run (not saved) to avoid too many disk writes
def add_expense(category: str, amount: int, note=""):
    if amount == 0:
        return
    expense = {
        "Category": category,
        "Amount": int(amount),
        "Date": str(datetime.date.today()),
        "Note": note or "Manual"
    }
    st.session_state.data["expenses"].append(expense)
    save_data(st.session_state.data)

def delete_category(section: str, name: str):
    if name in st.session_state.data[section]:
        st.session_state.data[section].pop(name)
        # remove related expenses
        st.session_state.data["expenses"] = [
            e for e in st.session_state.data["expenses"] if e["Category"] != name
        ]
        save_data(st.session_state.data)

def add_category(section: str, name: str, budget: int):
    if not name:
        return
    st.session_state.data[section][name] = int(budget)
    save_data(st.session_state.data)

def set_category_budget(section: str, name: str, new_budget: int):
    st.session_state.data[section][name] = int(new_budget)
    save_data(st.session_state.data)

def set_spent_to_budget(category: str, budget: int, note="set_max"):
    # compute current spent and add expense equal to diff
    current_spent = sum(e["Amount"] for e in st.session_state.data["expenses"] if e["Category"] == category)
    diff = int(budget) - current_spent
    if diff != 0:
        add_expense(category, diff, note=note)

# -------------------------
# Calculations
# -------------------------
def get_active_categories():
    cats = set()
    for s in ["needs", "wants", "savings", "debts"]:
        cats.update(st.session_state.data[s].keys())
    return cats

def calculate_totals():
    data = st.session_state.data
    earnings = float(data.get("earnings", 0.0))

    # Only include expenses whose category currently exists
    active = get_active_categories()
    valid_expenses = [e for e in data["expenses"] if e["Category"] in active]

    debt_cats = list(data.get("debts", {}).keys())
    spent_non_debt = sum(e["Amount"] for e in valid_expenses if e["Category"] not in debt_cats)
    debt_spent_total = sum(e["Amount"] for e in valid_expenses if e["Category"] in debt_cats)

    # Debt deduction: reserve MAX(spent, budget) per debt category
    debt_deduction = 0
    for dcat, dbudget in data.get("debts", {}).items():
        cat_spent = sum(e["Amount"] for e in valid_expenses if e["Category"] == dcat)
        debt_deduction += max(cat_spent, dbudget)

    remaining = earnings - spent_non_debt - debt_deduction
    total_spent = spent_non_debt + debt_spent_total
    total_budgeted = sum(sum(st.session_state.data[k].values()) for k in ["needs", "wants", "savings", "debts"])
    return {
        "earnings": earnings,
        "total_spent": total_spent,
        "remaining": remaining,
        "total_budgeted": total_budgeted
    }

# -------------------------
# Date helpers (weeks)
# -------------------------
def get_weeks_in_month(year, month):
    cal = calendar.monthcalendar(year, month)
    weeks = []
    for week in cal:
        days = [d for d in week if d != 0]
        if not days:
            continue
        start = datetime.date(year, month, days[0])
        end = datetime.date(year, month, days[-1])
        weeks.append((start, end))
    return weeks

# -------------------------
# Compact CSS (mobile first)
# -------------------------
COMPACT_CSS = """
<style>
/* container card */
.card {
  background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));
  border: 1px solid #2b2b2b;
  padding: 10px;
  border-radius: 10px;
  margin-bottom: 12px;
}
/* tiny caption style */
.small {
  font-size: 0.82rem;
  color: #9aa0a6;
}
/* compact label above inputs */
.inline-row { display:flex; gap:8px; align-items:center; }
.input-compact { width:100%; }
@media (min-width:600px) {
  .input-compact { max-width: 260px; }
}
</style>
"""
st.markdown(COMPACT_CSS, unsafe_allow_html=True)

# -------------------------
# UI: Header + Summary
# -------------------------
now = datetime.datetime.now()
st.title(f"{APP_TITLE} — {now.strftime('%B %Y')}")
t = calculate_totals()

col1, col2, col3 = st.columns([1,1,1], gap="small")
with col1:
    rem_color = "🟩" if t["remaining"] >= 0 else "🟥"
    st.markdown(f"**Remaining**\n\n{rem_color} ₹{int(t['remaining']):,}")
with col2:
    st.markdown(f"**Spent**\n\n📉 ₹{int(t['total_spent']):,}")
with col3:
    st.markdown(f"**Budgeted**\n\n💡 ₹{int(t['total_budgeted']):,}")

st.divider()

# -------------------------
# Tabs: Summary | Weekly | Categories
# -------------------------
tab_summary, tab_weeks, tab_categories = st.tabs(["Summary", "Weekly", "Categories"])

# -------------------------
# SUMMARY TAB
# -------------------------
with tab_summary:
    st.header("Snapshot")

    # Income input (compact)
    st.caption("Monthly Income")
    col_s1, col_s2 = st.columns([2,1])
    with col_s1:
        new_earn = st.number_input("Earnings", value=int(st.session_state.data.get("earnings", 0)), step=100, min_value=0, format="%d", key="earn_input")
        if new_earn != st.session_state.data.get("earnings", 0):
            st.session_state.data["earnings"] = int(new_earn)
            save_data(st.session_state.data)

    # Summary bar chart: spending by needs/wants/savings (percentage of income)
    def render_spend_chart():
        total_income = st.session_state.data.get("earnings", 0) or 0
        summary = []
        for sec in ["needs", "wants", "savings"]:
            budget = sum(st.session_state.data[sec].values())
            cats = set(st.session_state.data[sec].keys())
            spent = sum(e["Amount"] for e in st.session_state.data["expenses"] if e["Category"] in cats)
            percent = (spent / total_income * 100) if total_income > 0 else 0
            summary.append({"section": sec.capitalize(), "spent": spent, "budget": budget, "pct": percent})
        df = pd.DataFrame(summary)
        if df.empty:
            st.info("Add categories to see the summary chart.")
            return
        base = alt.Chart(df).encode(
            x=alt.X("section:N", title=""),
            y=alt.Y("pct:Q", title="% of Income"),
            tooltip=["section", "spent", "budget", alt.Tooltip("pct", format=".1f")]
        )
        bars = base.mark_bar().encode(color=alt.Color('section:N', legend=None))
        text = base.mark_text(dy=-8).encode(text=alt.Text('pct', format=".1f"))
        chart = (bars + text).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

    render_spend_chart()

    st.markdown("---")
    # Recent expenses (compact)
    st.subheader("Recent Transactions")
    recent = st.session_state.data["expenses"][-8:][::-1]
    if not recent:
        st.info("No transactions yet. Use Categories tab to add spent values quickly.")
    else:
        for r in recent:
            date = r.get("Date", "")
            cat = r.get("Category", "")
            amt = r.get("Amount", 0)
            note = r.get("Note", "")
            st.markdown(f"- **{cat}** • ₹{int(amt):,} • {date}  —  _{note}_")

# -------------------------
# WEEKLY TAB
# -------------------------
with tab_weeks:
    st.header("Weekly Plan (Wants-focused disposable)")
    # Dynamic weekly budget calculation using 'remaining' (after debt deduction)
    calc = calculate_totals()
    remaining = calc["remaining"]
    # weeks in month and which week index we are in
    weeks = get_weeks_in_month(now.year, now.month)
    current_week_idx = 0
    for i, (s, e) in enumerate(weeks):
        if s <= now.date() <= e:
            current_week_idx = i
            break
    weeks_remaining = max(1, len(weeks) - current_week_idx)
    weekly_budget = int(remaining / weeks_remaining) if weeks_remaining > 0 else 0

    st.caption(f"Disposable weekly budget (based on Remaining): ₹{weekly_budget:,} per week (for Wants)")
    wants_cats = set(st.session_state.data["wants"].keys())

    # render each week as a compact card with progress bar
    for i, (start, end) in enumerate(weeks):
        week_spent = sum(e["Amount"] for e in st.session_state.data["expenses"] 
                         if start <= datetime.datetime.strptime(e["Date"], "%Y-%m-%d").date() <= end
                         and e["Category"] in wants_cats)
        is_current = start <= now.date() <= end
        is_past = end < now.date()
        label = f"Week {i+1}: {start.strftime('%d %b')} - {end.strftime('%d %b')}"
        with st.container():
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            c1, c2 = st.columns([6,1])
            with c1:
                st.markdown(f"**{label}** {'(current)' if is_current else ''}")
                st.caption(f"Spent ₹{week_spent:,}")
            with c2:
                if is_past:
                    st.markdown("🔒")
                elif is_current:
                    st.markdown("👉")
                else:
                    st.markdown("📅")
            # progress bar relative to weekly_budget (if weekly_budget <=0 show plain value)
            if weekly_budget > 0:
                pct = min(1.0, week_spent / weekly_budget)
                st.progress(pct)
                st.caption(f"{int(pct*100)}% of weekly budget")
            else:
                st.caption("No disposable budget (increase earnings or reduce debt)")
            st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# CATEGORIES TAB (main interactive area)
# -------------------------
with tab_categories:
    st.header("Categories & Transactions")

    def compact_section_ui(title: str, key: str):
        st.markdown(f"### {title}")
        section = st.session_state.data.get(key, {})
        if not section:
            st.info("No categories. Add below.")
        # Render each category as a compact card
        for cat, budget in section.items():
            spent = sum(e["Amount"] for e in st.session_state.data["expenses"] if e["Category"] == cat)
            with st.container():
                st.markdown("<div class='card'>", unsafe_allow_html=True)
                # Top row: name + delete
                t1, t2 = st.columns([6,1])
                with t1:
                    st.markdown(f"**{cat}**  ·  <span class='small'>Budget ₹{int(budget):,}</span>", unsafe_allow_html=True)
                with t2:
                    if st.button("🗑️", key=f"del_{key}_{cat}"):
                        delete_category(key, cat)
                        st.experimental_rerun()

                # Second row: budget and spent inline
                b1, b2, b3 = st.columns([3,2,1])
                with b1:
                    newbud = st.number_input("Budget", value=int(budget), min_value=0, step=50,
                                             key=f"bud_{key}_{cat}", label_visibility="collapsed")
                    if newbud != budget:
                        set_category_budget(key, cat, newbud)
                with b2:
                    # Spent input uses session_state key so user edits don't immediately create many tiny expenses.
                    spent_key = f"tmp_spent_{key}_{cat}"
                    if spent_key not in st.session_state:
                        st.session_state[spent_key] = int(spent)
                    new_spent_val = st.number_input("Spent", value=int(st.session_state[spent_key]), min_value=0, step=10,
                                                    key=spent_key, label_visibility="collapsed")
                    # provide an 'apply' small button next to it to commit to expenses
                with b3:
                    if st.button("📍", key=f"setmax_{key}_{cat}"):
                        set_spent_to_budget(cat, newbud if 'newbud' in locals() else budget, note="max_button")
                        st.experimental_rerun()

                # Action row: commit spent change small button
                a1, a2 = st.columns([5,1])
                with a1:
                    st.caption(f"Spent so far: ₹{int(spent):,}")
                with a2:
                    if st.button("➕", key=f"commit_{key}_{cat}"):
                        # commit the difference between current total and desired session value
                        desired = int(st.session_state.get(f"tmp_spent_{key}_{cat}", spent))
                        diff = desired - spent
                        if diff != 0:
                            add_expense(cat, diff, note="manual_commit")
                            st.experimental_rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # Add new category compact form
        with st.expander(f"➕ Add to {title}"):
            nm_col, bud_col = st.columns([2,1])
            with nm_col:
                new_name = st.text_input(f"Name ({title})", key=f"newname_{key}")
            with bud_col:
                new_bud = st.number_input("Budget", min_value=0, step=50, key=f"newbud_{key}")
            if st.button("Add", key=f"addbtn_{key}"):
                if new_name and new_name.strip():
                    add_category(key, new_name.strip(), new_bud)
                    # initialize tmp_spent
                    st.session_state[f"tmp_spent_{key}_{new_name.strip()}"] = 0
                    st.experimental_rerun()
                else:
                    st.warning("Provide a non-empty category name.")

    compact_section_ui("Needs", "needs")
    st.divider()
    compact_section_ui("Wants", "wants")
    st.divider()
    compact_section_ui("Savings", "savings")
    st.divider()
    compact_section_ui("Debts", "debts")

# -------------------------
# Footer: debug / export
# -------------------------
st.sidebar.header("Debug & Export")
if st.sidebar.button("Export JSON"):
    st.sidebar.download_button("Download data", data=json.dumps(st.session_state.data, indent=4), file_name="budget_export.json", mime="application/json")

st.sidebar.caption("Tip: use small + buttons to commit spent values. Use the pin (📍) to set spent to budget quickly.")