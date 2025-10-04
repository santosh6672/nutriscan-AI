# NutriScan AI

NutriScan AI is an intelligent nutrition analysis web application that allows users to scan food products and instantly get detailed nutritional information. It leverages computer vision and AI models to recognize food items and provide actionable insights.

---

## 🌟 Key Features

- **Barcode Detection**: Uses **YOLOv5** and **PyZbar** to detect and decode barcodes from uploaded images.  
- **Nutrition Analysis**: Provides detailed nutritional values, Nutri-Score, and health insights.  
- **AI-powered Descriptions**: Integrates **LLaMA-3** to generate descriptive summaries for scanned products.  
- **User Authentication**: Secure login and registration for personalized experiences.  

---

## 🛠 Technology Stack

- **Backend**: Django 5.2  
- **Frontend**: HTML, CSS, JavaScript  
- **AI/ML Models**:  
  - **YOLOv5** for barcode detection  
  - **PyZbar** for barcode decoding  
  - **LLaMA-3** for product description generation  
- **Database**: SQLite (default), easily configurable for PostgreSQL  
- **Other Libraries**: NumPy, Pandas, OpenCV, EasyOCR, Pillow, Torch, etc.

---

## 🚀 Installation & Setup

1. **Clone the repository**

```bash
git clone https://github.com/santosh6672/nutriscan-AI.git
cd nutriscan-AI
Create and activate a virtual environment

bash
Copy code
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
Install dependencies

bash
Copy code
pip install -r requirements.txt
Configure environment variables

Create a .env file in the project root with the following:

env
Copy code
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
HF_TOKEN=your-huggingface-token
Note: Replace your-secret-key with a long, random string (use Django’s get_random_secret_key() function). Replace your-huggingface-token with your Hugging Face API token.

Run database migrations

bash
Copy code
python manage.py migrate
Collect static files

bash
Copy code
python manage.py collectstatic
Run the development server

bash
Copy code
python manage.py runserver
Open your browser at http://127.0.0.1:8000 to view NutriScan AI.
