# Glowall - Tiles & Marble Catalog

A modern, production-ready web application for a Tiles and Marble showroom catalog where customers can browse products and admins can manage the catalog.

## Features

### Customer Panel (Public Catalog)
- Modern showroom-style homepage with hero section
- Product catalog with filtering and search
- Category-based navigation
- Product detail pages with image gallery
- Gallery view for all products
- About and Contact pages
- Responsive design for mobile and desktop

### Admin Panel (Custom Dashboard)
- Secure admin authentication
- Dashboard with statistics overview
- Product management (CRUD operations)
- Category management with hierarchy support
- Color management
- Contact message management
- Multiple image upload support

## Tech Stack

- **Backend**: Django 5.0 (Python 3.11)
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Containerization**: Docker, Docker Compose
- **Web Server**: Gunicorn + Nginx

## Project Structure

```
tiles_catalog/
├── catalog/              # Main catalog app
│   ├── models.py         # Product, Category, etc.
│   ├── views.py          # Customer-facing views
│   ├── urls.py           # URL routing
│   └── forms.py          # Forms
├── admin_panel/          # Admin dashboard app
│   ├── views.py          # Admin views
│   ├── urls.py           # Admin URLs
│   └── forms.py          # Admin forms
├── accounts/             # Authentication app
├── tiles_catalog/        # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── templates/            # HTML templates
│   ├── base/             # Base templates
│   ├── catalog/          # Catalog templates
│   └── admin_panel/      # Admin templates
├── static/               # Static files
│   ├── css/
│   └── js/
├── media/                # Uploaded media files
├── docker/               # Docker configuration
│   └── nginx.conf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

## Installation

### Local Development (without Docker)

1. **Clone the repository**
   ```bash
   cd tiles_catalog
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Customer site: http://localhost:8000
   - Admin panel: http://localhost:8000/admin/
   - Django admin: http://localhost:8000/django-admin/

### Docker Deployment

1. **Build and run containers**
   ```bash
   docker-compose up -d --build
   ```

2. **Create superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

3. **Access the application**
   - Customer site: http://localhost:8000
   - Admin panel: http://localhost:8000/admin/

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
DJANGO_SECRET_KEY=your-super-secret-key-change-this-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Static Files

Static files are served via Whitenoise in development and Nginx in production.

```bash
python manage.py collectstatic
```

### Media Files

Uploaded product images are stored in `/media/products/`. In Docker deployment, this is a persistent volume.

## Usage

### Admin Panel

1. Navigate to `/admin/login/`
2. Login with your superuser credentials
3. Manage products, categories, and other data

### Adding Products

1. Go to Admin Panel → Products → Add Product
2. Fill in product details:
   - Name, Category
   - Weight, Color
   - Description
   - Price (optional)
   - Multiple product images

### Managing Categories

Categories support hierarchy (parent-child relationships):
- Tiles
  - Floor Tiles
  - Wall Tiles
  - Bathroom Tiles
  - Kitchen Tiles
- Marble
  - Italian Marble
  - Indian Marble
- Granite
- Natural Stone

## API Endpoints

- `GET /api/products/` - List products (JSON)
- `GET /api/search/?q=query` - Search products

## Production Deployment

1. Set `DJANGO_DEBUG=False` in `.env`
2. Use a strong `DJANGO_SECRET_KEY`
3. Configure proper `DJANGO_ALLOWED_HOSTS`
4. Set up SSL/TLS certificates
5. Configure email backend for notifications
6. Set up regular database backups

## License

This project is licensed under the MIT License.

## Support

For support or inquiries, contact: info@glowall.com
