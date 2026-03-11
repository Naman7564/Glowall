from django.core.management.base import BaseCommand
from catalog.models import Category, MaterialType, Finish, Color


class Command(BaseCommand):
    help = 'Set up initial data for the Tiles & Marble catalog'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create Material Types
        materials = ['Tile', 'Marble', 'Granite', 'Natural Stone', 'Vitrified']
        for name in materials:
            material, created = MaterialType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created material type: {name}'))
        
        # Create Finishes
        finishes = ['Glossy', 'Matte', 'Polished', 'Honed', 'Textured', 'Satin']
        for name in finishes:
            finish, created = Finish.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created finish: {name}'))
        
        # Create Colors
        colors = [
            ('White', '#FFFFFF'),
            ('Black', '#000000'),
            ('Grey', '#808080'),
            ('Beige', '#F5F5DC'),
            ('Brown', '#8B4513'),
            ('Cream', '#FFFDD0'),
            ('Blue', '#0000FF'),
            ('Green', '#008000'),
            ('Red', '#FF0000'),
            ('Gold', '#FFD700'),
        ]
        for name, hex_code in colors:
            color, created = Color.objects.get_or_create(name=name, defaults={'hex_code': hex_code})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created color: {name}'))
        
        # Create Categories
        categories_data = {
            'Tiles': ['Floor Tiles', 'Wall Tiles', 'Bathroom Tiles', 'Kitchen Tiles', 'Vitrified Tiles'],
            'Marble': ['Italian Marble', 'Indian Marble'],
            'Granite': [],
            'Natural Stone': ['Sandstone', 'Limestone', 'Slate'],
        }
        
        for parent_name, children in categories_data.items():
            parent, created = Category.objects.get_or_create(
                name=parent_name,
                defaults={'description': f'Premium {parent_name.lower()} collection for your spaces'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {parent_name}'))
            
            for child_name in children:
                child, created = Category.objects.get_or_create(
                    name=child_name,
                    defaults={
                        'parent': parent,
                        'description': f'{child_name} from our {parent_name} collection'
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created subcategory: {child_name}'))
        
        self.stdout.write(self.style.SUCCESS('\nInitial data setup complete!'))
        self.stdout.write('You can now:')
        self.stdout.write('  1. Create a superuser: python manage.py createsuperuser')
        self.stdout.write('  2. Access admin panel at: /admin/')
        self.stdout.write('  3. Add products through the admin dashboard')
