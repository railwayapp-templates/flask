from flask import Flask, request, jsonify, send_file
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
  <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Excel File Comparison</title>
<style>
body {
font-family: Arial, sans-serif;
text-align: center;
}

h1 {
margin-top: 50px;
color:green;
}

p {
margin-bottom: 20px;

}

form {
margin-top: 30px;
display: inline-block;
text-align: left;
}

label {
display: block;
margin-bottom: 10px;
}

input[type="file"] {
margin-bottom: 20px;
}

input[type="submit"] {
padding: 10px 20px;
background-color: green;
color: #fff;
border: none;
border-radius: 5px;
cursor: pointer;
}

input[type="submit"]:hover {
background-color: #0056b3;
}
</style>
</head>
<body>
<h1 class="padding">2024 Interns Control</h1>
<b><p class="position" color="red">Please Note:</p></b> 
<b><p class="notes">*Only put the excel files
<br>*File 1 must be an excel file with all the interns </br>
*File 2 must be an excel file of the interns that have submitted </p></b>
<br>
<br>
<form class="inputs" action="/compare" method="post" enctype="multipart/form-data">
<label>File 1:</label>  <input type="file" name="file1" id="file1" accept=".xlsx, .xls" required><br>
<br>
<br>
<label>File 2:</label><input type="file" name="file2" id="file2" accept=".xlsx, .xls" required><br>
<br>
<br>
<b><input type="submit" value="Upload" ></b>
<br>
</form>
</body>
</html>
"""

@app.route('/compare', methods=['POST'])
def compare_files():
    if 'file1' not in request.files or 'file2' not in request.files:
        return jsonify(error="Files not provided"), 400

    # Get the uploaded files
    file1 = request.files['file1']
    file2 = request.files['file2']

    # Read the Excel files into pandas DataFrames
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)
    
    df2['Email address'] = df2['Email address'].str.lower()
    df1['email'] = df1['email'].str.strip()
    df_not_submitted = df1[~df1['email'].str.lower().isin(df2['Email address'].str.strip())]
    df_not_submitted.to_excel('not_submitted.xlsx', index=False)

    return send_file('not_submitted.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=False)
