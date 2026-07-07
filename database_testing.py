from database_classes import TEM_lamella
import datetime

lam1 = TEM_lamella(
    grid_material='Copper',
    sample_id='123456',
    entry_created_date=datetime.datetime.now(),
    notes='This is a test lamella.'
)

print(lam1)
