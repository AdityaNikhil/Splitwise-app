
import streamlit as st
import pandas as pd
from splitwise import Splitwise
import plotly.express as px
import plotly.graph_objects as go
import calendar
from datetime import datetime

# Initialize Splitwise
def initialize_splitwise():
    consumer_key = st.secrets["consumer_key"]
    consumer_secret = st.secrets["consumer_secret"]
    api_key = st.secrets["api_key"]

    sObj = Splitwise(consumer_key, consumer_secret, api_key=api_key)
    return sObj

def fetch_expenses(sObj, year, month):
    # Get the Non-group expenses group ID
    # groups = sObj.getGroups()
    group_id = sObj.getGroup('Non-group expenses').getId()

    # Calculate start and end dates for the selected month
    _, last_day = calendar.monthrange(int(year), month)
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day}"
    
    all_expenses = sObj.getExpenses(group_id=group_id, dated_after=start_date, dated_before=end_date, visible=True, limit=1000)

    user_id = sObj.getCurrentUser().getId()
    month_expenses = []

    for expense in all_expenses:
        try:
            category = expense.getCategory().getName() if expense.getCategory() else "Uncategorized"
            
            # Skip expenses in 'General' category
            if category.lower() == 'general':
                continue
            print(expense.getDescription())
            date = pd.to_datetime(expense.getDate())
            
            for user in expense.getUsers():
                if user.getId() == user_id:
                    owed_share = float(user.getOwedShare())
                    paid_share = float(user.getPaidShare())
                    
                    # If user owes money
                    if owed_share > 0:
                        month_expenses.append({
                            'category': category,
                            'amount': owed_share,
                            'date': date,
                            'description': expense.getDescription(),
                        })
                    
                    # If user paid money and doesn't owe anything
                    if paid_share > 0 and owed_share == 0:
                        month_expenses.append({
                            'category': category,
                            'amount': paid_share,
                            'date': date,
                            'description': expense.getDescription(),
                        })
                    
                    break  # Found the current user, no need to continue loop
                    
        except Exception as e:
            print(f"Error processing expense: {str(e)}")
            continue

    return month_expenses



def create_pie_chart(df_summary):
    fig = px.pie(
        df_summary,
        values='amount',
        names='category',
        title='Expense Distribution by Category',
        hole=0.3,  # Makes it a donut chart
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='#000000', width=1))
    )
    
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )
    
    return fig

def create_bar_chart(df_summary):
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_summary['category'],
        y=df_summary['amount'],
        marker_color='rgb(58,137,232)',
        text=df_summary['amount'].round(2),
        textposition='auto',
    ))
    
    fig.update_layout(
        title='Expenses by Category',
        xaxis_title='Category',
        yaxis_title='Amount ($)',
        height=500,
        showlegend=False,
        xaxis_tickangle=-45
    )
    
    return fig

def create_daily_trend(df):
    daily_expenses = df.groupby('date')['amount'].sum().reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_expenses['date'],
        y=daily_expenses['amount'],
        mode='lines+markers',
        line=dict(color='rgb(58,137,232)', width=2),
        marker=dict(size=8, color='rgb(58,137,232)')
    ))
    
    fig.update_layout(
        title='Daily Expense Trend',
        xaxis_title='Date',
        yaxis_title='Amount ($)',
        height=400,
        showlegend=False
    )
    
    return fig

def main():
    st.set_page_config(layout="wide", page_title="Splitwise Expense Analytics")
    
    st.title("💰 Splitwise Expense Analytics")
    st.markdown("---")

    # Initialize Splitwise
    try:
        sObj = initialize_splitwise()
    except Exception as e:
        st.error(f"Failed to initialize Splitwise: {str(e)}")
        return
    
    # Create columns for filters
    col1, col2 = st.columns([1, 3])
    
    with col1:
        current_year = datetime.now().year
        selected_month = st.selectbox(
            "Select Month",
            range(1, 13),
            format_func=lambda x: pd.to_datetime(f'2024-{x}-01').strftime('%B'),
            index=datetime.now().month - 1
        )
    
    # Fetch expenses
    expenses = fetch_expenses(sObj, current_year, selected_month)
    if not expenses:
        st.info("No expenses found for this month.")
        return

    # Create DataFrame
    df = pd.DataFrame(expenses)
    df_summary = df.groupby('category')['amount'].sum().reset_index()

    # Detailed expenses table
    st.subheader("Detailed Expenses")
    detailed_df = df[['date', 'category', 'description', 'amount']].sort_values('date', ascending=False)
    detailed_df['date'] = detailed_df['date'].dt.strftime('%Y-%m-%d')
    detailed_df['amount'] = detailed_df['amount'].round(2)
    st.dataframe(
        detailed_df,
        column_config={
            "date": "Date",
            "category": "Category",
            "description": "Description",
            "amount": st.column_config.NumberColumn(
                "Amount ($)",
                format="$%.2f"
            )
        },
        hide_index=True
    )

    # Display total expenses
    total_amount = df['amount'].sum()
    st.metric("Total Expenses", f"${total_amount:.2f}")
    
    # Create three columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(create_pie_chart(df_summary), use_container_width=True)
    
    with col2:
        st.plotly_chart(create_bar_chart(df_summary), use_container_width=True)
    
    # Daily trend chart
    st.plotly_chart(create_daily_trend(df), use_container_width=True)
    

if __name__ == "__main__":
    main()
