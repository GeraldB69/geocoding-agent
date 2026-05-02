import requests

# Adresse de test (matérielle, comme demandé)
ADRESSE = "1 rue de la Paix, Paris"

def geocoder(adresse):
    """Interroge l'API Nominatim et retourne le premier résultat."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": adresse,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "MonAgentRechercheAdresse/1.0"
    }

    try:
        reponse = requests.get(url, params=params, headers=headers, timeout=10)
        reponse.raise_for_status()
        donnees = reponse.json()
        return donnees[0] if donnees else None
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'appel à l'API : {e}")
        return None

def main():
    print(f"Recherche de : {ADRESSE}")
    resultat = geocoder(ADRESSE)

    if resultat:
        print("Adresse trouvée :")
        print(f"  Affichage complet : {resultat.get('display_name')}")
        print(f"  Latitude  : {resultat['lat']}")
        print(f"  Longitude : {resultat['lon']}")
    else:
        print("Aucun résultat.")

if __name__ == "__main__":
    main()
