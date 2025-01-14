import sqlite3
import pandas as pd
from datetime import timedelta

# Connect to SQLite database
connection = sqlite3.connect('test.db')

# Read data from SQLite table
query = """
SELECT Employee_Name, DATE(Pay_Date) AS Pay_Date, Week_1, Week_2, Store_Name
FROM test_table
"""
df_from_db = pd.read_sql_query(query, connection)

# Convert Pay_Date to datetime
df_from_db['Pay_Date'] = pd.to_datetime(df_from_db['Pay_Date'])

# Sum the hours for duplicate pay dates
df_from_db = df_from_db.groupby(['Employee_Name', 'Pay_Date', 'Store_Name'], as_index=False).agg({
    'Week_1': 'sum',
    'Week_2': 'sum'
})

# Filter employees who have received at least one paycheck in the last year
df_last_year = df_from_db[df_from_db['Pay_Date'] >= pd.to_datetime('now') - pd.DateOffset(years=1)]

# Filter employees who have at least 26 paychecks overall
df_26_paychecks = df_from_db.groupby('Employee_Name').filter(lambda x: len(x) >= 26)

# Merge the two filters to get employees who meet both criteria
df_26_paychecks_last_year = df_26_paychecks[df_26_paychecks['Employee_Name'].isin(df_last_year['Employee_Name'])]

# Get employees who have received at least one paycheck in the last year but do not have 26 paychecks overall
df_less_than_26_paychecks = df_last_year[~df_last_year['Employee_Name'].isin(df_26_paychecks['Employee_Name'])]

# Combine the two dataframes
df_filtered = pd.concat([df_26_paychecks_last_year, df_less_than_26_paychecks])

# Create a new column "Total_Hours" by adding "Week_1" and "Week_2"
df_filtered['Total_Hours'] = df_filtered['Week_1'] + df_filtered['Week_2']

# Get the most recent Store_Name and Pay_Date for each Employee_Name
df_recent_store = df_filtered.sort_values('Pay_Date').groupby('Employee_Name').last().reset_index()

# Calculate the original Start_Date considering breaks less than one year
def calculate_start_date(group):
    pay_dates = group['Pay_Date'].sort_values().tolist()
    start_date = pay_dates[0]
    for i in range(1, len(pay_dates)):
        if (pay_dates[i] - pay_dates[i - 1]).days > 365:
            start_date = pay_dates[i]
    return start_date

df_start_date = df_filtered.groupby('Employee_Name').apply(calculate_start_date).reset_index()
df_start_date.columns = ['Employee_Name', 'Start_Date']

# Calculate YTD_Hours by grouping by Employee_Name and summing Total_Hours
df_ytd = df_filtered.groupby('Employee_Name', as_index=False)['Total_Hours'].sum()
df_ytd.rename(columns={'Total_Hours': 'YTD_Hours'}, inplace=True)

# Count the number of Pay_Dates for each Employee_Name
df_pay_date_count = df_filtered.groupby('Employee_Name', as_index=False)['Pay_Date'].count()
df_pay_date_count.rename(columns={'Pay_Date': 'Pay_Date_Count'}, inplace=True)

# Merge the YTD_Hours, Pay_Date_Count, Start_Date with the most recent Store_Name and Pay_Date
df_result = pd.merge(df_ytd, df_recent_store[['Employee_Name', 'Store_Name', 'Pay_Date']], on='Employee_Name')
df_result = pd.merge(df_result, df_pay_date_count, on='Employee_Name')
df_result = pd.merge(df_result, df_start_date, on='Employee_Name')

# Round YTD_Hours to 2 decimal places
df_result['YTD_Hours'] = df_result['YTD_Hours'].round(2)

# Format Store_Name column
df_result['Store_Name'] = df_result['Store_Name'].apply(lambda x: ' '.join([word.capitalize() for word in x.split()]))

# Close the connection
connection.close()

# Set the index to start from 1
df_result.index = df_result.index + 1

# Generate HTML content with filters
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Employee Data</title>
    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 8px;
            text-align: left;
        }
    </style>
    <script>
        function filterTable() {
            var inputStore = document.getElementById("storeFilter").value.toLowerCase();
            var inputEmployee = document.getElementById("employeeFilter").value.toLowerCase();
            var table = document.getElementById("dataTable");
            var tr = table.getElementsByTagName("tr");

            for (var i = 1; i < tr.length; i++) {
                var tdStore = tr[i].getElementsByTagName("td")[2];
                var tdEmployee = tr[i].getElementsByTagName("td")[1];
                if (tdStore && tdEmployee) {
                    var storeValue = tdStore.textContent || tdStore.innerText;
                    var employeeValue = tdEmployee.textContent || tdEmployee.innerText;
                    if (storeValue.toLowerCase().indexOf(inputStore) > -1 && employeeValue.toLowerCase().indexOf(inputEmployee) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
</head>
<body>

<h2>Employee Data</h2>

<label for="storeFilter">Filter by Store Name:</label>
<input type="text" id="storeFilter" onkeyup="filterTable()" placeholder="Search for store names..">

<label for="employeeFilter">Filter by Employee Name:</label>
<input type="text" id="employeeFilter" onkeyup="filterTable()" placeholder="Search for employee names..">

<br><br>

<table id="dataTable">
    <thead>
        <tr>
            <th>Index</th>
            <th>Employee Name</th>
            <th>Store Name</th>
            <th>YTD Hours</th>
            <th>Last Pay Date</th>
            <th>Pay Date Count</th>
            <th>Start Date</th>
        </tr>
    </thead>
    <tbody>
"""

# Append the data rows to the HTML content
for index, row in df_final.iterrows():
    html_content += f"""
        <tr>
            <td>{index}</td>
            <td>{row['Employee_Name']}</td>
            <td>{row['Store_Name']}</td>
            <td>{row['YTD_Hours']}</td>
            <td>{row['Last_Pay_Date']}</td>
            <td>{row['Pay_Date_Count']}</td>
            <td>{row['Start_Date']}</td>
        </tr>
    """

# Close the HTML tags
html_content += """
    </tbody>
</table>

</body>
</html>
"""

# Write the HTML content to a file
with open('output.html', 'w') as file:
    file.write(html_content)