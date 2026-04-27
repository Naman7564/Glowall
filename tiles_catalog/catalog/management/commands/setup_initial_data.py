from django.core.management.base import BaseCommand
from catalog.models import Category


class Command(BaseCommand):
    help = 'Set up initial data for the Tiles & Marble catalog'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
                
        # Create Categories
        categories_data = {
            'Tiles': 'Premium tiles collection for your spaces',
            'Floor Tiles': 'Durable floor tiles for residential and commercial use',
            'Wall Tiles': 'Decorative wall tiles for interior accents',
            'Bathroom Tiles': 'Water-resistant tiles designed for bathrooms',
            'Kitchen Tiles': 'Stylish and practical tiles for kitchen surfaces',
            'Vitrified Tiles': 'Low-porosity vitrified tile collection',
            'Marble': 'Premium marble collection for elegant interiors',
            'Italian Marble': 'Imported Italian marble collection',
            'Indian Marble': 'Quality Indian marble collection',
            'Granite': 'Premium granite collection for high-traffic areas',
            'Natural Stone': 'Natural stone collection for timeless spaces',
            'Sandstone': 'Textured sandstone products for indoor and outdoor use',
            'Limestone': 'Classic limestone options for refined spaces',
            'Slate': 'Slate collection with rich texture and depth',
        }

        for category_name, description in categories_data.items():
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        self.stdout.write(self.style.SUCCESS('\nInitial data setup complete!'))
        self.stdout.write('You can now:')
        self.stdout.write('  1. Create a superuser: python manage.py createsuperuser')
        self.stdout.write('  2. Access admin panel at: /admin/')
        self.stdout.write('  3. Add products through the admin dashboard')
