from flask import Blueprint, request, render_template, redirect
from werkzeug.security import generate_password_hash


def create_registration_blueprint(save_user):

    registration = Blueprint("registration", __name__)

    @registration.route("/register", methods=["GET", "POST"])
    def register():

        if request.method == "POST":

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            confirmation = request.form.get("confirmation", "")

            if not username:
                return "Must provide username", 400

            if not password:
                return "Must provide password", 400

            if not confirmation:
                return "Must confirm password", 400

            if password != confirmation:
                return "Passwords do not match", 400

            password_safe = generate_password_hash(password)

            try:
                save_user(username, password_safe) #create a fonctino that save the users information into the data base

            except ValueError:
                return "Username already exists", 409

            return redirect("/login")

        return render_template("register.html")

    return registration
