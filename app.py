import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
import json
import sqlite3
import os
import hashlib

st.set_page_config(page_title="Budget Tracker", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background: #0d1117; }
    .block-container { padding: 1rem; max-width: 600px; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; color: #f0f6fc; }
    div[data-testid="stMetricLabel"] { font-size: 0.75rem; color: #8b949e; }
    h1, h2, h3 { color: #f0f6fc !important; }
    input, select, textarea { 
        background: #0d1117 !important; 
        color: #f0f6fc !important; 
        border: 1px solid #30363d !important;
    }
    button {
        background: #21262d !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
    }
    button:hover { background: #30363d !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1f6feb 0%, #58a6ff 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1158c7 0%, #1f6feb 100%) !important;
    }
    .weekly-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    .weekly-title {
        color: #8b949e;
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .weekly-amount {
        color: #f0f6fc;
        font-size: 1.25rem;
        font-weight: 600;
    }
    .weekly-subtitle {
        color: #8b949e;
        font-size: 0.65rem;
        margin-top: 0.25rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #0d1117;
        padding: 4px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px;
        color: #8b949e;
        padding: 0.5rem 1.5rem;
    }
    .stTabs [aria-selected="true"] {
        background: #1f6feb !important;
        color: #ffffff !important;
    }
    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    /* Better number inputs on mobile */
    input[type="number"] {
        font-size: 16px !important;
        -webkit-appearance: none;
        -moz-appearance: textfield;
    }
    .stProgress > div > div {
        background: linear-gradient(90deg, #1f6feb 0%, #58a6ff 100%);
    }
</style>
""", unsafe_allow_html=True)

# ---- DATABASE SETUP ----
@st.cache_resource
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'budget_data.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            month_year TEXT NOT NULL,
            income INTEGER NOT NULL,
            categories TEXT NOT NULL,
            variable_categories TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, month_year)
        )
    ''')
    
    # Add variable_categories column if it doesn't exist (for existing databases)
    try:
        cursor.execute('SELECT variable_categories FROM monthly_budgets LIMIT 1')
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE monthly_budgets ADD COLUMN variable_categories TEXT')
    
    conn.commit()
    return conn

db_conn = init_db()

# ---- AUTH ----
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    try:
        cursor = db_conn.cursor()
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                      (username, hash_password(password)))
        db_conn.commit()
        return True
    except:
        return False

def authenticate_user(username, password):
    cursor = db_conn.cursor()
    cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    if result and hash_password(password) == result[1]:
        return result[0]
    return None

# ---- DATA FUNCTIONS ----
def get_current_month():
    return datetime.now().strftime("%Y-%m")

def load_monthly_data(user_id, month_year):
    try:
        cursor = db_conn.cursor()
        cursor.execute('SELECT income, categories, variable_categories FROM monthly_budgets WHERE user_id = ? AND month_year = ?', 
                      (user_id, month_year))
        result = cursor.fetchone()
        if result:
            return {
                'income': result[0], 
                'categories': json.loads(result[1]),
                'variable_categories': json.loads(result[2]) if result[2] else []
            }
    except Exception as e:
        st.error(f"Error loading data: {e}")
    return None

def save_monthly_data(user_id, month_year, income, categories, variable_categories):
    try:
        cursor = db_conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO monthly_budgets (user_id, month_year, income, categories, variable_categories)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, month_year, income, json.dumps(categories), json.dumps(variable_categories)))
        db_conn.commit()
    except Exception as e:
        st.error(f"Error saving data: {e}")

def get_available_months(user_id):
    cursor = db_conn.cursor()
    cursor.execute('SELECT month_year FROM monthly_budgets WHERE user_id = ? ORDER BY month_year DESC', 
                  (user_id,))
    return [row[0] for row in cursor.fetchall()]

# ---- SESSION STATE ----
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'selected_month' not in st.session_state:
    st.session_state.selected_month = get_current_month()
if 'variable_categories' not in st.session_state:
    st.session_state.variable_categories = []

# ---- LOGIN ----
if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; margin: 2rem 0 1rem 0;'>
        <h1 style='font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #58a6ff 0%, #1f6feb 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>Budget Tracker</h1>
        <p style='color: #8b949e; font-size: 0.9rem;'>Manage your finances with ease</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
        
        with tab1:
            st.markdown("""
            <div style='text-align: center; margin: 1rem 0;'>
                <h3 style='color: #f0f6fc; font-size: 1.25rem;'>Welcome Back</h3>
                <p style='color: #8b949e; font-size: 0.8rem;'>Sign in to continue</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                
                if st.form_submit_button("Login", use_container_width=True, type="primary"):
                    if username and password:
                        user_id = authenticate_user(username, password)
                        if user_id:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.error("❌ Invalid username or password")
                    else:
                        st.error("⚠️ Please fill all fields")
        
        with tab2:
            st.markdown("""
            <div style='text-align: center; margin: 1rem 0;'>
                <h3 style='color: #f0f6fc; font-size: 1.25rem;'>Create Account</h3>
                <p style='color: #8b949e; font-size: 0.8rem;'>Start tracking your budget today</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("signup_form"):
                new_username = st.text_input("👤 Username", placeholder="Choose a username")
                new_password = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters")
                confirm = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
                
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                
                if st.form_submit_button("Sign Up", use_container_width=True, type="primary"):
                    if new_username and new_password and confirm:
                        if new_password != confirm:
                            st.error("❌ Passwords don't match")
                        elif len(new_password) < 6:
                            st.error("⚠️ Password must be 6+ characters")
                        elif create_user(new_username, new_password):
                            st.success("✅ Account created! Please switch to Login tab.")
                        else:
                            st.error("❌ Username already exists")
                    else:
                        st.error("⚠️ Please fill all fields")
    
    st.stop()

# ---- LOAD DATA ----
def load_data():
    data = load_monthly_data(st.session_state.user_id, st.session_state.selected_month)
    if data:
        st.session_state.income = data['income']
        st.session_state.categories = data['categories']
        st.session_state.variable_categories = data.get('variable_categories', [])
    else:
        st.session_state.income = 0
        st.session_state.categories = {}
        st.session_state.variable_categories = []

def save_data():
    save_monthly_data(st.session_state.user_id, st.session_state.selected_month,
                     st.session_state.income, st.session_state.categories,
                     st.session_state.variable_categories)

if 'data_loaded' not in st.session_state or st.session_state.get('last_month') != st.session_state.selected_month:
    load_data()
    st.session_state.data_loaded = True
    st.session_state.last_month = st.session_state.selected_month

# ---- HEADER ----
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

with col2:
    months = get_available_months(st.session_state.user_id)
    current = get_current_month()
    if current not in months:
        months.insert(0, current)
    
    options = {datetime.strptime(m, "%Y-%m").strftime("%b %Y"): m for m in months}
    current_display = [k for k, v in options.items() if v == st.session_state.selected_month][0]
    
    selected = st.selectbox("📅 Month", list(options.keys()), 
                           index=list(options.keys()).index(current_display))
    
    if options[selected] != st.session_state.selected_month:
        st.session_state.selected_month = options[selected]
        st.rerun()

st.markdown("---")

# ---- INCOME ----
income = st.number_input("💰 Monthly Income", min_value=0, value=st.session_state.income, 
                        step=1000, key="income_input")
if income != st.session_state.income:
    st.session_state.income = income
    save_data()

# ---- METRICS ----
total_budget = sum(cat.get('budget', 0) for cat in st.session_state.categories.values())
total_spent = sum(cat.get('spent', 0) for cat in st.session_state.categories.values())
remaining = st.session_state.income - total_spent

col1, col2, col3 = st.columns(3)
col1.metric("Budget", f"₹{total_budget:,}")
col2.metric("Spent", f"₹{total_spent:,}")
col3.metric("Left", f"₹{remaining:,}")

if st.session_state.income > 0:
    progress = min(total_spent / st.session_state.income, 1.0)
    st.progress(progress)
    st.caption(f"{progress*100:.1f}% of income spent")

st.markdown("---")

# ---- CATEGORIES ----
st.markdown("### Categories")
for cat_name in list(st.session_state.categories.keys()):
    cat = st.session_state.categories[cat_name]
    
    col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 1.5, 0.8, 0.8])
    
    with col1:
        st.markdown(f"<div style='padding-top: 8px; color: #f0f6fc;'>{cat_name}</div>", 
                   unsafe_allow_html=True)
    
    with col2:
        spent = st.number_input("Spent", min_value=0, value=cat.get('spent', 0),
                               step=100, key=f"spent_{cat_name}", label_visibility="collapsed")
        if spent != cat.get('spent', 0):
            cat['spent'] = spent
            save_data()
    
    with col3:
        budget = st.number_input("Budget", min_value=0, value=cat.get('budget', 0),
                                step=100, key=f"budget_{cat_name}", label_visibility="collapsed")
        if budget != cat.get('budget', 0):
            cat['budget'] = budget
            save_data()
    
    with col4:
        is_variable = cat_name in st.session_state.variable_categories
        if st.checkbox("📊", value=is_variable, key=f"var_{cat_name}", help="Track weekly"):
            if not is_variable:
                st.session_state.variable_categories.append(cat_name)
                save_data()
        else:
            if is_variable:
                st.session_state.variable_categories.remove(cat_name)
                save_data()
    
    with col5:
        if st.button("×", key=f"del_{cat_name}", help="Delete"):
            del st.session_state.categories[cat_name]
            if cat_name in st.session_state.variable_categories:
                st.session_state.variable_categories.remove(cat_name)
            save_data()
            st.rerun()

# ---- ADD CATEGORY ----
with st.form("add_category", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        new_name = st.text_input("Name", placeholder="e.g. Groceries")
    with col2:
        new_budget = st.number_input("Budget", min_value=0, step=100)
    with col3:
        st.write("")
        st.write("")
        if st.form_submit_button("Add", use_container_width=True, type="primary"):
            if new_name and new_name not in st.session_state.categories:
                st.session_state.categories[new_name] = {'budget': new_budget, 'spent': 0}
                save_data()
                st.rerun()

# ---- WEEKLY SPENDING GUIDE ----
if st.session_state.variable_categories and st.session_state.selected_month == get_current_month():
    st.markdown("---")
    st.markdown("### 📅 Weekly Budget")
    
    # Calculate weeks remaining in month
    today = datetime.now()
    days_in_month = (datetime(today.year, today.month % 12 + 1, 1) - datetime(today.year, today.month, 1)).days
    days_remaining = days_in_month - today.day + 1
    weeks_remaining = max(days_remaining / 7, 1)
    
    cols = st.columns(len(st.session_state.variable_categories))
    
    for idx, cat_name in enumerate(st.session_state.variable_categories):
        if cat_name in st.session_state.categories:
            cat = st.session_state.categories[cat_name]
            budget = cat.get('budget', 0)
            spent = cat.get('spent', 0)
            remaining = budget - spent
            weekly = remaining / weeks_remaining if weeks_remaining > 0 else 0
            
            with cols[idx]:
                color = "#3fb950" if remaining > 0 else "#f85149"
                st.markdown(f"""
                <div class='weekly-card'>
                    <div class='weekly-title'>{cat_name}</div>
                    <div class='weekly-amount' style='color: {color};'>₹{int(weekly):,}</div>
                    <div class='weekly-subtitle'>per week</div>
                    <div class='weekly-subtitle'>₹{int(remaining):,} left</div>
                </div>
                """, unsafe_allow_html=True)

# ---- CHARTS ----
if st.session_state.categories:
    st.markdown("---")
    st.markdown("### 📊 Overview")
    
    col1, col2 = st.columns(2)
    
    # Bar chart
    with col1:
        df = pd.DataFrame([
            {'Category': name, 'Spent': data.get('spent', 0), 
             'Budget': data.get('budget', 0)}
            for name, data in st.session_state.categories.items()
        ])
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=df['Category'], 
            x=df['Spent'], 
            name='Spent',
            orientation='h',
            marker_color='#58a6ff',
            text=[f"₹{x:,}" for x in df['Spent']],
            textposition='inside'
        ))
        fig.add_trace(go.Bar(
            y=df['Category'], 
            x=df['Budget'] - df['Spent'], 
            name='Left',
            orientation='h',
            marker_color='#30363d',
            text=[f"₹{x:,}" if x > 0 else "" for x in df['Budget'] - df['Spent']],
            textposition='inside'
        ))
        
        fig.update_layout(
            barmode='stack',
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8b949e', size=10),
            showlegend=False,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Pie chart
    with col2:
        spending_data = [(name, data.get('spent', 0)) 
                        for name, data in st.session_state.categories.items() 
                        if data.get('spent', 0) > 0]
        
        if spending_data:
            labels, values = zip(*spending_data)
            
            fig2 = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.6,
                marker=dict(colors=['#58a6ff', '#1f6feb', '#388bfd', '#1158c7', '#0d419d', '#032d5d']),
                textinfo='label+percent',
                textposition='outside',
                textfont=dict(size=9)
            )])
            
            fig2.update_layout(
                height=250,
                margin=dict(l=0, r=0, t=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#8b949e', size=9),
                showlegend=False
            )
            
            st.plotly_chart(fig2, use_container_width=True)
