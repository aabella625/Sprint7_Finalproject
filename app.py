import streamlit as st
import pandas as pd
import plotly.express as px


# ---------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------

st.set_page_config(
    page_title="Case Management Performance Dashboard",
    layout="wide"
)

st.title("Case Management Task Performance Dashboard")

st.write(
    "This dashboard analyzes completed tasks to identify which business "
    "processes and employees are most likely to miss their deadlines."
)

# ---------------------------------------------------
# 1. LOAD THE DATASET
# ---------------------------------------------------

df = pd.read_excel("filtered_tasks.xlsx")


# ---------------------------------------------------
# 2. CLEAN THE DATA
# ---------------------------------------------------

# Convert Due Date
df["Due Date"] = pd.to_datetime(
    df["Due Date"],
    errors="coerce"
)


# Remove EST / EDT from Completed At
df["Completed At"] = (
    df["Completed At"]
    .astype(str)
    .str.replace(r"\s(EST|EDT)$", "", regex=True)
)


# Convert Completed At
df["Completed At"] = pd.to_datetime(
    df["Completed At"],
    errors="coerce"
)


# Clean text columns

df["Status"] = (
    df["Status"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["Assigned To"] = (
    df["Assigned To"]
    .astype(str)
    .str.strip()
)

df["Task Category"] = (
    df["Task Category"]
    .astype(str)
    .str.strip()
)


# ---------------------------------------------------
# DEBUG
# ---------------------------------------------------

st.write("TOTAL ROWS IN EXCEL:", len(df))

st.write("STATUS VALUES:")
st.write(df["Status"].value_counts())

st.write("VALID DUE DATES:")
st.write(df["Due Date"].notna().sum())

st.write("VALID COMPLETED DATES:")
st.write(df["Completed At"].notna().sum())

st.write("MIN COMPLETED DATE:")
st.write(df["Completed At"].min())

st.write("MAX COMPLETED DATE:")
st.write(df["Completed At"].max())


# ---------------------------------------------------
# 3. FILTER COMPLETED TASKS
# ---------------------------------------------------

completed_df = df[
    (df["Status"] == "complete")
    & df["Due Date"].notna()
    & df["Completed At"].notna()
    & (df["Due Date"] >= pd.Timestamp("2026-04-01"))
    & (df["Completed At"] >= pd.Timestamp("2026-04-01"))
].copy()


st.write(
    "ROWS AFTER STATUS + DATE CHECK:",
    completed_df.shape
)
# ---------------------------------------------------
# 4. CREATE CALCULATED COLUMNS
# ---------------------------------------------------

completed_df["Delay (Days)"] = (
    completed_df["Completed At"] - completed_df["Due Date"]
).dt.days

completed_df["Schedule Status"] = completed_df["Delay (Days)"].apply(
    lambda delay: (
        "Late"
        if delay > 0
        else "Early"
        if delay < 0
        else "On Time"
    )
)

completed_df["Month"] = (
    completed_df["Completed At"]
    .dt.to_period("M")
    .astype(str)
)

completed_df["Month Label"] = (
    completed_df["Completed At"]
    .dt.strftime("%b %Y")
)


# ---------------------------------------------------
# 5. REUSABLE PERFORMANCE SUMMARY FUNCTION
# ---------------------------------------------------

def create_performance_summary(dataframe, group_columns):
    """
    Create a performance summary grouped by one or more columns.

    Metrics:
    - Total completed tasks
    - Number of late tasks
    - Percentage of tasks completed late
    - Average days late among late tasks only
    - Maximum number of days late
    """

    if isinstance(group_columns, str):
        group_columns = [group_columns]

    summary = (
        dataframe.groupby(group_columns)
        .agg(
            Total_Tasks=("Schedule Status", "size"),
            Late_Tasks=(
                "Schedule Status",
                lambda status: (status == "Late").sum()
            ),
            Average_Days_Late=(
                "Delay (Days)",
                lambda delay: delay[delay > 0].mean()
            ),
            Maximum_Days_Late=(
                "Delay (Days)",
                lambda delay: delay[delay > 0].max()
            )
        )
        .reset_index()
    )

    summary["Percent_Late"] = (
        summary["Late_Tasks"]
        / summary["Total_Tasks"]
        * 100
    ).round(1)

    summary["Average_Days_Late"] = (
        summary["Average_Days_Late"]
        .fillna(0)
        .round(1)
    )

    summary["Maximum_Days_Late"] = (
        summary["Maximum_Days_Late"]
        .fillna(0)
        .astype(int)
    )

    return summary


# ---------------------------------------------------
# 6. CREATE SUMMARY DATAFRAMES
# ---------------------------------------------------

category_performance = create_performance_summary(
    completed_df,
    "Task Category"
)

category_performance = (
    category_performance
    .sort_values("Percent_Late", ascending=False)
    .reset_index(drop=True)
)


employee_performance = create_performance_summary(
    completed_df,
    "Assigned To"
)

employee_performance = (
    employee_performance
    .sort_values("Percent_Late", ascending=False)
    .reset_index(drop=True)
)


employee_month_performance = create_performance_summary(
    completed_df,
    ["Month", "Assigned To"]
)

employee_month_performance["Month Label"] = pd.to_datetime(
    employee_month_performance["Month"]
).dt.strftime("%b %Y")

employee_month_performance = (
    employee_month_performance
    .sort_values(["Month", "Assigned To"])
    .reset_index(drop=True)
)


# ---------------------------------------------------
# 7. KPI CARDS
# ---------------------------------------------------

total_completed_tasks = len(completed_df)

total_late_tasks = (
    completed_df["Schedule Status"] == "Late"
).sum()

overall_percent_late = (
    total_late_tasks
    / total_completed_tasks
    * 100
    if total_completed_tasks > 0
    else 0
)

late_tasks_only = completed_df[
    completed_df["Delay (Days)"] > 0
]

average_days_late = (
    late_tasks_only["Delay (Days)"].mean()
    if not late_tasks_only.empty
    else 0
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Completed Tasks",
    f"{total_completed_tasks:,}"
)

col2.metric(
    "Late Tasks",
    f"{total_late_tasks:,}"
)

col3.metric(
    "Late Tasks (%)",
    f"{overall_percent_late:.1f}%"
)

col4.metric(
    "Avg. Days Late",
    f"{average_days_late:.1f}"
)

st.caption(
    "Average Days Late is calculated only among tasks that were completed "
    "after their due date."
)
# ---------------------------------------------------
# 8. HISTOGRAM - DISTRIBUTION OF TASK DELAYS
# ---------------------------------------------------

st.header("Distribution of Task Delays")

st.write(
    "This histogram shows how many tasks were completed before or after "
    "their assigned deadline."
)

fig_delay = px.histogram(
    completed_df,
    x="Delay (Days)",
    nbins=15,
    title="Distribution of Days Relative to Due Date",
    labels={
        "Delay (Days)": "Days Before (-) or After (+) Due Date",
        "count": "Number of Tasks"
    }
)

fig_delay.update_layout(
    xaxis_title="Days Before (-) or After (+) Due Date",
    yaxis_title="Number of Tasks"
)

st.plotly_chart(
    fig_delay,
    use_container_width=True
)

# ---------------------------------------------------
# 8.1 DATASET PREVIEW
# ---------------------------------------------------

with st.expander("View completed task data"):
    st.dataframe(
        completed_df,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------
# 9. PERFORMANCE BY TASK CATEGORY
# ---------------------------------------------------

st.header("Performance by Task Category")

st.write(
    "This chart shows the percentage of completed tasks that missed their "
    "due date within each task category."
)

fig_category = px.bar(
    category_performance,
    x="Percent_Late",
    y="Task Category",
    orientation="h",
    text="Percent_Late",
    title="Percentage of Late Tasks by Category",
    hover_data={
        "Total_Tasks": True,
        "Late_Tasks": True,
        "Average_Days_Late": ":.1f",
        "Maximum_Days_Late": True,
        "Percent_Late": ":.1f"
    },
    labels={
        "Percent_Late": "Late Tasks (%)",
        "Task Category": "Task Category",
        "Total_Tasks": "Completed Tasks",
        "Late_Tasks": "Late Tasks",
        "Average_Days_Late": "Average Days Late",
        "Maximum_Days_Late": "Maximum Days Late"
    }
)

fig_category.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
    cliponaxis=False
)

fig_category.update_layout(
    xaxis_title="Late Tasks (%)",
    yaxis_title="",
    yaxis={
        "categoryorder": "array",
        "categoryarray": category_performance[
            "Task Category"
        ][::-1]
    }
)

category_max = category_performance["Percent_Late"].max()

fig_category.update_xaxes(
    range=[0, category_max + 10],
    ticksuffix="%"
)

st.plotly_chart(
    fig_category,
    use_container_width=True
)

with st.expander("View category performance data"):
    st.dataframe(
        category_performance.rename(
            columns={
                "Task Category": "Task Category",
                "Total_Tasks": "Completed Tasks",
                "Late_Tasks": "Late Tasks",
                "Percent_Late": "Late Tasks (%)",
                "Average_Days_Late": "Avg. Days Late",
                "Maximum_Days_Late": "Max. Days Late"
            }
        ),
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------
# 10. OVERALL PERFORMANCE BY EMPLOYEE
# ---------------------------------------------------

st.header("Overall Performance by Employee")

st.write(
    "This chart compares each employee's percentage of completed tasks "
    "that missed their due date."
)

fig_employee = px.bar(
    employee_performance,
    x="Percent_Late",
    y="Assigned To",
    orientation="h",
    text="Percent_Late",
    title="Percentage of Late Tasks by Employee",
    hover_data={
        "Total_Tasks": True,
        "Late_Tasks": True,
        "Average_Days_Late": ":.1f",
        "Maximum_Days_Late": True,
        "Percent_Late": ":.1f"
    },
    labels={
        "Percent_Late": "Late Tasks (%)",
        "Assigned To": "Employee",
        "Total_Tasks": "Completed Tasks",
        "Late_Tasks": "Late Tasks",
        "Average_Days_Late": "Average Days Late",
        "Maximum_Days_Late": "Maximum Days Late"
    }
)

fig_employee.update_traces(
    texttemplate="%{text:.1f}%",
    textposition="outside",
    cliponaxis=False
)

fig_employee.update_layout(
    xaxis_title="Late Tasks (%)",
    yaxis_title="",
    yaxis={
        "categoryorder": "array",
        "categoryarray": employee_performance[
            "Assigned To"
        ][::-1]
    }
)

employee_max = employee_performance["Percent_Late"].max()

fig_employee.update_xaxes(
    range=[0, employee_max + 10],
    ticksuffix="%"
)

st.plotly_chart(
    fig_employee,
    use_container_width=True
)

with st.expander("View overall employee performance data"):
    st.dataframe(
        employee_performance.rename(
            columns={
                "Assigned To": "Employee",
                "Total_Tasks": "Completed Tasks",
                "Late_Tasks": "Late Tasks",
                "Percent_Late": "Late Tasks (%)",
                "Average_Days_Late": "Avg. Days Late",
                "Maximum_Days_Late": "Max. Days Late"
            }
        ),
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------
# 11. EMPLOYEE PERFORMANCE BY MONTH
# ---------------------------------------------------

st.header("Employee Performance by Month")

st.write(
    "This chart shows how each employee's late-task percentage changed "
    "from month to month."
)

fig_employee_month = px.line(
    employee_month_performance,
    x="Month Label",
    y="Percent_Late",
    color="Assigned To",
    markers=True,
    title="Monthly Late-Task Percentage by Employee",
    hover_data={
        "Month": False,
        "Total_Tasks": True,
        "Late_Tasks": True,
        "Average_Days_Late": ":.1f",
        "Maximum_Days_Late": True,
        "Percent_Late": ":.1f"
    },
    labels={
        "Month Label": "Month",
        "Percent_Late": "Late Tasks (%)",
        "Assigned To": "Employee",
        "Total_Tasks": "Completed Tasks",
        "Late_Tasks": "Late Tasks",
        "Average_Days_Late": "Average Days Late",
        "Maximum_Days_Late": "Maximum Days Late"
    }
)

fig_employee_month.update_traces(
    mode="lines+markers"
)

fig_employee_month.update_layout(
    xaxis_title="Month",
    yaxis_title="Late Tasks (%)",
    legend_title="Employee",
    hovermode="x unified"
)

fig_employee_month.update_yaxes(
    rangemode="tozero",
    ticksuffix="%"
)

st.plotly_chart(
    fig_employee_month,
    use_container_width=True
)

with st.expander("View monthly employee performance data"):
    st.dataframe(
        employee_month_performance[
            [
                "Month Label",
                "Assigned To",
                "Total_Tasks",
                "Late_Tasks",
                "Percent_Late",
                "Average_Days_Late",
                "Maximum_Days_Late"
            ]
        ].rename(
            columns={
                "Month Label": "Month",
                "Assigned To": "Employee",
                "Total_Tasks": "Completed Tasks",
                "Late_Tasks": "Late Tasks",
                "Percent_Late": "Late Tasks (%)",
                "Average_Days_Late": "Avg. Days Late",
                "Maximum_Days_Late": "Max. Days Late"
            }
        ),
        use_container_width=True,
        hide_index=True
    )
