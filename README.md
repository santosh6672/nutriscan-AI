# 🥗 NutriScan AI - Intelligent Nutrition Analysis

NutriScan AI is an intelligent web application that uses computer vision and AI to analyze food products and provide detailed nutritional insights. Simply scan food items to get instant nutritional information, health scores, and AI-powered descriptions.

![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![AI](https://img.shields.io/badge/AI-Powered-FF6B6B)
---

## 🌟 Key Features

- **Barcode Detection**: Utilizes **YOLOv5** and **PyZbar** to detect and decode barcodes from uploaded images.  
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
    ```

2. **Create and activate a virtual environment**

    ```bash
    python -m venv venv

    # Windows
    venv\Scripts\activate

    # macOS/Linux
    source venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment variables**

    Create a `.env` file in the project root with the following:

    ```env
    DJANGO_SECRET_KEY=your-secret-key
    DEBUG=True
    DATABASE_URL=sqlite:///db.sqlite3
    HF_TOKEN=your-huggingface-token
    ```

    > **Note**: Replace `your-secret-key` with a long, random string (use Django’s `get_random_secret_key()` function). Replace `your-huggingface-token` with your Hugging Face API token.

5. **Run database migrations**

    ```bash
    python manage.py migrate
    ```

6. **Collect static files**

    ```bash
    python manage.py collectstatic
    ```

7. **Run the development server**

    ```bash
    python manage.py runserver
    ```

    Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000) to view NutriScan AI.
