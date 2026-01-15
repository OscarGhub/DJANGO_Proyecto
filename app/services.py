import requests
from .models import Character


# Mapeo para coger solo los datos necesarios de los personajes de la API
def sync_simpsons_characters():
    url = "https://thesimpsonsapi.com/api/characters"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        personajes_api = data.get('results', [])

        for item in personajes_api:
            Character.objects.using('mongodb').update_or_create(
                code=item['id'],
                defaults={
                    'name': item['name'],
                    'description': f"Occupation: {item.get('occupation', 'N/A')} - Status: {item.get('status', 'N/A')}",
                    'image': item.get('portrait_path', '')
                }
            )
        return True
    return False