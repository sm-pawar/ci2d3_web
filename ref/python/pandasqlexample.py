import pandas as pd
import pandasql as psql

# Sample DataFrame
data = {
    'id': [1, 2, 3, 4, 5],
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eva'],
    'age': [24, 27, 22, 32, 29],
    'city': ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
}

df = pd.DataFrame(data)

# Creating another DataFrame for join example
data2 = {
    'id': [1, 2, 3, 6],
    'salary': [70000, 80000, 120000, 90000]
}

df2 = pd.DataFrame(data2)

# Function to run SQL queries
def run_query(query):
    return psql.sqldf(query, globals())

### SQL Queries ###
print("### SQL Queries ###")

# SELECT equivalent
query_select = "SELECT name, age FROM df;"
result_select = run_query(query_select)
print(result_select)

# WHERE equivalent
query_where = "SELECT * FROM df WHERE age > 25;"
result_where = run_query(query_where)
print(result_where)

# GROUP BY equivalent
query_groupby = "SELECT city, COUNT(*) as count FROM df GROUP BY city;"
result_groupby = run_query(query_groupby)
print(result_groupby)

# JOIN equivalent
query_join = "SELECT df.id, df.name, df.age, df.city, df2.salary FROM df INNER JOIN df2 ON df.id = df2.id;"
result_join = run_query(query_join)
print(result_join)

# ORDER BY equivalent
query_orderby = "SELECT * FROM df ORDER BY age DESC;"
result_orderby = run_query(query_orderby)
print(result_orderby)

# LIMIT equivalent
query_limit = "SELECT * FROM df LIMIT 3;"
result_limit = run_query(query_limit)
print(result_limit)

# Aggregation functions
query_avg = "SELECT AVG(age) as average_age FROM df;"
result_avg = run_query(query_avg)
print(result_avg)

query_sum = "SELECT SUM(salary) as total_salary FROM df2;"
result_sum = run_query(query_sum)
print(result_sum)


### Pandas Equivalent Operations ###
print("\n\n### Pandas Equivalent Operations ###")

# SELECT equivalent
result_select = df[['name', 'age']]
print(result_select)

# WHERE equivalent
result_where = df[df['age'] > 25]
print(result_where)

# GROUP BY equivalent
result_groupby = df.groupby('city').size().reset_index(name='count')
print(result_groupby)

# JOIN equivalent
result_join = pd.merge(df, df2, on='id', how='inner')
print(result_join)

# ORDER BY equivalent
result_orderby = df.sort_values(by='age', ascending=False)
print(result_orderby)

# LIMIT equivalent
result_limit = df.head(3)
print(result_limit)

# Aggregation functions
result_avg = df['age'].mean()
print(result_avg)

result_sum = df2['salary'].sum()
print(result_sum)
