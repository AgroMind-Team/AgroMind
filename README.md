# 🌾 AgroMind

AgroMind is an AI-powered crop recommendation and agricultural analytics platform built using **Machine Learning** and **Flask**. It helps farmers make informed decisions by predicting the most suitable crop based on location, season, and land area while also providing production estimates, planting guidance, and crop analytics.

---

## ✨ Features

* 🌱 AI-based crop recommendation
* 📈 Expected production prediction
* 🌾 Planting guide for recommended crops
* 📊 Interactive analytics dashboard
* 📰 Community page for farmers
* 🌙 Modern responsive dark/light theme
* ⚡ Live agricultural updates ticker
* 📋 Advisory and farming recommendations

---

## 🛠️ Tech Stack

### Backend

* Python
* Flask
* Scikit-learn
* Pandas
* NumPy

### Frontend

* HTML5
* CSS3
* JavaScript

### Machine Learning

* Crop Recommendation Model
* Production Prediction Model

---

## 📁 Project Structure

```
AgroMind/
│
├── app.py
├── database.py
├── README.md
├── .gitignore
│
├── data/
│   └── crop_production_clean.csv
│
├── models/
│   ├── crop_model.pkl
│   └── production_model.pkl
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       └── community.js
│
└── templates/
    ├── index.html
    ├── analytics.html
    └── community.html
```

> **Note:** The trained `.pkl` model files are not included in this repository because they exceed GitHub's file size limit.

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/AgroMind-Team/AgroMind
```

Go to the project folder:

```bash
cd AgroMind
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

## 📌 Modules

### 🌱 Crop Recommendation

Predicts the best crop based on:

* State
* District
* Season
* Land Area

### 📈 Production Prediction

Estimates expected crop production using a trained Machine Learning model.

### 🌾 Planting Guide

Provides:

* Plant spacing
* Plants per acre
* Water requirements
* Fertilizer recommendations
* Planting method

### 📊 Analytics Dashboard

Visualizes agricultural trends and crop insights.

### 📰 Community

A simple social feed where farmers can share experiences and updates.

## 🔮 Future Enhancements

* User authentication
* Weather API integration
* Market price prediction
* Mobile application
* Community interactions (likes and comments)

---

## 📄 License

This project was developed for educational and academic purposes.

---

**Developed with ❤️ to support smarter agriculture using Artificial Intelligence.**
