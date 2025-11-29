import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import json
import os

st.set_page_config(page_title="Budget Tracker", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp {
        background: #0d1117;
    }
    .block-container {
        padding: 2rem 1rem;
        max-width: 900px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #f0f6fc;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        color: #8b949e;
    }
    .stProgress > div > div {
        background: #58a6ff;
    }
    div[data-testid="stExpander"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        margin-bottom: 0.75rem;
    }
    h1, h2, h3 {
        color: #f0f6fc !important;
    }
    input, select {
        background: #0d1117 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
    }
    button {
        background: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
    }
    button:hover {
        background: #30363d !important;
    }
    .stat-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .stat-label {
        color: #8b949e;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stat-value {
        color: #f0f6fc;
        font-size: 1.25rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

MONTH = datetime.now().strftime("%B %Y")
DATA_FILE = "budget_data.json"

# ---- DATA SETUP WITH FILE STORAGE ----
def load_data():
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                st.session_state.income = data.get('income', 104000)
                st.session_state.budgets = data.get('budgets', get_default_budgets())
                st.session_state.loans = data.get('loans', {})
                st.session_state.lending = data.get('lending', {})
        except Exception as e:
            st.error(f"Error loading data: {e}")
            initialize_default_data()
    else:
        initialize_default_data()

def initialize_default_data():
    """Initialize with default data"""
    st.session_state.income = 104000
    st.session_state.budgets = get_default_budgets()
    st.session_state.loans = {}
    st.session_state.lending = {}

def get_default_budgets():
    """Return default budget structure"""
    return {
        "Investments": {
            "Mutual Funds": {"budget": 25000, "spent": 0},
            "RD": {"budget": 5000, "spent": 0}
        },
        "Housing": {
            "Room Rent": {"budget": 21000, "spent": 0},
            "Furniture Rent": {"budget": 4000, "spent": 0}
        },
        "Utilities": {
            "Electricity": {"budget": 800, "spent": 0},
            "Water": {"budget": 1000, "spent": 0},
            "Mobile WIFI": {"budget": 1500, "spent": 0},
            "Milk": {"budget": 2940, "spent": 0}
        },
        "EMI": {
            "EMI": {"budget": 3600, "spent": 0}
        },
        "Family": {
            "Family Help": {"budget": 20000, "spent": 0}
        },
        "Variable Expenses": {
            "Grocery": {"budget": 8000, "spent": 0},
            "Entertainment": {"budget": 9560, "spent": 0},
            "Travel": {"budget": 1600, "spent": 0}
        }
    }

def save_data():
    """Save data to JSON file"""
    try:
        data = {
            'income': st.session_state.income,
            'budgets': st.session_state.budgets,
            'loans': st.session_state.loans,
            'lending': st.session_state.lending
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save data: {e}")

# Load data on startup
if 'data_loaded' not in st.session_state:
    load_data()
    st.session_state.data_loaded = True

# ---- HELPERS ----
def total_spent():
    return sum(i["spent"] for g in st.session_state.budgets.values() for i in g.values())

def total_budget():
    return sum(i["budget"] for g in st.session_state.budgets.values() for i in g.values())

def loan_total():
    return sum(st.session_state.loans.values())

def lending_total():
    return sum(st.session_state.lending.values())

def export_to_excel():
    """Export budget data to Excel file"""
    output = BytesIO()
    SALARY = st.session_state.income
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Summary sheet
        summary_data = {
            'Metric': ['Salary', 'Total Spent', 'Loans Taken', 'Money Lent', 'Remaining'],
            'Amount': [SALARY, total_spent(), loan_total(), lending_total(), SALARY - total_spent() - loan_total()]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        # Budget details sheet
        budget_rows = []
        for group in st.session_state.budgets:
            for name, data in st.session_state.budgets[group].items():
                budget_rows.append({
                    'Category': group,
                    'Item': name,
                    'Budget': data['budget'],
                    'Spent': data['spent'],
                    'Remaining': data['budget'] - data['spent']
                })
        pd.DataFrame(budget_rows).to_excel(writer, sheet_name='Budget Details', index=False)
        
        # Loans sheet
        if st.session_state.loans:
            loans_df = pd.DataFrame([
                {'Source': k, 'Amount': v} for k, v in st.session_state.loans.items()
            ])
            loans_df.to_excel(writer, sheet_name='Loans', index=False)
        
        # Lending sheet
        if st.session_state.lending:
            lending_df = pd.DataFrame([
                {'Person': k, 'Amount': v} for k, v in st.session_state.lending.items()
            ])
            lending_df.to_excel(writer, sheet_name='Lending', index=False)
    
    output.seek(0)
    return output

# ---- HEADER ----
st.markdown(f"""
<div style='text-align: center; margin-bottom: 2rem;'>
    <h1 style='font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #58a6ff 0%, #1f6feb 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.25rem;'>Budget Tracker</h1>
    <p style='color: #8b949e; font-size: 0.875rem; margin: 0;'>{MONTH}</p>
</div>
""", unsafe_allow_html=True)

# Income editor and download button
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    new_income = st.number_input("💰 Monthly Income", min_value=0, value=st.session_state.income, step=1000, key="income_input")
    if new_income != st.session_state.income:
        st.session_state.income = new_income
        save_data()
        st.rerun()

with col3:
    excel_file = export_to_excel()
    st.download_button(
        label="📥 Download Excel",
        data=excel_file,
        file_name=f"budget_tracker_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

SALARY = st.session_state.income

st.divider()

# ---- QUICK STATS ----
st.markdown("<h3 style='font-size: 1rem; color: #8b949e; margin-bottom: 0.5rem;'>Quick Stats</h3>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
total_budgeted = total_budget()
budget_utilization = (total_spent() / total_budgeted * 100) if total_budgeted > 0 else 0
savings_rate = ((SALARY - total_spent() - loan_total()) / SALARY * 100) if SALARY > 0 else 0

with col1:
    st.markdown(f"""
    <div class='stat-card'>
        <div class='stat-label'>Budget Used</div>
        <div class='stat-value'>{budget_utilization:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='stat-card'>
        <div class='stat-label'>Savings Rate</div>
        <div class='stat-value' style='color: {'#3fb950' if savings_rate > 20 else '#f85149'};'>{savings_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    net_position = lending_total() - loan_total()
    st.markdown(f"""
    <div class='stat-card'>
        <div class='stat-label'>Net Loan Position</div>
        <div class='stat-value' style='color: {'#3fb950' if net_position >= 0 else '#f85149'};'>₹{abs(net_position):,}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ---- MAIN METRICS ----
spent = total_spent()
loans = loan_total()
lending = lending_total()
remaining = SALARY - spent - loans

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Salary", f"₹{SALARY:,}")
with col2:
    st.metric("Spent", f"₹{spent:,}")
with col3:
    st.metric("Loans", f"₹{loans:,}")
with col4:
    color = "normal" if remaining >= 0 else "inverse"
    st.metric("Remaining", f"₹{remaining:,}", delta_color=color)

# Enhanced progress bar
progress = min((spent + loans) / SALARY, 1.0) if SALARY > 0 else 0
allocated_amount = spent + loans

st.markdown(f"""
<div style='background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 1rem; margin: 1rem 0;'>
    <div style='display: flex; justify-content: space-between; margin-bottom: 0.5rem;'>
        <span style='color: #8b949e; font-size: 0.875rem;'>Salary Allocated</span>
        <span style='color: #f0f6fc; font-weight: 600;'>₹{allocated_amount:,} / ₹{SALARY:,}</span>
    </div>
    <div style='background: #0d1117; border-radius: 4px; height: 24px; overflow: hidden; border: 1px solid #30363d;'>
        <div style='background: linear-gradient(90deg, #1f6feb 0%, #58a6ff 100%); height: 100%; width: {progress*100}%; transition: width 0.3s ease; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px;'>
            <span style='color: white; font-size: 0.75rem; font-weight: 600;'>{progress*100:.1f}%</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---- WEEKLY SPENDING RECOMMENDATIONS ----
st.markdown("<h3 style='font-size: 1.125rem; color: #f0f6fc; margin-bottom: 1rem;'>💡 Weekly Spending Guide</h3>", unsafe_allow_html=True)

# Calculate remaining money after all fixed expenses
variable_categories = ["Grocery", "Entertainment", "Travel"]

# Get budgets and spent for variable expenses
variable_budgets = {}
variable_spent = {}
for group in st.session_state.budgets:
    for name, data in st.session_state.budgets[group].items():
        if name in variable_categories:
            variable_budgets[name] = data["budget"]
            variable_spent[name] = data["spent"]

# Calculate weekly allowances
col1, col2, col3 = st.columns(3)
weeks_remaining = 4  # Assuming 4 weeks in a month

for idx, (col, category) in enumerate(zip([col1, col2, col3], variable_categories)):
    if category in variable_budgets:
        budget = variable_budgets[category]
        spent = variable_spent[category]
        remaining = budget - spent
        weekly_allowance = remaining / weeks_remaining if weeks_remaining > 0 else 0
        
        with col:
            color = "#3fb950" if remaining > 0 else "#f85149"
            st.markdown(f"""
            <div class='stat-card'>
                <div class='stat-label'>{category}</div>
                <div style='color: #8b949e; font-size: 0.7rem; margin-top: 0.25rem;'>Budget: ₹{budget:,} | Spent: ₹{spent:,}</div>
                <div class='stat-value' style='color: {color}; font-size: 1rem; margin-top: 0.5rem;'>₹{int(weekly_allowance):,}/week</div>
                <div style='color: #8b949e; font-size: 0.65rem; margin-top: 0.25rem;'>Remaining: ₹{int(remaining):,}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ---- INSIGHTS ----
col1, col2 = st.columns(2)

with col1:
    # Category breakdown
    category_data = []
    for group in st.session_state.budgets:
        group_spent = sum(v["spent"] for v in st.session_state.budgets[group].values())
        group_budget = sum(v["budget"] for v in st.session_state.budgets[group].values())
        if group_budget > 0:
            category_data.append({
                "Category": group,
                "Spent": group_spent,
                "Budget": group_budget,
                "Remaining": group_budget - group_spent
            })
    
    if category_data:
        df = pd.DataFrame(category_data)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df["Category"],
            x=df["Spent"],
            name="Spent",
            orientation='h',
            marker=dict(color='#58a6ff'),
            text=[f"₹{x:,}" for x in df["Spent"]],
            textposition='inside',
            textfont=dict(color='white', size=11),
            hovertemplate='%{y}<br>Spent: ₹%{x:,}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            y=df["Category"],
            x=df["Remaining"],
            name="Remaining",
            orientation='h',
            marker=dict(color='#30363d'),
            text=[f"₹{x:,}" if x > 0 else "" for x in df["Remaining"]],
            textposition='inside',
            textfont=dict(color='#8b949e', size=11),
            hovertemplate='%{y}<br>Remaining: ₹%{x:,}<extra></extra>'
        ))
        
        fig.update_layout(
            barmode='stack',
            height=220,
            margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8b949e', size=11),
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
            title=dict(text="Budget by Category", font=dict(size=14, color='#f0f6fc'))
        )
        
        st.plotly_chart(fig, use_container_width=True)

with col2:
    # Spending composition
    spending_data = []
    for group in st.session_state.budgets:
        group_spent = sum(v["spent"] for v in st.session_state.budgets[group].values())
        if group_spent > 0:
            spending_data.append({"Type": group, "Amount": group_spent})
    
    if loans > 0:
        spending_data.append({"Type": "Loans", "Amount": loans})
    
    if spending_data:
        df_spend = pd.DataFrame(spending_data)
        
        fig2 = go.Figure(data=[go.Pie(
            labels=df_spend["Type"],
            values=df_spend["Amount"],
            hole=.6,
            marker=dict(colors=['#58a6ff', '#1f6feb', '#388bfd', '#1158c7', '#0d419d', '#032d5d']),
            textinfo='label+percent',
            textposition='outside'
        )])
        
        fig2.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8b949e', size=11),
            showlegend=False,
            title=dict(text="Spending Distribution", font=dict(size=14, color='#f0f6fc'))
        )
        
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---- CATEGORIES ----
for group in st.session_state.budgets:
    with st.expander(f"{group}", expanded=False):
        items = st.session_state.budgets[group]
        
        for name, data in items.items():
            is_paid = data["spent"] == data["budget"]
            
            col1, col2, col3, col4, col5 = st.columns([0.5, 2.5, 2, 2, 1])
            
            # Checkbox to mark as paid
            with col1:
                paid = st.checkbox("", value=is_paid, key=f"paid-{group}-{name}", label_visibility="collapsed")
                if paid and not is_paid:
                    data["spent"] = data["budget"]
                    save_data()
                    st.rerun()
                elif not paid and is_paid:
                    data["spent"] = 0
                    save_data()
                    st.rerun()
            
            with col2:
                st.markdown(f"<div style='padding-top: 8px; color: {'#58a6ff' if is_paid else '#f0f6fc'};'>{name}</div>", unsafe_allow_html=True)
            
            with col3:
                new_spent = st.number_input(
                    "Spent",
                    min_value=0,
                    value=data["spent"],
                    step=100,
                    key=f"spent-{group}-{name}",
                    label_visibility="collapsed"
                )
                if new_spent != data["spent"]:
                    data["spent"] = new_spent
                    save_data()
            
            with col4:
                new_budget = st.number_input(
                    "Budget",
                    min_value=0,
                    value=data["budget"],
                    step=100,
                    key=f"budget-{group}-{name}",
                    label_visibility="collapsed"
                )
                if new_budget != data["budget"]:
                    data["budget"] = new_budget
                    save_data()
            
            with col5:
                if st.button("×", key=f"del-{group}-{name}", use_container_width=True, help="Delete"):
                    del st.session_state.budgets[group][name]
                    save_data()
                    st.rerun()
        
        # Add new item within category
        with st.form(f"add_{group}", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                new_name = st.text_input("Item name", key=f"new_name_{group}")
            with col2:
                new_budget = st.number_input("Budget", min_value=0, step=100, key=f"new_budget_{group}")
            with col3:
                st.write("")
                st.write("")
                if st.form_submit_button("Add", use_container_width=True):
                    if new_name and new_name not in st.session_state.budgets[group]:
                        st.session_state.budgets[group][new_name] = {"budget": new_budget, "spent": 0}
                        save_data()
                        st.rerun()

st.divider()

# ---- LOANS & LENDING ----
col1, col2 = st.columns(2)

with col1:
    with st.expander("Loans Taken", expanded=False):
        if st.session_state.loans:
            for lname in list(st.session_state.loans):
                col_a, col_b, col_c = st.columns([4, 3, 0.8])
                col_a.write(lname)
                col_b.write(f"₹{st.session_state.loans[lname]:,}")
                if col_c.button("×", key=f"loan-{lname}", help="Delete"):
                    del st.session_state.loans[lname]
                    save_data()
                    st.rerun()
        
        col_a, col_b = st.columns([4, 3])
        with col_a:
            lname = st.text_input("Source", key="loan_source", label_visibility="collapsed", placeholder="Source")
        with col_b:
            lamt = st.number_input("Amount", key="loan_amt", min_value=0, step=100, label_visibility="collapsed")
        
        if st.button("Add Loan", key="add_loan", use_container_width=True):
            if lname:
                st.session_state.loans[lname] = lamt
                save_data()
                st.rerun()

with col2:
    with st.expander("Money Lent", expanded=False):
        if st.session_state.lending:
            for lname in list(st.session_state.lending):
                col_a, col_b, col_c = st.columns([4, 3, 0.8])
                col_a.write(lname)
                col_b.write(f"₹{st.session_state.lending[lname]:,}")
                if col_c.button("×", key=f"lend-{lname}", help="Delete"):
                    del st.session_state.lending[lname]
                    save_data()
                    st.rerun()
        
        col_a, col_b = st.columns([4, 3])
        with col_a:
            lname = st.text_input("Person", key="lend_person", label_visibility="collapsed", placeholder="Person")
        with col_b:
            lamt = st.number_input("Amount", key="lend_amt", min_value=0, step=100, label_visibility="collapsed")
        
        if st.button("Add Lending", key="add_lending", use_container_width=True):
            if lname:
                st.session_state.lending[lname] = lamt
                save_data()
                st.rerun()
