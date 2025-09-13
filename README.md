# DublinMap - Property Scraper & Dashboard

A comprehensive property scraping and mapping solution for Dublin, Ireland, featuring a Python backend scraper and Next.js frontend dashboard.

## 🏗️ Project Structure

```
DublinMap/
├── Backend/           # Python API and scraper
│   ├── api/          # FastAPI endpoints
│   ├── core/         # Core scraping logic
│   ├── tests/        # Test suite
│   └── validation/   # Data validation
└── Frontend/         # Next.js dashboard
    └── my-app/       # React application
```

## 🚀 Features

### Backend
- **Daft.ie Scraper**: Automated property data extraction
- **Pagination Support**: Handles large datasets efficiently
- **REST API**: FastAPI-based endpoints for data access
- **Data Validation**: Robust input validation and error handling
- **Supabase Integration**: Database storage and management

### Frontend
- **Interactive Map**: Property visualization with Mapbox
- **Property Cards**: Detailed property information display
- **Filtering System**: Advanced search and filter capabilities
- **Responsive Design**: Modern UI with Tailwind CSS

## 🛠️ Quick Start

### Backend Setup
```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python run_api.py
```

### Frontend Setup
```bash
cd Frontend/my-app
npm install
npm run dev
```

## 📊 Data Sources

- **Daft.ie**: Ireland's leading property website
- **Property Types**: Sales and rental properties
- **Coverage**: Dublin and surrounding areas

## 🔧 Technology Stack

- **Backend**: Python, FastAPI, Supabase
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Mapping**: Mapbox GL JS
- **Database**: Supabase (PostgreSQL)

## 📝 License

MIT License - feel free to use for your projects.

---

*From a simple scraper to a full dashboard with interactive mapping capabilities.*
