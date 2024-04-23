from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a really really really really long secret key'


@app.route("/")
def main():
    return render_template("main.html")

@app.route("/base")
def base():
    return render_template("base.html")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)

