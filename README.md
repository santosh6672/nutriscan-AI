# 🥗 NutriScan AI - Intelligent Nutrition Analysis

NutriScan AI is an intelligent web application that uses computer vision and AI to analyze food products and provide detailed nutritional insights. Simply scan food items to get instant nutritional information, health scores, and AI-powered descriptions.

![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![AI](https://img.shields.io/badge/AI-Powered-FF6B6B)

## ✨ Features

### 🔍 Barcode Detection & Recognition
- **YOLOv5** for accurate barcode detection in images
- **PyZbar** for seamless barcode decoding
- Support for multiple barcode formats

### 📊 Comprehensive Nutrition Analysis
- Detailed nutritional values and breakdown
- Nutri-Score calculation for quick health assessment
- Personalized health insights and recommendations

### 🤖 AI-Powered Descriptions
- **LLaMA-3 integration** for intelligent product descriptions
- Contextual information about food items
- Allergy warnings and dietary information

### 👤 User Management
- Secure authentication system
- Personalized scan history
- User profiles and preferences

## 🛠 Tech Stack

**Backend Framework:** Django 5.2  
**Database:** SQLite (Development), PostgreSQL (Production)  
**AI/ML Models:** YOLOv5, PyZbar, LLaMA-3  
**Computer Vision:** OpenCV, EasyOCR  
**Additional Libraries:** NumPy, Pandas, Pillow, PyTorch  
**Frontend:** HTML5, CSS3, JavaScript  
**Deployment Ready:** WhiteNoise, Gunicorn, dj-database-url

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/santosh6672/nutriscan-AI.git
cd nutriscan-AI
Create and activate virtual environment

bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
Install dependencies

bash
pip install -r requirements.txt
Environment Configuration

bash
# Create .env file
cp .env.example .env
Edit .env file with your configuration:

env
SECRET_KEY=your-generated-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
HF_TOKEN=your-huggingface-token
Database Setup

bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
Collect Static Files

bash
python manage.py collectstatic
Run Development Server

bash
python manage.py runserver
Visit http://127.0.0.1:8000 to access the application.


⚙️ Configuration
Environment Variables
SECRET_KEY: Django secret key for security

DEBUG: Set to False in production

DATABASE_URL: Database connection string

HF_TOKEN: Hugging Face API token for LLaMA-3

Generating Secret Key
python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
🎯 Usage
Register/Login to your account

Upload an image of a food product or barcode

Get instant analysis including:

Nutritional values

Health score (Nutri-Score)

AI-generated description

Dietary recommendations
