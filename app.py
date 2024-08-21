from flask import Flask, request,render_template, redirect,session
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import pickle
from flask import Flask, request, app, jsonify, url_for, render_template
import numpy as np
import pandas as pd
import sklearn
import ctypes
from tkinter import messagebox
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'

#LOAD MODELS
log_reg_model = pickle.load(open('saved models\\churn_logistic_regression_model_for_deployment.pkl', "rb"))
xgb_model = pickle.load(open('saved models\\churn_xgb_model_for_deployment.pkl', "rb"))

#mapping from zip codes to population, latitude and longitude data
zip_code_map_df = pd.read_csv("created CSVs\\zip_code_map_df.csv", index_col = 'Zip Code')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    def __init__(self,email,password,name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self,password):
        return bcrypt.checkpw(password.encode('utf-8'),self.password.encode('utf-8'))

with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index1.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        # handle request
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        new_user = User(name=name,email=email,password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
        except:
            #print("This user already exists.")
            WS_EX_TOPMOST=40000
            ctypes.windll.user32.MessageBoxExW(None,"This Email id  already exists. Try with new one","Email id already exists",WS_EX_TOPMOST)
            messagebox.showinfo("alert","This email already exists.")
            return redirect('/register')
        return redirect('/login')



    return render_template('register.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/index')
        else:
            return render_template('login.html',error='Invalid user')

    return render_template('login.html')




#CREATE APP ROUTE
# Route for the home page
@app.route('/index')
def home():
    return render_template("index.html")

#ROUTE FOR PREDICTION API
@app.route('/predict_api', methods = ['POST'])
def predict_api():
    api_data = request.json['data']

    zip_code = int(api_data['zip_code'])

    #if an invalid zip code is entered default to the Zip code with maximum population
    if zip_code not in zip_code_map_df.index:
        zip_code = 90201

    tenure = int(api_data['tenure'])
    contract = api_data['contract']
    internet_service = api_data['internet_service']
    offer = api_data['offer']
    payement_method = api_data['payement_method']

    #All the variable features to be used by the Model to make predictions
    Age = int(api_data['age'])
    Latitude = zip_code_map_df.loc[zip_code]['Latitude']
    Longitude = zip_code_map_df.loc[zip_code]['Longitude']
    Senior_Citizen = int(Age > 65)
    Online_Security = int(api_data['online_security'])
    Tech_Support = int(api_data['tech_support'])
    Paperless_Billing = int(api_data['paperless_billing'])
    Under_30 = int(Age < 30)
    Married = int(api_data['married'])
    Population = zip_code_map_df.loc[zip_code]['Population']
    Referred_a_Friend = int(api_data['refered_a_friend'])
    Total_Revenue = float(api_data['total_revenue'])
    Satisfaction_Score = int(api_data['satisfaction_score'])
    Tenure_Bins__0_12_ = int((tenure > 0) and (tenure <= 12))
    Tenure_Bins__12_24_ = int((tenure > 12) and (tenure <= 24))
    Tenure_Bins__24_48_ = int((tenure > 24) and (tenure <= 48))
    Tenure_Bins__48_60_ = int((tenure > 48) and (tenure <= 60))
    Tenure_Bins__60_72_ = int(tenure > 60)
    Offer_None = int(offer == "None")
    Offer_Offer_A = int(offer == "Offer A")
    Offer_Offer_B = int(offer == "Offer B")
    Offer_Offer_C = int(offer == "Offer C")
    Offer_Offer_D = int(offer == "Offer D")
    Offer_Offer_E = int(offer == "Offer E")
    Payment_Method_Bank_transfer__automatic = int(payement_method == "Bank transfer (automatic)")
    Payment_Method_Credit_card__automatic = int(payement_method == "Credit card (automatic)")
    Payment_Method_Electronic_check = int(payement_method == "Electronic check")
    Payment_Method_Mailed_check = int(payement_method == "Mailed check")
    Contract_Month_to_month = int(contract == 'Month-to-month')
    Contract_One_year = int(contract == 'One year')
    Contract_Two_year = int(contract == 'Two year')
    Internet_Service_DSL = int(internet_service == 'DSL')
    Internet_Service_Fiber_optic = int(internet_service == 'Fiber Optic')
    Internet_Service_No = int(internet_service == 'No')

    data = [Latitude, Longitude, Senior_Citizen, Online_Security, Tech_Support, Paperless_Billing, Age, Under_30, Married,
        Population, Referred_a_Friend, Total_Revenue, Satisfaction_Score, Tenure_Bins__0_12_, Tenure_Bins__12_24_, Tenure_Bins__24_48_,
        Tenure_Bins__48_60_, Tenure_Bins__60_72_, Offer_None, Offer_Offer_A, Offer_Offer_B, Offer_Offer_C, Offer_Offer_D,
        Offer_Offer_E, Payment_Method_Bank_transfer__automatic, Payment_Method_Credit_card__automatic, Payment_Method_Electronic_check, 
        Payment_Method_Mailed_check, Contract_Month_to_month, Contract_One_year, Contract_Two_year, Internet_Service_DSL, 
        Internet_Service_Fiber_optic, Internet_Service_No]

    data = pd.Series(data)
    data = data.values.reshape(1, -1)

    output_log_reg = log_reg_model.predict(data)[0]
    output_probab_log_reg = log_reg_model.predict_proba(data)[0][1]

    output_xgb = log_reg_model.predict(data)[0]
    output_probab_xgb = xgb_model.predict_proba(data)[0][1]

    api_output_probab = (output_probab_xgb + output_probab_log_reg) / 2.0

    pred = "Churn" if api_output_probab > 0.4 else "Not Churn"

    res = {'prediction' : pred, 'probability of churning' : api_output_probab}

    return jsonify(res)

#Route to handle form submission
#FUNCTION TO MAKE PREDICTIONS
@app.route('/predict', methods = ['POST'])
def predict():
    # Retrieve the form data

    zip_code = int(request.form['zip_code'])

    #if an invalid zip code is entered default to the Zip code with maximum population
    if zip_code not in zip_code_map_df.index:
        zip_code = 90201

    tenure = int(request.form['tenure'])
    contract = request.form['contract']
    internet_service = request.form['internet_service']
    offer = request.form['offer']
    payement_method = request.form['payement_method']

    #All the variable features to be used by the Model to make predictions
    Age = int(request.form['age'])
    Latitude = zip_code_map_df.loc[zip_code]['Latitude']
    Longitude = zip_code_map_df.loc[zip_code]['Longitude']
    Senior_Citizen = int(Age > 65)
    Online_Security = int(request.form['online_security'])
    Tech_Support = int(request.form['tech_support'])
    Paperless_Billing = int(request.form['paperless_billing'])
    Under_30 = int(Age < 30)
    Married = int(request.form['married'])
    Population = zip_code_map_df.loc[zip_code]['Population']
    Referred_a_Friend = int(request.form['refered_a_friend'])
    Total_Revenue = float(request.form['total_revenue'])
    Satisfaction_Score = int(request.form['satisfaction_score'])
    Tenure_Bins__0_12_ = int((tenure > 0) and (tenure <= 12))
    Tenure_Bins__12_24_ = int((tenure > 12) and (tenure <= 24))
    Tenure_Bins__24_48_ = int((tenure > 24) and (tenure <= 48))
    Tenure_Bins__48_60_ = int((tenure > 48) and (tenure <= 60))
    Tenure_Bins__60_72_ = int(tenure > 60)
    Offer_None = int(offer == "None")
    Offer_Offer_A = int(offer == "Offer A")
    Offer_Offer_B = int(offer == "Offer B")
    Offer_Offer_C = int(offer == "Offer C")
    Offer_Offer_D = int(offer == "Offer D")
    Offer_Offer_E = int(offer == "Offer E")
    Payment_Method_Bank_transfer__automatic = int(payement_method == "Bank transfer (automatic)")
    Payment_Method_Credit_card__automatic = int(payement_method == "Credit card (automatic)")
    Payment_Method_Electronic_check = int(payement_method == "Electronic check")
    Payment_Method_Mailed_check = int(payement_method == "Mailed check")
    Contract_Month_to_month = int(contract == 'Month-to-month')
    Contract_One_year = int(contract == 'One year')
    Contract_Two_year = int(contract == 'Two year')
    Internet_Service_DSL = int(internet_service == 'DSL')
    Internet_Service_Fiber_optic = int(internet_service == 'Fiber Optic')
    Internet_Service_No = int(internet_service == 'No')

    data = [Latitude, Longitude, Senior_Citizen, Online_Security, Tech_Support, Paperless_Billing, Age, Under_30, Married,
        Population, Referred_a_Friend, Total_Revenue, Satisfaction_Score, Tenure_Bins__0_12_, Tenure_Bins__12_24_, Tenure_Bins__24_48_,
        Tenure_Bins__48_60_, Tenure_Bins__60_72_, Offer_None, Offer_Offer_A, Offer_Offer_B, Offer_Offer_C, Offer_Offer_D,
        Offer_Offer_E, Payment_Method_Bank_transfer__automatic, Payment_Method_Credit_card__automatic, Payment_Method_Electronic_check, 
        Payment_Method_Mailed_check, Contract_Month_to_month, Contract_One_year, Contract_Two_year, Internet_Service_DSL, 
        Internet_Service_Fiber_optic, Internet_Service_No]

    data = pd.Series(data)
    data = data.values.reshape(1, -1)

    output_log_reg = log_reg_model.predict(data)[0]
    output_probab_log_reg = log_reg_model.predict_proba(data)[0][1]

    output_xgb = log_reg_model.predict(data)[0]
    output_probab_xgb = xgb_model.predict_proba(data)[0][1]

    output_probab = (output_probab_xgb + output_probab_log_reg) / 2.0

    pred = "Churn" if output_probab > 0.4 else "Not Churn"

    return render_template("result.html", prediction = pred, predict_probabality = output_probab)


@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)